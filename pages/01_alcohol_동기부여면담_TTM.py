import streamlit as st
from alcohol_motivational_TTM import MITherapist
import os

# Initialize session states
if "messages" not in st.session_state:
    st.session_state.messages = []

if "therapist" not in st.session_state:
    st.session_state.therapist = None

if "current_version" not in st.session_state:
    st.session_state.current_version = 2  # Default to version 2


def initialize_therapist(version):
    """Initialize the MI therapist with OpenAI API key and version"""
    openai_api_key = st.secrets["OPENAI_API_KEY"]
    st.session_state.therapist = MITherapist(
        openai_api_key=openai_api_key, version=version)
    # Add initial message from therapist
    if not st.session_state.messages:
        initial_message = "안녕하세요, 저는 당신의 동기부여 상담사입니다. 오늘 어떤 이야기를 나누고 싶으신가요?"
        st.session_state.messages.append(
            {"role": "assistant", "content": initial_message})


def main():
    # Add version selector in sidebar
    st.sidebar.title("버전 선택")
    version_descriptions = {
        1: "V1",
        2: "V2"
    }
    selected_version = st.sidebar.radio(
        "테스트할 버전을 선택하세요:",
        options=list(version_descriptions.keys()),
        format_func=lambda x: version_descriptions[x]
    )

    st.sidebar.title("변화단계 선택")
    stage_descriptions = {
        1: "고려전",
        2: "고려",
        3: "준비",
        4: "실천",
        5: "유지",
        6: "종결",
    }
    stage = st.sidebar.radio(
        "환자(본인)의 변화단계를 선택하세요:",
        options=list(stage_descriptions.keys()),
        format_func=lambda x: stage_descriptions[x]
    )

    # Reset conversation if version changes
    if selected_version != st.session_state.current_version:
        st.session_state.messages = []
        st.session_state.therapist = None
        st.session_state.current_version = selected_version

    st.title("🤝 알코올 중독 동기부여 상담 챗봇")
    st.write("이 챗봇은 동기부여면담(Motivational Interviewing) 기법을 사용하여 당신의 변화를 돕습니다.")

    # Version info
    st.info(f"현재 버전: {version_descriptions[selected_version]}")

    # Initialize therapist if not already initialized
    if st.session_state.therapist is None:
        initialize_therapist(selected_version, stage)

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("메시지를 입력하세요..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get bot response
        with st.chat_message("assistant"):
            response = st.session_state.therapist.get_response(prompt, stage)
            st.markdown(response)
            st.session_state.messages.append(
                {"role": "assistant", "content": response})

    # Add a reset button
    if st.button("대화 초기화"):
        st.session_state.messages = []
        if st.session_state.therapist:
            st.session_state.therapist.clear_memory()
        initialize_therapist(selected_version)
        st.rerun()


if __name__ == "__main__":
    main()
