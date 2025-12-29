"""
4.2 SP Qualitative Validation - 데이터 추출 및 분석 페이지
14 cases의 평가자별 정성 평가 결과를 CSV로 추출

평가 항목: Mood, Affect, Thought Process, Thought Content, Insight, Suicidal, Homicidal
Likert Scale: 1 (Clearly incompatible) ~ 5 (Prototypical)
"""

import streamlit as st
import pandas as pd
import numpy as np
from firebase_config import get_firebase_ref
from SP_utils import sanitize_key
from datetime import datetime
import io

# ================================
# Configuration
# ================================
st.set_page_config(
    page_title="SP 정성 검증 데이터",
    page_icon="📝",
    layout="wide"
)

# ================================
# PRESET - SP Sequence (14 cases)
# ================================
SP_SEQUENCE = [
    (1, 6201),
    (2, 6202),
    (3, 6203),
    (4, 6204),
    (5, 6205),
    (6, 6206),
    (7, 6207),
    (8, 6203),  # Repeat
    (9, 6201),
    (10, 6204),
    (11, 6207),
    (12, 6202),
    (13, 6206),
    (14, 6205),
]

# Client to case mapping
CLIENT_TO_CASE = {
    6201: 'Case 1',
    6202: 'Case 2',
    6203: 'Case 3',
    6204: 'Case 4',
    6205: 'Case 5',
    6206: 'Case 6',
    6207: 'Case 7'
}

# Psychiatric elements for qualitative evaluation
PSYCHIATRIC_ELEMENTS = [
    'Mood',
    'Affect',
    'Thought Process',
    'Thought Content',
    'Insight',
    'Suicidal Ideation / Plan / Attempt',
    'Homicidal Ideation'
]

ELEMENT_KEYS = ['mood', 'affect', 'thought_process', 'thought_content', 
                'insight', 'suicidal', 'homicidal']

ELEMENT_KEY_MAP = dict(zip(ELEMENT_KEYS, PSYCHIATRIC_ELEMENTS))

# Text questions (for text summary file)
TEXT_QUESTIONS = {
    'plausible_aspects': 'What aspects of the dialogue made this plausible?',
    'less_plausible_aspects': 'What aspects appeared less plausible or contradictory?',
    'additional_impressions': 'Additional Clinically Relevant Impressions'
}

# ================================
# Data Loading Functions
# ================================
def load_all_sp_qualitative(firebase_ref):
    """Load all SP qualitative validation data from Firebase
    
    Returns:
        dict: {expert_name: {(page, client): {element: {rating, plausible, less_plausible}, ...}, ...}, ...}
    """
    all_data = {}
    
    try:
        all_keys = firebase_ref.get()
        if not all_keys:
            return all_data
        
        # Filter for sp_validation keys
        for key in all_keys.keys():
            if key.startswith('sp_validation_'):
                data = firebase_ref.child(key).get()
                
                if data and 'qualitative' in data:
                    expert_name = data.get('expert_name', 'Unknown')
                    client_num = data.get('client_number')
                    page_num = data.get('page_number')
                    
                    if expert_name not in all_data:
                        all_data[expert_name] = {}
                    
                    # Extract qualitative data
                    qual_data = {}
                    for elem_key in ELEMENT_KEYS:
                        if elem_key in data['qualitative']:
                            elem_data = data['qualitative'][elem_key]
                            qual_data[elem_key] = {
                                'rating': elem_data.get('rating'),
                                'plausible_aspects': elem_data.get('plausible_aspects', ''),
                                'less_plausible_aspects': elem_data.get('less_plausible_aspects', '')
                            }
                    
                    # Add additional impressions
                    qual_data['additional_impressions'] = data.get('additional_impressions', '')
                    
                    all_data[expert_name][(page_num, client_num)] = qual_data
        
        return all_data
    
    except Exception as e:
        st.error(f"데이터 로딩 오류: {e}")
        return {}

def create_raw_file_for_case_qualitative(all_data, page_num, client_num):
    """Create raw CSV file for a single case (qualitative ratings)
    
    Format: Rows=Elements, Columns=Evaluators, Values=Likert Ratings (1-5)
    
    Returns:
        pd.DataFrame: Raw qualitative data table
    """
    # Get all experts who evaluated this case
    experts = sorted([expert for expert in all_data.keys() 
                     if (page_num, client_num) in all_data[expert]])
    
    if not experts:
        return None
    
    # Create DataFrame
    rows = []
    for elem_key, elem_name in ELEMENT_KEY_MAP.items():
        row = {'Element': elem_name}
        for expert in experts:
            rating = all_data[expert][(page_num, client_num)].get(elem_key, {}).get('rating')
            row[expert] = rating if rating is not None else ''
        rows.append(row)
    
    df = pd.DataFrame(rows)
    return df

def create_average_file_qualitative(all_data):
    """Create average CSV file for qualitative ratings
    
    Format: Rows=7 Cases, Columns=Elements, Values=Average Ratings
    
    Returns:
        pd.DataFrame: Average qualitative ratings table
    """
    # Group by case (client_number)
    case_scores = {}
    
    for client_num in sorted(set(client for _, client in SP_SEQUENCE)):
        case_name = CLIENT_TO_CASE[client_num]
        element_scores = {elem_key: [] for elem_key in ELEMENT_KEYS}
        
        # Collect all ratings for this case
        for expert, expert_data in all_data.items():
            for (page_num, page_client), qual_data in expert_data.items():
                if page_client == client_num:
                    for elem_key in ELEMENT_KEYS:
                        rating = qual_data.get(elem_key, {}).get('rating')
                        if rating is not None:
                            element_scores[elem_key].append(rating)
        
        # Calculate averages
        avg_scores = {}
        for elem_key, ratings in element_scores.items():
            if ratings:
                avg_scores[ELEMENT_KEY_MAP[elem_key]] = np.mean(ratings)
            else:
                avg_scores[ELEMENT_KEY_MAP[elem_key]] = None
        
        case_scores[case_name] = avg_scores
    
    # Create DataFrame
    df = pd.DataFrame(case_scores).T  # Transpose so cases are rows
    df.index.name = 'Case'
    df = df.reset_index()
    
    return df

def create_text_summary_file(all_data):
    """Create text summary CSV file
    
    Format: Rows=Questions, Columns=Evaluators, Values=Text Responses
    Each case gets separate section
    
    Returns:
        pd.DataFrame: Text summary table
    """
    rows = []
    
    # For each case
    for page_num, client_num in SP_SEQUENCE:
        case_name = CLIENT_TO_CASE[client_num]
        
        # Get all experts who evaluated this case
        experts = sorted([expert for expert in all_data.keys() 
                         if (page_num, client_num) in all_data[expert]])
        
        if not experts:
            continue
        
        # Add case header
        rows.append({
            'Case': f"Page {page_num} - {case_name} (Client {client_num})",
            'Element': '---',
            'Question': '---',
            **{expert: '---' for expert in experts}
        })
        
        # For each element
        for elem_key, elem_name in ELEMENT_KEY_MAP.items():
            # Plausible aspects
            row_plausible = {
                'Case': '',
                'Element': elem_name,
                'Question': TEXT_QUESTIONS['plausible_aspects']
            }
            for expert in experts:
                text = all_data[expert][(page_num, client_num)].get(elem_key, {}).get('plausible_aspects', '')
                row_plausible[expert] = text
            rows.append(row_plausible)
            
            # Less plausible aspects
            row_less = {
                'Case': '',
                'Element': elem_name,
                'Question': TEXT_QUESTIONS['less_plausible_aspects']
            }
            for expert in experts:
                text = all_data[expert][(page_num, client_num)].get(elem_key, {}).get('less_plausible_aspects', '')
                row_less[expert] = text
            rows.append(row_less)
        
        # Additional impressions
        row_additional = {
            'Case': '',
            'Element': 'Additional',
            'Question': TEXT_QUESTIONS['additional_impressions']
        }
        for expert in experts:
            text = all_data[expert][(page_num, client_num)].get('additional_impressions', '')
            row_additional[expert] = text
        rows.append(row_additional)
        
        # Blank row separator
        rows.append({col: '' for col in ['Case', 'Element', 'Question'] + experts})
    
    df = pd.DataFrame(rows)
    return df

# ================================
# Main Application
# ================================
def main():
    st.title("📝 SP 정성 검증 데이터 추출")
    st.markdown("---")
    
    st.info("""
    **분석 개요:**
    - 14 cases (7개 case × 2회 반복)
    - 7개 psychiatric elements에 대한 Likert scale 평가 (1-5)
    - Raw files: Case별 평가자×element 테이블 (14개 파일)
    - 평균 파일: 7개 case의 element별 평균 점수 (1개 파일)
    - 텍스트 정리 파일: 평가자별 자유 응답 정리 (1개 파일)
    """)
    
    # Load data
    with st.spinner("Firebase에서 데이터 로딩 중..."):
        firebase_ref = get_firebase_ref()
        all_data = load_all_sp_qualitative(firebase_ref)
    
    if not all_data:
        st.warning("⚠️ 정성 검증 데이터가 없습니다. 먼저 '가상환자에 대한 전문가 검증' 페이지에서 검증을 완료해주세요.")
        return
    
    st.success(f"✅ 데이터 로딩 완료: {len(all_data)}명의 평가자 데이터")
    
    # Show data summary
    st.markdown("### 📋 데이터 요약")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("평가자 수", len(all_data))
    with col2:
        total_evaluations = sum(len(expert_data) for expert_data in all_data.values())
        st.metric("총 평가 수", total_evaluations)
    with col3:
        expected = len(all_data) * 14
        coverage = (total_evaluations / expected * 100) if expected > 0 else 0
        st.metric("완료율", f"{coverage:.1f}%")
    
    st.markdown("---")
    
    # Tab layout
    tab1, tab2, tab3 = st.tabs(["📄 Raw Files", "📊 평균 파일", "📝 텍스트 정리"])
    
    # ===== TAB 1: Raw Files =====
    with tab1:
        st.markdown("### 📄 Raw Files (Case별 분리)")
        st.caption("각 case별로 평가자×element 테이블 생성 (Likert ratings 1-5)")
        
        # Create all raw files
        raw_files = {}
        for page_num, client_num in SP_SEQUENCE:
            df = create_raw_file_for_case_qualitative(all_data, page_num, client_num)
            if df is not None:
                raw_files[(page_num, client_num)] = df
        
        st.write(f"**생성된 파일 수:** {len(raw_files)}/14")
        
        # Download all raw files as ZIP
        if raw_files:
            from zipfile import ZipFile
            zip_buffer = io.BytesIO()
            
            with ZipFile(zip_buffer, 'w') as zip_file:
                for (page_num, client_num), df in raw_files.items():
                    case_name = CLIENT_TO_CASE[client_num]
                    filename = f"qualitative_raw_page{page_num}_{case_name}_client{client_num}.csv"
                    csv_data = df.to_csv(index=False).encode('utf-8-sig')
                    zip_file.writestr(filename, csv_data)
            
            zip_buffer.seek(0)
            st.download_button(
                label="📥 모든 Raw Files 다운로드 (ZIP)",
                data=zip_buffer,
                file_name=f"sp_qualitative_raw_files_{datetime.now().strftime('%Y%m%d')}.zip",
                mime="application/zip",
                use_container_width=True
            )
        
        # Show sample
        if raw_files:
            st.markdown("#### 샘플 미리보기 (첫 번째 파일)")
            sample_key = list(raw_files.keys())[0]
            st.dataframe(raw_files[sample_key], use_container_width=True)
    
    # ===== TAB 2: 평균 파일 =====
    with tab2:
        st.markdown("### 📊 평균 파일 (7 Cases)")
        st.caption("각 case의 element별 평균 Likert rating (1-5 scale)")
        
        df_avg = create_average_file_qualitative(all_data)
        
        if df_avg is not None and not df_avg.empty:
            # Display table
            st.dataframe(df_avg, use_container_width=True)
            
            # Download button
            csv_avg = df_avg.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 평균 파일 다운로드 (CSV)",
                data=csv_avg,
                file_name=f"sp_qualitative_average_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            # Heatmap visualization
            st.markdown("#### 📈 Heatmap 미리보기")
            
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            # Prepare data for heatmap
            heatmap_data = df_avg.set_index('Case')
            
            # Create heatmap
            fig, ax = plt.subplots(figsize=(14, 6))
            sns.heatmap(heatmap_data.T, annot=True, fmt='.2f', cmap='RdYlGn', 
                       vmin=1, vmax=5, ax=ax, cbar_kws={'label': 'Average Likert Rating'})
            ax.set_title('SP Qualitative Validation Heatmap (Element × Case)', 
                        fontsize=14, fontweight='bold')
            ax.set_xlabel('Case', fontsize=12)
            ax.set_ylabel('Psychiatric Element', fontsize=12)
            plt.tight_layout()
            st.pyplot(fig)
            
            # Summary statistics
            st.markdown("#### 📊 Summary Statistics")
            
            summary_stats = []
            for col in heatmap_data.columns:
                stats = heatmap_data[col].describe()
                summary_stats.append({
                    'Element': col,
                    'Mean': stats['mean'],
                    'Std': stats['std'],
                    'Min': stats['min'],
                    'Max': stats['max']
                })
            
            df_stats = pd.DataFrame(summary_stats)
            st.dataframe(df_stats, use_container_width=True)
        else:
            st.warning("평균 파일을 생성할 수 없습니다.")
    
    # ===== TAB 3: 텍스트 정리 =====
    with tab3:
        st.markdown("### 📝 텍스트 정리 파일")
        st.caption("평가자별 자유 응답 텍스트 정리 (질문별/Case별)")
        
        df_text = create_text_summary_file(all_data)
        
        if df_text is not None and not df_text.empty:
            # Display table (with scrollable height)
            st.dataframe(df_text, use_container_width=True, height=600)
            
            # Download button
            csv_text = df_text.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 텍스트 정리 파일 다운로드 (CSV)",
                data=csv_text,
                file_name=f"sp_qualitative_text_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            st.markdown("---")
            st.info("""
            **텍스트 정리 파일 구조:**
            - Case별로 구분 (총 14개 case)
            - 각 psychiatric element마다:
              - What aspects made this plausible?
              - What aspects appeared less plausible?
            - Additional clinically relevant impressions
            """)
        else:
            st.warning("텍스트 정리 파일을 생성할 수 없습니다.")

if __name__ == "__main__":
    main()
