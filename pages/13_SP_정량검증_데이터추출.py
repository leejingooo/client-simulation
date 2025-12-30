"""
4.1 SP Quantitative Validation - 데이터 추출 및 분석 페이지
14 cases의 평가자별 element 검증 결과를 CSV로 추출

평가자들이 각 element를 "적절함(1점)" 또는 "적절하지 않음(0점)"으로 평가
같은 case를 두 번 평가하여 intra-observer reliability 측정
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
    page_title="SP 정량 검증 데이터",
    page_icon="📊",
    layout="wide"
)

# ================================
# PRESET - SP Sequence (14 cases)
# ================================
# (page_number, client_number) tuples
# 7 cases × 2 repetitions = 14 total cases
SP_SEQUENCE = [
    (1, 6201),
    (2, 6202),
    (3, 6203),
    (4, 6204),
    (5, 6205),
    (6, 6206),
    (7, 6207),
    (8, 6203),  # Repeat for intra-observer reliability
    (9, 6201),
    (10, 6204),
    (11, 6207),
    (12, 6202),
    (13, 6206),
    (14, 6205),
]

# Client to case mapping (for averaging)
CLIENT_TO_CASE = {
    6201: 'Case 1',
    6202: 'Case 2',
    6203: 'Case 3',
    6204: 'Case 4',
    6205: 'Case 5',
    6206: 'Case 6',
    6207: 'Case 7'
}

# Elements to validate (24 elements)
VALIDATION_ELEMENTS = [
    "Chief complaint",
    "Symptom name",
    "Alleviating factor",
    "Exacerbating factor",
    "Triggering factor",
    "Stressor",
    "Diagnosis",
    "Substance use",
    "Current family structure",
    "Suicidal ideation",
    "Self mutilating behavior risk",
    "Homicide risk",
    "Suicidal plan",
    "Suicidal attempt",
    "Mood",
    "Verbal productivity",
    "Insight",
    "Affect",
    "Perception",
    "Thought process",
    "Thought content",
    "Spontaneity",
    "Social judgement",
    "Reliability"
]

# ================================
# Data Loading Functions
# ================================
def load_all_sp_validations(firebase_ref):
    """Load all SP validation data from Firebase using stored expert_choice values.
    
    Returns:
        dict: {expert_name: {(page, client): {element: score, ...}, ...}, ...}
    """
    all_data = {}

    def _parse_meta_from_key(raw_key):
        # Expected pattern: sp_validation_<name>_<client>_<page>
        parts = raw_key.split('_')
        if len(parts) >= 5:
            try:
                client_val = int(parts[-2])
                page_val = int(parts[-1])
            except ValueError:
                client_val, page_val = None, None
            name_val = '_'.join(parts[2:-2])
            return name_val, client_val, page_val
        return None, None, None

    try:
        all_keys = firebase_ref.get()
        if not all_keys:
            return all_data

        for key in all_keys.keys():
            if not key.startswith('sp_validation_'):
                continue

            data = all_keys.get(key) or {}
            expert_name = data.get('expert_name')
            client_num = data.get('client_number')
            page_num = data.get('page_number')

            # Fallback to parsing from key name if metadata is missing
            if expert_name is None or client_num is None or page_num is None:
                parsed_name, parsed_client, parsed_page = _parse_meta_from_key(key)
                expert_name = expert_name or parsed_name or 'Unknown'
                client_num = client_num or parsed_client
                page_num = page_num or parsed_page

            if client_num is None or page_num is None:
                continue

            if expert_name not in all_data:
                all_data[expert_name] = {}

            element_scores = {}
            elements_block = data.get('elements', {})
            for element, elem_data in elements_block.items():
                choice = (elem_data or {}).get('expert_choice', '')
                if choice == '적절함':
                    element_scores[element] = 1
                elif choice == '적절하지 않음':
                    element_scores[element] = 0
                else:
                    element_scores[element] = None

            all_data[expert_name][(page_num, client_num)] = element_scores

        return all_data

    except Exception as e:
        st.error(f"데이터 로딩 오류: {e}")
        return {}

def create_raw_file_for_case(all_data, page_num, client_num):
    """Create raw CSV file for a single case
    
    Format: Rows=Elements, Columns=Evaluators, Values=Scores (0/1)
    
    Args:
        all_data: All validation data
        page_num: Page number
        client_num: Client number
        
    Returns:
        pd.DataFrame: Raw data table
    """
    # Get all experts who evaluated this case
    experts = sorted([expert for expert in all_data.keys() 
                     if (page_num, client_num) in all_data[expert]])
    
    if not experts:
        return None
    
    # Create DataFrame
    rows = []
    for element in VALIDATION_ELEMENTS:
        row = {'Element': element}
        for expert in experts:
            score = all_data[expert][(page_num, client_num)].get(element)
            row[expert] = score if score is not None else ''
        rows.append(row)
    
    df = pd.DataFrame(rows)
    return df

def create_average_file(all_data):
    """Create average CSV file across all 7 cases
    
    Format: Rows=7 Cases, Columns=Elements, Values=Average Scores
    For each case, average across all evaluators and both repetitions
    
    Returns:
        pd.DataFrame: Average scores table
    """
    # Group by case (client_number)
    case_scores = {}
    
    for client_num in sorted(set(client for _, client in SP_SEQUENCE)):
        case_name = CLIENT_TO_CASE[client_num]
        element_scores = {element: [] for element in VALIDATION_ELEMENTS}
        
        # Collect all scores for this case (from all pages/repetitions)
        for expert, expert_data in all_data.items():
            for (page_num, page_client), scores in expert_data.items():
                if page_client == client_num:
                    for element, score in scores.items():
                        if score is not None and element in element_scores:
                            element_scores[element].append(score)
        
        # Calculate averages
        avg_scores = {}
        for element, scores in element_scores.items():
            if scores:
                avg_scores[element] = np.mean(scores)
            else:
                avg_scores[element] = None
        
        case_scores[case_name] = avg_scores
    
    # Create DataFrame
    df = pd.DataFrame(case_scores).T  # Transpose so cases are rows
    df.index.name = 'Case'
    df = df.reset_index()
    
    return df

def calculate_reliability(all_data):
    """Calculate inter-observer and intra-observer reliability
    
    Returns:
        dict: Reliability metrics
    """
    reliability_stats = {}
    
    # Find repeated cases for intra-observer reliability
    # Cases that appear twice: 6201, 6202, 6203, 6204, 6205, 6206, 6207
    repeated_cases = {}
    for client_num in set(client for _, client in SP_SEQUENCE):
        pages = [page for page, client in SP_SEQUENCE if client == client_num]
        if len(pages) == 2:
            repeated_cases[client_num] = pages
    
    # Intra-observer reliability (agreement between two evaluations of same case)
    intra_agreements = []
    for expert, expert_data in all_data.items():
        for client_num, pages in repeated_cases.items():
            if len(pages) == 2:
                page1, page2 = pages
                if (page1, client_num) in expert_data and (page2, client_num) in expert_data:
                    scores1 = expert_data[(page1, client_num)]
                    scores2 = expert_data[(page2, client_num)]
                    
                    # Compare scores for each element
                    agreements = []
                    for element in VALIDATION_ELEMENTS:
                        score1 = scores1.get(element)
                        score2 = scores2.get(element)
                        if score1 is not None and score2 is not None:
                            agreements.append(1 if score1 == score2 else 0)
                    
                    if agreements:
                        intra_agreements.append(np.mean(agreements))
    
    reliability_stats['intra_observer_agreement'] = np.mean(intra_agreements) if intra_agreements else None
    reliability_stats['intra_observer_n'] = len(intra_agreements)
    
    # Inter-observer reliability (agreement between different evaluators for same case)
    inter_agreements = []
    for page_num, client_num in SP_SEQUENCE:
        experts_with_data = [expert for expert in all_data.keys() 
                            if (page_num, client_num) in all_data[expert]]
        
        if len(experts_with_data) >= 2:
            # Compare all pairs of experts
            for i, expert1 in enumerate(experts_with_data):
                for expert2 in experts_with_data[i+1:]:
                    scores1 = all_data[expert1][(page_num, client_num)]
                    scores2 = all_data[expert2][(page_num, client_num)]
                    
                    agreements = []
                    for element in VALIDATION_ELEMENTS:
                        score1 = scores1.get(element)
                        score2 = scores2.get(element)
                        if score1 is not None and score2 is not None:
                            agreements.append(1 if score1 == score2 else 0)
                    
                    if agreements:
                        inter_agreements.append(np.mean(agreements))
    
    reliability_stats['inter_observer_agreement'] = np.mean(inter_agreements) if inter_agreements else None
    reliability_stats['inter_observer_n'] = len(inter_agreements)
    
    return reliability_stats

# ================================
# Main Application
# ================================
def main():
    st.title("📊 SP 정량 검증 데이터 추출")
    st.markdown("---")
    
    st.info("""
    **분석 개요:**
    - 14 cases (7개 case × 2회 반복)
    - 24개 elements에 대한 평가자별 적절성 평가
    - Raw files: Case별 분리 (14개 파일)
    - 평균 파일: 7개 case의 element별 평균 점수 (1개 파일)
    - Reliability: Intra-observer 및 Inter-observer reliability 계산
    """)
    
    # Load data
    with st.spinner("Firebase에서 데이터 로딩 중..."):
        firebase_ref = get_firebase_ref()
        all_data = load_all_sp_validations(firebase_ref)
    
    if not all_data:
        st.warning("⚠️ 검증 데이터가 없습니다. 먼저 '가상환자에 대한 전문가 검증' 페이지에서 검증을 완료해주세요.")
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
    tab1, tab2, tab3 = st.tabs(["📄 Raw Files", "📊 평균 파일", "📈 Reliability"])
    
    # ===== TAB 1: Raw Files =====
    with tab1:
        st.markdown("### 📄 Raw Files (Case별 분리)")
        st.caption("각 case별로 평가자×element 테이블 생성 (14개 파일)")
        
        # Create all raw files
        raw_files = {}
        for page_num, client_num in SP_SEQUENCE:
            df = create_raw_file_for_case(all_data, page_num, client_num)
            if df is not None:
                raw_files[(page_num, client_num)] = df
        
        st.write(f"**생성된 파일 수:** {len(raw_files)}/14")
        
        # Download all raw files as ZIP
        if raw_files:
            # Create in-memory ZIP
            from zipfile import ZipFile
            zip_buffer = io.BytesIO()
            
            with ZipFile(zip_buffer, 'w') as zip_file:
                for (page_num, client_num), df in raw_files.items():
                    case_name = CLIENT_TO_CASE[client_num]
                    filename = f"raw_page{page_num}_{case_name}_client{client_num}.csv"
                    csv_data = df.to_csv(index=False).encode('utf-8-sig')
                    zip_file.writestr(filename, csv_data)
            
            zip_buffer.seek(0)
            st.download_button(
                label="📥 모든 Raw Files 다운로드 (ZIP)",
                data=zip_buffer,
                file_name=f"sp_validation_raw_files_{datetime.now().strftime('%Y%m%d')}.zip",
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
        st.caption("각 case의 element별 평균 점수 (평가자 및 반복 평균)")
        
        df_avg = create_average_file(all_data)
        
        if df_avg is not None and not df_avg.empty:
            # Display table
            st.dataframe(df_avg, use_container_width=True)
            
            # Download button
            csv_avg = df_avg.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 평균 파일 다운로드 (CSV)",
                data=csv_avg,
                file_name=f"sp_validation_average_{datetime.now().strftime('%Y%m%d')}.csv",
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
            fig, ax = plt.subplots(figsize=(20, 6))
            sns.heatmap(heatmap_data.T, annot=True, fmt='.2f', cmap='RdYlGn', 
                       vmin=0, vmax=1, ax=ax, cbar_kws={'label': 'Average Score'})
            ax.set_title('SP Validation Heatmap (Element × Case)', fontsize=14, fontweight='bold')
            ax.set_xlabel('Case', fontsize=12)
            ax.set_ylabel('Element', fontsize=12)
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.warning("평균 파일을 생성할 수 없습니다.")
    
    # ===== TAB 3: Reliability =====
    with tab3:
        st.markdown("### 📈 Reliability Analysis")
        
        reliability = calculate_reliability(all_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Intra-Observer Reliability")
            st.caption("같은 평가자가 같은 case를 두 번 평가한 결과의 일치도")
            
            if reliability['intra_observer_agreement'] is not None:
                st.metric(
                    "Simple Agreement",
                    f"{reliability['intra_observer_agreement']:.4f}",
                    help=f"Based on {reliability['intra_observer_n']} comparisons"
                )
                st.info(f"**n = {reliability['intra_observer_n']}** comparisons")
            else:
                st.warning("데이터 부족")
        
        with col2:
            st.markdown("#### Inter-Observer Reliability")
            st.caption("다른 평가자들 간의 평가 일치도")
            
            if reliability['inter_observer_agreement'] is not None:
                st.metric(
                    "Simple Agreement",
                    f"{reliability['inter_observer_agreement']:.4f}",
                    help=f"Based on {reliability['inter_observer_n']} comparisons"
                )
                st.info(f"**n = {reliability['inter_observer_n']}** comparisons")
            else:
                st.warning("데이터 부족")
        
        st.markdown("---")
        st.caption("""
        **Note:** 
        - Intra-observer reliability는 각 평가자가 같은 case를 두 번 평가한 결과 비교
        - Inter-observer reliability는 서로 다른 평가자들이 같은 case를 평가한 결과 비교
        - Simple Agreement: Element별 일치 비율의 평균
        - 논문에서는 Gwet's AC1, PABAK 등 추가 지표 사용
        """)

if __name__ == "__main__":
    main()
