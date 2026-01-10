import streamlit as st
import json
from datetime import datetime
from SP_utils import get_firebase_ref, load_from_firebase
from expert_validation_utils import sanitize_firebase_key

# ================================
# PRESET - 검증할 Experiment Numbers
# ================================
EXPERIMENT_NUMBERS = [
    # 6201 MDD
    (6201, 3111), (6201, 3117),
    (6201, 1121), (6201, 1123),
    (6201, 3134), (6201, 3138),
    (6201, 1143), (6201, 1145),

    # 6202 BD
    (6202, 3211), (6202, 3212),
    (6202, 1221), (6202, 1222),
    (6202, 3231), (6202, 3234),
    (6202, 1241), (6202, 1242),

    # 6206 OCD
    (6206, 3611), (6206, 3612),
    (6206, 1621), (6206, 1622),
    (6206, 3631), (6206, 3632),
    (6206, 1641), (6206, 1642),
]

# ================================
# Page Configuration
# ================================
st.set_page_config(
    page_title="PIQSCA 평가",
    page_icon="📊",
    layout="wide"
)

# ================================
# Session State Initialization
# ================================
def init_session_state():
    """Initialize session state variables"""
    if 'expert_name' not in st.session_state:
        st.session_state.expert_name = None

def init_expert_session_state(expert_name):
    """Initialize session state variables for specific expert"""
    expert_key = f"piqsca_{expert_name}"
    
    if expert_key not in st.session_state:
        st.session_state[expert_key] = {
            'current_experiment_index': 0,
            'piqsca_responses': {},
            'firebase_loaded': False
        }

# ================================
# Authentication Check
# ================================
def check_expert_login():
    """Check if expert is logged in"""
    if "name" not in st.session_state or not st.session_state.get("name_correct", False):
        st.warning("⚠️ 먼저 Home 페이지에서 로그인해주세요.")
        st.stop()
    else:
        st.session_state.expert_name = st.session_state["name"]
        return True

# ================================
# Main Validation Page
# ================================
def show_validation_page():
    """Display PIQSCA evaluation page"""
    st.title("📊 PIQSCA 평가")
    
    # Initialize Firebase
    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error("Firebase 연결에 실패했습니다. 설정을 확인해주세요.")
        st.stop()
    
    # Load progress from Firebase
    expert_name = st.session_state.expert_name
    init_expert_session_state(expert_name)
    expert_key = f"piqsca_{expert_name}"
    expert_state = st.session_state[expert_key]
    
    if not expert_state['firebase_loaded']:
        with st.spinner(f'{expert_name}님의 저장된 평가 결과를 불러오는 중...'):
            # Load individual PIQSCA results
            for idx, (client_num, exp_num) in enumerate(EXPERIMENT_NUMBERS):
                exp_key = f"{client_num}_{exp_num}"
                sanitized_expert_name = sanitize_firebase_key(expert_name)
                firebase_key = f"piqsca_{sanitized_expert_name}_{client_num}_{exp_num}"
                
                existing_response = firebase_ref.child(firebase_key).get()
                if existing_response:
                    expert_state['piqsca_responses'][exp_key] = existing_response
        
        expert_state['firebase_loaded'] = True
        
        # Show info about loaded data
        if expert_state['piqsca_responses']:
            loaded_count = len(expert_state['piqsca_responses'])
            if loaded_count > 0:
                st.success(f"✅ 이전 평가 결과 {loaded_count}개를 불러왔습니다.")
    
    # Progress display
    current_idx = expert_state['current_experiment_index']
    total_experiments = len(EXPERIMENT_NUMBERS)
    
    st.progress((current_idx) / total_experiments)
    st.markdown(f"### 진행도: {current_idx}/{total_experiments}")
    st.markdown("---")
    
    # Check if all evaluations are complete
    all_completed = current_idx >= total_experiments
    if all_completed:
        st.success("🎉 모든 평가가 완료되었습니다!")
        st.markdown(f"총 **{total_experiments}개**의 케이스에 대한 평가를 완료하셨습니다.")
        st.info("💡 이전 평가 항목을 수정하려면 아래에서 항목을 선택하세요.")
        st.markdown("---")
        
        # Allow user to select which experiment to review/edit
        col1, col2 = st.columns([3, 1])
        with col1:
            exp_options = [f"실험 {i+1}: Client {c}, Exp {e}" for i, (c, e) in enumerate(EXPERIMENT_NUMBERS)]
            selected_str = st.selectbox("수정할 항목 선택", exp_options)
            selected_idx = exp_options.index(selected_str)
        
        with col2:
            if st.button("선택한 항목으로 이동", use_container_width=True):
                expert_state['current_experiment_index'] = selected_idx
                st.rerun()
        
        current_idx = selected_idx
    
    # Get current experiment
    if current_idx >= total_experiments:
        current_idx = total_experiments - 1
    
    current_item = EXPERIMENT_NUMBERS[current_idx]
    client_number, exp_number = current_item
    client_number_str = str(client_number)
    exp_number_str = str(exp_number)
    
    st.info(f"**현재 평가 대상:** 실험 {current_idx + 1} - Client {client_number}, Exp {exp_number}")
    
    # Load conversation from Firebase
    try:
        conversation_key = f"conversation_log_{client_number_str}_{exp_number_str}"
        conversation_data = load_from_firebase(firebase_ref, client_number_str, conversation_key)
        
        if not conversation_data:
            st.error(f"대화 데이터를 찾을 수 없습니다: Client {client_number}, Exp {exp_number}")
            st.stop()
        
        # Display evaluation interface
        display_piqsca_interface(
            conversation_data,
            (client_number, exp_number),
            firebase_ref
        )
        
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        import traceback
        st.code(traceback.format_exc())

# ================================
# PIQSCA Evaluation Interface
# ================================
def display_piqsca_interface(conversation_data, exp_item, firebase_ref):
    """Display the PIQSCA evaluation interface"""
    
    client_number, exp_number = exp_item
    expert_name = st.session_state.expert_name
    expert_key = f"piqsca_{expert_name}"
    expert_state = st.session_state[expert_key]
    exp_key = f"{client_number}_{exp_number}"
    current_idx = expert_state['current_experiment_index']
    total_experiments = len(EXPERIMENT_NUMBERS)
    all_completed = current_idx >= total_experiments
    
    # 2-column layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📊 PIQSCA 평가 항목")
        st.markdown("---")
        st.info("아래 3가지 항목에 대해 1-5점 척도로 평가해주세요.")
        
        # Get current responses
        if exp_key not in expert_state['piqsca_responses']:
            expert_state['piqsca_responses'][exp_key] = {
                'process_of_the_interview': None,
                'techniques': None,
                'information_for_diagnosis': None
            }
        
        current_responses = expert_state['piqsca_responses'][exp_key]
        
        # 1. Process of the interview
        st.markdown("### 1. Process of the interview")
        st.caption("면담 진행 과정의 적절성을 평가해주세요.")
        
        process_score = st.radio(
            "Process of the interview 평가",
            [1, 2, 3, 4, 5],
            key=f"process_score_{client_number}_{exp_number}",
            horizontal=True,
            format_func=lambda x: f"{x}점",
            index=(current_responses['process_of_the_interview'] - 1) if current_responses['process_of_the_interview'] else None,
            label_visibility="collapsed"
        )
        current_responses['process_of_the_interview'] = process_score
        st.markdown("")
        
        # 2. Techniques
        st.markdown("### 2. Techniques")
        st.caption("면담 기법의 적절성을 평가해주세요.")
        
        techniques_score = st.radio(
            "Techniques 평가",
            [1, 2, 3, 4, 5],
            key=f"techniques_score_{client_number}_{exp_number}",
            horizontal=True,
            format_func=lambda x: f"{x}점",
            index=(current_responses['techniques'] - 1) if current_responses['techniques'] else None,
            label_visibility="collapsed"
        )
        current_responses['techniques'] = techniques_score
        st.markdown("")
        
        # 3. Information for diagnosis
        st.markdown("### 3. Information for diagnosis")
        st.caption("진단에 필요한 정보 수집의 적절성을 평가해주세요.")
        
        information_score = st.radio(
            "Information for diagnosis 평가",
            [1, 2, 3, 4, 5],
            key=f"information_score_{client_number}_{exp_number}",
            horizontal=True,
            format_func=lambda x: f"{x}점",
            index=(current_responses['information_for_diagnosis'] - 1) if current_responses['information_for_diagnosis'] else None,
            label_visibility="collapsed"
        )
        current_responses['information_for_diagnosis'] = information_score
        
        expert_state['piqsca_responses'][exp_key] = current_responses
    
    with col2:
        st.subheader("💬 대화 내역")
        st.markdown("---")
        
        # Display conversation history
        if 'data' in conversation_data:
            messages = conversation_data['data']
            for i, msg in enumerate(messages):
                if isinstance(msg, dict) and 'message' in msg:
                    message_text = msg['message']
                    # Alternate PACA/SP based on index
                    if i % 2 == 0:
                        st.markdown(f"**🤖 PACA:** {message_text}")
                    else:
                        st.markdown(f"**👤 SP:** {message_text}")
                    st.markdown("")
        else:
            st.warning("대화 데이터 형식이 예상과 다릅니다.")
    
    # Save and navigation buttons
    st.markdown("---")
    
    # Display save status
    if 'piqsca_save_status' in st.session_state:
        if st.session_state.piqsca_save_status == 'success':
            st.success("✅ 저장되었습니다!")
        elif st.session_state.piqsca_save_status == 'error':
            st.error("❌ 저장에 실패했습니다. 다시 시도해주세요.")
        del st.session_state.piqsca_save_status
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        # Back button
        if current_idx > 0:
            if st.button("◀️ 이전", use_container_width=True):
                save_piqsca_to_firebase(firebase_ref, expert_name, (client_number, exp_number), current_responses)
                expert_state['current_experiment_index'] = current_idx - 1
                st.rerun()
        else:
            st.button("◀️ 이전", use_container_width=True, disabled=True)
    
    with col2:
        if st.button("💾 중간 저장", use_container_width=True):
            success = save_piqsca_to_firebase(firebase_ref, expert_name, (client_number, exp_number), current_responses)
            if success:
                st.session_state.piqsca_save_status = 'success'
            else:
                st.session_state.piqsca_save_status = 'error'
            st.rerun()
    
    with col4:
        # Next button
        if all_completed:
            next_button_text = "💾 저장"
        elif current_idx == total_experiments - 1:
            next_button_text = "✅ 완료 및 저장"
        else:
            next_button_text = "저장 후 다음 ▶️"
        
        if st.button(next_button_text, use_container_width=True, type="primary"):
            # Check all fields are filled
            if None in current_responses.values():
                st.error("❌ 모든 항목을 평가해주세요.")
            else:
                success = save_piqsca_to_firebase(firebase_ref, expert_name, (client_number, exp_number), current_responses)
                if success:
                    if not all_completed:
                        expert_state['current_experiment_index'] = current_idx + 1
                    st.session_state.piqsca_save_status = 'success'
                    st.rerun()
                else:
                    st.session_state.piqsca_save_status = 'error'
                    st.rerun()

# ================================
# Firebase Save Function
# ================================
def save_piqsca_to_firebase(firebase_ref, expert_name, exp_item, responses):
    """Save PIQSCA evaluation result to Firebase"""
    try:
        client_number, exp_number = exp_item
        sanitized_expert_name = sanitize_firebase_key(expert_name)
        key = f"piqsca_{sanitized_expert_name}_{client_number}_{exp_number}"
        
        data = {
            'client_number': client_number,
            'experiment_number': exp_number,
            'expert_name': expert_name,
            'timestamp': int(datetime.now().timestamp()),
            'process_of_the_interview': responses['process_of_the_interview'],
            'techniques': responses['techniques'],
            'information_for_diagnosis': responses['information_for_diagnosis']
        }
        
        firebase_ref.child(key).set(data)
        return True
    except Exception as e:
        st.error(f"Firebase 저장 실패: {e}")
        return False

# ================================
# Main Function
# ================================
def main():
    """Main function"""
    init_session_state()
    check_expert_login()
    show_validation_page()

if __name__ == "__main__":
    main()
