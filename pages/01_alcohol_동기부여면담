import streamlit as st
from alcohol_motivational import MITherapist
import os

# Initialize session state for chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize session state for therapist if it doesn't exist
if "therapist" not in st.session_state:
    st.session_state.therapist = None


def initialize_therapist():
    """Initialize the MI therapist with OpenAI API key"""
    openai_api_key = st.secrets["OPENAI_API_KEY"]
    st.session_state.therapist = MITherapist(openai_api_key)
    # Add initial message from therapist
    if not st.session_state.messages:
        initial_message = "안녕하세요, 저는 당신의 동기부여 상담사입니다. 오늘 어떤 이야기를 나누고 싶으신가요?"
        st.session_state.messages.append(
            {"role": "assistant", "content": initial_message})


def main():
    st.title("🤝 알코올 중독 동기부여 상담 챗봇")
    st.write("이 챗봇은 동기부여면담(Motivational Interviewing) 기법을 사용하여 당신의 변화를 돕습니다.")

    # Initialize therapist if not already initialized
    if st.session_state.therapist is None:
        initialize_therapist()

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

    # Add a reset button
    if st.button("대화 초기화"):
        st.session_state.messages = []
        if st.session_state.therapist:
            st.session_state.therapist.clear_memory()
        initialize_therapist()
        st.rerun()


if __name__ == "__main__":
    main()
