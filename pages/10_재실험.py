import streamlit as st
from datetime import datetime
from Home import check_participant
from firebase_config import get_firebase_ref
from SP_utils import (
    load_from_firebase, 
    create_conversational_agent, 
    get_diag_from_given_information,
    load_prompt_and_get_version,
    sanitize_key,
    remove_detailed_examples_from_profile
)
from sp_construct_generator import create_sp_construct
from langchain_core.messages import HumanMessage, AIMessage

# ================================
# PRESET - SP 순서 설정 (6301번 MDD 2회 반복)
# ================================
SP_SEQUENCE = [
    (1, 6301),
    (2, 6301),
]

DIAGNOSES_INFO = """
-
"""

DIAGNOSIS_OPTIONS = [
    "Major depressive disorder",
]

# SP Construct에서 검증할 Element (length 제외한 24개)
VALIDATION_ELEMENTS = [
    "Chief complaint",
    "Symptom name",
    "Alleviating factor",
    "Exacerbating factor",
    "Triggering factor",
    "Stressor",
    "Diagnosis",
    "Substance use",
    "Current family structure",
    "Suicidal ideation",
    "Self mutilating behavior risk",
    "Homicide risk",
    "Suicidal plan",
    "Suicidal attempt",
    "Mood",
    "Verbal productivity",
    "Insight",
    "Affect",
    "Perception",
    "Thought process",
    "Thought content",
    "Spontaneity",
    "Social judgement",
    "Reliability"
]

# ================================
# Session State Initialization
# ================================
def init_session_state():
    """Initialize session state variables"""
    if 'sp_validation_stage' not in st.session_state:
        st.session_state.sp_validation_stage = 'intro'
    if 'current_sp_index' not in st.session_state:
        st.session_state.current_sp_index = 0
    if 'sp_validation_responses' not in st.session_state:
        st.session_state.sp_validation_responses = {}
    if 'sp_validation_progress' not in st.session_state:
        st.session_state.sp_validation_progress = {}
    if 'expert_name' not in st.session_state:
        st.session_state.expert_name = None


# ================================
# Page 1: Introduction
# ================================
def show_intro_page():
    """Display introduction page with instructions"""
    st.title("🔬 재실험")
    st.markdown("---")
    
    st.markdown("""
    ## 검증 프로세스 안내
    
    안녕하세요, 전문가님.
    본 시스템은 **"가상환자"가 얼마나 "실제 환자"와 비슷한지 평가**
    하기 위한 전문가 평가 도구입니다.
    
    ### 📌 절차
    
    1. **연습 단계**: 먼저 연습용 페이지에서 검증 방법을 연습합니다.
    2. **실제 검증**: **2회**의 면담을 진행하면서 가상환자를 검증합니다.
    3. **자동 저장**: 각 검증 완료 시 자동으로 저장됩니다.
    
    ### ✅ 검증 방법
    
    평가 항목들은 가상환자에게 그렇게 시뮬레이션 하도록 지시된 것들입니다.
    **가상환자와 면담을 진행하시면서,**
    가상환자가 **각 항목을 잘 시뮬레이션 하는지 평가**해주세요.
    
    **예시:**
    
    **Mood : Depressed**
    
    ☑︎ 적절함 = "가상환자가 Depressed Mood를 적절히 시뮬레이션 하고 있음"
    
    ◻︎ 적절하지 않음 = "그렇지 못함"
    
    **Affect : Restricted**
    
    ☑︎ 적절함 = "가상환자가 Restricted Affect를 적절히 시뮬레이션 하고 있음"
    
    ◻︎ 적절하지 않음 = "그렇지 못함"
    
    ### ⚠️ 유의사항
    
    **유의사항 1**: 위 평가 항목을 모두 평가할 수 있도록 면담을 진행하셔야 합니다.
    
    **유의사항 2**: 실제 환자를 외래에서 보시는 것처럼 면담을 진행해주세요. 
    진행하신 면담 내역을 바탕으로 본 연구가 제시하는 방법론을 기반으로 환자 만족도 평가 (친절함 등)를 진행할 예정입니다. 
    환자 만족도 평가를 진행하는 이유는 면담이 잘 진행되었는지 판단하기 위함이 아니며, 
    본 연구가 제시하는 평가 방법론을 검증하기 위함입니다.
    
    모든 항목에 대해 평가가 완료되었고 면담이 종료되었다면, 다음으로 버튼을 눌러주세요.
    
    위 과정을 총 **2회** 진행해주시면 됩니다.
    """)
    
    st.markdown("---")
    st.info(DIAGNOSES_INFO)
    
    st.markdown("---")
    if st.button("다음 → 연습 단계로", type="primary", use_container_width=True):
        st.session_state.sp_validation_stage = 'practice'
        st.rerun()


# ================================
# Page 2: Practice
# ================================
def show_practice_page():
    """Display practice page"""
    st.title("🎯 연습 페이지")
    st.markdown("---")
    
    st.info("이 페이지는 연습용입니다. 실제 검증과 동일한 방식으로 진행되지만 저장되지 않습니다.")
    
    # 2-Column Layout for practice
    col_left, col_right = st.columns([1, 1])
    
    # ===== LEFT COLUMN: Practice Conversation (Frozen) =====
    with col_left:
        st.markdown("### 💬 면담 (연습용 - 비활성화)")
        st.caption("안녕하세요, 저는 정신과 의사 000입니다. 로 면담을 시작해주세요.")
        
        # Display example conversation (frozen)
        example_messages = [
            ("user", "안녕하세요, 저는 정신과 의사 김철수입니다. 오늘 어떻게 오시게 되셨나요?"),
            ("assistant", "요즘... 잠을 잘 못 자서요. 계속 걱정이 되고...")
        ]
        
        for role, content in example_messages:
            with st.chat_message(role):
                st.markdown(content)
        
        # Disabled chat input
        st.text_input("면담 내용 (연습용 - 비활성화)", disabled=True, placeholder="실제 검증 페이지에서 활성화됩니다")
    
    # ===== RIGHT COLUMN: Practice Validation =====
    with col_right:
        st.markdown("### 검증 방법 연습")
        
        st.markdown("**예시: Chief complaint - 요즘 계속 우울하고 불안해요**")
        
        practice_choice = st.radio(
            "가상환자가 이 증상을 적절하게 표현했습니까?",
            options=["적절함", "적절하지 않음"],
            key="practice_1",
            horizontal=True
        )
        
        st.markdown("**예시: Mood - Depressed**")
        
        practice_choice2 = st.radio(
            "가상환자가 우울한 기분을 적절하게 시뮬레이션 했습니까?",
            options=["적절함", "적절하지 않음"],
            key="practice_2",
            horizontal=True
        )
        
        st.markdown("---")
        st.success("✅ 이런 방식으로 각 항목을 평가하시면 됩니다!")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 이전 (설명으로)", use_container_width=True):
            st.session_state.sp_validation_stage = 'intro'
            st.rerun()
    
    with col2:
        if st.button("다음 → 실제 검증 시작", type="primary", use_container_width=True):
            st.session_state.sp_validation_stage = 'validation'
            st.session_state.current_sp_index = 0
            st.rerun()


# ================================
# Page 3+: Actual Validation
# ================================
def show_validation_page():
    """Display actual validation page with 2-column layout"""
    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error("Firebase 초기화 실패. 연구진에게 문의해주세요.")
        st.stop()
    
    # Load progress from Firebase if not already loaded
    expert_name = st.session_state.expert_name
    if 'sp_progress_loaded' not in st.session_state:
        progress_data = load_sp_validation_progress(firebase_ref, expert_name)
        if progress_data and 'current_index' in progress_data:
            st.session_state.current_sp_index = progress_data['current_index']
            st.info(f"💾 이전 데이터를 불러왔습니다. (검증 {st.session_state.current_sp_index + 1}/{len(SP_SEQUENCE)})")
        st.session_state.sp_progress_loaded = True
    
    # Get current SP info
    all_completed = st.session_state.current_sp_index >= len(SP_SEQUENCE)
    
    if all_completed:
        st.success("🎉 모든 검증이 완료되었습니다!")
        st.markdown("**2회의 검증을 모두 완료하셨습니다.**")
        st.markdown("연구에 참여해주셔서 진심으로 감사드립니다.")
        st.info("💡 이전 검증 항목을 수정하려면 아래에서 항목을 선택하세요.")
        st.markdown("---")
        
        # Allow user to select which SP to review/edit
        col1, col2 = st.columns([3, 1])
        with col1:
            sp_options = [f"검증 {page}회차" 
                         for page, client in SP_SEQUENCE]
            selected_option = st.selectbox(
                "수정할 검증 회차 선택",
                options=sp_options,
                index=min(st.session_state.current_sp_index, len(SP_SEQUENCE) - 1)
            )
            selected_idx = sp_options.index(selected_option)
        
        with col2:
            if st.button("선택한 항목으로 이동", use_container_width=True, type="primary"):
                st.session_state.current_sp_index = selected_idx
                st.rerun()
        
        st.markdown("---")
        # Set index to selected SP for display
        st.session_state.current_sp_index = selected_idx
    
    # Ensure index is within bounds
    if st.session_state.current_sp_index >= len(SP_SEQUENCE):
        st.session_state.current_sp_index = len(SP_SEQUENCE) - 1
    
    page_number, client_number = SP_SEQUENCE[st.session_state.current_sp_index]
    
    # Progress bar
    progress = (st.session_state.current_sp_index) / len(SP_SEQUENCE)
    if all_completed:
        st.progress(1.0, text=f"진행도: {len(SP_SEQUENCE)}/{len(SP_SEQUENCE)} ✅ 완료")
    else:
        st.progress(progress, text=f"진행도: {st.session_state.current_sp_index}/{len(SP_SEQUENCE)}")
    
    st.title(f"검증 {page_number}회차")
    
    # Display instructions in an expander at the top
    with st.expander("📖 검증 안내사항 (클릭하여 펼치기/접기)", expanded=False):
        st.markdown("""
        ## 검증 프로세스 안내
        
        본 시스템은 **"가상환자"가 얼마나 "실제 환자"와 비슷한지 평가**
        하기 위한 전문가 평가 도구입니다.
        
        ### ✅ 검증 방법
        
        평가 항목들은 가상환자에게 그렇게 시뮬레이션 하도록 지시된 것들입니다.
        **가상환자와 면담을 진행하시면서,**
        가상환자가 **각 항목을 잘 시뮬레이션 하는지 평가**해주세요.
        
        **예시:**
        
        **Mood : Depressed**
        
        ☑︎ 적절함 = "가상환자가 Depressed Mood를 적절히 시뮬레이션 하고 있음"
        
        ◻︎ 적절하지 않음 = "그렇지 못함"
        
        **Affect : Restricted**
        
        ☑︎ 적절함 = "가상환자가 Restricted Affect를 적절히 시뮬레이션 하고 있음"
        
        ◻︎ 적절하지 않음 = "그렇지 못함"
        
        ### ⚠️ 유의사항
        
        **유의사항 1**: 위 평가 항목을 모두 평가할 수 있도록 면담을 진행하셔야 합니다.
        
        **유의사항 2**: 실제 환자를 외래에서 보시는 것처럼 면담을 진행해주세요. 
        진행하신 면담 내역을 바탕으로 본 연구가 제시하는 방법론을 기반으로 환자 만족도 평가 (친절함 등)를 진행할 예정입니다. 
        환자 만족도 평가를 진행하는 이유는 면담이 잘 진행되었는지 판단하기 위함이 아니며, 
        본 연구가 제시하는 평가 방법론을 검증하기 위함입니다.
        
        모든 항목에 대해 평가가 완료되었고 면담이 종료되었다면, 다음으로 버튼을 눌러주세요.
        
        ### 진단명 정보
        """)
        st.info(DIAGNOSES_INFO)
    
    st.markdown("---")
    
    # Load SP data
    profile_version = 6.0
    beh_dir_version = 6.0
    con_agent_version = 6.0
    
    profile = load_from_firebase(firebase_ref, client_number, f"profile_version6_0")
    history = load_from_firebase(firebase_ref, client_number, f"history_version6_0")
    beh_dir = load_from_firebase(firebase_ref, client_number, f"beh_dir_version6_0")
    given_information = load_from_firebase(firebase_ref, client_number, "given_information")
    
    if not all([profile, history, beh_dir]):
        st.error(f"Client {client_number} 데이터를 불러올 수 없습니다.")
        st.warning("18_MDD_MFC_Editor 페이지에서 MFC 데이터를 확인하거나, 19_MFC_Copier 페이지에서 데이터를 복제해주세요.")
        return
    
    # Get SP construct
    given_form_path = f"data/prompts/paca_system_prompt/given_form_version{con_agent_version}.json"
    
    # Remove detailed examples from profile for UI display (e.g., impulsivity explanations)
    profile_for_construct = remove_detailed_examples_from_profile(profile)
    
    sp_construct = create_sp_construct(
        client_number,
        f"{profile_version:.1f}",
        f"{beh_dir_version:.1f}",
        given_form_path,
        profile_override=profile_for_construct
    )
    
    # Get diagnosis for system prompt
    if given_information:
        diag = get_diag_from_given_information(given_information)
    else:
        diag = "MDD"  # Default for 6301
    
    if diag == "BD":
        con_agent_system_prompt, _ = load_prompt_and_get_version("con-agent", con_agent_version, diag)
    else:
        con_agent_system_prompt, _ = load_prompt_and_get_version("con-agent", con_agent_version)
    
    # Create unique session key for each expert and SP
    # CRITICAL: session_key ensures memory isolation between different page_numbers
    expert_name = st.session_state.expert_name
    session_key = f"sp_validation_{expert_name}_{page_number}_{client_number}"
    
    # Initialize agent for this specific SP and expert
    if session_key not in st.session_state:
        agent, memory = create_conversational_agent(
            "6_0", "6_0", client_number, con_agent_system_prompt
        )
        
        # Try to load previously saved conversation history
        conversation_key = f"sp_conversation_{sanitize_key(expert_name)}_{client_number}_{page_number}"
        saved_conversation = firebase_ref.child(conversation_key).get()
        
        if saved_conversation and 'conversation' in saved_conversation:
            st.info("💬 이전 대화 내역을 불러왔습니다.")
            # Add messages to memory
            for msg_data in saved_conversation['conversation']:
                if msg_data['role'] == 'user':
                    memory.add_message(HumanMessage(content=msg_data['content']))
                else:
                    memory.add_message(AIMessage(content=msg_data['content']))
        
        st.session_state[session_key] = {'agent': agent, 'memory': memory}
    
    agent_data = st.session_state[session_key]
    agent = agent_data['agent']
    memory = agent_data['memory']
    
    # 2-Column Layout
    col_left, col_right = st.columns([1, 1])
    
    # ===== LEFT COLUMN: Conversation =====
    with col_left:
        st.markdown("### 💬 면담")
        st.caption("안녕하세요, 저는 정신과 의사 000입니다. 오늘 어떤 일로 오셨나요? 로 면담을 시작해주세요.")
        
        # Display conversation history
        for message in memory.messages:
            if isinstance(message, HumanMessage):
                with st.chat_message("user"):
                    st.markdown(message.content)
            else:
                with st.chat_message("assistant"):
                    st.markdown(message.content)
        
        # Chat input
        if prompt := st.chat_input("면담 내용을 입력하세요"):
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = agent(prompt)
                message_placeholder.markdown(full_response)
            
            st.rerun()
        
        # New conversation button
        if st.button("🔄 대화 초기화 (면담 처음부터 다시 시작)", use_container_width=True):
            # Delete the session key to force recreation of agent with fresh memory
            if session_key in st.session_state:
                del st.session_state[session_key]
            st.success("대화가 초기화되었습니다.")
            st.rerun()
    
    # ===== RIGHT COLUMN: Validation Form =====
    with col_right:
        st.markdown("### ✅ 검증 항목")
        
        # Initialize response dict for this SP
        response_key = f"sp_{page_number}_{client_number}"
        if response_key not in st.session_state.sp_validation_responses:
            st.session_state.sp_validation_responses[response_key] = {}
            
            # Try to load previously saved data
            expert_name = st.session_state.expert_name
            validation_key = f"sp_validation_{sanitize_key(expert_name)}_{client_number}_{page_number}"
            saved_data = firebase_ref.child(validation_key).get()
            
            if saved_data:
                st.info("💾 이전에 저장된 데이터를 불러왔습니다.")
                # Load element responses
                if 'elements' in saved_data:
                    for elem_name, elem_data in saved_data['elements'].items():
                        if 'expert_choice' in elem_data:
                            st.session_state.sp_validation_responses[response_key][elem_name] = elem_data['expert_choice']
                
                # Load qualitative evaluation
                if 'qualitative' in saved_data:
                    st.session_state.sp_validation_responses[response_key]['qualitative'] = saved_data['qualitative']
                
                # Load additional impressions
                if 'additional_impressions' in saved_data:
                    st.session_state.sp_validation_responses[response_key]['additional_impressions'] = saved_data['additional_impressions']
        
        responses = st.session_state.sp_validation_responses[response_key]
        
        # Flatten SP construct to get values
        def get_sp_value(construct, element_name):
            """Extract value from SP construct"""
            from evaluator import get_value_from_construct
            return get_value_from_construct(construct, element_name)
        
        # Display validation items
        st.markdown("#### 각 항목에 대해 가상환자가 적절하게 시뮬레이션 했는지 평가해주세요")
        
        for element in VALIDATION_ELEMENTS:
            sp_content = get_sp_value(sp_construct, element)
            
            # Check if SP content is None or empty
            is_empty = sp_content is None or str(sp_content).strip() == '' or str(sp_content).lower() in ['none', 'n/a', 'null']
            
            # Determine display title and help text
            display_title = element
            help_text = None
            
            if element == "Triggering factor":
                help_text = "💡 환자가 왜 하필 오늘 병원을 찾게 된 이유"
            elif element == "Stressor":
                help_text = "💡 증상 유발 요인"
            elif element == "Diagnosis":
                display_title = "Family History - Diagnosis"
                help_text = "⚠️ 가족력의 정신과적 진단명입니다 (환자 본인의 진단명이 아님)"
            elif element == "Substance use":
                display_title = "Family History - Substance use"
                help_text = "⚠️ 가족의 물질 사용력입니다 (환자 본인의 물질 사용력이 아님)"
            
            # Display element with SP content
            with st.expander(f"**{display_title}**", expanded=False):
                if is_empty:
                    st.info("ℹ️ 지시된 내용이 없어 자동으로 '적절함' 처리되었습니다.")
                    st.markdown(f"**가상환자에게 지시된 내용:** (없음)")
                    # Auto-set to '적절함'
                    responses[element] = "적절함"
                else:
                    st.markdown(f"**가상환자에게 지시된 내용:**\n{sp_content}")
                    
                    # Display help text if available
                    if help_text:
                        st.caption(help_text)
                    
                    # Radio button for validation (only if content exists)
                    current_value = responses.get(element, "선택 안함")
                    if current_value not in ["선택 안함", "적절함", "적절하지 않음"]:
                        current_value = "선택 안함"
                    
                    choice = st.radio(
                        "가상환자는 위 내용을 적절히 시뮬레이션 하였습니까?",
                        options=["선택 안함", "적절함", "적절하지 않음"],
                        key=f"validation_{response_key}_{element}",
                        index=["선택 안함", "적절함", "적절하지 않음"].index(current_value),
                        horizontal=True
                    )
                    responses[element] = choice
        
        st.markdown("---")
        st.markdown("### 📊 질적 검증 섹션")
        
        # Display guideline in expander
        with st.expander("📖 평가 가이드라인 (클릭하여 펼치기/접기)", expanded=False):
            st.markdown("""
            아래 각 정신과적 요소에 대해, 가상환자의 면담 내용이 실제 환자의 표현과 얼마나 잘 일치하는지 평가해주세요.
            
            **평가 척도:**
            
            - **1 — Clearly incompatible**: 명백히 실제 환자와 맞지 않음
            - **2 — Weakly compatible / atypical**: 약간 어울리거나 비전형적
            - **3 — Plausible but non-specific**: 그럴듯하지만 비특이적
            - **4 — Typical**: 전형적임
            - **5 — Prototypical**: 매우 전형적, 모범적
            
            각 요소에 대해:
            1. **Rating**: 위 척도로 평가
            2. **Plausible features**: 타당한 특징들을 나열
            3. **Implausible features**: 타당하지 않은 특징들을 나열
            
            ---
            
            ### 평가 요소 설명
            
            1. **Mood**: 환자가 언어로 표현한 주관적 기분 상태
            2. **Affect**: 언어 표현에서 추론되는 정동 (감정의 외적 표현)
            3. **Thought Process**: 사고의 진행 방식 (논리적, 우회적, 비약적, 관념분산, 사고차단 등)
            4. **Thought Content**: 사고의 내용 (부정적 인지, 강박사고, 망상, 집착 등)
            5. **Insight**: 질병에 대한 환자의 인식 및 도움 필요성에 대한 인식
            6. **Suicidal Ideation/Plan/Attempt**: 자살 관련 생각, 계획, 시도 (언어적 표현)
            7. **Homicidal Ideation**: 타해 관련 생각 (해당되는 경우)
            """)
        
        st.markdown("---")
        
        # Define psychiatric elements for evaluation
        PSYCHIATRIC_ELEMENTS = [
            {
                'name': 'Mood',
                'key': 'mood',
                'description': ''
            },
            {
                'name': 'Affect',
                'key': 'affect',
                'description': '(as inferred from language)'
            },
            {
                'name': 'Thought Process',
                'key': 'thought_process',
                'description': '(linear, circumstantial, tangential, FOI, blocking, etc.)'
            },
            {
                'name': 'Thought Content',
                'key': 'thought_content',
                'description': '(negative cognitions, obsessions, delusions, preoccupations)'
            },
            {
                'name': 'Insight',
                'key': 'insight',
                'description': "(patient's awareness of illness, need for help)"
            },
            {
                'name': 'Suicidal Ideation / Plan / Attempt',
                'key': 'suicidal',
                'description': '(as verbally expressed)'
            },
            {
                'name': 'Homicidal Ideation',
                'key': 'homicidal',
                'description': '(if applicable in transcript)'
            }
        ]
        
        # Initialize qualitative responses if not exists
        if 'qualitative' not in responses:
            responses['qualitative'] = {}
        
        # Rating scale options
        rating_options = [
            "1 — Clearly incompatible",
            "2 — Weakly compatible / atypical",
            "3 — Plausible but non-specific",
            "4 — Typical",
            "5 — Prototypical"
        ]
        
        # Evaluate each psychiatric element
        for idx, element in enumerate(PSYCHIATRIC_ELEMENTS, 1):
            st.markdown(f"#### {idx}. {element['name']}")
            if element['description']:
                st.caption(element['description'])
            
            element_key = element['key']
            
            # Initialize element data if not exists
            if element_key not in responses['qualitative']:
                responses['qualitative'][element_key] = {
                    'rating': None,
                    'plausible_aspects': '',
                    'less_plausible_aspects': ''
                }
            
            # Rating
            current_rating = responses['qualitative'][element_key].get('rating')
            if current_rating and isinstance(current_rating, int):
                # Convert int to index (1-5 -> 0-4)
                current_index = current_rating - 1
            else:
                current_index = 2  # Default to middle option (3)
            
            selected_rating = st.radio(
                f"Rating for {element['name']}",
                options=rating_options,
                index=current_index,
                key=f"qual_rating_{response_key}_{element_key}",
                horizontal=False,
                label_visibility="collapsed"
            )
            
            # Extract numeric rating (1-5)
            rating_value = int(selected_rating.split("—")[0].strip())
            responses['qualitative'][element_key]['rating'] = rating_value
            
            # Plausible aspects
            plausible = st.text_area(
                "What aspects of the dialogue made this plausible?",
                value=responses['qualitative'][element_key].get('plausible_aspects', ''),
                key=f"qual_plausible_{response_key}_{element_key}",
                height=80,
                placeholder="Describe what aspects made this clinically plausible..."
            )
            responses['qualitative'][element_key]['plausible_aspects'] = plausible
            
            # Less plausible aspects
            less_plausible = st.text_area(
                "What aspects appeared less plausible or contradictory?",
                value=responses['qualitative'][element_key].get('less_plausible_aspects', ''),
                key=f"qual_less_plausible_{response_key}_{element_key}",
                height=80,
                placeholder="Describe what aspects appeared less plausible..."
            )
            responses['qualitative'][element_key]['less_plausible_aspects'] = less_plausible
            
            st.markdown("---")
        
        # Additional impressions
        st.markdown("#### 8. Additional Clinically Relevant Impressions (Optional)")
        st.caption("Please list any additional clinically plausible or implausible features you noticed that were not directly asked about.")
        
        additional_impressions = st.text_area(
            "Additional impressions",
            value=responses.get('additional_impressions', ''),
            key=f"qual_additional_{response_key}",
            height=150,
            placeholder="Any other clinical observations...",
            label_visibility="collapsed"
        )
        responses['additional_impressions'] = additional_impressions
        
        st.markdown("---")
        
        # Save and navigation buttons
        col_save1, col_save2, col_save3 = st.columns(3)
        
        with col_save1:
            # Back button - only show if not on first SP
            if st.session_state.current_sp_index > 0:
                if st.button("⬅️ 이전으로", use_container_width=True):
                    # Save current state before going back
                    save_sp_validation(firebase_ref, page_number, client_number, responses, memory, is_final=False)
                    # Decrease index to go back
                    st.session_state.current_sp_index -= 1
                    # Save progress to Firebase
                    save_sp_validation_progress(firebase_ref, st.session_state.expert_name, st.session_state.current_sp_index)
                    # Clear current session to force reload of previous SP
                    if session_key in st.session_state:
                        del st.session_state[session_key]
                    st.rerun()
            else:
                st.write("")  # Empty placeholder
        
        with col_save2:
            if st.button("💾 중간 저장", use_container_width=True):
                save_sp_validation(firebase_ref, page_number, client_number, responses, memory, is_final=False)
                st.success("중간 저장되었습니다!")
        
        with col_save3:
            # Determine button text based on completion status
            if all_completed:
                next_button_text = "✅ 저장"
            elif st.session_state.current_sp_index == len(SP_SEQUENCE) - 1:
                next_button_text = "✅ 완료"
            else:
                next_button_text = "✅ 검증 완료 및 다음으로"
            
            if st.button(next_button_text, type="primary", use_container_width=True):
                # Validate that all non-empty items are selected
                missing_items = []
                
                # Check element responses
                for element in VALIDATION_ELEMENTS:
                    sp_content = get_sp_value(sp_construct, element)
                    is_empty = sp_content is None or str(sp_content).strip() == '' or str(sp_content).lower() in ['none', 'n/a', 'null']
                    
                    # Only check non-empty items
                    if not is_empty:
                        if element not in responses or not responses[element] or responses[element] == "선택 안함":
                            missing_items.append(element)
                
                # Check qualitative evaluation
                if 'qualitative' not in responses:
                    missing_items.append("Qualitative Evaluation (전체)")
                else:
                    PSYCHIATRIC_ELEMENTS_KEYS = ['mood', 'affect', 'thought_process', 'thought_content', 'insight', 'suicidal', 'homicidal']
                    for elem_key in PSYCHIATRIC_ELEMENTS_KEYS:
                        if elem_key not in responses['qualitative']:
                            missing_items.append(f"Qualitative Evaluation - {elem_key}")
                        else:
                            elem_data = responses['qualitative'][elem_key]
                            if not elem_data.get('rating'):
                                missing_items.append(f"Qualitative Evaluation - {elem_key} (rating)")
                            # Text fields are optional, only rating is required
                
                if missing_items:
                    st.error(f"⚠️ 다음 항목을 평가해주세요:\n\n" + "\n".join([f"- {item}" for item in missing_items]))
                    st.stop()
                
                # Final save
                save_sp_validation(firebase_ref, page_number, client_number, responses, memory, is_final=True)
                
                # If all completed, just save (don't move forward)
                if all_completed:
                    st.success("검증이 저장되었습니다!")
                    st.rerun()
                else:
                    # Move to next SP
                    st.session_state.current_sp_index += 1
                    
                    # Save progress to Firebase
                    save_sp_validation_progress(firebase_ref, st.session_state.expert_name, st.session_state.current_sp_index)
                    
                    # Clear current session to force agent recreation for next SP
                    if session_key in st.session_state:
                        del st.session_state[session_key]
                    
                    st.success("검증이 완료되었습니다! 다음 검증으로 이동합니다.")
                    st.rerun()


def save_sp_validation(firebase_ref, page_number, client_number, responses, memory, is_final=True):
    """Save SP validation result to Firebase"""
    expert_name = st.session_state.expert_name
    
    # Prepare validation result
    validation_result = {
        'page_number': page_number,
        'client_number': client_number,
        'expert_name': expert_name,
        'timestamp': datetime.now().isoformat(),
        'is_final': is_final,
        'elements': {},
        'qualitative': responses.get('qualitative', {}),
        'additional_impressions': responses.get('additional_impressions', '')
    }
    
    # Add element validations
    for element in VALIDATION_ELEMENTS:
        if element in responses:
            validation_result['elements'][element] = {
                'expert_choice': responses[element],
                'is_appropriate': responses[element] == "적절함"
            }
    
    # Save validation result
    validation_key = f"sp_validation_{sanitize_key(expert_name)}_{client_number}_{page_number}"
    firebase_ref.child(validation_key).set(validation_result)
    
    # Save conversation log
    conversation_log = []
    for msg in memory.messages:
        conversation_log.append({
            'role': 'user' if isinstance(msg, HumanMessage) else 'assistant',
            'content': msg.content
        })
    
    conversation_key = f"sp_conversation_{sanitize_key(expert_name)}_{client_number}_{page_number}"
    firebase_ref.child(conversation_key).set({
        'page_number': page_number,
        'client_number': client_number,
        'expert_name': expert_name,
        'timestamp': datetime.now().isoformat(),
        'conversation': conversation_log
    })


def save_sp_validation_progress(firebase_ref, expert_name, current_index):
    """Save SP validation progress to Firebase"""
    try:
        progress_key = f"sp_validation_progress_{sanitize_key(expert_name)}"
        firebase_ref.child(progress_key).set({
            'current_index': current_index,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        st.error(f"진행 상태 저장 실패: {str(e)}")


def load_sp_validation_progress(firebase_ref, expert_name):
    """Load SP validation progress from Firebase"""
    try:
        progress_key = f"sp_validation_progress_{sanitize_key(expert_name)}"
        return firebase_ref.child(progress_key).get()
    except Exception as e:
        st.error(f"진행 상태 불러오기 실패: {str(e)}")
        return None


# ================================
# Main Page Controller
# ================================
def main():
    st.set_page_config(
        page_title="재실험",
        page_icon="🔬",
        layout="wide"
    )
    
    # Check authentication
    if not check_participant():
        st.stop()
    
    # Set expert name from login
    if 'name' in st.session_state and st.session_state.get('name_correct', False):
        st.session_state.expert_name = st.session_state['name']
    else:
        st.error("로그인이 필요합니다.")
        st.stop()
    
    # Initialize session state
    init_session_state()
    
    # Display appropriate page based on stage
    if st.session_state.sp_validation_stage == 'intro':
        show_intro_page()
    elif st.session_state.sp_validation_stage == 'practice':
        show_practice_page()
    elif st.session_state.sp_validation_stage == 'validation':
        show_validation_page()


if __name__ == "__main__":
    main()
