import streamlit as st
from firebase_config import get_firebase_ref
from SP_utils import sanitize_key
import json

st.set_page_config(
    page_title="MFC Copier (2) - Given Information",
    page_icon="📋",
    layout="wide"
)

st.title("🔄 MFC Copier (2) - Given Information Only")
st.markdown("이 페이지는 6201번 가상환자의 `given_information`을 6301번으로 복제합니다.")
st.warning("⚠️ 이전 MFC Copier에서 누락된 `given_information`만 복제하는 페이지입니다.")

# Initialize Firebase
firebase_ref = get_firebase_ref()
if firebase_ref is None:
    st.error("Firebase 초기화 실패. 설정을 확인하세요.")
    st.stop()

SOURCE_CLIENT = 6201
TARGET_CLIENT = 6301

st.markdown("---")

# Show source data
st.subheader(f"📖 Source: Client {SOURCE_CLIENT}")

# Load source given_information
source_key = f"clients_{SOURCE_CLIENT}_given_information"
source_given_info = firebase_ref.child(source_key).get()

if source_given_info:
    st.success(f"✅ Source `given_information` 발견")
    with st.expander("Source Given Information 내용 보기", expanded=True):
        st.code(source_given_info, language=None)
else:
    st.error(f"❌ Client {SOURCE_CLIENT}의 `given_information`을 찾을 수 없습니다.")
    st.stop()

st.markdown("---")

# Check if target already exists
st.subheader(f"🎯 Target: Client {TARGET_CLIENT}")

target_key = f"clients_{TARGET_CLIENT}_given_information"
target_given_info = firebase_ref.child(target_key).get()

if target_given_info:
    st.warning(f"⚠️ Client {TARGET_CLIENT}의 `given_information`이 이미 존재합니다!")
    with st.expander("기존 Target Given Information 내용 보기"):
        st.code(target_given_info, language=None)
    
    overwrite = st.checkbox("⚠️ 기존 데이터를 덮어쓰시겠습니까?")
else:
    st.success(f"✅ Client {TARGET_CLIENT}에 `given_information`이 없습니다. 복제 가능합니다.")
    overwrite = True

st.markdown("---")

# Copy button
if st.button("🚀 Given Information 복제 실행", type="primary", disabled=not overwrite):
    if not source_given_info:
        st.error("❌ Source 데이터를 불러올 수 없습니다. 복제를 진행할 수 없습니다.")
    else:
        with st.spinner("복제 중..."):
            try:
                # Copy given_information directly
                firebase_ref.child(target_key).set(source_given_info)
                st.success("✅ Given Information 복제 완료")
                
                st.balloons()
                st.success(f"🎉 Client {SOURCE_CLIENT}의 `given_information`이 Client {TARGET_CLIENT}로 성공적으로 복제되었습니다!")
                st.info("이제 10_재실험 페이지에서 6301번 가상환자를 검증할 수 있습니다.")
                
                # Display copied data for verification
                with st.expander("복제된 데이터 확인"):
                    verification = firebase_ref.child(target_key).get()
                    st.code(verification, language=None)
                
            except Exception as e:
                st.error(f"❌ 복제 중 오류 발생: {str(e)}")

st.markdown("---")
st.caption("이 페이지는 복제 완료 후 삭제할 수 있습니다.")

# Additional info section
with st.expander("ℹ️ 참고 정보"):
    st.markdown("""
    ### Given Information이란?
    
    `given_information`은 가상환자 생성 시 입력된 기본 정보입니다:
    - 진단명 (Diagnosis)
    - 나이 (Age)
    - 성별 (Sex)
    - 국적 (Nationality)
    
    이 정보는 SP 에이전트가 적절한 system prompt를 로드하는 데 사용됩니다.
    
    ### Firebase 저장 구조
    
    - **Source**: `clients_6201_given_information`
    - **Target**: `clients_6301_given_information`
    
    이 데이터는 루트 레벨에 직접 저장됩니다 (clients/{client_number} 경로 아님).
    """)
