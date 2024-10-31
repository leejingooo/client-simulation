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

# Add to session state initialization section:
if "stage" not in st.session_state:
    st.session_state.stage = 1  # Default to stage 1

if "session_started" not in st.session_state:
    st.session_state.session_started = False


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


# Replace the main version and stage selection section with:
def main():
    # Always get current version, but only allow changes before session starts
    if not st.session_state.session_started:
        st.sidebar.title("버전 선택")
        version_descriptions = {
            1: "V1",
            2: "V2"
        }
        selected_version = st.sidebar.radio(
            "테스트할 버전을 선택하세요:",
            options=list(version_descriptions.keys()),
            format_func=lambda x: version_descriptions[x],
            key="version_select"
        )

        # Update current_version if changed
        if selected_version != st.session_state.current_version:
            st.session_state.current_version = selected_version
            st.session_state.messages = []
            st.session_state.therapist = None

        st.sidebar.title("변화단계 선택")
        stage_descriptions = {
            1: "고려전",
            2: "고려",
            3: "준비",
            4: "실천",
            5: "유지",
            6: "종결",
        }
        selected_stage = st.sidebar.radio(
            "환자(본인)의 변화단계를 선택하세요:",
            options=list(stage_descriptions.keys()),
            format_func=lambda x: stage_descriptions[x],
            key="stage_select"
        )

        if st.sidebar.button("대화 시작"):
            st.session_state.session_started = True
            st.session_state.stage = selected_stage
            initialize_therapist(st.session_state.current_version)
            st.rerun()
    else:
        # Just display the current version and stage when session is started
        st.sidebar.title("현재 설정")
        st.sidebar.text(
            f"버전: {'V1' if st.session_state.current_version == 1 else 'V2'}")
        stage_names = {1: "고려전", 2: "고려", 3: "준비", 4: "실천", 5: "유지", 6: "종결"}
        st.sidebar.text(f"변화단계: {stage_names[st.session_state.stage]}")

    st.title("🤝 알코올 중독 동기부여 상담 챗봇")
    st.write("이 챗봇은 동기부여면담(Motivational Interviewing) 기법을 사용하여 당신의 변화를 돕습니다.")

    # Initialize therapist if needed
    if st.session_state.therapist is None and st.session_state.session_started:
        initialize_therapist(st.session_state.current_version)

    # Display chat messages and handle input as before...
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("메시지를 입력하세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = st.session_state.therapist.get_response(
                prompt, st.session_state.stage)
            st.markdown(response)
            st.session_state.messages.append(
                {"role": "assistant", "content": response})

    # Reset button
    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.session_state.session_started = False
        if st.session_state.therapist:
            st.session_state.therapist.clear_memory()
        st.rerun()


if __name__ == "__main__":
    main()
