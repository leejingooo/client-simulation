"""
4.3 PACA Quantitative Validation - 검증 결과 분석 페이지
Expert Score vs PSYCHE Score 비교 및 Correlation 분석

검증자 6명: 이강토, 김태환, 김광현, 김주오, 허율, 장재용
24 experiments: 3 disorders × 4 models × 2 reps
"""

import streamlit as st
import pandas as pd
import numpy as np
from firebase_config import get_firebase_ref
from expert_validation_utils import sanitize_firebase_key
import matplotlib.pyplot as plt
import matplotlib
from scipy import stats

# ================================
# Configuration
# ================================
st.set_page_config(
    page_title="PACA 검증 결과 분석",
    page_icon="📊",
    layout="wide"
)

# 한글 폰트 설정
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
matplotlib.rcParams['axes.unicode_minus'] = False

# ================================
# PRESET - Experiment Numbers
# ================================
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

# 검증자 목록
VALIDATORS = ["이강토", "김태환", "김광현", "김주오", "허율", "장재용"]

# 검증자 영어 이니셜 매핑 (한글 깨짐 방지)
VALIDATOR_INITIALS = {
    "이강토": "K.T. Lee",
    "김태환": "T.H. Kim",
    "김광현": "K.H. Kim",
    "김주오": "J.O. Kim",
    "허율": "Y. Heo",
    "장재용": "J.Y. Jang"
}

# Disorder mapping
DISORDER_MAP = {
    6201: "mdd",
    6202: "bd",
    6206: "ocd"
}

DISORDER_NAMES = {
    "mdd": "Major Depressive Disorder",
    "bd": "Bipolar Disorder",
    "ocd": "Obsessive-Compulsive Disorder"
}

# Model identification (explicit mapping for 24 experiments)
MODEL_BY_EXP = {
    # 6201 MDD
    3111: 'gptsmaller',
    3117: 'gptsmaller',
    1121: 'gptlarge',
    1123: 'gptlarge',
    3134: 'claudesmaller',
    3138: 'claudesmaller',
    1143: 'claudelarge',
    1145: 'claudelarge',
    # 6202 BD
    3211: 'gptsmaller',
    3212: 'gptsmaller',
    1221: 'gptlarge',
    1222: 'gptlarge',
    3231: 'claudesmaller',
    3234: 'claudesmaller',
    1241: 'claudelarge',
    1242: 'claudelarge',
    # 6206 OCD
    3611: 'gptsmaller',
    3612: 'gptsmaller',
    1621: 'gptlarge',
    1622: 'gptlarge',
    3631: 'claudesmaller',
    3632: 'claudesmaller',
    1641: 'claudelarge',
    1642: 'claudelarge',
}


def get_model_from_exp(exp_num):
    """Identify model from experiment number (explicit mapping)."""
    return MODEL_BY_EXP.get(exp_num, 'unknown')

# ================================
# Data Loading Functions
# ================================
def _possible_model_tags(base_model):
    # Support both old (smaller/large) and guided/basic naming seen in Firebase
    mapping = {
        'gptsmaller': ['gptsmaller', 'gptbasic'],
        'gptlarge': ['gptlarge', 'gptguided'],
        'claudesmaller': ['claudesmaller', 'claudebasic'],
        'claudelarge': ['claudelarge', 'claudeguided']
    }
    return mapping.get(base_model, [base_model])


def load_expert_scores(root_data):
    """Load expert scores for all validators and experiments from root snapshot."""
    expert_data = {}

    for validator in VALIDATORS:
        sanitized_name = sanitize_firebase_key(validator)
        validator_scores = {}

        for client_num, exp_num in EXPERIMENT_NUMBERS:
            key = f"expert_{sanitized_name}_{client_num}_{exp_num}"
            data = (root_data or {}).get(key, {}) or {}

            if 'expert_score' in data:
                validator_scores[(client_num, exp_num)] = data['expert_score']
            elif 'psyche_score' in data:  # backward compatibility
                validator_scores[(client_num, exp_num)] = data['psyche_score']
            else:
                validator_scores[(client_num, exp_num)] = None

        expert_data[validator] = validator_scores

    return expert_data


def load_psyche_scores(root_data):
    """Load automated PSYCHE scores from root snapshot.

    Model tags are ignored; exp_num is unique, so we match by client and exp suffix.
    """
    psyche_data = {}

    for client_num, exp_num in EXPERIMENT_NUMBERS:
        value = None
        target_prefix = f"clients_{client_num}_psyche_"
        target_suffix = f"_{exp_num}"

        for key, data in (root_data or {}).items():
            if not key.startswith(target_prefix):
                continue
            if not key.endswith(target_suffix):
                continue
            record = data or {}
            if 'psyche_score' in record:
                value = record['psyche_score']
                break

        psyche_data[(client_num, exp_num)] = value

    return psyche_data

def calculate_average_expert_scores(expert_data):
    """Calculate average expert scores across validators"""
    avg_scores = {}
    
    for exp in EXPERIMENT_NUMBERS:
        scores = []
        for validator in VALIDATORS:
            score = expert_data[validator].get(exp)
            if score is not None:
                scores.append(score)
        
        if scores:
            avg_scores[exp] = np.mean(scores)
        else:
            avg_scores[exp] = None
    
    return avg_scores

# ================================
# Visualization Functions
# ================================
def plot_correlation(avg_expert_scores, psyche_scores, title="Overall Correlation", 
                     color_by_model=False, disorder_filter=None, figsize=(8, 6)):
    """Plot correlation between average expert scores and PSYCHE scores"""
    fig, ax = plt.subplots(figsize=figsize)
    
    # Prepare data
    data_points = {'gptsmaller': [], 'gptlarge': [], 'claudesmaller': [], 'claudelarge': [], 'unknown': []}
    
    for exp in EXPERIMENT_NUMBERS:
        client_num, exp_num = exp
        
        # Filter by disorder if specified
        if disorder_filter and DISORDER_MAP[client_num] != disorder_filter:
            continue
        
        avg_score = avg_expert_scores.get(exp)
        psyche_score = psyche_scores.get(exp)
        
        if avg_score is not None and psyche_score is not None:
            model = get_model_from_exp(exp_num)
            if model not in data_points:
                model = 'unknown'
            data_points[model].append((psyche_score, avg_score))
    
    # Plot styles
    model_styles = {
        'gptsmaller': {'marker': 'o', 'color': 'blue', 'label': 'GPT Smaller'},
        'gptlarge': {'marker': 's', 'color': 'darkblue', 'label': 'GPT Large'},
        'claudesmaller': {'marker': '^', 'color': 'red', 'label': 'Claude Smaller'},
        'claudelarge': {'marker': 'D', 'color': 'darkred', 'label': 'Claude Large'},
        'unknown': {'marker': 'x', 'color': 'gray', 'label': 'Unknown'}
    }
    
    # Plot points
    all_x, all_y = [], []
    for model, points in data_points.items():
        if points:
            x, y = zip(*points)
            all_x.extend(x)
            all_y.extend(y)
            
            style = model_styles[model]
            if color_by_model:
                ax.scatter(x, y, marker=style['marker'], c=style['color'], 
                          s=100, alpha=0.6, label=style['label'], edgecolors='black')
            else:
                ax.scatter(x, y, marker=style['marker'], c='gray', 
                          s=100, alpha=0.6, label=style['label'], edgecolors='black')
    
    # Calculate correlation
    if len(all_x) >= 2:
        pearson_r, pearson_p = stats.pearsonr(all_x, all_y)
        spearman_r, spearman_p = stats.spearmanr(all_x, all_y)
        
        # Regression line
        z = np.polyfit(all_x, all_y, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(all_x), max(all_x), 100)
        ax.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2)
        
        # Add correlation info
        ax.text(0.05, 0.95, 
                f"Pearson's r = {pearson_r:.4f} (p = {pearson_p:.4f})\n"
                f"Spearman's ρ = {spearman_r:.4f} (p = {spearman_p:.4f})\n"
                f"n = {len(all_x)}",
                transform=ax.transAxes, fontsize=10,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    ax.set_xlabel('PSYCHE Score (Automated)', fontsize=12)
    ax.set_ylabel('Average Expert Score', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)
    
    return fig

# ================================
# Main Application
# ================================
def main():
    # Clear any existing matplotlib figures
    plt.close('all')
    
    st.title("📊 PACA 검증 결과 분석")
    st.markdown("---")
    
    st.info("""
    **분석 개요:**
    - 6명의 전문가 검증자의 Expert Score를 평균하여 PSYCHE Score와 비교합니다
    - 24개 실험: 3개 질환 (MDD, BD, OCD) × 4개 모델 × 2회 반복
    - 검증자: 이강토, 김태환, 김광현, 김주오, 허율, 장재용
    """)
    
    # Load data
    with st.spinner("데이터 로딩 중..."):
        firebase_ref = get_firebase_ref()
        root_snapshot = firebase_ref.get() or {}
        expert_data = load_expert_scores(root_snapshot)
        psyche_scores = load_psyche_scores(root_snapshot)
        avg_expert_scores = calculate_average_expert_scores(expert_data)
    
    st.success("✅ 데이터 로딩 완료")
    
    # Show data summary
    st.markdown("### 📋 데이터 요약")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        loaded_experts = sum(1 for v in expert_data.values() 
                           for score in v.values() if score is not None)
        st.metric("Expert Score 데이터", f"{loaded_experts} / {len(VALIDATORS) * len(EXPERIMENT_NUMBERS)}")
    
    with col2:
        loaded_psyche = sum(1 for score in psyche_scores.values() if score is not None)
        st.metric("PSYCHE Score 데이터", f"{loaded_psyche} / {len(EXPERIMENT_NUMBERS)}")
    
    with col3:
        valid_pairs = sum(1 for exp in EXPERIMENT_NUMBERS 
                         if avg_expert_scores.get(exp) is not None 
                         and psyche_scores.get(exp) is not None)
        st.metric("유효한 비교 쌍", f"{valid_pairs} / {len(EXPERIMENT_NUMBERS)}")
    
    st.markdown("---")
    
    # Overall correlation plot
    st.markdown("### 📈 전체 Correlation Plot (24개 실험)")
    fig_overall = plot_correlation(avg_expert_scores, psyche_scores, 
                                   title="Overall: Average Expert Score vs PSYCHE Score",
                                   color_by_model=True)
    st.pyplot(fig_overall)
    plt.close(fig_overall)
    
    st.markdown("---")
    
    # Disorder-specific plots
    st.markdown("### 📊 질환별 Correlation Plot (각 8개 실험)")
    
    # Create 3-column layout for disorders
    disorder_cols = st.columns(3)
    
    for i, disorder in enumerate(["mdd", "bd", "ocd"]):
        with disorder_cols[i]:
            fig_disorder = plot_correlation(
                avg_expert_scores, psyche_scores,
                title=f"{DISORDER_NAMES[disorder]}",
                color_by_model=True,
                disorder_filter=disorder,
                figsize=(5, 4)
            )
            st.pyplot(fig_disorder)
            plt.close(fig_disorder)
    
    st.markdown("---")
    
    # Individual validator correlation plots
    st.markdown("### 👥 검증자별 Correlation Plot")
    st.caption("각 검증자의 Expert Score와 PSYCHE Score의 상관관계 분석")
    
    # Create 2x3 grid for 6 validators
    cols_per_row = 3
    validator_rows = [VALIDATORS[i:i+cols_per_row] for i in range(0, len(VALIDATORS), cols_per_row)]
    
    for row_validators in validator_rows:
        cols = st.columns(cols_per_row)
        
        for idx, validator in enumerate(row_validators):
            with cols[idx]:
                # Collect data points for this validator (grouped by model)
                validator_data_points = {'gptsmaller': [], 'gptlarge': [], 'claudesmaller': [], 'claudelarge': []}
                
                for exp in EXPERIMENT_NUMBERS:
                    client_num, exp_num = exp
                    expert_score = expert_data[validator].get(exp)
                    psyche_score = psyche_scores.get(exp)
                    
                    if expert_score is not None and psyche_score is not None:
                        model = get_model_from_exp(exp_num)
                        if model in validator_data_points:
                            validator_data_points[model].append((psyche_score, expert_score))
                
                # Create mini plot
                fig_validator, ax_validator = plt.subplots(figsize=(5, 4))
                
                # Model styles (same as main plot)
                model_styles = {
                    'gptsmaller': {'marker': 'o', 'color': 'blue'},
                    'gptlarge': {'marker': 's', 'color': 'darkblue'},
                    'claudesmaller': {'marker': '^', 'color': 'red'},
                    'claudelarge': {'marker': 'D', 'color': 'darkred'}
                }
                
                # Collect all points for correlation calculation
                validator_x, validator_y = [], []
                
                # Plot points by model
                for model, points in validator_data_points.items():
                    if points:
                        x, y = zip(*points)
                        validator_x.extend(x)
                        validator_y.extend(y)
                        
                        style = model_styles[model]
                        ax_validator.scatter(x, y, marker=style['marker'], c=style['color'], 
                                           s=50, alpha=0.6, edgecolors='black')
                
                if len(validator_x) >= 2:
                    
                    # Calculate correlation
                    pearson_r, pearson_p = stats.pearsonr(validator_x, validator_y)
                    
                    # Regression line
                    z = np.polyfit(validator_x, validator_y, 1)
                    p = np.poly1d(z)
                    x_line = np.linspace(min(validator_x), max(validator_x), 100)
                    ax_validator.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2)
                    
                    # Add correlation info
                    ax_validator.text(0.05, 0.95, 
                                     f"r = {pearson_r:.3f}\np = {pearson_p:.4f}\nn = {len(validator_x)}",
                                     transform=ax_validator.transAxes, fontsize=9,
                                     verticalalignment='top',
                                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                else:
                    ax_validator.text(0.5, 0.5, 'Insufficient Data', 
                                     ha='center', va='center', fontsize=10)
                
                ax_validator.set_xlabel('PSYCHE Score', fontsize=10)
                ax_validator.set_ylabel('Expert Score', fontsize=10)
                ax_validator.set_title(VALIDATOR_INITIALS.get(validator, validator), fontsize=11, fontweight='bold')
                ax_validator.grid(True, alpha=0.3)
                plt.tight_layout()
                
                st.pyplot(fig_validator)
                plt.close(fig_validator)
    
    # Summary table of correlations
    st.markdown("#### 📊 검증자별 Correlation 요약")
    
    correlation_summary = []
    for validator in VALIDATORS:
        validator_x, validator_y = [], []
        
        for exp in EXPERIMENT_NUMBERS:
            expert_score = expert_data[validator].get(exp)
            psyche_score = psyche_scores.get(exp)
            
            if expert_score is not None and psyche_score is not None:
                validator_x.append(psyche_score)
                validator_y.append(expert_score)
        
        if len(validator_x) >= 2:
            pearson_r, pearson_p = stats.pearsonr(validator_x, validator_y)
            spearman_r, spearman_p = stats.spearmanr(validator_x, validator_y)
            
            correlation_summary.append({
                '검증자': validator,
                'n': len(validator_x),
                "Pearson's r": f"{pearson_r:.4f}",
                "Pearson's p": f"{pearson_p:.4f}",
                "Spearman's ρ": f"{spearman_r:.4f}",
                "Spearman's p": f"{spearman_p:.4f}"
            })
        else:
            correlation_summary.append({
                '검증자': validator,
                'n': len(validator_x),
                "Pearson's r": 'N/A',
                "Pearson's p": 'N/A',
                "Spearman's ρ": 'N/A',
                "Spearman's p": 'N/A'
            })
    
    df_corr_summary = pd.DataFrame(correlation_summary)
    st.dataframe(df_corr_summary, use_container_width=True)
    
    st.markdown("---")
    
    # Detailed data table
    st.markdown("### 📋 상세 데이터")
    
    # Create DataFrame
    rows = []
    for client_num, exp_num in EXPERIMENT_NUMBERS:
        disorder = DISORDER_MAP[client_num]
        model = get_model_from_exp(exp_num)
        
        row = {
            'Client': client_num,
            'Exp': exp_num,
            'Disorder': disorder.upper(),
            'Model': model,
            'PSYCHE Score': psyche_scores.get((client_num, exp_num), 'N/A')
        }
        
        # Add individual validator scores
        for validator in VALIDATORS:
            score = expert_data[validator].get((client_num, exp_num))
            row[validator] = score if score is not None else 'N/A'
        
        # Add average
        avg = avg_expert_scores.get((client_num, exp_num))
        row['Avg Expert Score'] = avg if avg is not None else 'N/A'
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
    
    # Download button
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name="paca_validation_results.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
