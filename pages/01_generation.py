import streamlit as st
from Home import check_password
from firebase_config import get_firebase_ref
from SP_utils import *

st.set_page_config(
    page_title="Simulation",
    page_icon="🔥",
)

instructions = """
    1. Setting 을 조정해주세요.

    * 정식 실험용 Client number는 2001번부터 진행해주세요.
    * 연습 테스트용 Client number는 1001번부터 진행해주세요.
    * 이미 존재하는 Client number&Version로 Create new data -> Generate하면 이미 존재하는 데이터를 Load 해옵니다.

    2. 원하는 Patient Information을 입력해주세요.

    * 미리 세팅되어 있는 값은 40/Female/South Korea/MDD 입니다.
    * 변경 가능합니다.

    3. Generate 버튼을 눌러주세요.

    4. 생성이 완료되면 대화를 시작하세요.

    5. 대화가 끝나면 End/Save로 대화를 저장하세요.

    6. 저장된 대화내역 / Profile / History / Beh-Direction은 Viewer 페이지에서 확인할 수 있습니다.
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
    if not check_password():
        st.stop()

    st.title("Client-Simulation")

    st.write(instructions, unsafe_allow_html=True)

    st.sidebar.header("Settings")
    new_client_number = st.sidebar.number_input(
        "Client Number", min_value=1, value=1)

    if 'client_number' not in st.session_state or st.session_state.client_number != new_client_number:
        st.session_state.client_number = new_client_number
        st.session_state.agent_and_memory = None

    action = st.sidebar.radio(
        "Choose action", ["Create new data", "Load existing data"])

    if action == "Load existing data":
        profile_version = st.sidebar.number_input(
            "Profile Version : profile_form=profile-maker=history-maker", min_value=1.0, value=5.0, step=0.1, format="%.1f")
        con_agent_version = st.sidebar.number_input(
            "Con-agent System Prompt Version", min_value=1.0, value=5.0, step=0.1, format="%.1f")
        beh_dir_version = st.sidebar.number_input(
            "beh_dir Version", min_value=1.0, value=5.0, step=0.1, format="%.1f")

        if st.sidebar.button("Load Data", key="load_data_button"):
            success = load_existing_client_data(
                st.session_state.client_number, profile_version, beh_dir_version)
            con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
                "con-agent", con_agent_version)
            if success:
                st.sidebar.success(
                    f"Loaded existing data for Client {st.session_state.client_number}")

                st.session_state.agent_and_memory = create_conversational_agent(
                    format_version(profile_version), format_version(
                        beh_dir_version), st.session_state.client_number, con_agent_system_prompt
                )

                st.success(
                    f"Profile version {format_version(profile_version)} successfully loaded")
                st.success(
                    f"Beh-dir version {format_version(beh_dir_version)} successfully loaded")
                st.success(
                    f"Con-agent version {format_version(con_agent_version)} successfully loaded")
            else:
                st.sidebar.error("Failed to load existing data.")
    else:  # Create new data
        st.sidebar.subheader("Version Settings")
        profile_version = st.sidebar.number_input(
            "Profile Version", min_value=1.0, value=5.0, step=0.1, format="%.1f")
        beh_dir_version = st.sidebar.number_input(
            "Beh-dir-maker Version", min_value=1.0, value=5.0, step=0.1, format="%.1f")
        con_agent_version = st.sidebar.number_input(
            "Con-agent Version", min_value=1.0, value=5.0, step=0.1, format="%.1f")

        # Load prompts based on versions
        profile_system_prompt, actual_profile_version = load_prompt_and_get_version(
            "profile-maker", profile_version)
        history_system_prompt, actual_history_version = load_prompt_and_get_version(
            "history-maker", profile_version)
        con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
            "con-agent", con_agent_version)
        beh_dir_system_prompt, actual_beh_dir_version = load_prompt_and_get_version(
            "beh-dir-maker", beh_dir_version)

        st.sidebar.subheader("Patient Information")
        age = st.sidebar.number_input(
            "Age", min_value=0, max_value=120, value=40)
        gender = st.sidebar.selectbox("Gender", ["Female", "Male", "Other"])
        nationality = st.sidebar.text_input("Nationality", "South Korea")
        diagnosis = st.sidebar.text_input(
            "Diagnosis", "Major depressive disorder")

        given_information = f"""
        <Given information>
        Diagnosis : {diagnosis}
        Age : {age}
        Sex : {gender}
        Nationality: {nationality}
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

            filename = save_conversation_to_firebase(
                firebase_ref,
                st.session_state.client_number,
                memory.chat_memory.messages,
                con_agent_version  # Pass the version number directly
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
