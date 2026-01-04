"""
21_System_Prompt_Test.py
System Prompt를 실시간으로 수정하고 즉시 테스트할 수 있는 페이지
"""

import streamlit as st
from firebase_config import get_firebase_ref
from SP_utils import (
    load_from_firebase,
    create_conversational_agent,
    get_diag_from_given_information,
    sanitize_key
)
from langchain_core.messages import HumanMessage, AIMessage
import json

st.set_page_config(
    page_title="System Prompt Test",
    page_icon="🧪",
    layout="wide"
)

# Initialize Firebase
firebase_ref = get_firebase_ref()
if firebase_ref is None:
    st.error("Firebase 초기화 실패. 설정을 확인하세요.")
    st.stop()

# Initialize session state
if 'sp_test_mode' not in st.session_state:
    st.session_state.sp_test_mode = 'edit'  # 'edit' or 'chat'
if 'sp_test_agent' not in st.session_state:
    st.session_state.sp_test_agent = None
if 'sp_test_memory' not in st.session_state:
    st.session_state.sp_test_memory = None
if 'edited_prompt' not in st.session_state:
    st.session_state.edited_prompt = None
if 'prompt_reset_counter' not in st.session_state:
    st.session_state.prompt_reset_counter = 0
if 'show_message' not in st.session_state:
    st.session_state.show_message = None
if 'recall_failure_prob' not in st.session_state:
    st.session_state.recall_failure_prob = 1.0

# ================================
# Configuration
# ================================
CLIENT_NUMBER = 6301  # Default test client (MDD)
PROFILE_VERSION = "6_0"
BEH_DIR_VERSION = "6_0"

st.title("🧪 System Prompt Test")
st.markdown("System Prompt를 수정하고 즉시 가상환자(SP)를 테스트할 수 있습니다.")
st.markdown("---")

# Display any pending messages
if st.session_state.show_message:
    msg_type, msg_text = st.session_state.show_message
    if msg_type == "success":
        st.success(msg_text)
    elif msg_type == "info":
        st.info(msg_text)
    elif msg_type == "warning":
        st.warning(msg_text)
    elif msg_type == "error":
        st.error(msg_text)
    st.session_state.show_message = None

# ================================
# Mode: Edit System Prompt
# ================================
if st.session_state.sp_test_mode == 'edit':
    st.subheader("✏️ System Prompt 수정")
    
    # Load current system prompt from Firebase
    try:
        current_prompt = firebase_ref.child("system_prompts/con-agent_version6_0").get()
        if not current_prompt:
            st.error("❌ Firebase에 System Prompt가 없습니다.")
            st.warning("먼저 20_Upload_System_Prompt_to_Firebase 페이지에서 업로드해주세요.")
            st.stop()
    except Exception as e:
        st.error(f"System Prompt 로딩 실패: {str(e)}")
        st.stop()
    
    # Initialize edited_prompt if not set
    if st.session_state.edited_prompt is None:
        st.session_state.edited_prompt = current_prompt
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📄 현재 System Prompt**")
        st.text_area(
            "Current System Prompt (Read-only)",
            value=current_prompt,
            height=500,
            disabled=True,
            key="current_prompt_display"
        )
    
    with col2:
        st.markdown("**✍️ 수정할 System Prompt**")
        edited_prompt_text = st.text_area(
            "수정할 System Prompt",
            value=st.session_state.edited_prompt,
            height=500,
            key=f"edit_prompt_area_{st.session_state.prompt_reset_counter}",
            help="System Prompt를 수정하세요. {given_information}, {current_date}, {profile_json}, {history}, {behavioral_instruction}, {recall_failure_mode} 플레이스홀더는 반드시 유지해야 합니다."
        )
        st.session_state.edited_prompt = edited_prompt_text
    
    st.markdown("---")
    
    # Recall Failure Probability Setting
    st.subheader("⚙️ 설정")
    st.markdown("**Recall Failure 확률 (MDD 환자 전용)**")
    st.caption("MDD 환자가 과거 상세 질문에 대해 기억 회상 실패 모드를 활성화할 확률입니다.")
    
    recall_prob = st.slider(
        "확률 설정",
        min_value=0.0,
        max_value=1.0,
        value=st.session_state.recall_failure_prob,
        step=0.1,
        help="0.0 = 회상 실패 없음, 1.0 = 항상 회상 실패 모드 활성화"
    )
    st.session_state.recall_failure_prob = recall_prob
    
    st.markdown("---")
    
    # Validation
    required_placeholders = [
        "{given_information}",
        "{current_date}",
        "{profile_json}",
        "{history}",
        "{behavioral_instruction}",
        "{recall_failure_mode}"
    ]
    
    missing_placeholders = [p for p in required_placeholders if p not in st.session_state.edited_prompt]
    
    if missing_placeholders:
        st.error(f"⚠️ 필수 플레이스홀더가 누락되었습니다: {', '.join(missing_placeholders)}")
        st.info("위 플레이스홀더들은 SP 에이전트가 동작하는데 필수적입니다.")
    else:
        st.success("✅ 모든 필수 플레이스홀더가 포함되어 있습니다.")
    
    st.markdown("---")
    
    # Button to save and start test
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    
    with col_btn1:
        if st.button("🚀 테스트만 하기", type="primary", use_container_width=True, disabled=bool(missing_placeholders)):
            # Save to temporary location for testing
            try:
                firebase_ref.child("system_prompts/con-agent_version6_0_test").set(st.session_state.edited_prompt)
                st.session_state.sp_test_mode = 'chat'
                st.rerun()
            except Exception as e:
                st.error(f"임시 저장 실패: {str(e)}")
    
    with col_btn2:
        if st.button("🔄 수정 취소", use_container_width=True):
            st.session_state.edited_prompt = current_prompt
            st.session_state.prompt_reset_counter += 1  # Force widget recreation
            st.session_state.show_message = ("success", "수정 내용이 취소되었습니다.")
            st.rerun()
    
    with col_btn3:
        if st.button("💾 Firebase에 저장", type="secondary", use_container_width=True):
            try:
                firebase_ref.child("system_prompts/con-agent_version6_0").set(st.session_state.edited_prompt)
                st.session_state.prompt_reset_counter += 1  # Force widget recreation to sync
                st.session_state.show_message = ("success", "✅ System Prompt가 Firebase에 저장되었습니다!\n\n💡 참고: 10_재실험 페이지는 아직 로컬 파일을 사용하므로 이 변경사항이 적용되지 않습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {str(e)}")
    
    # Button explanations
    st.info("""
    **📌 버튼 설명**
    - **테스트만 하기**: 임시 경로에 저장하고 테스트
    - **수정 취소**: 우측의 수정 내용을 좌측의 원본으로 되돌림
    - **Firebase에 저장**: Firebase 원본 경로에 저장. 테스트 완료하고 성능이 괜찮으면 저장하시면 됩니다.
      현재는 다른 페이지들(10_재실험 등)은 로컬 파일을 사용하므로 이 곳의 수정 사항은 반영되지 않음.
    """)

# ================================
# Mode: Chat with SP
# ================================
elif st.session_state.sp_test_mode == 'chat':
    st.subheader("💬 가상환자(SP) 테스트")
    
    # Load SP data
    profile = load_from_firebase(firebase_ref, CLIENT_NUMBER, f"profile_version{PROFILE_VERSION}")
    history = load_from_firebase(firebase_ref, CLIENT_NUMBER, f"history_version{PROFILE_VERSION}")
    beh_dir = load_from_firebase(firebase_ref, CLIENT_NUMBER, f"beh_dir_version{BEH_DIR_VERSION}")
    given_information = load_from_firebase(firebase_ref, CLIENT_NUMBER, "given_information")
    
    if not all([profile, history, beh_dir]):
        st.error(f"Client {CLIENT_NUMBER} 데이터를 불러올 수 없습니다.")
        st.warning("18_MDD_MFC_Editor 페이지에서 MFC 데이터를 확인하거나, 19_MFC_Copier 페이지에서 데이터를 복제해주세요.")
        if st.button("◀️ 돌아가기"):
            st.session_state.sp_test_mode = 'edit'
            st.rerun()
        st.stop()
    
    # Load the test system prompt
    try:
        test_prompt = firebase_ref.child("system_prompts/con-agent_version6_0_test").get()
        if not test_prompt:
            st.error("테스트용 System Prompt를 찾을 수 없습니다.")
            st.stop()
    except Exception as e:
        st.error(f"System Prompt 로딩 실패: {str(e)}")
        st.stop()
    
    # Create agent if not exists
    if st.session_state.sp_test_agent is None or st.session_state.sp_test_memory is None:
        # Get diagnosis
        if given_information:
            diag = get_diag_from_given_information(given_information)
        else:
            diag = "MDD"
        
        # Create agent with custom system prompt
        # We need to manually create the agent since we're using a custom prompt
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_core.chat_history import InMemoryChatMessageHistory
        from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
        import random
        
        FIXED_DATE = "2025-12-01"
        
        chat_llm = ChatOpenAI(
            temperature=0.7,
            model="gpt-5.1-2025-11-13",
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()]
        )
        
        # Ensure recall_failure_mode placeholder exists
        if "{recall_failure_mode}" not in test_prompt:
            test_prompt = test_prompt + "\n\n{recall_failure_mode}\n"
        
        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", test_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{human_input}")
        ])
        
        memory = InMemoryChatMessageHistory()
        chain = chat_prompt | chat_llm
        
        # Recall failure state machine - Use user-configured probability
        RECALL_FAILURE_PROB = st.session_state.recall_failure_prob
        RECALL_FAILURE_TURNS = 2
        recall_failure_turns_left = [0]  # Use list for nonlocal mutation
        
        RECALL_FAILURE_TEXT = (
            "RECALL-FAILURE MODE (apply only if relevant to the clinician's question):\n"
            "Although the following information defines your background, you experience difficulty "
            "spontaneously recalling or articulating parts of it due to your current depressive state. "
            "If asked about past events, symptom onset, stressors, or factors that worsen or relieve symptoms, "
            "you may respond vaguely or say you are not sure. If the clinician asks again with more specific "
            "questions, you may recall partially and disclose reluctantly.\n"
        )
        
        def is_past_detail_question(text: str) -> bool:
            text_lower = text.lower()
            keywords = [
                "언제", "when", "얼마", "how long", "duration", "onset",
                "시작", "start", "began", "trigger", "원인", "cause",
                "악화", "worsen", "exacerbate", "완화", "relieve", "allevia",
                "스트레스", "stressor", "유발", "provoke", "기억", "recall", "remember"
            ]
            return any(kw in text_lower for kw in keywords)
        
        def agent(human_input: str):
            past_detail = is_past_detail_question(human_input)
            
            if not past_detail:
                recall_failure_turns_left[0] = 0
            
            if diag == "MDD" and past_detail and recall_failure_turns_left[0] <= 0:
                if random.random() < RECALL_FAILURE_PROB:
                    recall_failure_turns_left[0] = RECALL_FAILURE_TURNS
            
            recall_failure_mode = RECALL_FAILURE_TEXT if recall_failure_turns_left[0] > 0 else ""
            
            if recall_failure_turns_left[0] > 0:
                recall_failure_turns_left[0] -= 1
            
            messages = list(memory.messages) if memory.messages else []
            
            response = chain.invoke({
                "given_information": given_information,
                "current_date": FIXED_DATE,
                "profile_json": json.dumps(profile, indent=2),
                "history": history,
                "behavioral_instruction": beh_dir,
                "recall_failure_mode": recall_failure_mode,
                "chat_history": messages,
                "human_input": human_input
            })
            
            memory.add_user_message(human_input)
            memory.add_ai_message(response.content)
            
            return response.content
        
        st.session_state.sp_test_agent = agent
        st.session_state.sp_test_memory = memory
        
        st.success("✅ SP 에이전트가 생성되었습니다!")
    
    agent = st.session_state.sp_test_agent
    memory = st.session_state.sp_test_memory
    
    # Display test configuration in expandable section
    with st.expander("🔍 현재 테스트 설정", expanded=False):
        st.markdown("**System Prompt (처음 100자)**")
        test_prompt_preview = firebase_ref.child("system_prompts/con-agent_version6_0_test").get()
        if test_prompt_preview:
            st.code(test_prompt_preview[:100] + "...")
        
        st.markdown("**Recall Failure 확률**")
        st.info(f"현재 설정: **{st.session_state.recall_failure_prob:.1f}** (0.0 = 회상 실패 없음, 1.0 = 항상 활성화)")
    
    st.markdown("---")
    
    # Display info
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.info(f"**Client**: {CLIENT_NUMBER} (MDD)")
    with col_info2:
        st.info(f"**Messages**: {len(memory.messages)}")
    with col_info3:
        if st.button("◀️ 프롬프트 수정으로 돌아가기", use_container_width=True):
            st.session_state.sp_test_mode = 'edit'
            st.session_state.sp_test_agent = None
            st.session_state.sp_test_memory = None
            st.rerun()
    
    st.markdown("---")
    
    # Chat interface
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
    
    st.markdown("---")
    
    # Action buttons
    col_action1, col_action2 = st.columns(2)
    
    with col_action1:
        if st.button("🔄 대화 초기화", use_container_width=True):
            st.session_state.sp_test_agent = None
            st.session_state.sp_test_memory = None
            st.success("대화가 초기화되었습니다.")
            st.rerun()
    
    with col_action2:
        if st.button("📝 대화 내용 저장 (Firebase)", use_container_width=True):
            # Save conversation to Firebase
            try:
                conversation_data = []
                for msg in memory.messages:
                    if isinstance(msg, HumanMessage):
                        conversation_data.append({"role": "user", "content": msg.content})
                    else:
                        conversation_data.append({"role": "assistant", "content": msg.content})
                
                import time
                timestamp = int(time.time())
                save_key = f"system_prompt_test_conversations/test_{CLIENT_NUMBER}_{timestamp}"
                
                firebase_ref.child(save_key).set({
                    "client_number": CLIENT_NUMBER,
                    "timestamp": timestamp,
                    "conversation": conversation_data,
                    "system_prompt": st.session_state.edited_prompt
                })
                
                st.success(f"✅ 대화가 저장되었습니다! (Key: {save_key})")
            except Exception as e:
                st.error(f"저장 실패: {str(e)}")
