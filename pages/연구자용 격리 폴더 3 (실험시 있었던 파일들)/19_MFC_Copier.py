import streamlit as st
from firebase_config import get_firebase_ref
from SP_utils import save_to_firebase, load_from_firebase
import json

st.set_page_config(
    page_title="MFC Copier",
    page_icon="📋",
    layout="wide"
)

st.title("🔄 MFC Copier - One-Time Use Page")
st.markdown("이 페이지는 6201번 가상환자의 MFC를 6301번으로 복제합니다.")
st.warning("⚠️ 이 작업은 한 번만 실행하면 됩니다. 복제 완료 후 이 페이지는 삭제할 수 있습니다.")

# Initialize Firebase
firebase_ref = get_firebase_ref()
if firebase_ref is None:
    st.error("Firebase 초기화 실패. 설정을 확인하세요.")
    st.stop()

SOURCE_CLIENT = 6201
TARGET_CLIENT = 6301
VERSION = "6_0"

st.markdown("---")

# Show source data
st.subheader(f"📖 Source: Client {SOURCE_CLIENT}")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Profile**")
    source_profile = load_from_firebase(firebase_ref, SOURCE_CLIENT, f"profile_version{VERSION}")
    if source_profile:
        st.json(source_profile)
    else:
        st.error("Profile을 불러올 수 없습니다.")

with col2:
    st.markdown("**History**")
    source_history = load_from_firebase(firebase_ref, SOURCE_CLIENT, f"history_version{VERSION}")
    if source_history:
        st.text_area("History Content", value=source_history, height=300, disabled=True, key="source_history")
    else:
        st.error("History를 불러올 수 없습니다.")

with col3:
    st.markdown("**Behavioral Directive**")
    source_beh_dir = load_from_firebase(firebase_ref, SOURCE_CLIENT, f"beh_dir_version{VERSION}")
    if source_beh_dir:
        st.text_area("Behavioral Directive Content", value=source_beh_dir, height=300, disabled=True, key="source_beh")
    else:
        st.error("Behavioral Directive를 불러올 수 없습니다.")

st.markdown("---")

# Check if target already exists
st.subheader(f"🎯 Target: Client {TARGET_CLIENT}")

target_profile = load_from_firebase(firebase_ref, TARGET_CLIENT, f"profile_version{VERSION}")
target_history = load_from_firebase(firebase_ref, TARGET_CLIENT, f"history_version{VERSION}")
target_beh_dir = load_from_firebase(firebase_ref, TARGET_CLIENT, f"beh_dir_version{VERSION}")

if any([target_profile, target_history, target_beh_dir]):
    st.warning(f"⚠️ Client {TARGET_CLIENT}의 데이터가 이미 존재합니다!")
    st.markdown("**기존 데이터:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        if target_profile:
            st.info("Profile 존재")
    with col2:
        if target_history:
            st.info("History 존재")
    with col3:
        if target_beh_dir:
            st.info("Behavioral Directive 존재")
    
    overwrite = st.checkbox("⚠️ 기존 데이터를 덮어쓰시겠습니까?")
else:
    st.success(f"✅ Client {TARGET_CLIENT}에 데이터가 없습니다. 복제 가능합니다.")
    overwrite = True

st.markdown("---")

# Copy button
if st.button("🚀 복제 실행", type="primary", disabled=not overwrite):
    if not all([source_profile, source_history, source_beh_dir]):
        st.error("❌ Source 데이터를 모두 불러올 수 없습니다. 복제를 진행할 수 없습니다.")
    else:
        with st.spinner("복제 중..."):
            try:
                # Copy Profile
                save_to_firebase(firebase_ref, TARGET_CLIENT, f"profile_version{VERSION}", source_profile)
                st.success("✅ Profile 복제 완료")
                
                # Copy History
                save_to_firebase(firebase_ref, TARGET_CLIENT, f"history_version{VERSION}", source_history)
                st.success("✅ History 복제 완료")
                
                # Copy Behavioral Directive
                save_to_firebase(firebase_ref, TARGET_CLIENT, f"beh_dir_version{VERSION}", source_beh_dir)
                st.success("✅ Behavioral Directive 복제 완료")
                
                st.balloons()
                st.success(f"🎉 Client {SOURCE_CLIENT}의 MFC가 Client {TARGET_CLIENT}로 성공적으로 복제되었습니다!")
                st.info("이제 18_MDD_MFC_Editor 페이지에서 수정할 수 있습니다.")
                
            except Exception as e:
                st.error(f"❌ 복제 중 오류 발생: {str(e)}")

st.markdown("---")
st.caption("이 페이지는 복제 완료 후 삭제할 수 있습니다.")
