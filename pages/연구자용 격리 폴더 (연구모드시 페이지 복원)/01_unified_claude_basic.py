import streamlit as st
from PACA_claude_basic_utils import create_paca_agent, simulate_conversation, save_conversation_to_csv
from SP_utils import create_conversational_agent, load_from_firebase, get_diag_from_given_information, load_prompt_and_get_version, save_to_firebase
from firebase_config import get_firebase_ref
import time

try:
    from sp_construct_generator import create_sp_construct
except Exception:
    create_sp_construct = None

try:
    from paca_construct_generator import create_paca_construct
except Exception:
    create_paca_construct = None

# PRESET
profile_version = 6.0
beh_dir_version = 6.0
con_agent_version = 6.0
paca_version = 3.0

# Disorder mapping
DISORDERS = {
    'MDD': {'client_number': 6201, 'name': 'Major Depressive Disorder', 'emoji': '😔'},
    'BD': {'client_number': 6202, 'name': 'Bipolar Disorder', 'emoji': '🔄'},
    'OCD': {'client_number': 6206, 'name': 'Obsessive-Compulsive Disorder', 'emoji': '🔁'}
}


def check_experiment_number_exists(firebase_ref, client_number, exp_number):
    """Check if the experiment number is already used for this client."""
    keys_to_check = [
        f"construct_paca_{client_number}_{exp_number}",
        f"conversation_log_{client_number}_{exp_number}"
    ]
    
    for key in keys_to_check:
        data = load_from_firebase(firebase_ref, client_number, key)
        if data is not None:
            return True
    return False


def construct_generator_conversation_new(paca_agent):
    """Generate PACA construct using the new structured approach."""
    if create_paca_construct is None:
        return None
    
    try:
        paca_construct = create_paca_construct(paca_agent)
        return paca_construct
    except Exception as e:
        st.error(f"Failed to create PACA construct: {e}")
        return None


def initialize_disorder_state(disorder):
    """Initialize session state for a specific disorder."""
    prefix = f"{disorder}_"
    
    if f'{prefix}conversation' not in st.session_state:
        st.session_state[f'{prefix}conversation'] = []
    if f'{prefix}conversation_generator' not in st.session_state:
        st.session_state[f'{prefix}conversation_generator'] = None
    if f'{prefix}constructs' not in st.session_state:
        st.session_state[f'{prefix}constructs'] = None
    if f'{prefix}sp_construct' not in st.session_state:
        st.session_state[f'{prefix}sp_construct'] = None
    if f'{prefix}sp_memory' not in st.session_state:
        st.session_state[f'{prefix}sp_memory'] = None
    if f'{prefix}paca_agent' not in st.session_state:
        st.session_state[f'{prefix}paca_agent'] = None
    if f'{prefix}paca_memory' not in st.session_state:
        st.session_state[f'{prefix}paca_memory'] = None
    if f'{prefix}agents_loaded' not in st.session_state:
        st.session_state[f'{prefix}agents_loaded'] = False


def render_experiment_column(disorder, disorder_info, firebase_ref):
    """Render a single experiment column for a disorder."""
    client_number = disorder_info['client_number']
    prefix = f"{disorder}_"
    
    st.markdown(f"### {disorder_info['emoji']} {disorder}")
    st.caption(disorder_info['name'])
    st.divider()
    
    # Load SP data
    profile = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version:.1f}".replace(".", "_"))
    history = load_from_firebase(
        firebase_ref, client_number, f"history_version{profile_version:.1f}".replace(".", "_"))
    beh_dir = load_from_firebase(
        firebase_ref, client_number, f"beh_dir_version{beh_dir_version:.1f}".replace(".", "_"))
    given_information = load_from_firebase(
        firebase_ref, client_number, "given_information")

    if not all([profile, history, beh_dir, given_information]):
        st.error(f"Failed to load client data for {disorder}")
        return

    # Create agents if not loaded
    if not st.session_state[f'{prefix}agents_loaded']:
        diag = get_diag_from_given_information(given_information)
        
        # Create SP agent
        if diag == "BD":
            con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
                "con-agent", con_agent_version, diag)
        else:
            con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
                "con-agent", con_agent_version)

        if con_agent_system_prompt:
            sp_agent, sp_memory = create_conversational_agent(
                f"{profile_version:.1f}".replace(".", "_"),
                f"{beh_dir_version:.1f}".replace(".", "_"),
                client_number,
                con_agent_system_prompt
            )
            st.session_state[f'{prefix}sp_memory'] = sp_memory
            st.session_state[f'{prefix}sp_agent'] = sp_agent
        else:
            st.error("Failed to load SP system prompt.")
            return

        # Create PACA agent
        paca_agent, paca_memory, actual_paca_version = create_paca_agent(paca_version)
        st.session_state[f'{prefix}paca_agent'] = paca_agent
        st.session_state[f'{prefix}paca_memory'] = paca_memory
        st.session_state[f'{prefix}actual_paca_version'] = actual_paca_version
        st.session_state[f'{prefix}actual_con_agent_version'] = actual_con_agent_version
        st.session_state[f'{prefix}agents_loaded'] = True

        # Initialize conversation generator
        st.session_state[f'{prefix}conversation_generator'] = simulate_conversation(
            paca_agent, sp_agent)
        # Add the initial greeting
        paca_memory.add_ai_message("안녕하세요, 저는 정신과 의사 김민수입니다. 이름이 어떻게 되시나요?")
        sp_memory.add_user_message("안녕하세요, 저는 정신과 의사 김민수입니다. 이름이 어떻게 되시나요?")

    # Experiment number input
    st.markdown("#### 📝 Experiment Number")
    exp_number = st.text_input(
        "Enter experiment number:",
        key=f"{prefix}exp_number_input",
        help="Enter a unique number for this experiment"
    )
    
    # Validate experiment number
    exp_number_valid = False
    if exp_number:
        if not exp_number.isdigit():
            st.error("⚠️ Please enter a valid number")
        elif check_experiment_number_exists(firebase_ref, client_number, exp_number):
            st.error(f"⚠️ Experiment {exp_number} already exists")
        else:
            st.success(f"✅ Experiment {exp_number} available")
            exp_number_valid = True
    else:
        st.info("Enter experiment number")
    
    st.divider()

    # Conversation area
    conversation_area = st.empty()

    # Control buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎬 Generate Conversation", key=f"{prefix}generate_btn", use_container_width=True):
            paca_agent = st.session_state[f'{prefix}paca_agent']
            sp_agent = st.session_state[f'{prefix}sp_agent']
            
            # Reset generator if needed
            if st.session_state[f'{prefix}conversation_generator'] is None:
                st.session_state[f'{prefix}conversation_generator'] = simulate_conversation(
                    paca_agent, sp_agent)
            
            # Generate conversation and update display in real-time
            while True:
                try:
                    next_turn = next(st.session_state[f'{prefix}conversation_generator'])
                    st.session_state[f'{prefix}conversation'].append(next_turn)
                    
                    # Update conversation display in real-time
                    with conversation_area.container():
                        for speaker, message in st.session_state[f'{prefix}conversation']:
                            with st.chat_message(speaker):
                                st.write(message)
                except StopIteration:
                    break
                time.sleep(0.1)

    with col2:
        if st.button("⏹️ Stop & Generate Constructs", key=f"{prefix}stop_btn", use_container_width=True):
            # Generate PACA construct
            if st.session_state[f'{prefix}constructs'] is None:
                st.session_state[f'{prefix}constructs'] = construct_generator_conversation_new(
                    st.session_state[f'{prefix}paca_agent'])
                if st.session_state[f'{prefix}constructs']:
                    st.success("PACA Construct generated!")
            
            # Generate SP construct
            if st.session_state[f'{prefix}sp_construct'] is None:
                if create_sp_construct is not None:
                    given_form_path = f"data/prompts/paca_system_prompt/given_form_version{paca_version}.json"
                    try:
                        sp_construct = create_sp_construct(
                            client_number,
                            f"{profile_version:.1f}",
                            f"{beh_dir_version:.1f}",
                            given_form_path,
                        )
                        if sp_construct:
                            st.session_state[f'{prefix}sp_construct'] = sp_construct
                            st.success("SP Construct generated!")
                    except Exception as e:
                        st.error(f"Failed to create SP construct: {e}")
            st.rerun()

    # Display the conversation
    with conversation_area.container():
        for speaker, message in st.session_state[f'{prefix}conversation']:
            with st.chat_message(speaker):
                st.write(message)

    # Save button - only show if constructs are generated
    if st.session_state[f'{prefix}constructs'] and st.button("💾 Save Conversation and Constructs", key=f"{prefix}save_btn", use_container_width=True):
        if not exp_number_valid:
            st.error("⚠️ Please enter a valid and unique experiment number before saving.")
        else:
            # Save conversation
            conversation_data = [
                {'speaker': speaker, 'message': message}
                for speaker, message in st.session_state[f'{prefix}conversation']
            ]
            
            conversation_content = {
                'paca_version': st.session_state.get(f'{prefix}actual_paca_version', paca_version),
                'sp_version': st.session_state.get(f'{prefix}actual_con_agent_version', con_agent_version),
                'timestamp': int(time.time()),
                'total_turns': len(st.session_state[f'{prefix}conversation']),
                'data': conversation_data
            }
            
            conversation_key = f"conversation_log_{client_number}_{exp_number}"
            save_to_firebase(firebase_ref, client_number, conversation_key, conversation_content)
            
            # Save PACA construct
            if st.session_state[f'{prefix}constructs']:
                paca_construct_key = f"construct_paca_{client_number}_{exp_number}"
                save_to_firebase(firebase_ref, client_number, paca_construct_key, 
                               st.session_state[f'{prefix}constructs'])
            
            # Save SP construct
            if st.session_state[f'{prefix}sp_construct']:
                sp_construct_key = f"construct_sp_{client_number}_{exp_number}"
                save_to_firebase(firebase_ref, client_number, sp_construct_key, 
                               st.session_state[f'{prefix}sp_construct'])
            
            st.success(f"✅ Saved experiment {exp_number} for {disorder}!")

    # Download CSV button
    if st.session_state[f'{prefix}conversation']:
        csv_data = save_conversation_to_csv(st.session_state[f'{prefix}conversation'])
        st.download_button(
            label="⬇️ Download CSV",
            data=csv_data,
            file_name=f"conversation_{disorder}_{exp_number if exp_number else 'temp'}.csv",
            mime="text/csv",
            key=f"{prefix}download_btn",
            use_container_width=True
        )

    # Display constructs in expanders
    if st.session_state[f'{prefix}constructs']:
        with st.expander("📊 PACA Construct", expanded=False):
            st.json(st.session_state[f'{prefix}constructs'])
    
    if st.session_state[f'{prefix}sp_construct']:
        with st.expander("📋 SP Construct", expanded=False):
            st.json(st.session_state[f'{prefix}sp_construct'])


def main():
    st.set_page_config(
        page_title="Unified Experiment - Claude Basic",
        page_icon="🧠",
        layout="wide"
    )

    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error("Firebase initialization failed. Please check your configuration and try again.")
        st.stop()

    st.title("🧠 Unified Experiment Page - Claude Basic")
    st.markdown("Conduct experiments for **MDD, BD, and OCD** simultaneously")
    st.divider()

    # Initialize state for all disorders
    for disorder in DISORDERS.keys():
        initialize_disorder_state(disorder)

    # Create three columns
    col1, col2, col3 = st.columns(3)

    with col1:
        render_experiment_column('MDD', DISORDERS['MDD'], firebase_ref)

    with col2:
        render_experiment_column('BD', DISORDERS['BD'], firebase_ref)

    with col3:
        render_experiment_column('OCD', DISORDERS['OCD'], firebase_ref)


if __name__ == "__main__":
    main()
