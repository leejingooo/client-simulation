import streamlit as st
import pandas as pd
import json
from firebase_config import get_firebase_ref
from SP_utils import sanitize_key

st.set_page_config(
    page_title="SP Validation Viewer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 SP Validation Viewer")
st.markdown("SP 검증 결과를 확인하는 페이지입니다.")

firebase_ref = get_firebase_ref()
if firebase_ref is None:
    st.error("Firebase 초기화 실패")
    st.stop()

# Get all data from Firebase
try:
    all_data = firebase_ref.get()
    
    if not all_data:
        st.warning("Firebase에 저장된 데이터가 없습니다.")
        st.stop()
    
    # Filter SP validation data
    sp_validations = {}
    sp_conversations = {}
    
    for key, value in all_data.items():
        if key.startswith("sp_validation_"):
            sp_validations[key] = value
        elif key.startswith("sp_conversation_"):
            sp_conversations[key] = value
    
    if not sp_validations:
        st.info("아직 SP 검증 데이터가 없습니다.")
        st.stop()
    
    # Display summary
    st.markdown("---")
    st.subheader(f"📋 총 {len(sp_validations)}개의 검증 결과")
    
    # Create summary table
    summary_data = []
    for key, data in sp_validations.items():
        summary_data.append({
            'Expert': data.get('expert_name', 'Unknown'),
            'Page #': data.get('page_number', '?'),
            'Client #': data.get('client_number', '?'),
            'Timestamp': data.get('timestamp', '')[:19] if data.get('timestamp') else '',
            'Status': '완료' if data.get('is_final') else '중간저장',
            'Diagnosis Guess': data.get('diagnosis_guess', ''),
            'Firebase Key': key
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df = summary_df.sort_values(['Expert', 'Page #'])
    
    st.dataframe(summary_df[['Expert', 'Page #', 'Client #', 'Timestamp', 'Status', 'Diagnosis Guess']], 
                 use_container_width=True, hide_index=True)
    
    # Selection
    st.markdown("---")
    st.subheader("🔍 상세 보기")
    
    selected_key = st.selectbox(
        "검증 결과 선택",
        options=list(sp_validations.keys()),
        format_func=lambda x: f"{sp_validations[x].get('expert_name', '?')} - 가상환자 {sp_validations[x].get('page_number', '?')} (Client {sp_validations[x].get('client_number', '?')})"
    )
    
    if selected_key:
        selected_data = sp_validations[selected_key]
        
        # Display metadata
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("검증자", selected_data.get('expert_name', 'Unknown'))
        with col2:
            st.metric("페이지 번호", selected_data.get('page_number', '?'))
        with col3:
            st.metric("Client Number", selected_data.get('client_number', '?'))
        with col4:
            status = '✅ 완료' if selected_data.get('is_final') else '💾 중간저장'
            st.metric("상태", status)
        
        st.caption(f"Timestamp: {selected_data.get('timestamp', '')}")
        
        st.markdown("---")
        
        # Display in tabs
        tab1, tab2, tab3 = st.tabs(["검증 결과", "대화 내역", "JSON 원본"])
        
        with tab1:
            st.subheader("검증 결과")
            
            # Element validations
            elements = selected_data.get('elements', {})
            
            if elements:
                # Create DataFrame for elements
                element_data = []
                for element_name, element_info in elements.items():
                    element_data.append({
                        'Element': element_name,
                        'SP Content': element_info.get('sp_content', ''),
                        'Expert Choice': element_info.get('expert_choice', '')
                    })
                
                element_df = pd.DataFrame(element_data)
                st.dataframe(element_df, use_container_width=True, hide_index=True)
                
                # Statistics
                st.markdown("---")
                st.markdown("#### 통계")
                
                total_elements = len(element_data)
                appropriate = sum(1 for e in element_data if e['Expert Choice'] == '적절함')
                inappropriate = total_elements - appropriate
                
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("총 항목 수", total_elements)
                with col_stat2:
                    st.metric("적절함", appropriate, delta=f"{appropriate/total_elements*100:.1f}%")
                with col_stat3:
                    st.metric("적절하지 않음", inappropriate, delta=f"{inappropriate/total_elements*100:.1f}%")
            else:
                st.info("검증된 항목이 없습니다.")
            
            st.markdown("---")
            
            # Additional questions
            st.markdown("#### 추가 질문 응답")
            
            col_q1, col_q2 = st.columns(2)
            with col_q1:
                st.markdown("**진단명 추측**")
                st.info(selected_data.get('diagnosis_guess', '없음'))
            
            with col_q2:
                st.markdown("**총평**")
                st.text_area(
                    "Comment",
                    value=selected_data.get('overall_comment', ''),
                    height=150,
                    disabled=True,
                    label_visibility="collapsed"
                )
        
        with tab2:
            st.subheader("대화 내역")
            
            # Find corresponding conversation
            expert = selected_data.get('expert_name', '')
            client_num = selected_data.get('client_number', '')
            page_num = selected_data.get('page_number', '')
            
            conv_key = f"sp_conversation_{sanitize_key(expert)}_{client_num}_{page_num}"
            
            if conv_key in sp_conversations:
                conversation = sp_conversations[conv_key].get('conversation', [])
                
                if conversation:
                    for msg in conversation:
                        role = msg.get('role', 'user')
                        content = msg.get('content', '')
                        
                        with st.chat_message(role):
                            st.markdown(content)
                else:
                    st.info("대화 내역이 없습니다.")
            else:
                st.warning(f"대화 내역을 찾을 수 없습니다. (Key: {conv_key})")
        
        with tab3:
            st.subheader("JSON 원본 데이터")
            st.json(selected_data)
    
    # Export functionality
    st.markdown("---")
    st.subheader("📥 데이터 내보내기")
    
    if st.button("모든 검증 결과를 CSV로 다운로드"):
        # Prepare CSV data
        csv_rows = []
        
        for key, data in sp_validations.items():
            expert = data.get('expert_name', '')
            page_num = data.get('page_number', '')
            client_num = data.get('client_number', '')
            timestamp = data.get('timestamp', '')
            is_final = data.get('is_final', False)
            diagnosis_guess = data.get('diagnosis_guess', '')
            overall_comment = data.get('overall_comment', '')
            
            elements = data.get('elements', {})
            
            for element_name, element_info in elements.items():
                csv_rows.append({
                    'expert_name': expert,
                    'page_number': page_num,
                    'client_number': client_num,
                    'timestamp': timestamp,
                    'is_final': is_final,
                    'element': element_name,
                    'sp_content': element_info.get('sp_content', ''),
                    'expert_choice': element_info.get('expert_choice', ''),
                    'diagnosis_guess': diagnosis_guess,
                    'overall_comment': overall_comment
                })
        
        if csv_rows:
            export_df = pd.DataFrame(csv_rows)
            csv = export_df.to_csv(index=False, encoding='utf-8-sig')
            
            st.download_button(
                label="📥 CSV 다운로드",
                data=csv,
                file_name=f"sp_validation_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning("내보낼 데이터가 없습니다.")

except Exception as e:
    st.error(f"데이터 로드 중 오류 발생: {e}")
    import traceback
    with st.expander("상세 오류"):
        st.code(traceback.format_exc())
