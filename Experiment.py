import streamlit as st
from PACA_utils import create_paca_agent, simulate_conversation, save_ai_conversation_to_firebase
from SP_utils import create_conversational_agent, load_from_firebase, get_diag_from_given_information, load_prompt_and_get_version
from firebase_config import get_firebase_ref

# PRESET
profile_version = 5.0
beh_dir_version = 5.0
con_agent_version = 5.0
paca_version = 1.0

instructions = """
    지시사항...
    """


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

    st.write(instructions, unsafe_allow_html=True)

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
        else:
            st.error("Failed to load SP system prompt.")
            st.stop()

        # Create PACA agent
        paca_agent, paca_memory, actual_paca_version = create_paca_agent(
            paca_version)
        if not paca_agent:
            st.stop()

        st.success("Both SP and PACA agents loaded successfully.")

        # Initialize conversation
        if 'conversation' not in st.session_state:
            st.session_state.conversation = []

        # Button to generate next turn
        if st.button("Generate Next Turn"):
            if not st.session_state.conversation:
                initial_prompt = "Hello, I'm Dr.Kim. What brings you here today?"
                conversation_generator = simulate_conversation(
                    paca_agent, sp_agent, initial_prompt)
                st.session_state.conversation_generator = conversation_generator

            try:
                next_turn = next(st.session_state.conversation_generator)
                st.session_state.conversation.append(next_turn)
            except StopIteration:
                st.warning("The conversation has reached its maximum length.")

            st.experimental_rerun()

        # Display the conversation
        for speaker, message in st.session_state.conversation:
            with st.chat_message(speaker):
                st.write(message)

        # Save conversation button
        if st.button("Save Conversation"):
            conversation_id = save_ai_conversation_to_firebase(
                firebase_ref,
                client_number,
                st.session_state.conversation,  # 변경된 부분
                actual_paca_version,
                actual_con_agent_version
            )
            st.success(f"Conversation saved with ID: {conversation_id}")

    else:
        st.error(
            "Failed to load client data. Please check if the data exists for the specified versions.")
