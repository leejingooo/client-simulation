"""
6301 클라이언트 검증 결과 뷰어 (임시 페이지)

10_재실험.py에서 저장된 6301 클라이언트에 대한 평가 결과를 확인합니다.
"""

import streamlit as st
from datetime import datetime
from Home import check_participant
from firebase_config import get_firebase_ref
from SP_utils import sanitize_key
import json

def main():
    st.set_page_config(
        page_title="6301 검증 결과 뷰어",
        page_icon="🔍",
        layout="wide"
    )
    
    # Check authentication
    if not check_participant():
        st.stop()
    
    st.title("🔍 6301 클라이언트 검증 결과 뷰어")
    st.markdown("---")
    
    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error("Firebase 초기화 실패")
        st.stop()
    
    # Get all data from Firebase
    all_data = firebase_ref.get()
    
    if not all_data:
        st.warning("Firebase에 데이터가 없습니다.")
        st.stop()
    
    # Filter keys related to 6301 client
    sp_validation_keys = []
    sp_conversation_keys = []
    progress_keys = []
    
    for key in all_data.keys():
        if 'sp_validation_' in key and '_6301_' in key:
            sp_validation_keys.append(key)
        elif 'sp_conversation_' in key and '_6301_' in key:
            sp_conversation_keys.append(key)
        elif 'sp_validation_progress_' in key or 'sp_progress_' in key:
            progress_keys.append(key)
    
    # Display overview
    st.markdown("### 📊 데이터 개요")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("검증 결과", len(sp_validation_keys))
    with col2:
        st.metric("대화 로그", len(sp_conversation_keys))
    with col3:
        st.metric("진행 상태", len(progress_keys))
    
    st.markdown("---")
    
    # Show validation results
    if sp_validation_keys:
        st.markdown("### ✅ 검증 결과 데이터")
        
        for key in sorted(sp_validation_keys):
            # Parse key to extract information
            parts = key.split('_')
            # Format: sp_validation_{expert}_{client}_{page}
            expert_name = '_'.join(parts[2:-2])  # Everything between sp_validation and last two parts
            client_num = parts[-2]
            page_num = parts[-1]
            
            with st.expander(f"📄 {key}", expanded=False):
                data = all_data[key]
                
                col_info, col_status = st.columns([2, 1])
                with col_info:
                    st.write(f"**전문가:** {data.get('expert_name', expert_name)}")
                    st.write(f"**클라이언트:** {data.get('client_number', client_num)}")
                    st.write(f"**페이지:** {data.get('page_number', page_num)}")
                with col_status:
                    st.write(f"**최종 저장:** {'✅ Yes' if data.get('is_final') else '⏳ No'}")
                    st.write(f"**저장 시간:** {data.get('timestamp', 'N/A')}")
                
                st.markdown("---")
                
                # Elements validation
                if 'elements' in data:
                    st.markdown("#### 검증 항목")
                    elements = data['elements']
                    
                    # Count statistics
                    appropriate_count = sum(1 for elem in elements.values() 
                                          if elem.get('expert_choice') == '적절함' or elem.get('is_appropriate'))
                    inappropriate_count = sum(1 for elem in elements.values() 
                                            if elem.get('expert_choice') == '적절하지 않음')
                    total_count = len(elements)
                    
                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                    with col_stat1:
                        st.metric("전체", total_count)
                    with col_stat2:
                        st.metric("적절함", appropriate_count)
                    with col_stat3:
                        st.metric("적절하지 않음", inappropriate_count)
                    
                    st.markdown("**항목별 상세:**")
                    for elem_name, elem_data in elements.items():
                        choice = elem_data.get('expert_choice', 'N/A')
                        sp_content = elem_data.get('sp_content', '')
                        
                        if choice == '적절함':
                            icon = "✅"
                        elif choice == '적절하지 않음':
                            icon = "❌"
                        else:
                            icon = "❓"
                        
                        st.write(f"{icon} **{elem_name}**: {choice}")
                        if sp_content:
                            st.caption(f"   SP Content: {sp_content[:100]}..." if len(sp_content) > 100 else f"   SP Content: {sp_content}")
                else:
                    st.warning("검증 항목 데이터가 없습니다.")
                
                # Qualitative evaluation
                if 'qualitative' in data and data['qualitative']:
                    st.markdown("---")
                    st.markdown("#### 📊 질적 평가")
                    qualitative = data['qualitative']
                    
                    for elem_key, elem_data in qualitative.items():
                        st.markdown(f"**{elem_key.upper()}**")
                        
                        rating = elem_data.get('rating', 'N/A')
                        st.write(f"   Rating: **{rating}**/5")
                        
                        plausible = elem_data.get('plausible_aspects', '')
                        if plausible:
                            st.write(f"   ✅ Plausible: {plausible}")
                        
                        less_plausible = elem_data.get('less_plausible_aspects', '')
                        if less_plausible:
                            st.write(f"   ⚠️ Less plausible: {less_plausible}")
                        
                        st.markdown("")
                
                # Additional impressions
                if 'additional_impressions' in data and data['additional_impressions']:
                    st.markdown("---")
                    st.markdown("#### 💭 추가 소견")
                    st.write(data['additional_impressions'])
                
                # Raw JSON
                with st.expander("🔧 Raw JSON", expanded=False):
                    st.json(data)
    else:
        st.info("6301 클라이언트에 대한 검증 결과가 없습니다.")
    
    st.markdown("---")
    
    # Show conversation logs
    if sp_conversation_keys:
        st.markdown("### 💬 대화 로그")
        
        for key in sorted(sp_conversation_keys):
            # Parse key to extract information
            parts = key.split('_')
            expert_name = '_'.join(parts[2:-2])
            client_num = parts[-2]
            page_num = parts[-1]
            
            with st.expander(f"💬 {key}", expanded=False):
                data = all_data[key]
                
                st.write(f"**전문가:** {data.get('expert_name', expert_name)}")
                st.write(f"**클라이언트:** {data.get('client_number', client_num)}")
                st.write(f"**페이지:** {data.get('page_number', page_num)}")
                st.write(f"**저장 시간:** {data.get('timestamp', 'N/A')}")
                
                st.markdown("---")
                
                if 'conversation' in data:
                    conversation = data['conversation']
                    st.markdown(f"**대화 메시지 수:** {len(conversation)}")
                    
                    for i, msg in enumerate(conversation):
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')
                        
                        if role == 'user':
                            st.markdown(f"**👨‍⚕️ Expert ({i}):**")
                            st.info(content)
                        else:
                            st.markdown(f"**🤖 SP ({i}):**")
                            st.success(content)
                else:
                    st.warning("대화 데이터가 없습니다.")
                
                # Raw JSON
                with st.expander("🔧 Raw JSON", expanded=False):
                    st.json(data)
    else:
        st.info("6301 클라이언트에 대한 대화 로그가 없습니다.")
    
    st.markdown("---")
    
    # Show progress data
    if progress_keys:
        st.markdown("### 📈 진행 상태")
        
        for key in sorted(progress_keys):
            with st.expander(f"📈 {key}", expanded=False):
                data = all_data[key]
                st.json(data)
    else:
        st.info("진행 상태 데이터가 없습니다.")
    
    st.markdown("---")
    
    # Debug: Show all keys containing 6301
    with st.expander("🔍 모든 6301 관련 키 (디버그)", expanded=False):
        all_6301_keys = [key for key in all_data.keys() if '6301' in key]
        st.write(f"총 {len(all_6301_keys)}개의 키 발견:")
        for key in sorted(all_6301_keys):
            st.write(f"- {key}")


if __name__ == "__main__":
    main()
