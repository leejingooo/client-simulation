import streamlit as st
import os
from alcohol_motivational import MIBot

# Page config
st.set_page_config(
    page_title="Motivational Interviewing Chatbot", page_icon="🤝")

# Initialize session state for chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []


def initialize_bot():
    """Initialize the MI bot with OpenAI API key"""
    if "bot" not in st.session_state:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            st.error(
                "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
            st.stop()
        st.session_state.bot = MIBot(openai_api_key)


# Main UI
st.title("🤝 Motivational Interviewing Chatbot")
st.write("A safe space to discuss your relationship with alcohol. Your conversations are private and confidential.")

# Initialize bot
initialize_bot()

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Share your thoughts..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get bot response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = st.session_state.bot.get_response(prompt)
            st.markdown(response)
            st.session_state.messages.append(
                {"role": "assistant", "content": response})

# Sidebar
with st.sidebar:
    st.header("About this Chatbot")
    st.write("""
    This chatbot uses Motivational Interviewing techniques to help you explore your relationship with alcohol. 
    It provides a non-judgmental space to discuss your thoughts and feelings about drinking.
    """)

    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.bot.clear_history()
        st.rerun()

    st.markdown("---")
    st.markdown("### Privacy Note")
    st.write(
        "Your conversations are not stored permanently and are cleared when you end the session.")
