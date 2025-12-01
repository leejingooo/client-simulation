import streamlit as st
from Experiment_gpt_guided import experiment_page

client_number = 6002

# Initialize session state for page tracking
if 'current_page' not in st.session_state:
    st.session_state.current_page = None

current_page = "bd)_gpt_guided.py"

# If page changed, clear relevant session state to reset LLM and memory
if st.session_state.current_page != current_page:
    st.session_state.current_page = current_page
    # Clear conversation and constructs but keep PACA agent for this session
    if 'conversation' in st.session_state:
        st.session_state.conversation = []
    if 'conversation_generator' in st.session_state:
        del st.session_state.conversation_generator
    if 'constructs' in st.session_state:
        st.session_state.constructs = None
    if 'sp_construct' in st.session_state:
        st.session_state.sp_construct = None
    if 'paca_agent' in st.session_state:
        del st.session_state.paca_agent
    if 'paca_memory' in st.session_state:
        del st.session_state.paca_memory
    if 'sp_memory' in st.session_state:
        del st.session_state.sp_memory

if __name__ == "__main__":
    experiment_page(client_number)
