import streamlit as st
from firebase_config import get_firebase_ref
from SP_utils import save_to_firebase, load_from_firebase
import json
import copy

st.set_page_config(
    page_title="MDD MFC Editor",
    page_icon="✏️",
    layout="wide"
)

st.title("✏️ MDD MFC Editor")
st.markdown("6301번 가상환자(MDD)의 MFC를 수정합니다.")

# Initialize Firebase
firebase_ref = get_firebase_ref()
if firebase_ref is None:
    st.error("Firebase 초기화 실패. 설정을 확인하세요.")
    st.stop()

CLIENT_NUMBER = 6301
VERSION = "6_0"

# Initialize session state
if 'editing_mode' not in st.session_state:
    st.session_state.editing_mode = False
if 'changes_confirmed' not in st.session_state:
    st.session_state.changes_confirmed = False
if 'edited_profile' not in st.session_state:
    st.session_state.edited_profile = None
if 'edited_history' not in st.session_state:
    st.session_state.edited_history = None
if 'edited_beh_dir' not in st.session_state:
    st.session_state.edited_beh_dir = None

# Load current data
st.markdown("---")
st.subheader(f"📚 현재 Client {CLIENT_NUMBER} MFC 데이터")

with st.spinner("데이터 로딩 중..."):
    current_profile = load_from_firebase(firebase_ref, CLIENT_NUMBER, f"profile_version{VERSION}")
    current_history = load_from_firebase(firebase_ref, CLIENT_NUMBER, f"history_version{VERSION}")
    current_beh_dir = load_from_firebase(firebase_ref, CLIENT_NUMBER, f"beh_dir_version{VERSION}")

if not all([current_profile, current_history, current_beh_dir]):
    st.error("❌ MFC 데이터를 불러올 수 없습니다.")
    st.warning("19_MFC_Copier 페이지에서 먼저 6201번 데이터를 6301번으로 복제해주세요.")
    st.stop()

st.success("✅ 데이터 로딩 완료")

# Editing section
st.markdown("---")
st.subheader("✏️ MFC 수정")
st.info("💡 좌측에는 현재 내용, 우측에는 수정할 내용을 입력하세요. JSON 형식을 정확히 유지해야 합니다.")

tab1, tab2, tab3 = st.tabs(["📄 Profile", "📖 History", "🎭 Behavioral Directive"])

# Tab 1: Profile
with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**현재 Profile**")
        current_profile_json = json.dumps(current_profile, indent=2, ensure_ascii=False)
        st.text_area(
            "Current Profile (Read-only)",
            value=current_profile_json,
            height=600,
            disabled=True,
            key="current_profile_display"
        )
    
    with col2:
        st.markdown("**수정할 Profile**")
        if st.session_state.edited_profile is None:
            default_profile_value = current_profile_json
        else:
            default_profile_value = st.session_state.edited_profile
        
        edited_profile_text = st.text_area(
            "수정할 Profile (JSON 형식)",
            value=default_profile_value,
            height=600,
            key="edit_profile"
        )
        st.session_state.edited_profile = edited_profile_text

# Tab 2: History
with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**현재 History**")
        st.text_area(
            "Current History (Read-only)",
            value=current_history if isinstance(current_history, str) else json.dumps(current_history, indent=2, ensure_ascii=False),
            height=600,
            disabled=True,
            key="current_history_display"
        )
    
    with col2:
        st.markdown("**수정할 History**")
        if st.session_state.edited_history is None:
            default_history_value = current_history if isinstance(current_history, str) else json.dumps(current_history, indent=2, ensure_ascii=False)
        else:
            default_history_value = st.session_state.edited_history
        
        edited_history_text = st.text_area(
            "수정할 History",
            value=default_history_value,
            height=600,
            key="edit_history"
        )
        st.session_state.edited_history = edited_history_text

# Tab 3: Behavioral Directive
with tab3:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**현재 Behavioral Directive**")
        st.text_area(
            "Current Behavioral Directive (Read-only)",
            value=current_beh_dir if isinstance(current_beh_dir, str) else json.dumps(current_beh_dir, indent=2, ensure_ascii=False),
            height=600,
            disabled=True,
            key="current_beh_dir_display"
        )
    
    with col2:
        st.markdown("**수정할 Behavioral Directive**")
        if st.session_state.edited_beh_dir is None:
            default_beh_dir_value = current_beh_dir if isinstance(current_beh_dir, str) else json.dumps(current_beh_dir, indent=2, ensure_ascii=False)
        else:
            default_beh_dir_value = st.session_state.edited_beh_dir
        
        edited_beh_dir_text = st.text_area(
            "수정할 Behavioral Directive",
            value=default_beh_dir_value,
            height=600,
            key="edit_beh_dir"
        )
        st.session_state.edited_beh_dir = edited_beh_dir_text

# Preview changes button
st.markdown("---")

if not st.session_state.editing_mode:
    if st.button("🔍 변경사항 미리보기", type="primary"):
        st.session_state.editing_mode = True
        st.rerun()
else:
    st.subheader("📋 변경사항 확인")
    
    # Validate and show changes
    all_valid = True
    parsed_profile = None
    parsed_history = None
    parsed_beh_dir = None
    
    try:
        # Validate Profile JSON
        parsed_profile = json.loads(st.session_state.edited_profile)
        st.success("✅ Profile JSON 형식이 올바릅니다.")
        
        with st.expander("Profile 변경사항 보기"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**변경 전**")
                st.json(current_profile)
            with col2:
                st.markdown("**변경 후**")
                st.json(parsed_profile)
    except json.JSONDecodeError as e:
        st.error(f"❌ Profile JSON 형식 오류: {str(e)}")
        all_valid = False
    
    try:
        # History - might be string or JSON
        if st.session_state.edited_history.strip().startswith('{'):
            parsed_history = json.loads(st.session_state.edited_history)
        else:
            parsed_history = st.session_state.edited_history
        st.success("✅ History 형식이 올바릅니다.")
        
        with st.expander("History 변경사항 보기"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**변경 전**")
                st.text(current_history if isinstance(current_history, str) else json.dumps(current_history, indent=2, ensure_ascii=False))
            with col2:
                st.markdown("**변경 후**")
                st.text(parsed_history if isinstance(parsed_history, str) else json.dumps(parsed_history, indent=2, ensure_ascii=False))
    except json.JSONDecodeError as e:
        st.error(f"❌ History 형식 오류: {str(e)}")
        all_valid = False
    
    try:
        # Behavioral Directive - might be string or JSON
        if st.session_state.edited_beh_dir.strip().startswith('{'):
            parsed_beh_dir = json.loads(st.session_state.edited_beh_dir)
        else:
            parsed_beh_dir = st.session_state.edited_beh_dir
        st.success("✅ Behavioral Directive 형식이 올바릅니다.")
        
        with st.expander("Behavioral Directive 변경사항 보기"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**변경 전**")
                st.text(current_beh_dir if isinstance(current_beh_dir, str) else json.dumps(current_beh_dir, indent=2, ensure_ascii=False))
            with col2:
                st.markdown("**변경 후**")
                st.text(parsed_beh_dir if isinstance(parsed_beh_dir, str) else json.dumps(parsed_beh_dir, indent=2, ensure_ascii=False))
    except json.JSONDecodeError as e:
        st.error(f"❌ Behavioral Directive 형식 오류: {str(e)}")
        all_valid = False
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔙 돌아가기 (편집 계속)", type="secondary"):
            st.session_state.editing_mode = False
            st.rerun()
    
    with col2:
        if all_valid:
            if st.button("✅ 최종 확인 및 저장", type="primary"):
                st.session_state.changes_confirmed = True
                
                # Save to Firebase
                with st.spinner("Firebase에 저장 중..."):
                    try:
                        save_to_firebase(firebase_ref, CLIENT_NUMBER, f"profile_version{VERSION}", parsed_profile)
                        st.success("✅ Profile 저장 완료")
                        
                        save_to_firebase(firebase_ref, CLIENT_NUMBER, f"history_version{VERSION}", parsed_history)
                        st.success("✅ History 저장 완료")
                        
                        save_to_firebase(firebase_ref, CLIENT_NUMBER, f"beh_dir_version{VERSION}", parsed_beh_dir)
                        st.success("✅ Behavioral Directive 저장 완료")
                        
                        st.balloons()
                        st.success(f"🎉 Client {CLIENT_NUMBER}의 MFC가 성공적으로 업데이트되었습니다!")
                        
                        # Reset session state
                        st.session_state.editing_mode = False
                        st.session_state.edited_profile = None
                        st.session_state.edited_history = None
                        st.session_state.edited_beh_dir = None
                        
                        st.info("페이지를 새로고침하여 변경된 내용을 확인하세요.")
                        
                    except Exception as e:
                        st.error(f"❌ 저장 중 오류 발생: {str(e)}")
        else:
            st.button("✅ 최종 확인 및 저장", type="primary", disabled=True)
            st.warning("⚠️ 모든 데이터의 형식이 올바른지 확인해주세요.")

st.markdown("---")
st.caption(f"Client {CLIENT_NUMBER} MFC Editor - version {VERSION}")
