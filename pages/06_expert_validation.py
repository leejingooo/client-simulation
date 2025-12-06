import streamlit as st
import json
from datetime import datetime
from SP_utils import get_firebase_ref, load_from_firebase
from expert_validation_utils import (
    calculate_score,
    create_validation_result,
    save_validation_to_firebase,
    load_validation_progress,
    get_scoring_options,
    sanitize_firebase_key
)

# ================================
# PRESET - 검증할 Experiment Numbers
# ================================
# 각 항목은 (client_number, experiment_number) 튜플입니다
# client_number: 4자리 숫자 (예: 6101, 6102)
# experiment_number: 실험 번호 (예: 101, 102)
EXPERIMENT_NUMBERS = [
    (6101, 101),  # 테스트용 예시 1
    (6101, 102),  # 테스트용 예시 2
    # 여기에 총 24개의 (client_number, experiment_number) 쌍을 추가하세요
    # 예: (6101, 103), (6102, 101), ...
]

# ================================
# Page Configuration
# ================================
st.set_page_config(
    page_title="전문가 검증",
    page_icon="📋",
    layout="wide"
)

# ================================
# Session State Initialization
# ================================
def init_session_state():
    """Initialize session state variables"""
    if 'validation_stage' not in st.session_state:
        st.session_state.validation_stage = 'intro'  # intro, test, validation
    if 'current_experiment_index' not in st.session_state:
        st.session_state.current_experiment_index = 0
    if 'validation_responses' not in st.session_state:
        st.session_state.validation_responses = {}
    if 'expert_name' not in st.session_state:
        st.session_state.expert_name = None
    if 'firebase_loaded' not in st.session_state:
        st.session_state.firebase_loaded = False

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
# Page 1: Introduction
# ================================
def show_intro_page():
    """Display introduction page with instructions"""
    st.title("📋 전문가 검증 시스템")
    st.markdown("---")
    
    st.markdown("""
    ## 검증 프로세스 안내
    
    안녕하세요, 전문가님. 본 시스템은 정신과 평가 대화형 에이전트(PACA, Psychiatric Assessment Conversational Agent)의 
    성능을 검증하기 위한 전문가 평가 도구입니다.
    
    ### 📌 검증 절차
    
    1. **연습 단계**: 먼저 테스트 페이지에서 검증 방법을 연습합니다.
    2. **실제 검증**: 총 **{total}개**의 대화-평가 쌍을 검증합니다.
    3. **자동 저장**: 각 검증 완료 시 자동으로 Firebase에 저장됩니다.
    
    ### 📝 검증 내용
    
    각 케이스마다 다음을 검토하게 됩니다:
    
    - **왼쪽 패널**: SP(Simulated Patient)와 PACA 간의 대화 내역
    - **오른쪽 패널**: PACA가 생성한 평가 리포트 (PACA Construct)
    
    ### ✅ 평가 기준
    
    다음 세 가지 영역에 대해 평가합니다:
    
    1. **주관적 정보 (Subjective Information)** - 가중치: 1
       - Chief Complaint, Present Illness, Family History 등
    
    2. **충동성 (Impulsivity)** - 가중치: 5
       - Suicidal ideation, Self-mutilating behavior risk 등
    
    3. **행동 (Behavior)** - 가중치: 2
       - Mood, Verbal productivity, Insight, Affect 등
    
    ### 💾 중간 저장
    
    - 언제든지 중단하고 나갔다가 다시 로그인하면 이전에 저장한 시점부터 계속할 수 있습니다.
    - "완료" 버튼을 누르면 해당 케이스의 검증이 저장되고 다음 케이스로 이동합니다.
    
    ### ⚠️ 유의사항
    
    - 모든 항목에 대해 신중하게 평가해주시기 바랍니다.
    - SP Construct는 평가 대상에 포함되지 않습니다.
    - 검증 결과는 향후 PACA 개선에 중요한 자료로 활용됩니다.
    
    """.format(total=len(EXPERIMENT_NUMBERS)))
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("▶️ 테스트 페이지로 이동", use_container_width=True, type="primary"):
            st.session_state.validation_stage = 'test'
            st.rerun()

# ================================
# Page 2: Test Page
# ================================
def show_test_page():
    """Display test page with example validation"""
    st.title("🧪 테스트 페이지")
    st.info("실제 검증과 동일한 형식으로 연습해보세요. 이 페이지의 응답은 저장되지 않습니다.")
    st.markdown("---")
    
    # Example data (hardcoded for demonstration)
    example_conversation = [
        {"speaker": "PACA", "message": "안녕하세요, 저는 정신과 의사입니다. 오늘 어떻게 오시게 되셨나요?"},
        {"speaker": "SP", "message": "요즘... 잠을 잘 못 자서요. 계속 걱정이 되고..."},
        {"speaker": "PACA", "message": "잠을 못 주무신다고 하셨는데, 구체적으로 어떤 상황인지 말씀해 주시겠어요?"},
        {"speaker": "SP", "message": "밤에 자려고 누우면 머릿속이 복잡해져요. 일 생각도 나고, 가족 걱정도 되고..."},
        {"speaker": "PACA", "message": "그런 증상이 얼마나 지속되셨나요?"},
        {"speaker": "SP", "message": "한 두 달 정도 된 것 같아요."},
    ]
    
    # 2-column layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("💬 대화 내역")
        st.markdown("---")
        for msg in example_conversation:
            if msg["speaker"] == "PACA":
                st.markdown(f"**🤖 PACA:** {msg['message']}")
            else:
                st.markdown(f"**👤 SP:** {msg['message']}")
            st.markdown("")
    
    with col2:
        st.subheader("✅ 평가 항목")
        st.markdown("---")
        
        # Example evaluation items
        st.markdown("#### Subjective Information")
        
        st.markdown("**Chief complaint**")
        st.info(f"📌 PACA 값: **불면증과 지속적인 걱정**")
        st.radio(
            "평가",
            ["[선택 안 함]", "Correct", "Partially correct", "Incorrect"],
            key="test_chief_complaint",
            label_visibility="collapsed",
            horizontal=True
        )
        st.markdown("")
        
        st.markdown("**Symptom name**")
        st.info("📌 PACA 값:\n\n- Insomnia\n- Anxiety")
        st.radio(
            "평가",
            ["[선택 안 함]", "Correct", "Partially correct", "Incorrect"],
            key="test_symptom",
            label_visibility="collapsed",
            horizontal=True
        )
        st.markdown("")
        
        st.markdown("#### Behavior (Mental Status Examination)")
        
        st.markdown("**Mood**")
        st.info(f"📌 PACA 값: **anxious, dysphoric**")
        st.radio(
            "Expert의 판단",
            ["[선택 안 함]", "Irritable", "Euphoric", "Elated", "Euthymic", "Dysphoric", "Depressed"],
            key="test_mood",
            label_visibility="collapsed",
            horizontal=True
        )
        st.markdown("")
        
        st.markdown("**Verbal productivity**")
        st.info(f"📌 PACA 값: **moderate**")
        st.radio(
            "Expert의 판단",
            ["[선택 안 함]", "Increased", "Moderate", "Decreased"],
            index=2,  # Default to "Moderate"
            key="test_verbal",
            label_visibility="collapsed",
            horizontal=True
        )
        
        # PACA Quality Assessment
        st.markdown("---")
        st.markdown("### 🎯 PACA 시뮬레이션 품질 평가")
        st.info("아래 3가지 항목에 대해 1-5점 척도로 PACA의 전반적인 면담 품질을 평가해주세요.")
        
        from expert_validation_utils import PACA_QUALITY_CRITERIA
        
        for idx, (criterion_name, criterion_data) in enumerate(PACA_QUALITY_CRITERIA.items()):
            st.markdown(f"#### {criterion_name}")
            st.caption(criterion_data['description'])
            
            # Create expander for detailed criteria
            with st.expander("📖 평가 기준 및 예시 보기"):
                for score, details in criterion_data['scale'].items():
                    st.markdown(f"**{details['label']}**")
                    st.markdown(f"- {details['description']}")
                    st.markdown(f"- *Example: {details['example']}*")
                    st.markdown("")
            
            # Radio buttons for scoring
            score_options = [f"{i}점" for i in range(1, 6)]
            
            st.radio(
                f"{criterion_name} 점수 선택",
                score_options,
                index=2,  # Default to 3점
                key=f"test_quality_{idx}",
                horizontal=True
            )
            st.markdown("")
        
        st.info("💡 **안내사항**\n- Expert는 자신의 판단만 선택하면 됩니다. Score는 자동으로 계산됩니다.\n- PACA 값이 None 또는 N/A인 경우 자동으로 0점 처리됩니다.\n- '[선택 안 함]'으로 선택된 항목이 남아있으면 안 됩니다.")
    
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("✅ 테스트 완료 - 실제 검증 시작", use_container_width=True, type="primary"):
            st.session_state.validation_stage = 'validation'
            st.rerun()

# ================================
# Page 3+: Validation Pages
# ================================
def show_validation_page():
    """Display actual validation page"""
    st.title("📋 전문가 검증")
    
    # Initialize Firebase
    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error("Firebase 연결에 실패했습니다. 설정을 확인해주세요.")
        st.stop()
    
    # Load progress from Firebase (only once per session)
    expert_name = st.session_state.expert_name
    
    if not st.session_state.get('firebase_loaded', False):
        with st.spinner(f'{expert_name}님의 저장된 검증 결과를 불러오는 중...'):
            progress_data = load_validation_progress(firebase_ref, expert_name)
        
        if progress_data:
            st.session_state.validation_responses = progress_data.get('responses', {})
            st.session_state.current_experiment_index = progress_data.get('current_index', 0)
        
        # Also load individual validation results
        for idx, (client_num, exp_num) in enumerate(EXPERIMENT_NUMBERS):
            exp_key = f"{client_num}_{exp_num}"
            # Sanitize expert name for Firebase key
            sanitized_expert_name = sanitize_firebase_key(expert_name)
            firebase_key = f"expert_{sanitized_expert_name}_{client_num}_{exp_num}"
            
            existing_response = firebase_ref.child(firebase_key).get()
            if existing_response and 'elements' in existing_response:
                # Convert elements to simple responses
                loaded_responses = {}
                for element_name, element_data in existing_response['elements'].items():
                    if 'expert_choice' in element_data:
                        # Use original element name if available, otherwise use sanitized key
                        original_name = element_data.get('element_name_original', element_name)
                        loaded_responses[original_name] = element_data['expert_choice']
                st.session_state.validation_responses[exp_key] = loaded_responses
                
                # Also load quality assessment if exists
                if 'quality_assessment' in existing_response:
                    quality_key = f"{exp_key}_quality"
                    st.session_state.validation_responses[quality_key] = existing_response['quality_assessment']
        
        st.session_state.firebase_loaded = True
        
        # Show info about loaded data
        if st.session_state.validation_responses:
            loaded_count = len([k for k in st.session_state.validation_responses.keys() if st.session_state.validation_responses[k]])
            if loaded_count > 0:
                st.success(f"✅ 이전 검증 결과 {loaded_count}개를 불러왔습니다.")
    
    # Progress display
    current_idx = st.session_state.current_experiment_index
    total_experiments = len(EXPERIMENT_NUMBERS)
    
    st.progress((current_idx) / total_experiments)
    st.markdown(f"### 진행도: {current_idx}/{total_experiments}")
    st.markdown("---")
    
    # Check if all validations are complete
    if current_idx >= total_experiments:
        st.success("🎉 모든 검증이 완료되었습니다!")
        st.balloons()
        st.markdown(f"총 **{total_experiments}개**의 케이스에 대한 검증을 완료하셨습니다.")
        st.markdown("검증 결과는 Firebase에 저장되었습니다.")
        st.stop()
    
    # Get current experiment number
    current_item = EXPERIMENT_NUMBERS[current_idx]
    client_number, exp_number = current_item
    
    # Convert to strings for Firebase keys
    client_number_str = str(client_number)
    exp_number_str = str(exp_number)
    
    st.info(f"**현재 검증 대상:** Client #{client_number}, Experiment #{exp_number}")
    
    # Load conversation and construct from Firebase
    try:
        conversation_key = f"conversation_log_{client_number_str}_{exp_number_str}"
        construct_key = f"construct_paca_{client_number_str}_{exp_number_str}"
        
        conversation_data = load_from_firebase(firebase_ref, client_number_str, conversation_key)
        construct_data = load_from_firebase(firebase_ref, client_number_str, construct_key)
        
        if not conversation_data or not construct_data:
            st.error(f"데이터를 불러올 수 없습니다: Client {client_number}, Exp {exp_number}")
            st.markdown("다음 케이스로 건너뛰시겠습니까?")
            if st.button("다음으로 건너뛰기"):
                st.session_state.current_experiment_index += 1
                st.rerun()
            st.stop()
        
        # Display validation interface
        display_validation_interface(
            conversation_data,
            construct_data,
            (client_number, exp_number),
            firebase_ref
        )
        
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        import traceback
        st.code(traceback.format_exc())

# ================================
# Validation Interface
# ================================
def display_validation_interface(conversation_data, construct_data, exp_item, firebase_ref):
    """Display the main validation interface with scoring options"""
    
    client_number, exp_number = exp_item
    exp_key = f"{client_number}_{exp_number}"  # Unique key for this experiment
    
    # 2-column layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("💬 대화 내역")
        st.markdown("---")
        
        # Display conversation
        if 'data' in conversation_data:
            messages = conversation_data['data']
            for msg in messages:
                speaker = msg.get('speaker', 'Unknown')
                message = msg.get('message', '')
                
                if speaker == 'PACA':
                    st.markdown(f"**🤖 PACA:** {message}")
                else:
                    st.markdown(f"**👤 SP:** {message}")
                st.markdown("")
        else:
            st.warning("대화 데이터 형식이 올바르지 않습니다.")
    
    with col2:
        st.subheader("✅ 평가 항목")
        st.markdown("---")
        
        # Get current responses (already loaded from Firebase in show_validation_page)
        if exp_key not in st.session_state.validation_responses:
            st.session_state.validation_responses[exp_key] = {}
        
        current_responses = st.session_state.validation_responses[exp_key]
        
        # Initialize quality assessment responses
        quality_key = f"{exp_key}_quality"
        if quality_key not in st.session_state.validation_responses:
            st.session_state.validation_responses[quality_key] = {}
        
        # Display scoring options by category
        scoring_options = get_scoring_options(construct_data)
        
        for category, items in scoring_options.items():
            st.markdown(f"#### {category}")
            
            for item in items:
                element_name = item['element']
                options = item['options']
                paca_value = item.get('paca_value', 'N/A')
                
                # Display element name and PACA's value
                st.markdown(f"**{element_name}**")
                
                # Handle multiline PACA values properly (e.g., symptom lists)
                if '\n' in str(paca_value):
                    # Display with proper line breaks
                    st.info(f"📌 PACA 값:\n\n{paca_value}")
                else:
                    st.info(f"📌 PACA 값: **{paca_value}**")
                
                # Create unique key for this element
                key = f"{exp_key}_{element_name}"
                
                # Add "선택 안 함" option at the beginning
                options_with_none = ["[선택 안 함]"] + options
                
                # Get default value if already responded
                default_idx = 0  # Default to "선택 안 함"
                if element_name in current_responses:
                    try:
                        # Find index in the new options list (offset by 1)
                        default_idx = options.index(current_responses[element_name]) + 1
                    except ValueError:
                        default_idx = 0
                
                # Display radio buttons (horizontal layout for better UX)
                selected = st.radio(
                    "평가",
                    options_with_none,
                    index=default_idx,
                    key=key,
                    label_visibility="collapsed",
                    horizontal=True
                )
                
                # Store response only if not "선택 안 함"
                if selected != "[선택 안 함]":
                    current_responses[element_name] = selected
                elif element_name in current_responses:
                    # Remove from responses if user deselected
                    del current_responses[element_name]
                
                st.markdown("")
        
        st.session_state.validation_responses[exp_key] = current_responses
        
        # ================================
        # PACA Quality Assessment (Likert Scale)
        # ================================
        st.markdown("---")
        st.markdown("### 🎯 PACA 시뮬레이션 품질 평가")
        st.info("아래 3가지 항목에 대해 1-5점 척도로 PACA의 전반적인 면담 품질을 평가해주세요.")
        
        from expert_validation_utils import PACA_QUALITY_CRITERIA
        
        quality_responses = st.session_state.validation_responses[quality_key]
        
        for criterion_name, criterion_data in PACA_QUALITY_CRITERIA.items():
            st.markdown(f"#### {criterion_name}")
            st.caption(criterion_data['description'])
            
            # Create expander for detailed criteria
            with st.expander("📖 평가 기준 및 예시 보기"):
                for score, details in criterion_data['scale'].items():
                    st.markdown(f"**{details['label']}**")
                    st.markdown(f"- {details['description']}")
                    st.markdown(f"- *Example: {details['example']}*")
                    st.markdown("")
            
            # Radio buttons for scoring
            score_options = [f"{i}점" for i in range(1, 6)]
            
            # Get default value if already responded
            default_idx = 0
            if criterion_name in quality_responses:
                try:
                    saved_score = quality_responses[criterion_name]
                    default_idx = int(saved_score) - 1  # Convert 1-5 to 0-4 index
                except (ValueError, TypeError):
                    default_idx = 0
            
            selected_score = st.radio(
                f"{criterion_name} 점수 선택",
                score_options,
                index=default_idx,
                key=f"{quality_key}_{criterion_name}",
                horizontal=True
            )
            
            # Store the numeric score (1-5)
            quality_responses[criterion_name] = int(selected_score[0])  # Extract number from "X점"
            st.markdown("")
        
        st.session_state.validation_responses[quality_key] = quality_responses
    
    # Save and navigation buttons
    st.markdown("---")
    
    # Display save status if exists
    if 'save_status' in st.session_state:
        if st.session_state.save_status == 'success':
            st.success("✅ 중간 저장이 완료되었습니다!")
        elif st.session_state.save_status == 'error':
            st.error("❌ 저장 실패. 다시 시도해주세요.")
        # Clear status after displaying
        del st.session_state.save_status
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("💾 중간 저장", use_container_width=True):
            # Save current responses to Firebase immediately
            validation_result = create_validation_result(
                construct_data,
                current_responses,
                exp_item,
                is_partial=True  # Mark as partial save
            )
            # Add quality assessment
            validation_result['quality_assessment'] = st.session_state.validation_responses.get(quality_key, {})
            
            success = save_validation_to_firebase(
                firebase_ref,
                st.session_state.expert_name,
                exp_item,
                validation_result
            )
            
            if success:
                # Also save progress
                save_validation_progress(firebase_ref, st.session_state.expert_name,
                                       st.session_state.current_experiment_index,
                                       st.session_state.validation_responses)
                st.session_state.save_status = 'success'
                st.rerun()
            else:
                st.session_state.save_status = 'error'
                st.rerun()
    
    with col3:
        if st.button("✅ 완료 - 다음으로", use_container_width=True, type="primary"):
            # Calculate and save final validation result
            validation_result = create_validation_result(
                construct_data,
                current_responses,
                exp_item  # Pass (client_number, exp_number) tuple
            )
            # Add quality assessment
            validation_result['quality_assessment'] = st.session_state.validation_responses.get(quality_key, {})
            
            # Save to Firebase
            success = save_validation_to_firebase(
                firebase_ref,
                st.session_state.expert_name,
                exp_item,  # Pass (client_number, exp_number) tuple
                validation_result
            )
            
            if success:
                st.success(f"검증 결과가 저장되었습니다! (Client {client_number}, Exp {exp_number})")
                st.session_state.current_experiment_index += 1
                
                # Also save progress
                save_validation_progress(firebase_ref, st.session_state.expert_name,
                                       st.session_state.current_experiment_index,
                                       st.session_state.validation_responses)
                st.rerun()
            else:
                st.error("저장 중 오류가 발생했습니다. 다시 시도해주세요.")

def save_validation_progress(firebase_ref, expert_name, current_index, responses):
    """Save validation progress to Firebase"""
    try:
        # Sanitize expert name for Firebase key
        sanitized_expert_name = sanitize_firebase_key(expert_name)
        progress_key = f"expert_progress_{sanitized_expert_name}"
        progress_data = {
            'current_index': current_index,
            'responses': responses,
            'timestamp': int(datetime.now().timestamp())
        }
        firebase_ref.child(progress_key).set(progress_data)
        return True
    except Exception as e:
        st.error(f"진행도 저장 실패: {e}")
        return False

# ================================
# Main Function
# ================================
def main():
    """Main function to route to appropriate page"""
    init_session_state()
    check_expert_login()
    
    # Display appropriate page based on stage
    stage = st.session_state.validation_stage
    
    if stage == 'intro':
        show_intro_page()
    elif stage == 'test':
        show_test_page()
    elif stage == 'validation':
        show_validation_page()
    else:
        st.error("알 수 없는 단계입니다.")

if __name__ == "__main__":
    main()
