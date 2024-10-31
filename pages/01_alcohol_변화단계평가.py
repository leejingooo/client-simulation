import streamlit as st
from alcohol_TTM import TTMChatbot
import os


def main():
    st.title("음주 행동 변화단계 평가")

    # OpenAI API 키 설정
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = os.getenv('OPENAI_API_KEY', '')

    # 챗봇 초기화
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = TTMChatbot(st.session_state.openai_api_key)

    # 대화 기록 초기화
    if 'messages' not in st.session_state:
        st.session_state.messages = []
        # 첫 메시지 추가
        response = st.session_state.chatbot.get_stage("")
        st.session_state.messages.append(
            {"role": "assistant", "content": response})

    # 대화 기록 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # 사용자 입력
    if prompt := st.chat_input():
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # 챗봇 응답
        response = st.session_state.chatbot.get_stage(prompt)

        # 변화단계가 결정되었을 경우
        if isinstance(response, dict) and response["stage"]:
            st.session_state.messages.append(
                {"role": "assistant", "content": response["message"]})
            with st.chat_message("assistant"):
                st.write(response["message"])

            # 변화단계 결과 표시
            st.success(f"평가된 변화단계: {response['stage']}")

            # 여기서 MI 챗봇으로 전달할 수 있음
            st.session_state.ttm_stage = response["stage"]
        else:
            st.session_state.messages.append(
                {"role": "assistant", "content": response["message"]})
            with st.chat_message("assistant"):
                st.write(response["message"])


if __name__ == "__main__":
    main()
