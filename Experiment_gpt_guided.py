import streamlit as st
from PACA_gpt_guided_utils import create_paca_agent, simulate_conversation, save_ai_conversation_to_firebase, save_conversation_to_csv
from SP_utils import create_conversational_agent, load_from_firebase, get_diag_from_given_information, load_prompt_and_get_version
from firebase_config import get_firebase_ref
# from langchain.schema import HumanMessage, AIMessage
import time
from SP_utils import create_conversational_agent, save_to_firebase

# PRESET
profile_version = 6.0
beh_dir_version = 6.0
con_agent_version = 6.0
paca_version = 3.0


def construct_generator_conversation(paca_agent, paca_memory):
    constructs = [
        ("Chief complaint", "Describe in the patient's words"),
        ("Symptom name", ""),
        ("Alleviating factors", ""),
        ("Exacerbating factors", ""),
        ("Symptom duration", "Unit: week"),
        ("Triggering factors", "The reason patient came to the hospital at this time"),
        ("Stressors", "multiple answers available: home/work/school/legal issue/medical comorbidity/interpersonal difficulty/null"),
        ("Family history-diagnosis", "Describe a psychiatric family history"),
        ("Family history-substance use",
         "Describe a family history of substance use (alcohol, opioid, cannabinoid, hallucinogen, stimulant, narcotic, etc.)"),
        ("Current family structure", ""),
        ("Suicidal ideation", "candidate: high/moderate/low"),
        ("Suicidal plan", "candidate: presence/absence"),
        ("Suicidal attempt", "candidate: presence/absence"),
        ("Self-harming behavior risk", "candidate: high/moderate/low"),
        ("Homicide risk", "candidate: high/moderate/low"),
        ("Mood", "candidate: euphoric/elated/euthymic/dysphoric/depressed/irritable"),
        ("Affect", "candidate: broad/restricted/blunt/flat/labile/anxious/tense/shallow/inadequate/inappropriate"),
        ("Verbal productivity", "candidate: increased/moderate/decreased"),
        ("Insight", "candidate: Complete denial of illness/Slight awareness of being sick and needing help, but denying it at the same time/Awareness of being sick but blaming it on others, external events/Intellectual insight/True emotional insight"),
        ("Perception", "candidate: Normal/Illusion/Auditory hallucination/Visual hallucination/Olfactory hallucination/Gustatory hallucination/Depersonalization/Derealization/Déjà vu/Jamais vu"),
        ("Thought process", "candidate: Normal/Loosening of association/flight of idea/circumstantiality/tangentiality/Word salad or incoherence/Neologism/Illogical/Irrelevant"),
        ("Thought content", "candidate: Normal/preoccupation/overvalued idea/idea of reference/grandiosity, obsession/compulsion/rumination/delusion/phobia"),
        ("Spontaneity", "candidate: (+)/(-)"),
        ("Social judgment", "candidate: Normal/Impaired"),
        ("Reliability", "candidate: Yes/No")
    ]

    filled_constructs = {}

    for construct, guide in constructs:
        question = f"""Based on your psychiatric interview and the entire conversation history, what is the patient's {construct}? Please provide a concise answer, referencing the following guideline if applicable: {guide}. For example, if the mood is depressed, DO NOT say "The patient's mood is depressed", but just answer "depressed" as if it were a given candidate. In other words, except for unavoidable cases like "Chief complaint", DO NOT answer in sentence form, but in SHORT-ANSWER form. If you're uncertain, simply state "I don't know". Use English."""
        paca_response = paca_agent(question)

        if "i don't know" in paca_response.lower() or "uncertain" in paca_response.lower():
            filled_constructs[construct] = "N/A"
        else:
            filled_constructs[construct] = paca_response.strip()

    return filled_constructs


def experiment_page(client_number):
    st.set_page_config(
        page_title=f"AI-to-AI Experiment - Client {client_number}",
        page_icon="🤖",
    )

    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error(
            "Firebase initialization failed. Please check your configuration and try again.")
        st.stop()

    st.title(f"AI-to-AI Conversation Experiment - Client {client_number}")

    # Load SP data
    profile = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version:.1f}".replace(".", "_"))
    history = load_from_firebase(
        firebase_ref, client_number, f"history_version{profile_version:.1f}".replace(".", "_"))
    beh_dir = load_from_firebase(
        firebase_ref, client_number, f"beh_dir_version{beh_dir_version:.1f}".replace(".", "_"))
    given_information = load_from_firebase(
        firebase_ref, client_number, "given_information")

    if all([profile, history, beh_dir, given_information]):
        diag = get_diag_from_given_information(given_information)

        # Create SP agent
        if diag == "BD":
            con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
                "con-agent", con_agent_version, diag)
            st.success("BD success")
        else:
            con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
                "con-agent", con_agent_version)

        if con_agent_system_prompt:
            sp_agent, sp_memory = create_conversational_agent(
                f"{profile_version:.1f}".replace(".", "_"),
                f"{beh_dir_version:.1f}".replace(".", "_"),
                client_number,
                con_agent_system_prompt
            )
            # Store SP memory in session state to maintain state across reruns
            if 'sp_memory' not in st.session_state:
                st.session_state.sp_memory = sp_memory
        else:
            st.error("Failed to load SP system prompt.")
            st.stop()

        # Create PACA agent
        if 'paca_agent' not in st.session_state or st.session_state.get('force_paca_update', False):
            st.session_state.paca_agent, st.session_state.paca_memory, actual_paca_version = create_paca_agent(
                paca_version)
        else:
            actual_paca_version = paca_version

        paca_agent = st.session_state.paca_agent
        paca_memory = st.session_state.paca_memory

        st.success("SP and PACA agents loaded successfully.")

        # Initialize session state
        if 'conversation' not in st.session_state:
            st.session_state.conversation = []
        if 'conversation_generator' not in st.session_state:
            st.session_state.conversation_generator = simulate_conversation(
                paca_agent, sp_agent)
            # Add the initial greeting to PACA's memory
            paca_memory.add_ai_message("안녕하세요, 저는 정신과 의사 김민수입니다. 이름이 어떻게 되시나요?")
            # SP needs to understand the initial message from PACA
            st.session_state.sp_memory.add_user_message("안녕하세요, 저는 정신과 의사 김민수입니다. 이름이 어떻게 되시나요?")
        if 'constructs' not in st.session_state:
            st.session_state.constructs = None

        # Conversation area
        conversation_area = st.empty()

        # Button to generate conversation
        if st.sidebar.button("Generate Conversation"):
            while True:
                try:
                    next_turn = next(st.session_state.conversation_generator)
                    st.session_state.conversation.append(next_turn)

                    # Update conversation display
                    with conversation_area.container():
                        for speaker, message in st.session_state.conversation:
                            with st.chat_message(speaker):
                                st.write(message)

                except StopIteration:
                    break

                # Add a small delay to allow for visual updates
                time.sleep(0.1)

        # Button to stop conversation and generate constructs
        if st.sidebar.button("Stop and Generate Constructs"):
            if st.session_state.constructs is None:
                with st.spinner("Generating constructs..."):
                    st.session_state.constructs = construct_generator_conversation(
                        paca_agent, paca_memory)
                st.success("Constructs generated!")
            st.rerun()

        # Display the conversation
        with conversation_area.container():
            for speaker, message in st.session_state.conversation:
                with st.chat_message(speaker):
                    st.write(message)

        # Display constructs if they have been generated
        if st.session_state.constructs:
            st.subheader("Construct Generator Output")
            for construct, value in st.session_state.constructs.items():
                st.write(f"{construct}: {value}")

        # Save conversation button
        if st.button("Save Conversation and Constructs"):
            conversation_id = save_ai_conversation_to_firebase(
                firebase_ref,
                client_number,
                st.session_state.conversation,
                actual_paca_version,
                actual_con_agent_version
            )

            if st.session_state.constructs:
                save_to_firebase(firebase_ref, client_number,
                                 f"constructs_{conversation_id}", st.session_state.constructs)

            st.success(
                f"Conversation and constructs saved with ID: {conversation_id}")

        if st.session_state.conversation:
            csv_data = save_conversation_to_csv(st.session_state.conversation)
            st.download_button(
                label="Download Conversation as CSV",
                data=csv_data,
                file_name="conversation.csv",
                mime="text/csv"
            )

    else:
        st.error(
            "Failed to load client data. Please check if the data exists for the specified versions.")

# import streamlit as st
# from PACA_utils import create_paca_agent, simulate_conversation, save_ai_conversation_to_firebase, save_conversation_to_csv
# from SP_utils import create_conversational_agent, load_from_firebase, get_diag_from_given_information, load_prompt_and_get_version
# from firebase_config import get_firebase_ref

# # PRESET
# profile_version = 5.0
# beh_dir_version = 5.0
# con_agent_version = 5.0
# # given_form_version = paca_version = 3.0
# paca_version = 3.0

# instructions = """
#     지시사항...
#     """


# def experiment_page(client_number):
#     st.set_page_config(
#         page_title=f"AI-to-AI Experiment - Client {client_number}",
#         page_icon="🤖",
#     )

#     firebase_ref = get_firebase_ref()
#     if firebase_ref is None:
#         st.error(
#             "Firebase initialization failed. Please check your configuration and try again.")
#         st.stop()

#     st.title(f"AI-to-AI Conversation Experiment - Client {client_number}")

#     st.write(instructions, unsafe_allow_html=True)

#     # Load SP data
#     profile = load_from_firebase(
#         firebase_ref, client_number, f"profile_version{profile_version:.1f}".replace(".", "_"))
#     history = load_from_firebase(
#         firebase_ref, client_number, f"history_version{profile_version:.1f}".replace(".", "_"))
#     beh_dir = load_from_firebase(
#         firebase_ref, client_number, f"beh_dir_version{beh_dir_version:.1f}".replace(".", "_"))
#     given_information = load_from_firebase(
#         firebase_ref, client_number, "given_information")

#     if all([profile, history, beh_dir, given_information]):
#         diag = get_diag_from_given_information(given_information)

#         # Create SP agent
#         if diag == "BD":
#             con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
#                 "con-agent", con_agent_version, diag)
#             st.success("BD success")
#         else:
#             con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
#                 "con-agent", con_agent_version)

#         if con_agent_system_prompt:
#             sp_agent, sp_memory = create_conversational_agent(
#                 f"{profile_version:.1f}".replace(".", "_"),
#                 f"{beh_dir_version:.1f}".replace(".", "_"),
#                 client_number,
#                 con_agent_system_prompt
#             )
#         else:
#             st.error("Failed to load SP system prompt.")
#             st.stop()

#         # Create PACA agent
#         paca_agent, paca_memory, actual_paca_version = create_paca_agent(
#             paca_version)
#         if not paca_agent:
#             st.stop()

#         st.success("Both SP and PACA agents loaded successfully.")

#         # Initialize session state for conversation and generator
#         if 'conversation' not in st.session_state:
#             st.session_state.conversation = []
#         if 'conversation_generator' not in st.session_state:
#             st.session_state.conversation_generator = simulate_conversation(
#                 paca_agent, sp_agent)

#         # Button to generate next turn
#         if st.button("Generate Next Turn"):
#             if not st.session_state.conversation:
#                 conversation_generator = simulate_conversation(
#                     paca_agent, sp_agent)
#                 st.session_state.conversation_generator = conversation_generator

#             try:
#                 next_turn = next(st.session_state.conversation_generator)
#                 st.session_state.conversation.append(next_turn)
#             except StopIteration:
#                 st.warning("The conversation has reached its maximum length.")

#             st.rerun()

#         # Display the conversation
#         for speaker, message in st.session_state.conversation:
#             with st.chat_message(speaker):
#                 st.write(message)

#         # Save conversation button
#         if st.button("Save Conversation"):
#             conversation_id = save_ai_conversation_to_firebase(
#                 firebase_ref,
#                 client_number,
#                 st.session_state.conversation,
#                 actual_paca_version,
#                 actual_con_agent_version
#             )
#             st.success(f"Conversation saved with ID: {conversation_id}")

#         if st.session_state.conversation:
#             csv_data = save_conversation_to_csv(st.session_state.conversation)
#             st.download_button(
#                 label="Download Conversation as CSV",
#                 data=csv_data,
#                 file_name="conversation.csv",
#                 mime="text/csv"
#             )

#     else:
#         st.error(
#             "Failed to load client data. Please check if the data exists for the specified versions.")


# # import streamlit as st
# # from PACA_utils import create_paca_agent, simulate_conversation, save_ai_conversation_to_firebase
# # from SP_utils import create_conversational_agent, load_from_firebase, get_diag_from_given_information, load_prompt_and_get_version
# # from firebase_config import get_firebase_ref

# # # PRESET
# # profile_version = 5.0
# # beh_dir_version = 5.0
# # con_agent_version = 5.0
# # given_form_version = paca_version = 3.0

# # instructions = """
# #     지시사항...
# #     """


# # def experiment_page(client_number):
# #     st.set_page_config(
# #         page_title=f"AI-to-AI Experiment - Client {client_number}",
# #         page_icon="🤖",
# #     )

# #     firebase_ref = get_firebase_ref()
# #     if firebase_ref is None:
# #         st.error(
# #             "Firebase initialization failed. Please check your configuration and try again.")
# #         st.stop()

# #     st.title(f"AI-to-AI Conversation Experiment - Client {client_number}")

# #     st.write(instructions, unsafe_allow_html=True)

# #     # Load SP data
# #     profile = load_from_firebase(
# #         firebase_ref, client_number, f"profile_version{profile_version:.1f}".replace(".", "_"))
# #     history = load_from_firebase(
# #         firebase_ref, client_number, f"history_version{profile_version:.1f}".replace(".", "_"))
# #     beh_dir = load_from_firebase(
# #         firebase_ref, client_number, f"beh_dir_version{beh_dir_version:.1f}".replace(".", "_"))
# #     given_information = load_from_firebase(
# #         firebase_ref, client_number, "given_information")

# #     if all([profile, history, beh_dir, given_information]):
# #         diag = get_diag_from_given_information(given_information)

# #         # Create SP agent
# #         if diag == "BD":
# #             con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
# #                 "con-agent", con_agent_version, diag)
# #             st.success("BD success")
# #         else:
# #             con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
# #                 "con-agent", con_agent_version)

# #         if con_agent_system_prompt:
# #             sp_agent, sp_memory = create_conversational_agent(
# #                 f"{profile_version:.1f}".replace(".", "_"),
# #                 f"{beh_dir_version:.1f}".replace(".", "_"),
# #                 client_number,
# #                 con_agent_system_prompt
# #             )
# #         else:
# #             st.error("Failed to load SP system prompt.")
# #             st.stop()

# #         # Create PACA agent
# #         paca_agent, paca_memory, actual_paca_version = create_paca_agent(
# #             paca_version)
# #         if not paca_agent:
# #             st.stop()

# #         st.success("Both SP and PACA agents loaded successfully.")

# #         # Initialize session state for conversation and generator
# #         if 'conversation' not in st.session_state:
# #             st.session_state.conversation = []
# #         if 'conversation_generator' not in st.session_state:
# #             st.session_state.conversation_generator = simulate_conversation(
# #                 paca_agent, sp_agent)

# #         # Button to generate next turn
# #         if st.button("Generate Next Turn"):
# #             if not st.session_state.conversation:
# #                 conversation_generator = simulate_conversation(
# #                     paca_agent, sp_agent)
# #                 st.session_state.conversation_generator = conversation_generator

# #             try:
# #                 next_turn = next(st.session_state.conversation_generator)
# #                 st.session_state.conversation.append(next_turn)
# #             except StopIteration:
# #                 st.warning("The conversation has reached its maximum length.")

# #             st.rerun()

# #         # Display the conversation
# #         for speaker, message in st.session_state.conversation:
# #             with st.chat_message(speaker):
# #                 st.write(message)

# #         # Save conversation button
# #         if st.button("Save Conversation"):
# #             conversation_id = save_ai_conversation_to_firebase(
# #                 firebase_ref,
# #                 client_number,
# #                 st.session_state.conversation,  # 변경된 부분
# #                 actual_paca_version,
# #                 actual_con_agent_version
# #             )
# #             st.success(f"Conversation saved with ID: {conversation_id}")

# #     else:
# #         st.error(
# #             "Failed to load client data. Please check if the data exists for the specified versions.")
