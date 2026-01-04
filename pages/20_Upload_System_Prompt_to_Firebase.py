"""
일회성 페이지: System Prompt를 Firebase에 업로드
로컬의 con-agent_system_prompt_version6.0.txt를 Firebase에 저장
"""

import streamlit as st
from firebase_config import get_firebase_ref
import os

st.set_page_config(
    page_title="System Prompt Upload",
    page_icon="⬆️",
    layout="wide"
)

st.title("⬆️ System Prompt Firebase 업로드")
st.markdown("---")

st.warning("⚠️ **주의**: 이 페이지는 일회성으로 사용 후 삭제할 예정입니다.")

# Initialize Firebase
firebase_ref = get_firebase_ref()
if firebase_ref is None:
    st.error("Firebase 초기화 실패. 설정을 확인하세요.")
    st.stop()

# Load local system prompt
import os
base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
local_path = os.path.join(base_path, "data", "prompts", "con-agent_system_prompt", "con-agent_system_prompt_version6.0.txt")

st.subheader("📄 로컬 System Prompt 내용")

if not os.path.exists(local_path):
    st.error(f"파일을 찾을 수 없습니다: {local_path}")
    st.stop()

try:
    with open(local_path, "r", encoding="utf-8") as f:
        system_prompt_content = f.read()
    
    st.text_area(
        "System Prompt Content (Read-only)",
        value=system_prompt_content,
        height=400,
        disabled=True
    )
    
    st.markdown("---")
    st.subheader("🚀 Firebase 업로드")
    
    # Show current Firebase content if exists
    try:
        current_firebase_prompt = firebase_ref.child("system_prompts/con-agent_version6_0").get()
        if current_firebase_prompt:
            st.info("ℹ️ Firebase에 이미 System Prompt가 저장되어 있습니다.")
            with st.expander("현재 Firebase에 저장된 내용 보기"):
                st.text_area(
                    "Current Firebase Content",
                    value=current_firebase_prompt,
                    height=300,
                    disabled=True
                )
    except Exception as e:
        st.warning(f"Firebase 확인 중 오류: {str(e)}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 Firebase에 업로드", type="primary", use_container_width=True):
            try:
                firebase_ref.child("system_prompts/con-agent_version6_0").set(system_prompt_content)
                st.success("✅ System Prompt가 Firebase에 성공적으로 업로드되었습니다!")
                st.balloons()
            except Exception as e:
                st.error(f"업로드 실패: {str(e)}")
    
    with col2:
        if st.button("🔄 업로드 확인", use_container_width=True):
            try:
                uploaded_content = firebase_ref.child("system_prompts/con-agent_version6_0").get()
                if uploaded_content:
                    if uploaded_content == system_prompt_content:
                        st.success("✅ Firebase의 내용이 로컬 파일과 일치합니다!")
                    else:
                        st.warning("⚠️ Firebase의 내용이 로컬 파일과 다릅니다.")
                else:
                    st.error("❌ Firebase에 아직 업로드되지 않았습니다.")
            except Exception as e:
                st.error(f"확인 실패: {str(e)}")
    
    st.markdown("---")
    st.info("💡 **업로드 후**: 21_System_Prompt_Test 페이지에서 테스트할 수 있습니다.")
    
except Exception as e:
    st.error(f"파일 읽기 실패: {str(e)}")
