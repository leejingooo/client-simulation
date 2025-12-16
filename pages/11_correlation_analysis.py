import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr, spearmanr
from SP_utils import get_firebase_ref, load_from_firebase
from expert_validation_utils import sanitize_firebase_key
from evaluator import PSYCHE_RUBRIC
import json

# ================================
# PRESET - 분석 대상 Experiment Numbers
# ================================
# 에이전트 전문가 검증 페이지와 동일한 리스트
EXPERIMENT_NUMBERS = [
    # 6201 MDD
    (6201, 3111),  # gptsmaller
    (6201, 3117),  # gptsmaller
    (6201, 1121),  # gptlarge
    (6201, 1123),  # gptlarge
    (6201, 3134),  # claudesmaller
    (6201, 3138),  # claudesmaller
    (6201, 1143),  # claudelarge
    (6201, 1145),  # claudelarge

    # 6202 BD
    (6202, 3211),  # gptsmaller
    (6202, 3212),  # gptsmaller
    (6202, 1221),  # gptlarge
    (6202, 1222),  # gptlarge
    (6202, 3231),  # claudesmaller
    (6202, 3234),  # claudesmaller
    (6202, 1241),  # claudelarge
    (6202, 1242),  # claudelarge

    # 6206 OCD
    (6206, 3611),  # gptsmaller
    (6206, 3612),  # gptsmaller
    (6206, 1621),  # gptlarge
    (6206, 1622),  # gptlarge
    (6206, 3631),  # claudesmaller
    (6206, 3632),  # claudesmaller
    (6206, 1641),  # claudelarge
    (6206, 1642),  # claudelarge
]

# ================================
# Element Categories (from PSYCHE RUBRIC)
# ================================
ELEMENT_CATEGORIES = {
    'Subjective Information': [
        'Chief complaint',
        'Symptom name',
        'Alleviating factor',
        'Exacerbating factor',
        'Triggering factor',
        'Stressor',
        'Diagnosis',
        'Substance use',
        'Current family structure',
        'length'
    ],
    'Impulsivity': [
        'Suicidal ideation',
        'Self mutilating behavior risk',
        'Homicide risk',
        'Suicidal plan',
        'Suicidal attempt'
    ],
    'Behavior': [
        'Mood',
        'Verbal productivity',
        'Insight',
        'Affect',
        'Perception',
        'Thought process',
        'Thought content',
        'Spontaneity',
        'Social judgement',
        'Reliability'
    ]
}

# ================================
# Page Configuration
# ================================
st.set_page_config(
    page_title="PSYCHE vs Expert Correlation Analysis",
    page_icon="📈",
    layout="wide"
)

# ================================
# Authentication Check
# ================================
def check_expert_login():
    """Check if expert is logged in"""
    if "name" not in st.session_state or not st.session_state.get("name_correct", False):
        st.warning("⚠️ 먼저 Home 페이지에서 로그인해주세요.")
        st.stop()
    else:
        return True

# ================================
# Data Loading Functions
# ================================
def find_psyche_key_for_experiment(firebase_ref, client_num, exp_num):
    """
    Find the PSYCHE score key for a given experiment.
    Format: psyche_{diagnosis}_{model}_{exp_num}
    
    Returns the matching key or None if not found.
    """
    try:
        all_data = firebase_ref.get()
        if not all_data:
            return None
        
        # Search for keys matching pattern: psyche_*_*_{exp_num}
        exp_num_str = str(exp_num)
        for key in all_data.keys():
            if key.startswith(f"clients_{client_num}_psyche_") and key.endswith(f"_{exp_num_str}"):
                # Extract the psyche key part
                # Format: clients_{client_num}_psyche_{diagnosis}_{model}_{exp_num}
                psyche_key = key.replace(f"clients_{client_num}_", "")
                return psyche_key
        
        return None
    except Exception as e:
        st.warning(f"Error searching for PSYCHE key: {e}")
        return None


def load_psyche_score(firebase_ref, client_num, exp_num):
    """
    Load PSYCHE score data for a given experiment.
    Returns dict with element-level scores or None if not found.
    """
    try:
        psyche_key = find_psyche_key_for_experiment(firebase_ref, client_num, exp_num)
        if not psyche_key:
            return None
        
        data = load_from_firebase(firebase_ref, str(client_num), psyche_key)
        return data
    except Exception as e:
        st.warning(f"Error loading PSYCHE score for {client_num}_{exp_num}: {e}")
        return None


def load_expert_score(firebase_ref, expert_name, client_num, exp_num):
    """
    Load Expert score data for a given experiment.
    Returns dict with element-level scores or None if not found.
    """
    try:
        sanitized_expert_name = sanitize_firebase_key(expert_name)
        expert_key = f"expert_{sanitized_expert_name}_{client_num}_{exp_num}"
        
        data = firebase_ref.child(expert_key).get()
        return data
    except Exception as e:
        st.warning(f"Error loading Expert score for {client_num}_{exp_num}: {e}")
        return None


def load_all_scores(firebase_ref, expert_name, experiment_list):
    """
    Load all PSYCHE and Expert scores for the given experiment list.
    
    Returns:
        List of dicts with structure:
        [{
            'client_num': 6201,
            'exp_num': 1111,
            'psyche_data': {...},
            'expert_data': {...},
            'psyche_score': 35.5,
            'expert_score': 42.0
        }, ...]
    """
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, (client_num, exp_num) in enumerate(experiment_list):
        status_text.text(f"Loading {idx+1}/{len(experiment_list)}: Client {client_num}, Exp {exp_num}")
        
        psyche_data = load_psyche_score(firebase_ref, client_num, exp_num)
        expert_data = load_expert_score(firebase_ref, expert_name, client_num, exp_num)
        
        # Only include if both data exist
        if psyche_data and expert_data:
            psyche_score = psyche_data.get('psyche_score', 0)
            expert_score = expert_data.get('expert_score', 0)
            
            results.append({
                'client_num': client_num,
                'exp_num': exp_num,
                'psyche_data': psyche_data,
                'expert_data': expert_data,
                'psyche_score': psyche_score,
                'expert_score': expert_score
            })
        
        progress_bar.progress((idx + 1) / len(experiment_list))
    
    status_text.text(f"✅ Loaded {len(results)}/{len(experiment_list)} complete pairs")
    
    return results


# ================================
# Category Score Calculation
# ================================
def calculate_category_scores(data_list, category_name):
    """
    Calculate category-specific scores for both PSYCHE and Expert.
    
    Args:
        data_list: List of experiment data dicts
        category_name: 'Subjective Information', 'Impulsivity', or 'Behavior'
    
    Returns:
        List of tuples: [(psyche_category_score, expert_category_score), ...]
    """
    category_elements = ELEMENT_CATEGORIES[category_name]
    category_scores = []
    
    for item in data_list:
        psyche_data = item['psyche_data']
        expert_data = item['expert_data']
        
        # Calculate PSYCHE category score
        psyche_category_score = 0
        for element in category_elements:
            if element in psyche_data and isinstance(psyche_data[element], dict):
                weighted_score = psyche_data[element].get('weighted_score', 0)
                psyche_category_score += weighted_score
        
        # Calculate Expert category score
        expert_category_score = 0
        if 'elements' in expert_data:
            for element in category_elements:
                if element in expert_data['elements']:
                    weighted_score = expert_data['elements'][element].get('weighted_score', 0)
                    expert_category_score += weighted_score
        
        category_scores.append((psyche_category_score, expert_category_score))
    
    return category_scores


def calculate_element_scores(data_list, element_name):
    """
    Calculate element-specific scores for both PSYCHE and Expert.
    
    Args:
        data_list: List of experiment data dicts
        element_name: Name of the element (e.g., 'Mood', 'Chief complaint')
    
    Returns:
        List of tuples: [(psyche_element_score, expert_element_score), ...]
    """
    element_scores = []
    
    for item in data_list:
        psyche_data = item['psyche_data']
        expert_data = item['expert_data']
        
        psyche_weighted = 0
        expert_weighted = 0
        
        # Get PSYCHE weighted score
        if element_name in psyche_data and isinstance(psyche_data[element_name], dict):
            psyche_weighted = psyche_data[element_name].get('weighted_score', 0)
        
        # Get Expert weighted score
        if 'elements' in expert_data and element_name in expert_data['elements']:
            expert_weighted = expert_data['elements'][element_name].get('weighted_score', 0)
        
        element_scores.append((psyche_weighted, expert_weighted))
    
    return element_scores


# ================================
# Correlation Calculation
# ================================
def calculate_correlation(x_values, y_values, method='pearson'):
    """
    Calculate correlation coefficient and p-value.
    
    Args:
        x_values: List of x values (e.g., PSYCHE scores)
        y_values: List of y values (e.g., Expert scores)
        method: 'pearson' or 'spearman'
    
    Returns:
        (correlation_coefficient, p_value)
    """
    if len(x_values) < 2 or len(y_values) < 2:
        return None, None
    
    if method == 'pearson':
        corr, pval = pearsonr(x_values, y_values)
    else:  # spearman
        corr, pval = spearmanr(x_values, y_values)
    
    return corr, pval


# ================================
# Visualization Functions
# ================================
def plot_scatter(x_values, y_values, title, xlabel, ylabel, corr=None, pval=None):
    """
    Create scatter plot with regression line.
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Scatter plot
    ax.scatter(x_values, y_values, alpha=0.6, s=100)
    
    # Add regression line
    if len(x_values) > 1:
        z = np.polyfit(x_values, y_values, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(x_values), max(x_values), 100)
        ax.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2)
    
    # Add correlation info
    if corr is not None and pval is not None:
        textstr = f'r = {corr:.3f}\np = {pval:.4f}'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=12,
                verticalalignment='top', bbox=props)
    
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    return fig


def create_correlation_heatmap(correlation_matrix, labels, title):
    """
    Create heatmap of correlation matrix.
    """
    fig, ax = plt.subplots(figsize=(10, 8))
    
    sns.heatmap(correlation_matrix, annot=True, fmt='.3f', cmap='coolwarm',
                center=0, vmin=-1, vmax=1, square=True,
                xticklabels=labels, yticklabels=labels,
                cbar_kws={'label': 'Correlation Coefficient'}, ax=ax)
    
    ax.set_title(title, fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    return fig


# ================================
# Main Page
# ================================
def main():
    check_expert_login()
    
    st.title("📈 PSYCHE vs Expert Score Correlation Analysis")
    st.markdown("---")
    
    st.markdown("""
    ## 분석 개요
    
    본 페이지는 **자동 평가(PSYCHE Score)**와 **전문가 검증(Expert Score)** 간의 상관관계를 분석합니다.
    
    ### 분석 수준
    1. **Overall Correlation**: 전체 점수 (0-55점) 간 상관관계
    2. **Category-level Correlation**: 카테고리별 부분 점수 상관관계
       - Subjective Information (최대 10점)
       - Impulsivity (최대 25점)
       - Behavior (최대 20점)
    3. **Element-level Correlation**: 개별 element별 상관관계
    
    ### 분석 대상
    - 총 **{total}개**의 실험 (MDD, BD, OCD 환자 대상)
    - Client 번호: 6201 (MDD), 6202 (BD), 6206 (OCD)
    """.format(total=len(EXPERIMENT_NUMBERS)))
    
    st.markdown("---")
    
    # Initialize Firebase
    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error("Firebase 연결에 실패했습니다. 설정을 확인해주세요.")
        st.stop()
    
    # Select expert for analysis
    expert_name = st.session_state.get("name", "")
    
    st.info(f"📊 분석 대상 전문가: **{expert_name}**")
    
    # Load data
    if st.button("🔍 데이터 로드 및 분석 시작", type="primary", use_container_width=True):
        with st.spinner("데이터를 로드하는 중..."):
            data_list = load_all_scores(firebase_ref, expert_name, EXPERIMENT_NUMBERS)
        
        if not data_list:
            st.error("데이터를 찾을 수 없습니다. PSYCHE 평가와 전문가 검증이 모두 완료되었는지 확인해주세요.")
            st.stop()
        
        st.success(f"✅ {len(data_list)}개의 완전한 데이터 쌍을 로드했습니다!")
        
        # Store in session state
        st.session_state.correlation_data = data_list
    
    # Display analysis if data is loaded
    if 'correlation_data' in st.session_state:
        data_list = st.session_state.correlation_data
        
        st.markdown("---")
        st.header("📊 분석 결과")
        
        # Create tabs for different analysis levels
        tab1, tab2, tab3, tab4 = st.tabs([
            "Overall Correlation",
            "Category-level Correlation",
            "Element-level Correlation",
            "Data Table"
        ])
        
        # ================================
        # Tab 1: Overall Correlation
        # ================================
        with tab1:
            st.subheader("전체 점수 상관관계 (Overall)")
            
            psyche_scores = [item['psyche_score'] for item in data_list]
            expert_scores = [item['expert_score'] for item in data_list]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("PSYCHE Score 평균", f"{np.mean(psyche_scores):.2f}")
                st.metric("PSYCHE Score 표준편차", f"{np.std(psyche_scores):.2f}")
            
            with col2:
                st.metric("Expert Score 평균", f"{np.mean(expert_scores):.2f}")
                st.metric("Expert Score 표준편차", f"{np.std(expert_scores):.2f}")
            
            # Calculate correlations
            pearson_corr, pearson_pval = calculate_correlation(psyche_scores, expert_scores, 'pearson')
            spearman_corr, spearman_pval = calculate_correlation(psyche_scores, expert_scores, 'spearman')
            
            st.markdown("### 상관계수")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Pearson r", f"{pearson_corr:.3f}")
                st.caption(f"p-value: {pearson_pval:.4f}")
            
            with col2:
                st.metric("Spearman ρ", f"{spearman_corr:.3f}")
                st.caption(f"p-value: {spearman_pval:.4f}")
            
            # Scatter plot
            fig = plot_scatter(
                psyche_scores, expert_scores,
                "PSYCHE Score vs Expert Score (Overall)",
                "PSYCHE Score (0-55)",
                "Expert Score (0-55)",
                pearson_corr, pearson_pval
            )
            st.pyplot(fig)
            plt.close()
        
        # ================================
        # Tab 2: Category-level Correlation
        # ================================
        with tab2:
            st.subheader("카테고리별 상관관계")
            
            for category_name in ELEMENT_CATEGORIES.keys():
                st.markdown(f"### {category_name}")
                
                category_scores = calculate_category_scores(data_list, category_name)
                psyche_cat_scores = [score[0] for score in category_scores]
                expert_cat_scores = [score[1] for score in category_scores]
                
                # Get max possible score for this category
                elements = ELEMENT_CATEGORIES[category_name]
                max_score = sum(PSYCHE_RUBRIC[elem]['weight'] for elem in elements if elem in PSYCHE_RUBRIC)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("최대 점수", f"{max_score}")
                
                with col2:
                    st.metric("PSYCHE 평균", f"{np.mean(psyche_cat_scores):.2f}")
                
                with col3:
                    st.metric("Expert 평균", f"{np.mean(expert_cat_scores):.2f}")
                
                # Calculate correlations
                pearson_corr, pearson_pval = calculate_correlation(psyche_cat_scores, expert_cat_scores, 'pearson')
                spearman_corr, spearman_pval = calculate_correlation(psyche_cat_scores, expert_cat_scores, 'spearman')
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Pearson r", f"{pearson_corr:.3f}" if pearson_corr else "N/A")
                    if pearson_pval:
                        st.caption(f"p-value: {pearson_pval:.4f}")
                
                with col2:
                    st.metric("Spearman ρ", f"{spearman_corr:.3f}" if spearman_corr else "N/A")
                    if spearman_pval:
                        st.caption(f"p-value: {spearman_pval:.4f}")
                
                # Scatter plot
                if pearson_corr:
                    fig = plot_scatter(
                        psyche_cat_scores, expert_cat_scores,
                        f"{category_name} - PSYCHE vs Expert",
                        f"PSYCHE Score (0-{max_score})",
                        f"Expert Score (0-{max_score})",
                        pearson_corr, pearson_pval
                    )
                    st.pyplot(fig)
                    plt.close()
                
                st.markdown("---")
        
        # ================================
        # Tab 3: Element-level Correlation
        # ================================
        with tab3:
            st.subheader("Element별 상관관계")
            
            st.info("💡 각 PSYCHE RUBRIC element별로 weighted score 간 상관관계를 분석합니다.")
            
            # Select category to view
            selected_category = st.selectbox(
                "카테고리 선택",
                list(ELEMENT_CATEGORIES.keys())
            )
            
            elements = ELEMENT_CATEGORIES[selected_category]
            
            # Calculate correlations for all elements in category
            element_results = []
            
            for element in elements:
                if element not in PSYCHE_RUBRIC:
                    continue
                
                element_scores = calculate_element_scores(data_list, element)
                psyche_elem_scores = [score[0] for score in element_scores]
                expert_elem_scores = [score[1] for score in element_scores]
                
                # Only calculate if there's variation
                if len(set(psyche_elem_scores)) > 1 and len(set(expert_elem_scores)) > 1:
                    pearson_corr, pearson_pval = calculate_correlation(
                        psyche_elem_scores, expert_elem_scores, 'pearson'
                    )
                    
                    element_results.append({
                        'Element': element,
                        'Weight': PSYCHE_RUBRIC[element]['weight'],
                        'Pearson r': f"{pearson_corr:.3f}" if pearson_corr else "N/A",
                        'p-value': f"{pearson_pval:.4f}" if pearson_pval else "N/A",
                        'PSYCHE Mean': f"{np.mean(psyche_elem_scores):.2f}",
                        'Expert Mean': f"{np.mean(expert_elem_scores):.2f}"
                    })
            
            if element_results:
                df_elements = pd.DataFrame(element_results)
                st.dataframe(df_elements, use_container_width=True, hide_index=True)
                
                # Select specific element to visualize
                st.markdown("---")
                selected_element = st.selectbox(
                    "상세 시각화할 Element 선택",
                    [elem['Element'] for elem in element_results]
                )
                
                if selected_element:
                    element_scores = calculate_element_scores(data_list, selected_element)
                    psyche_elem_scores = [score[0] for score in element_scores]
                    expert_elem_scores = [score[1] for score in element_scores]
                    
                    pearson_corr, pearson_pval = calculate_correlation(
                        psyche_elem_scores, expert_elem_scores, 'pearson'
                    )
                    
                    weight = PSYCHE_RUBRIC[selected_element]['weight']
                    
                    fig = plot_scatter(
                        psyche_elem_scores, expert_elem_scores,
                        f"{selected_element} - PSYCHE vs Expert",
                        f"PSYCHE Weighted Score (weight={weight})",
                        f"Expert Weighted Score (weight={weight})",
                        pearson_corr, pearson_pval
                    )
                    st.pyplot(fig)
                    plt.close()
            else:
                st.warning("이 카테고리에는 분석 가능한 element가 없습니다.")
        
        # ================================
        # Tab 4: Data Table
        # ================================
        with tab4:
            st.subheader("원본 데이터")
            
            # Create summary table
            summary_data = []
            for item in data_list:
                summary_data.append({
                    'Client Number': item['client_num'],
                    'Experiment Number': item['exp_num'],
                    'PSYCHE Score': f"{item['psyche_score']:.2f}",
                    'Expert Score': f"{item['expert_score']:.2f}"
                })
            
            df_summary = pd.DataFrame(summary_data)
            st.dataframe(df_summary, use_container_width=True, hide_index=True)
            
            # Download button
            csv = df_summary.to_csv(index=False)
            st.download_button(
                label="📥 CSV 다운로드",
                data=csv,
                file_name=f"correlation_data_{expert_name}.csv",
                mime="text/csv"
            )


if __name__ == "__main__":
    main()
