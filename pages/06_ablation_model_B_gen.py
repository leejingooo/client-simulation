import streamlit as st
from firebase_config import get_firebase_ref
from SP_utils import *

st.set_page_config(
    page_title="Ablation - Model B - Disorder-based Approach Deletion",
    page_icon="🔥",
)

CLIENT_NUMBER = 8882
profile_version = 5.8
beh_dir_version = 5.8
con_agent_version = 5.8


instructions = """
    Model B Ablation위한 Generator
"""

# Initialize Firebase
firebase_ref = get_firebase_ref()
if firebase_ref is None:
    st.error(
        "Firebase initialization failed. Please check your configuration and try again.")
    st.stop()
else:
    st.success("Firebase initialized successfully")


def load_existing_client_data(client_number, profile_version, beh_dir_version):
    profile_version_formatted = f"{profile_version:.1f}".replace(".", "_")
    beh_dir_version_formatted = f"{beh_dir_version:.1f}".replace(".", "_")

    profile = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version_formatted}")
    history = load_from_firebase(
        firebase_ref, client_number, f"history_version{profile_version_formatted}")
    beh_dir = load_from_firebase(
        firebase_ref, client_number, f"beh_dir_version{beh_dir_version_formatted}")

    if all([profile, history, beh_dir]):
        st.session_state.profile = profile
        st.session_state.history = history
        st.session_state.beh_dir = beh_dir
        return True
    else:
        st.error(
            f"Could not find existing client data or the specified prompt versions.")
        return False


def main():

    st.title("Ablation - Model B - Disorder-based Approach Deletion")

    st.write(instructions, unsafe_allow_html=True)

    st.sidebar.header("Settings")
    new_client_number = CLIENT_NUMBER

    if 'client_number' not in st.session_state or st.session_state.client_number != new_client_number:
        st.session_state.client_number = new_client_number
        st.session_state.agent_and_memory = None

    action = st.sidebar.radio(
        "Choose action", ["Create new data", "Load existing data"])

    # Load prompts based on versions
    profile_system_prompt, actual_profile_version = load_prompt_and_get_version(
        "profile-maker", profile_version)
    history_system_prompt, actual_history_version = load_prompt_and_get_version(
        "history-maker", profile_version)
    con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
        "con-agent", con_agent_version)
    beh_dir_system_prompt, actual_beh_dir_version = load_prompt_and_get_version(
        "beh-dir-maker", beh_dir_version)

    given_information = f"""
        <Given information>
        Diagnosis : Major depressive disorder
        Age : 40
        Sex : Female
        Nationality: South Korea
        </Given information>
        """

    if st.sidebar.button("Generate Profile, History, and Behavioral Direction", key="generate_all_button"):
        if check_client_exists(firebase_ref, st.session_state.client_number):
            st.error(
                f"Client {st.session_state.client_number} already exists. Please choose a different client number.")
        elif all([profile_system_prompt, history_system_prompt, con_agent_system_prompt, beh_dir_system_prompt]):
            with st.spinner(""):
                save_to_firebase(
                    firebase_ref, st.session_state.client_number, "given_information", given_information)

                profile = profile_maker(format_version(
                    profile_version), given_information, st.session_state.client_number, profile_system_prompt)
                if profile is not None:
                    st.session_state.profile = profile

                    with st.spinner(""):
                        history = history_maker(format_version(
                            profile_version), st.session_state.client_number, history_system_prompt)
                        if history is not None:
                            st.session_state.history = history

                            with st.spinner(""):
                                beh_dir = beh_dir_maker(format_version(profile_version), format_version(
                                    beh_dir_version), st.session_state.client_number, beh_dir_system_prompt, given_information)
                                if beh_dir is not None:
                                    st.session_state.beh_dir = beh_dir

                                    st.session_state.agent_and_memory = create_conversational_agent(
                                        format_version(profile_version), format_version(
                                            beh_dir_version),
                                        st.session_state.client_number, con_agent_system_prompt
                                    )
                                else:
                                    st.error(
                                        "Failed to generate behavioral direction.")
                        else:
                            st.error("Failed to generate history.")
                else:
                    st.error(
                        "Failed to generate profile. Please check the error messages above.")
        else:
            st.error(
                "Failed to load one or more prompts. Please check the version settings.")

    # Main area for conversation
    st.header("Conversation with Simulated Client")

    if 'agent_and_memory' in st.session_state and st.session_state.agent_and_memory:
        agent, memory = st.session_state.agent_and_memory
        for message in memory.chat_memory.messages:
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
        st.warning(
            "Please load existing data or generate a new profile and history.")

    if st.button("Start New Conversation"):
        if 'agent_and_memory' in st.session_state and st.session_state.agent_and_memory:
            # Reset the memory of the existing agent
            agent, memory = st.session_state.agent_and_memory
            memory.chat_memory.clear()
            st.success("New conversation started with the same client data.")
            st.rerun()
        else:
            st.error(
                "Please load client data first before starting a new conversation.")

    if st.button("End/Save Conversation", key="end_save_conversation_button"):
        if st.session_state.client_number is not None and 'agent_and_memory' in st.session_state and st.session_state.agent_and_memory is not None:
            _, memory = st.session_state.agent_and_memory

            participant_name = st.session_state['name']
            filename = save_conversation_to_firebase(
                firebase_ref,
                st.session_state.client_number,
                memory.chat_memory.messages,
                con_agent_version,
                participant_name  # Pass the version number directly
            )
            if filename:
                st.success(
                    f"Conversation saved to Firebase for Client {st.session_state.client_number}!")
            else:
                st.error("Failed to save conversation.")
        else:
            st.error(
                "Unable to save conversation. Client number is not set or no conversation has taken place.")


if __name__ == "__main__":
    main()
