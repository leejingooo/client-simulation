import streamlit as st
from datetime import datetime
from Home import check_participant
from firebase_config import get_firebase_ref
from SP_utils import sanitize_key

# ================================
# PRESET - Validation Requirements
# ================================

# ========== 기존 목록 (주석 처리) ==========
# EXPERT_VALIDATION_EXPERIMENTS = [
#     # 6201 MDD
#     (6201, 1111), (6201, 1112), (6201, 1121), (6201, 1122),
#     (6201, 1131), (6201, 1132), (6201, 1141), (6201, 1142),
#     
#     # 6202 BD
#     (6202, 1211), (6202, 1212), (6202, 1221), (6202, 1222),
#     (6202, 1231), (6202, 1232), (6202, 1241), (6202, 1242),
#     
#     # 6206 OCD
#     (6206, 1611), (6206, 1612), (6206, 1621), (6206, 1622),
#     (6206, 1631), (6206, 1632), (6206, 1641), (6206, 1642),
# ]

# ========== 새로운 목록 (Smaller vs Large 비교) ==========
# 에이전트에 대한 전문가 검증: 24 experiments
EXPERT_VALIDATION_EXPERIMENTS = [
    # 6201 MDD
    (6201, 3111), (6201, 3117), (6201, 1121), (6201, 1123),
    (6201, 3134), (6201, 3138), (6201, 1143), (6201, 1145),
    
    # 6202 BD
    (6202, 3211), (6202, 3212), (6202, 1221), (6202, 1222),
    (6202, 3231), (6202, 3234), (6202, 1241), (6202, 1242),
    
    # 6206 OCD
    (6206, 3611), (6206, 3612), (6206, 1621), (6206, 1622),
    (6206, 3631), (6206, 3632), (6206, 1641), (6206, 1642),
]

# 가상환자에 대한 전문가 검증: 14 virtual patients
SP_VALIDATION_SEQUENCE = [
    (1, 6201), (2, 6202), (3, 6203), (4, 6204),
    (5, 6205), (6, 6206), (7, 6207),
    (8, 6203), (9, 6201), (10, 6204),
    (11, 6207), (12, 6202), (13, 6206), (14, 6205),
]


# ================================
# Helper Functions
# ================================

def check_expert_validation_completion(firebase_ref, expert_name):
    """Check which expert validation experiments are completed"""
    completed = []
    
    for client_num, exp_num in EXPERT_VALIDATION_EXPERIMENTS:
        # Check if validation exists in Firebase
        validation_key = f"expert_{sanitize_key(expert_name)}_{client_num}_{exp_num}"
        data = firebase_ref.child(validation_key).get()
        
        if data:
            completed.append((client_num, exp_num))
    
    return completed


def check_sp_validation_completion(firebase_ref, expert_name):
    """Check which SP validation cases are completed"""
    completed = []
    
    for page_num, client_num in SP_VALIDATION_SEQUENCE:
        # Check if validation exists and is final
        validation_key = f"sp_validation_{sanitize_key(expert_name)}_{client_num}_{page_num}"
        data = firebase_ref.child(validation_key).get()
        
        if data and data.get('is_final', False):
            completed.append((page_num, client_num))
    
    return completed


# ================================
# Main Page
# ================================

def main():
    st.set_page_config(
        page_title="Validation Home",
        page_icon="🏠",
        layout="wide"
    )
    
    # Check authentication
    if not check_participant():
        st.stop()
    
    # Get expert name
    if 'name' in st.session_state and st.session_state.get('name_correct', False):
        expert_name = st.session_state['name']
    else:
        st.error("로그인이 필요합니다.")
        st.stop()
    
    # Firebase connection
    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error("Firebase 초기화 실패")
        st.stop()
    
    # Page Header
    st.title("🏠 검증 진행 현황 대시보드")
    st.markdown(f"**검증자:** {expert_name}")
    st.markdown("---")
    
    # Check completion status
    expert_completed = check_expert_validation_completion(firebase_ref, expert_name)
    sp_completed = check_sp_validation_completion(firebase_ref, expert_name)
    
    expert_total = len(EXPERT_VALIDATION_EXPERIMENTS)
    sp_total = len(SP_VALIDATION_SEQUENCE)
    
    expert_progress = len(expert_completed) / expert_total
    sp_progress = len(sp_completed) / sp_total
    total_progress = (len(expert_completed) + len(sp_completed)) / (expert_total + sp_total)
    
    # Overall Progress
    st.header("📊 전체 진행 현황")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "에이전트에 대한 전문가 검증",
            f"{len(expert_completed)}/{expert_total}",
            f"{expert_progress*100:.1f}%"
        )
    
    with col2:
        st.metric(
            "가상환자에 대한 전문가 검증",
            f"{len(sp_completed)}/{sp_total}",
            f"{sp_progress*100:.1f}%"
        )
    
    with col3:
        st.metric(
            "전체 진행률",
            f"{len(expert_completed) + len(sp_completed)}/{expert_total + sp_total}",
            f"{total_progress*100:.1f}%"
        )
    
    st.progress(total_progress, text=f"전체 진행률: {total_progress*100:.1f}%")
    
    # Check if all completed
    if len(expert_completed) == expert_total and len(sp_completed) == sp_total:
        st.balloons()
        st.success("🎉 **모든 검증을 완료하셨습니다!**")
        st.markdown("""
        ---
        ## 🙏 연구 참여에 진심으로 감사드립니다
        
        귀하께서 수행하신 검증 작업은 본 연구에 매우 중요한 기여를 하였습니다.
        
        모든 데이터가 안전하게 저장되었으며, 연구 목적으로만 사용될 것입니다.
        
        다시 한번 감사드립니다.
        
        ---
        """)
    
    # st.markdown("---")
    
    # # Detailed Status
    # col_left, col_right = st.columns(2)
    
    # # Expert Validation Details
    # with col_left:
    #     st.header("📋 Expert Validation 상세")
    #     st.progress(expert_progress, text=f"{len(expert_completed)}/{expert_total} 완료")
        
    #     if expert_progress < 1.0:
    #         st.info("👉 Expert Validation 페이지로 이동하여 검증을 계속하세요.")
        
    #     # Group by client number
    #     expert_by_client = {}
    #     for client_num, exp_num in EXPERT_VALIDATION_EXPERIMENTS:
    #         if client_num not in expert_by_client:
    #             expert_by_client[client_num] = {'total': 0, 'completed': 0, 'experiments': []}
    #         expert_by_client[client_num]['total'] += 1
    #         expert_by_client[client_num]['experiments'].append(exp_num)
    #         if (client_num, exp_num) in expert_completed:
    #             expert_by_client[client_num]['completed'] += 1
        
    #     for client_num in sorted(expert_by_client.keys()):
    #         info = expert_by_client[client_num]
    #         with st.expander(f"Client {client_num} - {info['completed']}/{info['total']} 완료"):
    #             for exp_num in sorted(info['experiments']):
    #                 if (client_num, exp_num) in expert_completed:
    #                     st.success(f"✅ Experiment {exp_num}")
    #                 else:
    #                     st.warning(f"⏳ Experiment {exp_num} - 미완료")
    
    # # SP Validation Details
    # with col_right:
    #     st.header("👥 SP Validation 상세")
    #     st.progress(sp_progress, text=f"{len(sp_completed)}/{sp_total} 완료")
        
    #     if sp_progress < 1.0:
    #         st.info("👉 SP Validation 페이지로 이동하여 검증을 계속하세요.")
        
    #     # Display by page number
    #     for page_num, client_num in SP_VALIDATION_SEQUENCE:
    #         if (page_num, client_num) in sp_completed:
    #             st.success(f"✅ 가상환자 {page_num} (Client {client_num})")
    #         else:
    #             st.warning(f"⏳ 가상환자 {page_num} (Client {client_num}) - 미완료")
    
    # st.markdown("---")
    
    # # Quick Links
    # st.header("🔗 바로가기")
    
    # col1, col2 = st.columns(2)
    
    # with col1:
    #     if expert_progress < 1.0:
    #         st.page_link("pages/06_expert_validation.py", label="📋 Expert Validation 페이지로 이동", icon="📋")
    #     else:
    #         st.success("✅ Expert Validation 완료")
    
    # with col2:
    #     if sp_progress < 1.0:
    #         st.page_link("pages/07_sp_validation.py", label="👥 SP Validation 페이지로 이동", icon="👥")
    #     else:
    #         st.success("✅ SP Validation 완료")


if __name__ == "__main__":
    main()
