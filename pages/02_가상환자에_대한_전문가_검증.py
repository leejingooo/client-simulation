import streamlit as st
from datetime import datetime
from Home import check_participant
from firebase_config import get_firebase_ref
from SP_utils import (
    load_from_firebase, 
    create_conversational_agent, 
    get_diag_from_given_information,
    load_prompt_and_get_version,
    sanitize_key
)
from sp_construct_generator import create_sp_construct
from langchain_core.messages import HumanMessage, AIMessage
import json

# ================================
# PRESET - SP 순서 설정
# ================================
# 각 항목은 (page_number, client_number) 튜플
# page_number: 1-14 (화면에 표시되는 순서)
# client_number: 6101-6107 (실제 SP 번호, 각 SP를 2번씩)
SP_SEQUENCE = [
    (1, 6201),
    (2, 6202),
    (3, 6203),
    (4, 6204),
    (5, 6205),
    (6, 6206),
    (7, 6207),
    (8, 6203),  # 두 번째 라운드
    (9, 6201),
    (10, 6204),
    (11, 6207),
    (12, 6202),
    (13, 6206),
    (14, 6205),
]

DIAGNOSES_INFO = """
가상환자 14개의 케이스는 다음 진단명/나이/성별 중에 하나를 가집니다.

- Major depressive disorder / 40 / F
- Bipolar 1 disorder, currently mania / 25 / M
- Panic disorder / 25 / F
- Generalized anxiety disorder / 35 / F
- Social anxiety disorder / 30 / M
- Obsessive-compulsive disorder / 25 / M
- Post-traumatic stress disorder / 30 / F
"""

DIAGNOSIS_OPTIONS = [
    "Major depressive disorder",
    "Bipolar 1 disorder, currently mania",
    "Panic disorder",
    "Generalized anxiety disorder",
    "Social anxiety disorder",
    "Obsessive-compulsive disorder",
    "Post-traumatic stress disorder"
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
        st.session_state.sp_validation_stage = 'intro'  # intro, practice, validation
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
    st.title("📋 가상환자에 대한 전문가 검증")
    st.markdown("---")
    
    st.markdown("""
    ## 검증 프로세스 안내
    
    안녕하세요, 전문가님.
    본 시스템은 **"가상환자"가 얼마나 "실제 환자"와 비슷한지 평가**
    하기 위한 전문가 평가 도구입니다.
    
    ### 📌 절차
    
    1. **연습 단계**: 먼저 연습용 페이지에서 검증 방법을 연습합니다.
    2. **실제 검증**: 총 **14명**의 가상환자와 면담하면서 검증합니다.
    3. **자동 저장**: 각 가상환자 검증 완료 시 자동으로 저장됩니다.
    
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
    
    위 과정을 모든 가상환자 (1-14, 총 14명) 에 대하여 진행해주시면 됩니다.
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
    
    # Get current SP info
    if st.session_state.current_sp_index >= len(SP_SEQUENCE):
        show_completion_page()
        return
    
    page_number, client_number = SP_SEQUENCE[st.session_state.current_sp_index]
    
    # Progress bar
    progress = (st.session_state.current_sp_index) / len(SP_SEQUENCE)
    st.progress(progress, text=f"진행도: {st.session_state.current_sp_index}/{len(SP_SEQUENCE)}")
    
    st.title(f"가상환자 {page_number}")
    st.caption(f"Client Number: {client_number} (내부 번호)")
    
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
        
        위 과정을 모든 가상환자 (1-14, 총 14명) 에 대하여 진행해주시면 됩니다.
        
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
    
    if not all([profile, history, beh_dir, given_information]):
        st.error(f"Client {client_number} 데이터를 불러올 수 없습니다. 연구진에게 문의해주세요.")
        return
    
    # Get SP construct
    given_form_path = f"data/prompts/paca_system_prompt/given_form_version{con_agent_version}.json"
    sp_construct = create_sp_construct(
        client_number,
        f"{profile_version:.1f}",
        f"{beh_dir_version:.1f}",
        given_form_path
    )
    
    # Get diagnosis for system prompt
    diag = get_diag_from_given_information(given_information)
    if diag == "BD":
        con_agent_system_prompt, _ = load_prompt_and_get_version("con-agent", con_agent_version, diag)
    else:
        con_agent_system_prompt, _ = load_prompt_and_get_version("con-agent", con_agent_version)
    
    # Create unique session key for each expert and SP
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
        st.caption("안녕하세요, 저는 정신과 의사 000입니다. 로 면담을 시작해주세요.")
        
        # Display conversation history
        for message in memory.messages:
            if isinstance(message, HumanMessage):
                with st.chat_message("user"):
                    st.markdown(message.content)
            else:
                with st.chat_message("assistant"):
                    st.markdown(message.content)
                with st.chat_message("user" if isinstance(message, HumanMessage) else "assistant"):
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
            # Reset memory
            from SP_utils import reset_agent_memory
            st.session_state[session_key] = reset_agent_memory((agent, memory))
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
            # This is simplified - you may need to adjust based on actual structure
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
            시뮬레이션된 환자를 평가하실 때에는, 해당 진단을 고려하였을 때 제공된 대화 기록에서 환자가 발화한 내용이 임상적으로 타당한 표현인지에만 집중해 주십시오.
                        
            평가자의 과제는 환자의 언어적 표현이 기분(mood), 정동(affect), 사고 과정(thought process), 사고 내용(thought content), 병식(insight), 자살 사고/계획/시도, 타해 사고(homicidal ideation) 등의 임상적 영역에서 얼마나 그럴듯하게 나타나는지를, 오직 발화 내용과 전체적인 패턴을 기준으로 판단하는 것입니다.
                        
            면담자의 질문 방식이나 면담 기술은 평가 대상에서 제외해 주십시오.
            
            각 대화 기록을 검토하실 때, 시뮬레이션된 환자의 표현 방식이 해당 진단에서 일반적으로 관찰되는 임상적 양상과 부합하는지를 아래 **Rating scale**을 바탕으로 평가해 주시고,
            
            항목별로 특히 그럴듯하게 느껴진 부분과 그렇지 않았던 부분을 간단히 기록해 주시기 바랍니다.
            
            또한 미리 제시된 항목에 포함되지 않더라도, 대화 내용에서 추가로 임상적으로 합당하거나 그렇지 않다고 판단되는 점이 있다면 자유롭게 의견을 적어 주셔도 됩니다.
                        
            ---
            #### Rating Scale (1–5 Likert)
            For each psychiatric element, rate:
            
            **"To what extent does the simulated patient's verbal presentation show a clinically plausible manifestation of this element for a real patient with the given diagnosis?"**
            
            - **1 — Clearly incompatible**
              - Strongly contradicts expected clinical presentation
              - Highly implausible or misleading for this diagnosis
              - Would make you question whether the patient has this condition
            
            - **2 — Weakly compatible / atypical**
              - Could appear in rare or atypical cases
              - Generally inconsistent with common clinical experience
            
            - **3 — Plausible but non-specific**
              - Reasonably compatible
              - Could fit several disorders
              - Not strongly characteristic
            
            - **4 — Typical**
              - Commonly seen in patients with this diagnosis
              - Clinically appropriate and realistic
            
            - **5 — Prototypical**
              - Very characteristic or textbook-like
              - Strongly aligns with typical clinical phenomenology
            
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
        
        # Save buttons
        col_save1, col_save2 = st.columns(2)
        
        with col_save1:
            if st.button("💾 중간 저장", use_container_width=True):
                save_sp_validation(firebase_ref, page_number, client_number, responses, memory, is_final=False)
                st.success("중간 저장되었습니다!")
        
        with col_save2:
            if st.button("✅ 검증 완료 및 다음으로", type="primary", use_container_width=True):
                # Validate that all non-empty items are selected
                missing_items = []
                
                # Check element responses
                for element in VALIDATION_ELEMENTS:
                    sp_content = get_sp_value(sp_construct, element)
                    is_empty = sp_content is None or str(sp_content).strip() == '' or str(sp_content).lower() in ['none', 'n/a', 'null']
                    
                    # Only check non-empty items
                    if not is_empty:
                        if element not in responses or not responses[element]:
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
                
                # If there are missing items, show error and don't proceed
                if missing_items:
                    # Separate required vs recommended
                    required_missing = [item for item in missing_items if item != "총평 (권장 사항)"]
                    recommended_missing = [item for item in missing_items if item == "총평 (권장 사항)"]
                    
                    error_msg = ""
                    if required_missing:
                        error_msg += f"⚠️ 다음 필수 항목이 선택되지 않았습니다:\n\n" + "\n".join([f"- {item}" for item in required_missing])
                    
                    if recommended_missing:
                        if error_msg:
                            error_msg += "\n\n"
                        error_msg += f"💡 다음 권장 항목이 비어있습니다:\n\n" + "\n".join([f"- {item}" for item in recommended_missing])
                    
                    # Only block if required items are missing
                    if required_missing:
                        st.error(error_msg + "\n\n모든 필수 항목을 선택한 후 다시 시도해주세요.")
                    else:
                        # Only recommended items missing - show warning but allow proceeding
                        st.warning(error_msg + "\n\n계속 진행하려면 다시 버튼을 클릭해주세요.")
                        # Set a flag to allow next click to proceed
                        if 'allow_skip_comment' not in st.session_state:
                            st.session_state.allow_skip_comment = True
                        elif st.session_state.allow_skip_comment:
                            # Second click - proceed
                            del st.session_state.allow_skip_comment
                            # Final save
                            save_sp_validation(firebase_ref, page_number, client_number, responses, memory, is_final=True)
                            
                            # Move to next SP
                            st.session_state.current_sp_index += 1
                            
                            # Clear session for this SP
                            if session_key in st.session_state:
                                del st.session_state[session_key]
                            
                            st.success("검증이 완료되었습니다! 다음 가상환자로 이동합니다.")
                            st.rerun()
                else:
                    # All items selected - proceed
                    # Final save
                    save_sp_validation(firebase_ref, page_number, client_number, responses, memory, is_final=True)
                    
                    # Move to next SP
                    st.session_state.current_sp_index += 1
                    
                    # Clear session for this SP
                    if session_key in st.session_state:
                        del st.session_state[session_key]
                    
                    st.success("검증이 완료되었습니다! 다음 가상환자로 이동합니다.")
                    st.rerun()


def save_sp_validation(firebase_ref, page_number, client_number, responses, memory, is_final=True):
    """Save SP validation result to Firebase
    
    Args:
        firebase_ref: Firebase reference
        page_number: SP page number (1-14)
        client_number: Client number (6101-6107)
        responses: Validation responses dict
        memory: LangChain memory object with conversation history
        is_final: Whether this is final save (True) or mid-save (False)
    """
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
            # Get SP content
            profile_version = 6.0
            beh_dir_version = 6.0
            con_agent_version = 6.0
            given_form_path = f"data/prompts/paca_system_prompt/given_form_version{con_agent_version:.1f}.json"
            sp_construct = create_sp_construct(
                client_number,
                f"{profile_version:.1f}",
                f"{beh_dir_version:.1f}",
                given_form_path
            )
            from evaluator import get_value_from_construct
            sp_content = get_value_from_construct(sp_construct, element)
            
            validation_result['elements'][element] = {
                'sp_content': str(sp_content) if sp_content else '',
                'expert_choice': responses[element]
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


def show_completion_page():
    """Display completion page"""
    st.title("🎉 모든 검증이 완료되었습니다!")
    st.markdown("---")
    
    st.success("""
    **14명의 가상환자에 대한 검증을 모두 완료하셨습니다.**
    
    연구에 참여해주셔서 진심으로 감사드립니다.
    
    모든 데이터가 안전하게 저장되었습니다.
    """)
    
    # if st.button("처음으로 돌아가기"):
    #     st.session_state.sp_validation_stage = 'intro'
    #     st.session_state.current_sp_index = 0
    #     st.rerun()


# ================================
# Main Page Controller
# ================================
def main():
    st.set_page_config(
        page_title="가상환자에 대한 전문가 검증",
        page_icon="📋",
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
