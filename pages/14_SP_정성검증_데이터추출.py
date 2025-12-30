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
import pingouin as pg

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
    6201: 'MDD',  # Major Depressive Disorder
    6202: 'BD',   # Bipolar Disorder
    6203: 'PD',   # Panic Disorder
    6204: 'GAD',  # Generalized Anxiety Disorder
    6205: 'SAD',  # Social Anxiety Disorder
    6206: 'OCD',  # Obsessive-Compulsive Disorder
    6207: 'PTSD'  # Post-Traumatic Stress Disorder
}

# 검증자 목록 (12번 페이지와 동일)
VALIDATORS = ["이강토", "김태환", "김광현", "김주오", "허율", "장재용"]

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
    """Load SP qualitative validation data using stored ratings and text.
    
    Returns:
        dict: {expert_name: {(page, client): {element: {rating, plausible, less_plausible}, ...}, ...}, ...}
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

            # Fallback: parse from key name if metadata missing
            if expert_name is None or client_num is None or page_num is None:
                parsed_name, parsed_client, parsed_page = _parse_meta_from_key(key)
                expert_name = expert_name or parsed_name or 'Unknown'
                client_num = client_num or parsed_client
                page_num = page_num or parsed_page

            if client_num is None or page_num is None:
                continue

            # Filter: only load data from specified validators
            if expert_name not in VALIDATORS:
                continue

            if expert_name not in all_data:
                all_data[expert_name] = {}

            qual_data = {}
            qualitative_block = data.get('qualitative', {})
            for elem_key in ELEMENT_KEYS:
                if elem_key in qualitative_block:
                    elem_data = qualitative_block.get(elem_key, {})
                    qual_data[elem_key] = {
                        'rating': elem_data.get('rating'),
                        'plausible_aspects': elem_data.get('plausible_aspects', ''),
                        'less_plausible_aspects': elem_data.get('less_plausible_aspects', '')
                    }

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

def calculate_icc_accurate(case_element_ratings):
    """Calculate accurate ICC using pingouin library
    
    Args:
        case_element_ratings: dict of {(page, client, element): [ratings]}
    
    Returns:
        float: ICC(2,1) value - absolute agreement, single rater
    """
    if not case_element_ratings:
        return None
    
    # Prepare data in long format for pingouin
    # Format: targets (cases), raters (experts), ratings (values)
    data_rows = []
    
    for (page, client, element), ratings in case_element_ratings.items():
        if len(ratings) < 2:
            continue
        
        target_id = f"{page}_{client}_{element}"
        for rater_idx, rating in enumerate(ratings):
            data_rows.append({
                'targets': target_id,
                'raters': rater_idx,
                'ratings': rating
            })
    
    if len(data_rows) < 3:  # Need minimum data
        return None
    
    df = pd.DataFrame(data_rows)
    
    try:
        # Calculate ICC(2,1) - two-way random effects, absolute agreement, single rater
        icc_result = pg.intraclass_corr(data=df, targets='targets', raters='raters', ratings='ratings')
        # Extract ICC2 (two-way random effects, absolute agreement)
        icc2_row = icc_result[icc_result['Type'] == 'ICC2']
        if not icc2_row.empty:
            return icc2_row['ICC'].values[0]
        else:
            return None
    except Exception as e:
        st.warning(f"ICC calculation error: {e}")
        return None


def calculate_qualitative_reliability(all_data):
    """Calculate reliability for qualitative Likert scale ratings
    
    Returns:
        dict: Reliability metrics for Likert scale data
    """
    reliability_stats = {}
    
    # Find repeated cases
    repeated_cases = {}
    for client_num in set(client for _, client in SP_SEQUENCE):
        pages = [page for page, client in SP_SEQUENCE if client == client_num]
        if len(pages) == 2:
            repeated_cases[client_num] = pages
    
    # ===== INTRA-OBSERVER RELIABILITY =====
    # For Likert scale, we use Weighted Kappa or ICC
    intra_agreements = []
    intra_weighted_agreements = []
    
    for expert, expert_data in all_data.items():
        for client_num, pages in repeated_cases.items():
            if len(pages) == 2:
                page1, page2 = pages
                if (page1, client_num) in expert_data and (page2, client_num) in expert_data:
                    qual1 = expert_data[(page1, client_num)]
                    qual2 = expert_data[(page2, client_num)]
                    
                    # Compare ratings for each element
                    exact_matches = []
                    weighted_diffs = []
                    
                    for elem_key in ELEMENT_KEYS:
                        rating1 = qual1.get(elem_key, {}).get('rating')
                        rating2 = qual2.get(elem_key, {}).get('rating')
                        
                        if rating1 is not None and rating2 is not None:
                            # Exact match
                            exact_matches.append(1 if rating1 == rating2 else 0)
                            # Weighted agreement (closer ratings = higher agreement)
                            diff = abs(rating1 - rating2)
                            # Weight: 1 for exact match, 0.75 for 1-off, 0.5 for 2-off, etc.
                            weighted_score = max(0, 1 - (diff * 0.25))
                            weighted_diffs.append(weighted_score)
                    
                    if exact_matches:
                        intra_agreements.append(np.mean(exact_matches))
                    if weighted_diffs:
                        intra_weighted_agreements.append(np.mean(weighted_diffs))
    
    reliability_stats['intra_observer_agreement'] = np.mean(intra_agreements) if intra_agreements else None
    reliability_stats['intra_observer_weighted_agreement'] = np.mean(intra_weighted_agreements) if intra_weighted_agreements else None
    reliability_stats['intra_observer_n'] = len(intra_agreements)
    
    # ===== INTER-OBSERVER RELIABILITY =====
    # Collect all ratings by case and element for ICC calculation
    inter_agreements = []
    inter_weighted_agreements = []
    
    # For ICC: organize ratings by case-element pairs
    case_element_ratings = {}  # {(page, client, element): [ratings]}
    
    for page_num, client_num in SP_SEQUENCE:
        experts_with_data = [expert for expert in all_data.keys() 
                            if (page_num, client_num) in all_data[expert]]
        
        if len(experts_with_data) >= 2:
            # Collect ratings for ICC
            for elem_key in ELEMENT_KEYS:
                ratings_for_element = []
                for expert in experts_with_data:
                    rating = all_data[expert][(page_num, client_num)].get(elem_key, {}).get('rating')
                    if rating is not None:
                        ratings_for_element.append(rating)
                
                if len(ratings_for_element) >= 2:
                    key = (page_num, client_num, elem_key)
                    case_element_ratings[key] = ratings_for_element
            
            # Pairwise comparisons
            for i, expert1 in enumerate(experts_with_data):
                for expert2 in experts_with_data[i+1:]:
                    qual1 = all_data[expert1][(page_num, client_num)]
                    qual2 = all_data[expert2][(page_num, client_num)]
                    
                    exact_matches = []
                    weighted_diffs = []
                    
                    for elem_key in ELEMENT_KEYS:
                        rating1 = qual1.get(elem_key, {}).get('rating')
                        rating2 = qual2.get(elem_key, {}).get('rating')
                        
                        if rating1 is not None and rating2 is not None:
                            exact_matches.append(1 if rating1 == rating2 else 0)
                            diff = abs(rating1 - rating2)
                            weighted_score = max(0, 1 - (diff * 0.25))
                            weighted_diffs.append(weighted_score)
                    
                    if exact_matches:
                        inter_agreements.append(np.mean(exact_matches))
                    if weighted_diffs:
                        inter_weighted_agreements.append(np.mean(weighted_diffs))
    
    reliability_stats['inter_observer_agreement'] = np.mean(inter_agreements) if inter_agreements else None
    reliability_stats['inter_observer_weighted_agreement'] = np.mean(inter_weighted_agreements) if inter_weighted_agreements else None
    reliability_stats['inter_observer_n'] = len(inter_agreements)
    
    # Calculate ICC if we have enough data
    if case_element_ratings:
        # Use pingouin for accurate ICC calculation
        reliability_stats['inter_observer_icc'] = calculate_icc_accurate(case_element_ratings)
    else:
        reliability_stats['inter_observer_icc'] = None
    
    return reliability_stats


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
    # Clear any existing matplotlib figures
    import matplotlib.pyplot as plt
    plt.close('all')
    
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
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Raw Files", "📊 평균 파일", "📈 Reliability", "📝 텍스트 정리"])
    
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
            plt.close(fig)
            
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
    
    # ===== TAB 3: Reliability =====
    with tab3:
        st.markdown("### 📈 Reliability Analysis (Likert Scale)")
        
        reliability = calculate_qualitative_reliability(all_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Intra-Observer Reliability")
            st.caption("같은 평가자가 같은 case를 두 번 평가한 결과의 일치도 (Likert 1-5)")
            
            if reliability['intra_observer_agreement'] is not None:
                st.metric(
                    "Exact Agreement",
                    f"{reliability['intra_observer_agreement']:.4f}",
                    help="Proportion of ratings that exactly matched"
                )
                
                if reliability['intra_observer_weighted_agreement'] is not None:
                    st.metric(
                        "Weighted Agreement",
                        f"{reliability['intra_observer_weighted_agreement']:.4f}",
                        help="Agreement weighted by distance (1-off = 0.75, 2-off = 0.5, etc.)"
                    )
                
                st.info(f"**n = {reliability['intra_observer_n']}** comparisons")
            else:
                st.warning("데이터 부족")
        
        with col2:
            st.markdown("#### Inter-Observer Reliability")
            st.caption("다른 평가자들 간의 평가 일치도 (Likert 1-5)")
            
            if reliability['inter_observer_agreement'] is not None:
                st.metric(
                    "Exact Agreement",
                    f"{reliability['inter_observer_agreement']:.4f}",
                    help="Proportion of ratings that exactly matched"
                )
                
                if reliability['inter_observer_weighted_agreement'] is not None:
                    st.metric(
                        "Weighted Agreement",
                        f"{reliability['inter_observer_weighted_agreement']:.4f}",
                        help="Agreement weighted by distance"
                    )
                
                if reliability['inter_observer_icc'] is not None:
                    st.metric(
                        "ICC(2,1)",
                        f"{reliability['inter_observer_icc']:.4f}",
                        help="ICC(2,1): Two-way random effects, absolute agreement, single rater (calculated with pingouin)"
                    )
                
                st.info(f"**n = {reliability['inter_observer_n']}** comparisons")
            else:
                st.warning("데이터 부족")
        
        st.markdown("---")
        st.caption("""
        **Note (Likert Scale):** 
        - **Exact Agreement**: Proportion of identical ratings
        - **Weighted Agreement**: Closer ratings receive higher agreement scores (1-off = 0.75, 2-off = 0.5)
        - **ICC**: Intraclass Correlation Coefficient for continuous-like data, measures consistency across raters
        - Likert scale (1-5) requires different reliability measures than binary data
        """)
    
    # ===== TAB 4: 텍스트 정리 =====
    with tab4:
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
