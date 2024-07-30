import streamlit as st
import json
import time
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferMemory
from firebase_config import get_firebase_ref
from Home import check_password
from pages.simulation_deployed import (
    load_prompt_and_get_version,
    profile_maker,
    history_maker,
    beh_dir_maker,
    create_conversational_agent,
    save_conversation_to_firebase,
    FIXED_DATE
)

st.set_page_config(
    page_title="Blind Test (Test)",
    page_icon="🔬",
)

# Preset values (hidden from the user)
PRESET_CLIENT_NUMBER = 3001
PRESET_PROFILE_VERSION = 4.0
PRESET_BEH_DIR_VERSION = 4.0
PRESET_CON_AGENT_VERSION = 4.0
PRESET_AGE = 40
PRESET_GENDER = "Female"
PRESET_NATIONALITY = "South Korea"
PRESET_DIAGNOSIS = "Major Depressive Disorder"

# Initialize Firebase
firebase_ref = get_firebase_ref()
if firebase_ref is None:
    st.error(
        "Firebase initialization failed. Please check your configuration and try again.")
    st.stop()

# Initialize session state
if 'agent_and_memory' not in st.session_state:
    st.session_state.agent_and_memory = None
if 'test_completed' not in st.session_state:
    st.session_state.test_completed = False


def main():
    if not check_password():
        st.stop()

    st.title("Blind Test (1)")
    st.write("시뮬레이션 환자와 대화합니다. 한글로 대화해주세요.")

    if st.session_state.test_completed:
        st.warning(
            "This blind test has been completed. Thank you for participating.")
        return

    if st.session_state.agent_and_memory is None:
        if st.button("Start Blind Test"):
            with st.spinner("Preparing the simulated patient..."):
                setup_blind_test()
    else:
        display_conversation()

    if st.session_state.agent_and_memory and st.button("End Test"):
        end_test()


def setup_blind_test():
    profile_system_prompt, _ = load_prompt_and_get_version(
        "profile-maker", PRESET_PROFILE_VERSION)
    history_system_prompt, _ = load_prompt_and_get_version(
        "history-maker", PRESET_PROFILE_VERSION)
    beh_dir_system_prompt, _ = load_prompt_and_get_version(
        "beh-dir-maker", PRESET_BEH_DIR_VERSION)
    con_agent_system_prompt, _ = load_prompt_and_get_version(
        "con-agent", PRESET_CON_AGENT_VERSION)

    given_information = f"""
    <Given information>
    Age : {PRESET_AGE}
    Gender : {PRESET_GENDER}
    Nationality: {PRESET_NATIONALITY}
    Diagnosis : {PRESET_DIAGNOSIS}
    </Given information>
    """

    profile = profile_maker(PRESET_PROFILE_VERSION, given_information,
                            PRESET_CLIENT_NUMBER, profile_system_prompt)
    if profile is not None:
        history = history_maker(PRESET_PROFILE_VERSION,
                                PRESET_CLIENT_NUMBER, history_system_prompt)
        if history is not None:
            beh_dir = beh_dir_maker(
                PRESET_PROFILE_VERSION, PRESET_BEH_DIR_VERSION, PRESET_CLIENT_NUMBER, beh_dir_system_prompt)
            if beh_dir is not None:
                st.session_state.agent_and_memory = create_conversational_agent(
                    PRESET_PROFILE_VERSION, PRESET_BEH_DIR_VERSION, PRESET_CLIENT_NUMBER, con_agent_system_prompt
                )
                st.success(
                    "Simulated patient is ready. You can start the conversation.")
            else:
                st.error("Failed to generate behavioral direction.")
        else:
            st.error("Failed to generate history.")
    else:
        st.error("Failed to generate profile.")


def display_conversation():
    agent, memory = st.session_state.agent_and_memory
    for message in memory.chat_memory.messages:
        with st.chat_message("user" if message.type == "human" else "assistant"):
            st.markdown(message.content)

    if prompt := st.chat_input("Interviewer:"):
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = agent(prompt)
            message_placeholder.markdown(full_response)


def end_test():
    if st.session_state.agent_and_memory:
        _, memory = st.session_state.agent_and_memory
        save_conversation_to_firebase(
            firebase_ref,
            PRESET_CLIENT_NUMBER,
            memory.chat_memory.messages,
            PRESET_CON_AGENT_VERSION
        )
        st.success(
            "Test completed and conversation saved. Thank you for participating.")
        st.session_state.test_completed = True
        st.session_state.agent_and_memory = None
    else:
        st.error(
            "No conversation to save. Please start and conduct a conversation first.")


if __name__ == "__main__":
    main()
