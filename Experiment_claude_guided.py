import streamlit as st
from PACA_claude_guided_utils import create_paca_agent, simulate_conversation, save_ai_conversation_to_firebase, save_conversation_to_csv
from SP_utils import create_conversational_agent, load_from_firebase, get_diag_from_given_information, load_prompt_and_get_version
from firebase_config import get_firebase_ref
import time
from SP_utils import create_conversational_agent, save_to_firebase
try:
    from sp_construct_generator import create_sp_construct
except Exception:
    create_sp_construct = None

try:
    from paca_construct_generator import create_paca_construct
except Exception:
    create_paca_construct = None

# PRESET
profile_version = 6.0
beh_dir_version = 6.0
con_agent_version = 6.0
paca_version = 3.0


def check_experiment_number_exists(firebase_ref, client_number, exp_number):
    """
    Check if the experiment number is already used for this client.
    Only checks PACA construct and conversation log (SP construct can be created separately).
    Returns True if any of the expected keys exist.
    """
    keys_to_check = [
        f"construct_paca_{client_number}_{exp_number}",
        f"conversation_log_{client_number}_{exp_number}"
    ]
    
    for key in keys_to_check:
        data = load_from_firebase(firebase_ref, client_number, key)
        if data is not None:
            return True
    return False


def construct_generator_conversation_new(paca_agent):
    """
    Generate PACA construct using the new structured approach.
    This creates a construct with the same structure as SP construct.
    """
    if create_paca_construct is None:
        st.error("PACA construct generator not available (missing module 'paca_construct_generator').")
        return None
    
    try:
        with st.spinner("Generating PACA construct from conversation..."):
            paca_construct = create_paca_construct(paca_agent)
        return paca_construct
    except Exception as e:
        st.error(f"Failed to create PACA construct: {e}")
        return None


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
        
        # Display current agent type
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🤖 Current Agent")
        agent_type = st.session_state.get('agent_type', 'Unknown')
        st.sidebar.info(f"**Type:** {agent_type}")
        st.sidebar.info(f"**Client:** {client_number}")
        st.sidebar.markdown("---")
        
        # Experiment number input
        st.sidebar.markdown("### 📝 Experiment Number")
        exp_number = st.sidebar.text_input(
            "Enter experiment number:",
            key="exp_number_input",
            help="Enter a unique number for this experiment"
        )
        
        # Validate experiment number
        exp_number_valid = False
        if exp_number:
            if not exp_number.isdigit():
                st.sidebar.error("⚠️ Please enter a valid number")
            elif check_experiment_number_exists(firebase_ref, client_number, exp_number):
                st.sidebar.error(f"⚠️ Experiment number {exp_number} is already used. Please enter a different number.")
            else:
                st.sidebar.success(f"✅ Experiment number {exp_number} is available")
                exp_number_valid = True
        else:
            st.sidebar.info("Please enter an experiment number before saving")
        
        st.sidebar.markdown("---")

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
        if 'sp_construct' not in st.session_state:
            st.session_state.sp_construct = None

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
            # Generate PACA construct
            if st.session_state.constructs is None:
                st.session_state.constructs = construct_generator_conversation(
                        paca_agent, paca_memory)
                st.success("Constructs generated!")
            
            # Generate SP construct
            if create_sp_construct is not None:
                given_form_path = f"data/prompts/paca_system_prompt/given_form_version{paca_version}.json"
                try:
                    sp_construct = create_sp_construct(
                        client_number,
                        f"{profile_version:.1f}",
                        f"{beh_dir_version:.1f}",
                        given_form_path,
                    )
                    if sp_construct:
                        st.session_state.sp_construct = sp_construct
                        st.success("SP Construct generated!")
                except Exception as e:
                    st.error(f"Failed to create SP construct: {e}")
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
            if not exp_number_valid:
                st.error("⚠️ Please enter a valid and unique experiment number before saving.")
            else:
                # Save conversation with new naming convention
                conversation_data = [
                    {'speaker': speaker, 'message': message}
                    for speaker, message in st.session_state.conversation
                ]
                
                conversation_content = {
                    'paca_version': actual_paca_version,
                    'sp_version': actual_con_agent_version,
                    'timestamp': int(__import__('time').time()),
                    'data': conversation_data
                }
                
                conversation_key = f"conversation_log_{client_number}_{exp_number}"
                save_to_firebase(firebase_ref, client_number, conversation_key, conversation_content)
                
                saved_items = [f"- Conversation: {conversation_key}"]
                
                # Save PACA construct with new naming convention
                if st.session_state.constructs:
                    paca_construct_key = f"construct_paca_{client_number}_{exp_number}"
                    save_to_firebase(firebase_ref, client_number, paca_construct_key, st.session_state.constructs)
                    saved_items.append(f"- PACA Construct: {paca_construct_key}")
                
                # Save SP construct with new naming convention
                if st.session_state.sp_construct:
                    sp_construct_key = f"construct_sp_{client_number}_{exp_number}"
                    save_to_firebase(firebase_ref, client_number, sp_construct_key, st.session_state.sp_construct)
                    saved_items.append(f"- SP Construct: {sp_construct_key}")
                
                st.success(
                    f"✅ Conversation and constructs saved successfully!\n\n" + "\n".join(saved_items)
                )

        # Display SP construct if it has been generated
        if st.session_state.sp_construct:
            st.subheader("SP Construct Output")
            st.json(st.session_state.sp_construct)

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
