import json
import streamlit as st
from alcohol_TTM import TTMChatbot
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
    st.session_state.therapist = TTMChatbot(
        openai_api_key=openai_api_key, version=version)
    # Add initial message from therapist
    if not st.session_state.messages:
        initial_message = "안녕하세요. 오늘 음주 행동 변화에 대해 이야기를 나눠보려고 합니다. 현재 음주가 걱정되거나 변화가 필요하다고 생각하시나요?"
        st.session_state.messages.append(
            {"role": "assistant", "content": initial_message})


def parse_stage(response: str) -> str:
    """JSON 형식의 단계 평가 결과를 파싱"""
    try:
        # 응답에서 JSON 부분 찾기
        start_idx = response.find("{")
        end_idx = response.find("}") + 1
        if start_idx != -1 and end_idx != -1:
            json_str = response[start_idx:end_idx]
            result = json.loads(json_str)
            return result.get("stage", "평가 불가")
    except:
        return "평가 불가"
    return "평가 불가"


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

    # Reset conversation if version changes
    if selected_version != st.session_state.current_version:
        st.session_state.messages = []
        st.session_state.therapist = None
        st.session_state.current_version = selected_version

    st.title("🤝 알코올 중독 변화단계평가 챗봇")
    st.write("이 챗봇은 범이론적 모형 (Transtheoretical model)에 기반한 변화단계평가를 수행합니다.")

    # Version info
    st.info(f"현재 버전: {version_descriptions[selected_version]}")

    # Initialize therapist if not already initialized
    if st.session_state.therapist is None:
        initialize_therapist(selected_version)

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
            response = st.session_state.therapist.get_response(prompt)
            st.markdown(response)
            st.session_state.messages.append(
                {"role": "assistant", "content": response})

            # 마지막 메시지에서 변화단계 파싱
            stage = parse_stage(response)
            if stage != "평가 불가":
                st.success(f"📊 평가된 변화단계: {stage}")

    # Add a reset button
    if st.button("대화 초기화"):
        st.session_state.messages = []
        if st.session_state.therapist:
            st.session_state.therapist.clear_memory()
        initialize_therapist(selected_version)
        st.rerun()


if __name__ == "__main__":
    main()
