import streamlit as st
from Home import check_participant
from firebase_config import get_firebase_ref
from SP_utils import *


instructions = """
    연구에 참여해주셔서 감사드립니다.
    구글폼 페이지와 함께 진행해주세요.
    """


def validation_page(client_number, profile_version=5.0, beh_dir_version=5.0, con_agent_version=5.0):
    st.set_page_config(
        page_title="정신과 환자의 다면적 시뮬레이션",
        page_icon="🔬",
    )

    # Initialize Firebase
    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error(
            "Firebase initialization failed. Please check your configuration and try again.")
        st.stop()

    if not check_participant():
        st.stop()

    st.title("정신과 환자의 다면적 시뮬레이션")

    st.write(instructions, unsafe_allow_html=True)

    profile = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version:.1f}".replace(".", "_"))
    history = load_from_firebase(
        firebase_ref, client_number, f"history_version{profile_version:.1f}".replace(".", "_"))
    beh_dir = load_from_firebase(
        firebase_ref, client_number, f"beh_dir_version{beh_dir_version:.1f}".replace(".", "_"))

    if all([profile, history, beh_dir]):
        st.session_state.profile = profile
        st.session_state.history = history
        st.session_state.beh_dir = beh_dir

        given_information = load_from_firebase(
            firebase_ref, client_number, "given_information")
       # Get the diagnosis from the profile
        diag = get_diag_from_given_information(
            given_information)

        if diag == "BD":
            con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
                "con-agent", con_agent_version, diag)
        else:
            con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
                "con-agent", con_agent_version)

        if con_agent_system_prompt:
            st.session_state.agent_and_memory = create_conversational_agent(
                f"{profile_version:.1f}".replace(".", "_"),
                f"{beh_dir_version:.1f}".replace(".", "_"),
                client_number,
                con_agent_system_prompt
            )
            st.success(f"Start a conversation.")
        else:
            st.error("Failed to load conversational agent system prompt.")
    else:
        st.error(
            "Failed to load client data. Please check if the data exists for the specified versions.")

    st.header("Simulated Session")

    if 'agent_and_memory' in st.session_state and st.session_state.agent_and_memory:
        agent, memory = st.session_state.agent_and_memory
        for message in memory.messages:
            with st.chat_message("user" if isinstance(message, HumanMessage) else "assistant"):
                st.markdown(message.content)

        if prompt := st.chat_input("Interviewer:"):
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = agent(prompt)
                message_placeholder.markdown(full_response)
    else:
        st.warning("Please load client data first.")

    if st.button("Start New Conversation"):
        if 'agent_and_memory' in st.session_state and st.session_state.agent_and_memory:
            agent, memory = st.session_state.agent_and_memory
            memory.clear()
            st.success("New conversation started with the same client data.")
            st.rerun()
        else:
            st.error(
                "Please load client data first before starting a new conversation.")

    if st.button("End/Save Conversation"):
        if 'agent_and_memory' in st.session_state and st.session_state.agent_and_memory is not None:
            _, memory = st.session_state.agent_and_memory
            if 'name' in st.session_state and st.session_state['name_correct']:
                participant_name = st.session_state['name']
                filename = save_conversation_to_firebase(
                    firebase_ref,
                    client_number,
                    memory.messages,
                    con_agent_version,
                    participant_name
                )
                if filename:
                    st.success(
                        f"Conversation saved to Firebase for Client {client_number} by {participant_name}!")
                else:
                    st.error("Failed to save conversation.")
            else:
                st.error(
                    "Please ensure you've entered a valid name on the home page before saving.")
        else:
            st.error(
                "Unable to save conversation. No conversation has taken place.")
