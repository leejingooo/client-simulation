import streamlit as st
from Experiment_claude_basic import experiment_page

client_number = 6001

# Initialize session state for page tracking
if 'current_page' not in st.session_state:
    st.session_state.current_page = None

current_page = "experiment_mdd_claude_basic"
current_agent_type = "Claude Basic"

# If page changed, clear relevant session state to reset LLM and memory
if st.session_state.current_page != current_page:
    st.session_state.current_page = current_page
    st.session_state.agent_type = current_agent_type
    # Clear conversation and constructs and FORCE PACA agent recreation
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
    # Force PACA agent recreation
    st.session_state.force_paca_update = True
else:
    # Same page, ensure agent_type is set
    if 'agent_type' not in st.session_state:
        st.session_state.agent_type = current_agent_type

if __name__ == "__main__":
    experiment_page(client_number)
