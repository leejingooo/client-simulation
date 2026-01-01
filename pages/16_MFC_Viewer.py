"""
MFC (Multi-faceted Construct) Viewer
Profile, History, Behavior 데이터 확인 페이지
"""

import streamlit as st
import json
from firebase_config import get_firebase_ref
from SP_utils import sanitize_key

# ================================
# Configuration
# ================================
st.set_page_config(
    page_title="MFC Viewer",
    page_icon="📋",
    layout="wide"
)

# ================================
# Client to Disorder Mapping
# ================================
CLIENT_DISORDER_MAP = {
    6201: 'MDD',  # Major Depressive Disorder
    6202: 'BD',   # Bipolar Disorder
    6203: 'PD',   # Panic Disorder
    6204: 'GAD',  # Generalized Anxiety Disorder
    6205: 'SAD',  # Social Anxiety Disorder
    6206: 'OCD',  # Obsessive-Compulsive Disorder
    6207: 'PTSD'  # Post-Traumatic Stress Disorder
}

# ================================
# Data Loading Functions
# ================================
def load_mfc_data(firebase_ref, client_number, version="6_0"):
    """Load all three MFC components from Firebase.
    
    Args:
        firebase_ref: Firebase reference
        client_number: Client number (e.g., 6201)
        version: Version string with underscore (e.g., "6_0")
    
    Returns:
        dict: {'profile': {...}, 'history': str, 'behavior': str}
    """
    mfc_data = {}
    
    # Load Profile
    profile_key = f"clients_{client_number}_profile_version{version}"
    profile_data = firebase_ref.child(profile_key.replace('_', '/')).get()
    if profile_data:
        mfc_data['profile'] = profile_data
    else:
        mfc_data['profile'] = None
    
    # Load History
    history_key = f"clients_{client_number}_history_version{version}"
    history_data = firebase_ref.child(history_key.replace('_', '/')).get()
    if history_data:
        mfc_data['history'] = history_data
    else:
        mfc_data['history'] = None
    
    # Load Behavior (Behavioral Directive)
    behavior_key = f"clients_{client_number}_beh_dir_version{version}"
    behavior_data = firebase_ref.child(behavior_key.replace('_', '/')).get()
    if behavior_data:
        mfc_data['behavior'] = behavior_data
    else:
        mfc_data['behavior'] = None
    
    return mfc_data

def get_available_clients(firebase_ref):
    """Scan Firebase to find available client numbers.
    
    Returns:
        list: Available client numbers (6201-6207 only)
    """
    # Current research cohort: 6201-6207
    common_clients = list(range(6201, 6208))
    available = []
    
    for client_num in common_clients:
        # Check if profile exists
        profile_key = f"clients/{client_num}/profile_version6_0"
        data = firebase_ref.child(profile_key).get()
        if data:
            available.append(client_num)
    
    return sorted(available)

# ================================
# Display Functions
# ================================
def display_profile(profile_data):
    """Display profile data in organized sections."""
    if profile_data is None:
        st.warning("⚠️ Profile data not found")
        return
    
    st.markdown("### 📋 MFC-Profile")
    st.caption("Clinically grounded psychiatric schema - analogous to medical records")
    
    # Profile is typically a nested JSON structure
    # Display each category
    if isinstance(profile_data, dict):
        for category, content in profile_data.items():
            with st.expander(f"**{category}**", expanded=False):
                if isinstance(content, dict):
                    # Nested structure
                    for subcategory, value in content.items():
                        if isinstance(value, dict):
                            st.markdown(f"**{subcategory}:**")
                            st.json(value)
                        elif isinstance(value, list):
                            st.markdown(f"**{subcategory}:**")
                            for i, item in enumerate(value, 1):
                                st.markdown(f"{i}. {item}")
                        else:
                            st.markdown(f"**{subcategory}:** {value}")
                elif isinstance(content, list):
                    for i, item in enumerate(content, 1):
                        st.markdown(f"{i}. {item}")
                else:
                    st.markdown(content)
    else:
        st.json(profile_data)

def display_history(history_data):
    """Display history data."""
    if history_data is None:
        st.warning("⚠️ History data not found")
        return
    
    st.markdown("### 📖 MFC-History")
    st.caption("Dynamic lifetime biography complementing Profile - enriches patient context")
    
    if isinstance(history_data, str):
        # Display as markdown text
        st.markdown(history_data)
    else:
        st.json(history_data)

def display_behavior(behavior_data):
    """Display behavioral directive data."""
    if behavior_data is None:
        st.warning("⚠️ Behavior data not found")
        return
    
    st.markdown("### 🎭 MFC-Behavior")
    st.caption("MSE-based behavioral instructions - observable aspects for realistic patient simulation")
    
    if isinstance(behavior_data, str):
        # Display as markdown text
        st.markdown(behavior_data)
    else:
        st.json(behavior_data)

def display_raw_json(data, component_name):
    """Display raw JSON data."""
    st.markdown(f"#### Raw JSON - {component_name}")
    if data is not None:
        st.json(data)
    else:
        st.warning(f"⚠️ {component_name} data not found")

# ================================
# Main Application
# ================================
def main():
    st.title("📋 MFC (Multi-faceted Construct) Viewer")
    st.markdown("---")
    
    st.info("""
    **MFC (Multi-faceted Construct)란?**
    
    PSYCHE 프레임워크의 핵심 구성 요소로, 임상적으로 타당한 정신과 환자 시뮬레이션을 위한 다면적 스키마입니다.
    
    **3가지 구성 요소:**
    1. **MFC-Profile**: 환자 인구통계, 증상, 병력 (정신과 의무기록과 유사)
    2. **MFC-History**: 환자의 생애 전반에 걸친 동적 전기적 서사
    3. **MFC-Behavior**: MSE(Mental Status Examination) 기반 관찰 가능한 행동 지침
    """)
    
    # Initialize Firebase
    firebase_ref = get_firebase_ref()
    
    # Sidebar - Client Selection
    st.sidebar.header("⚙️ 설정")
    
    # Get available clients
    with st.spinner("Available clients 확인 중..."):
        available_clients = get_available_clients(firebase_ref)
    
    if not available_clients:
        st.error("사용 가능한 클라이언트 데이터가 없습니다.")
        return
    
    # Client number selection
    client_options = []
    for client_num in available_clients:
        disorder = CLIENT_DISORDER_MAP.get(client_num, "Unknown")
        client_options.append(f"{client_num} - {disorder}")
    
    selected_option = st.sidebar.selectbox(
        "Client Number",
        client_options,
        help="데이터가 있는 클라이언트만 표시됩니다"
    )
    
    client_number = int(selected_option.split(" - ")[0])
    disorder = CLIENT_DISORDER_MAP.get(client_number, "Unknown")
    
    # Version fixed at 6.0
    version_input = 6.0
    version_str = "6_0"
    
    st.sidebar.info("Version: 6.0 (고정)")
    
    # Display mode
    display_mode = st.sidebar.radio(
        "Display Mode",
        ["Formatted View", "Raw JSON"],
        help="Formatted: 구조화된 뷰 | Raw JSON: 원본 JSON"
    )
    
    # Load button
    if st.sidebar.button("🔄 Load MFC Data", use_container_width=True):
        st.session_state.mfc_loaded = True
        st.session_state.current_client = client_number
        st.session_state.current_version = version_str
    
    # Main content
    if st.session_state.get('mfc_loaded', False):
        with st.spinner(f"Loading MFC data for Client {client_number}..."):
            mfc_data = load_mfc_data(firebase_ref, client_number, version_str)
        
        # Header
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Client Number", client_number)
        with col2:
            st.metric("Disorder", disorder)
        
        st.markdown("---")
        
        # Check data availability
        profile_exists = mfc_data['profile'] is not None
        history_exists = mfc_data['history'] is not None
        behavior_exists = mfc_data['behavior'] is not None
        
        st.markdown("### 📊 Data Availability")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Profile", "✅" if profile_exists else "❌")
        with col2:
            st.metric("History", "✅" if history_exists else "❌")
        with col3:
            st.metric("Behavior", "✅" if behavior_exists else "❌")
        
        st.markdown("---")
        
        # Display data in tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Profile", "📖 History", "🎭 Behavior", "📥 Download"])
        
        with tab1:
            if display_mode == "Formatted View":
                display_profile(mfc_data['profile'])
            else:
                display_raw_json(mfc_data['profile'], "Profile")
        
        with tab2:
            if display_mode == "Formatted View":
                display_history(mfc_data['history'])
            else:
                display_raw_json(mfc_data['history'], "History")
        
        with tab3:
            if display_mode == "Formatted View":
                display_behavior(mfc_data['behavior'])
            else:
                display_raw_json(mfc_data['behavior'], "Behavior")
        
        with tab4:
            st.markdown("### 📥 Download MFC Data")
            st.caption("JSON 형식으로 다운로드")
            
            # Prepare combined data
            combined_data = {
                'client_number': client_number,
                'disorder': disorder,
                'version': version_input,
                'mfc': {
                    'profile': mfc_data['profile'],
                    'history': mfc_data['history'],
                    'behavior': mfc_data['behavior']
                }
            }
            
            # Download buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if profile_exists:
                    profile_json = json.dumps(mfc_data['profile'], indent=2, ensure_ascii=False)
                    st.download_button(
                        label="📋 Download Profile",
                        data=profile_json,
                        file_name=f"mfc_profile_{client_number}_{disorder}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
                if history_exists:
                    if isinstance(mfc_data['history'], str):
                        history_data = mfc_data['history']
                    else:
                        history_data = json.dumps(mfc_data['history'], indent=2, ensure_ascii=False)
                    
                    st.download_button(
                        label="📖 Download History",
                        data=history_data,
                        file_name=f"mfc_history_{client_number}_{disorder}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
            
            with col2:
                if behavior_exists:
                    if isinstance(mfc_data['behavior'], str):
                        behavior_data = mfc_data['behavior']
                    else:
                        behavior_data = json.dumps(mfc_data['behavior'], indent=2, ensure_ascii=False)
                    
                    st.download_button(
                        label="🎭 Download Behavior",
                        data=behavior_data,
                        file_name=f"mfc_behavior_{client_number}_{disorder}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                # Combined download
                combined_json = json.dumps(combined_data, indent=2, ensure_ascii=False)
                st.download_button(
                    label="📦 Download All (Combined)",
                    data=combined_json,
                    file_name=f"mfc_combined_{client_number}_{disorder}.json",
                    mime="application/json",
                    use_container_width=True
                )
    else:
        st.info("👈 사이드바에서 클라이언트를 선택하고 'Load MFC Data' 버튼을 클릭하세요.")

if __name__ == "__main__":
    main()
