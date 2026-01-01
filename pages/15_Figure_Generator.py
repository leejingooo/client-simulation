"""
논문용 Figure 생성 페이지
Publication-quality figures for PSYCHE framework paper

모든 폰트는 Helvetica로 통일
All fonts unified to Helvetica
"""

import streamlit as st
import pandas as pd
import numpy as np
from firebase_config import get_firebase_ref
from expert_validation_utils import sanitize_firebase_key
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import rcParams
from scipy import stats
import seaborn as sns
import io

# ================================
# Configuration
# ================================
st.set_page_config(
    page_title="Publication Figures",
    page_icon="📊",
    layout="wide"
)

# Helvetica 폰트 설정
rcParams['font.family'] = 'Helvetica'
rcParams['axes.unicode_minus'] = False

# Seaborn 스타일
sns.set_style("ticks")

# ================================
# PRESET - Experiment Numbers
# ================================
EXPERIMENT_NUMBERS = [
    # 6201 MDD
    (6201, 3111), (6201, 3117),  # gptsmaller
    (6201, 1121), (6201, 1123),  # gptlarge
    (6201, 3134), (6201, 3138),  # claudesmaller
    (6201, 1143), (6201, 1145),  # claudelarge
    # 6202 BD
    (6202, 3211), (6202, 3212),  # gptsmaller
    (6202, 1221), (6202, 1222),  # gptlarge
    (6202, 3231), (6202, 3234),  # claudesmaller
    (6202, 1241), (6202, 1242),  # claudelarge
    # 6206 OCD
    (6206, 3611), (6206, 3612),  # gptsmaller
    (6206, 1621), (6206, 1622),  # gptlarge
    (6206, 3631), (6206, 3632),  # claudesmaller
    (6206, 1641), (6206, 1642),  # claudelarge
]

VALIDATORS = ["이강토", "김태환", "김광현", "김주오", "허율", "장재용"]

VALIDATOR_INITIALS = {
    "이강토": "K.T. Lee",
    "김태환": "T.H. Kim",
    "김광현": "K.H. Kim",
    "김주오": "J.O. Kim",
    "허율": "Y. Heo",
    "장재용": "J.Y. Jang"
}

DISORDER_MAP = {6201: "mdd", 6202: "bd", 6206: "ocd"}
DISORDER_NAMES = {
    "mdd": "Major Depressive Disorder",
    "bd": "Bipolar Disorder",
    "ocd": "Obsessive-Compulsive Disorder"
}

MODEL_BY_EXP = {
    3111: 'gptsmaller', 3117: 'gptsmaller',
    1121: 'gptlarge', 1123: 'gptlarge',
    3134: 'claudesmaller', 3138: 'claudesmaller',
    1143: 'claudelarge', 1145: 'claudelarge',
    3211: 'gptsmaller', 3212: 'gptsmaller',
    1221: 'gptlarge', 1222: 'gptlarge',
    3231: 'claudesmaller', 3234: 'claudesmaller',
    1241: 'claudelarge', 1242: 'claudelarge',
    3611: 'gptsmaller', 3612: 'gptsmaller',
    1621: 'gptlarge', 1622: 'gptlarge',
    3631: 'claudesmaller', 3632: 'claudesmaller',
    1641: 'claudelarge', 1642: 'claudelarge',
}

# 색상 및 마커 매핑 (논문용)
COLOR_MAP = {
    "gptsmaller": "#2ecc71",     # 초록색
    "gptlarge": "#27ae60",       # 진한 초록색
    "claudesmaller": "#e67e22",  # 주황색
    "claudelarge": "#d35400"     # 진한 주황색
}

MARKER_MAP = {
    "gptsmaller": {"marker": "o", "size": 300},
    "gptlarge": {"marker": "*", "size": 600},
    "claudesmaller": {"marker": "o", "size": 300},
    "claudelarge": {"marker": "*", "size": 600}
}

LABEL_MAP = {
    "gptsmaller": "GPT-Smaller",
    "gptlarge": "GPT-Large",
    "claudesmaller": "Claude-Smaller",
    "claudelarge": "Claude-Large"
}

def get_model_from_exp(exp_num):
    """Identify model from experiment number."""
    return MODEL_BY_EXP.get(exp_num, 'unknown')

# ================================
# Data Loading Functions
# ================================
def load_expert_scores(root_data):
    """Load expert scores for all validators and experiments."""
    expert_data = {}
    for validator in VALIDATORS:
        sanitized_name = sanitize_firebase_key(validator)
        validator_scores = {}
        for client_num, exp_num in EXPERIMENT_NUMBERS:
            key = f"expert_{sanitized_name}_{client_num}_{exp_num}"
            data = (root_data or {}).get(key, {}) or {}
            if 'expert_score' in data:
                validator_scores[(client_num, exp_num)] = data['expert_score']
            elif 'psyche_score' in data:
                validator_scores[(client_num, exp_num)] = data['psyche_score']
            else:
                validator_scores[(client_num, exp_num)] = None
        expert_data[validator] = validator_scores
    return expert_data

def load_psyche_scores(root_data):
    """Load automated PSYCHE scores."""
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
    """Calculate average expert scores across validators."""
    avg_scores = {}
    for exp in EXPERIMENT_NUMBERS:
        scores = [expert_data[v].get(exp) for v in VALIDATORS if expert_data[v].get(exp) is not None]
        avg_scores[exp] = np.mean(scores) if scores else None
    return avg_scores

# ================================
# Figure 1: PSYCHE-Expert Correlation
# ================================
def create_correlation_plot_average(psyche_scores, avg_expert_scores, figsize=(8, 8)):
    """Figure 1-1: Average expert score correlation plot."""
    fig, ax = plt.subplots(figsize=figsize)
    
    # 데이터 준비
    data_by_model = {model: [] for model in COLOR_MAP.keys()}
    
    for exp in EXPERIMENT_NUMBERS:
        psyche = psyche_scores.get(exp)
        expert = avg_expert_scores.get(exp)
        if psyche is not None and expert is not None:
            model = get_model_from_exp(exp[1])
            if model in data_by_model:
                data_by_model[model].append((psyche, expert))
    
    # Scatter plot
    all_x, all_y = [], []
    for model, points in data_by_model.items():
        if points:
            x, y = zip(*points)
            all_x.extend(x)
            all_y.extend(y)
            ax.scatter(x, y, 
                      c=COLOR_MAP[model],
                      marker=MARKER_MAP[model]["marker"],
                      s=MARKER_MAP[model]["size"],
                      label=LABEL_MAP[model],
                      alpha=0.7)
    
    # 회귀선
    if len(all_x) >= 2:
        z = np.polyfit(all_x, all_y, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(all_x), max(all_x), 100)
        ax.plot(x_line, p(x_line), '#3498db', linestyle='-', linewidth=2)
        
        # Correlation
        correlation, p_value = stats.pearsonr(all_x, all_y)
        p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
        ax.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
               transform=ax.transAxes, fontsize=32, family='Helvetica')
    
    # 스타일링
    ax.set_title('PSYCHE SCORE vs. Expert score', fontsize=36, pad=20, family='Helvetica')
    ax.set_xlabel('PSYCHE SCORE', fontsize=36, family='Helvetica')
    ax.set_ylabel('Expert score', fontsize=36, family='Helvetica')
    ax.tick_params(labelsize=32)
    ax.legend(loc='upper left', prop={'size': 22, 'weight': 'bold', 'family': 'Helvetica'})
    
    # 테두리
    for spine in ax.spines.values():
        spine.set_color('black')
        spine.set_linewidth(2)
    
    plt.tight_layout()
    return fig

def create_correlation_plot_by_validator(psyche_scores, expert_data):
    """Figure 1-2: Individual validator correlation plots."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()
    
    for idx, validator in enumerate(VALIDATORS):
        ax = axes[idx]
        
        # 데이터 수집
        validator_x, validator_y = [], []
        data_by_model = {model: [] for model in COLOR_MAP.keys()}
        
        for exp in EXPERIMENT_NUMBERS:
            psyche = psyche_scores.get(exp)
            expert = expert_data[validator].get(exp)
            if psyche is not None and expert is not None:
                validator_x.append(psyche)
                validator_y.append(expert)
                model = get_model_from_exp(exp[1])
                if model in data_by_model:
                    data_by_model[model].append((psyche, expert))
        
        # Scatter plot
        for model, points in data_by_model.items():
            if points:
                x, y = zip(*points)
                ax.scatter(x, y,
                          c=COLOR_MAP[model],
                          marker=MARKER_MAP[model]["marker"],
                          s=150,
                          alpha=0.7)
        
        # 회귀선 및 correlation
        if len(validator_x) >= 2:
            z = np.polyfit(validator_x, validator_y, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(validator_x), max(validator_x), 100)
            ax.plot(x_line, p(x_line), '#3498db', linestyle='-', linewidth=2)
            
            correlation, p_value = stats.pearsonr(validator_x, validator_y)
            p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
            ax.text(0.05, 0.95, f'r = {correlation:.3f}\n{p_text}\nn = {len(validator_x)}',
                   transform=ax.transAxes, fontsize=14, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                   family='Helvetica')
        
        # 스타일링
        ax.set_title(VALIDATOR_INITIALS[validator], fontsize=18, fontweight='bold', family='Helvetica')
        ax.set_xlabel('PSYCHE SCORE', fontsize=14, family='Helvetica')
        ax.set_ylabel('Expert score', fontsize=14, family='Helvetica')
        ax.tick_params(labelsize=12)
        ax.grid(True, alpha=0.3)
        
        for spine in ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(1)
    
    plt.tight_layout()
    return fig

def create_correlation_plot_by_disorder(psyche_scores, avg_expert_scores):
    """Figure 1-3: Disorder-specific correlation plots."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    for idx, (disorder_code, disorder_name) in enumerate([(6201, "MDD"), (6202, "BD"), (6206, "OCD")]):
        ax = axes[idx]
        
        # 해당 disorder 데이터만 필터링
        data_by_model = {model: [] for model in COLOR_MAP.keys()}
        all_x, all_y = [], []
        
        for exp in EXPERIMENT_NUMBERS:
            if exp[0] != disorder_code:
                continue
            psyche = psyche_scores.get(exp)
            expert = avg_expert_scores.get(exp)
            if psyche is not None and expert is not None:
                all_x.append(psyche)
                all_y.append(expert)
                model = get_model_from_exp(exp[1])
                if model in data_by_model:
                    data_by_model[model].append((psyche, expert))
        
        # Scatter plot
        for model, points in data_by_model.items():
            if points:
                x, y = zip(*points)
                ax.scatter(x, y,
                          c=COLOR_MAP[model],
                          marker=MARKER_MAP[model]["marker"],
                          s=200,
                          alpha=0.7)
        
        # 회귀선
        if len(all_x) >= 2:
            z = np.polyfit(all_x, all_y, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(all_x), max(all_x), 100)
            ax.plot(x_line, p(x_line), '#3498db', linestyle='-', linewidth=2)
            
            correlation, p_value = stats.pearsonr(all_x, all_y)
            p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
            ax.text(0.05, 0.95, f'r = {correlation:.4f}\n{p_text}',
                   transform=ax.transAxes, fontsize=14, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                   family='Helvetica')
        
        # 스타일링
        ax.set_title(DISORDER_NAMES[DISORDER_MAP[disorder_code]], fontsize=18, fontweight='bold', family='Helvetica')
        ax.set_xlabel('PSYCHE SCORE', fontsize=14, family='Helvetica')
        ax.set_ylabel('Expert score', fontsize=14, family='Helvetica')
        ax.tick_params(labelsize=12)
        ax.grid(True, alpha=0.3)
        
        for spine in ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(1)
    
    plt.tight_layout()
    return fig

# ================================
# Figure 2: Weight-Correlation Analysis
# ================================
def load_element_scores(root_data):
    """Load element-level scores for weight analysis."""
    element_scores = {}
    
    for client_num, exp_num in EXPERIMENT_NUMBERS:
        # Load PSYCHE evaluation data
        target_prefix = f"clients_{client_num}_psyche_"
        target_suffix = f"_{exp_num}"
        
        for key, data in (root_data or {}).items():
            if not key.startswith(target_prefix):
                continue
            if not key.endswith(target_suffix):
                continue
            
            record = data or {}
            if 'elements' in record:
                element_scores[(client_num, exp_num)] = record['elements']
                break
    
    return element_scores

def calculate_weighted_correlation_from_elements(element_scores_psyche, element_scores_expert, 
                                                  weight_impulsivity, weight_behavior, weight_subjective=1):
    """
    Element별 가중치를 변경하여 correlation 재계산
    
    Parameters:
    - weight_impulsivity: Impulsivity category weight (default: 5)
    - weight_behavior: Behavior category weight (default: 2)
    - weight_subjective: Subjective category weight (fixed: 1)
    """
    from evaluator import PSYCHE_RUBRIC
    
    # Category별 element 분류
    impulsivity_elements = [k for k, v in PSYCHE_RUBRIC.items() if v.get('type') == 'impulsivity']
    behavior_elements = [k for k, v in PSYCHE_RUBRIC.items() if v.get('type') == 'behavior']
    subjective_elements = [k for k, v in PSYCHE_RUBRIC.items() if v.get('type') in ['g-eval', 'binary'] and v.get('weight') == 1]
    
    weighted_psyche_scores = []
    weighted_expert_scores = []
    
    for exp in EXPERIMENT_NUMBERS:
        psyche_elements = element_scores_psyche.get(exp, {})
        expert_elements = element_scores_expert.get(exp, {})
        
        if not psyche_elements or not expert_elements:
            continue
        
        psyche_total = 0
        expert_total = 0
        
        # Calculate weighted scores
        for element, rubric_info in PSYCHE_RUBRIC.items():
            if element not in psyche_elements or element not in expert_elements:
                continue
            
            psyche_elem = psyche_elements[element]
            expert_elem = expert_elements[element]
            
            # Get scores (0-1 range)
            psyche_score = psyche_elem.get('score', 0) if isinstance(psyche_elem, dict) else 0
            expert_score = expert_elem.get('score', 0) if isinstance(expert_elem, dict) else 0
            
            # Apply weights
            if element in impulsivity_elements:
                weight = weight_impulsivity
            elif element in behavior_elements:
                weight = weight_behavior
            elif element in subjective_elements:
                weight = weight_subjective
            else:
                weight = rubric_info.get('weight', 1)
            
            psyche_total += psyche_score * weight
            expert_total += expert_score * weight
        
        weighted_psyche_scores.append(psyche_total)
        weighted_expert_scores.append(expert_total)
    
    # Calculate correlation
    if len(weighted_psyche_scores) >= 2:
        correlation, _ = stats.pearsonr(weighted_psyche_scores, weighted_expert_scores)
        return correlation
    return None

def create_weight_correlation_heatmaps(element_scores_psyche, element_scores_expert):
    """Figure 2: Weight-correlation analysis heatmaps."""
    weight_range = range(1, 11)  # 1-10
    
    # Heatmap 1: Equal weights (PSYCHE와 Expert 모두 가중치 변경)
    correlation_equal = np.zeros((10, 10))
    for i, w_imp in enumerate(weight_range):
        for j, w_beh in enumerate(weight_range):
            corr = calculate_weighted_correlation_from_elements(
                element_scores_psyche, element_scores_expert, w_imp, w_beh
            )
            correlation_equal[9-i, j] = corr if corr is not None else 0  # y축 반전 (top=10, bottom=1)
    
    # Heatmap 2: Fixed expert weights at (5, 2, 1)
    # Expert는 (5,2,1) 고정, PSYCHE만 가중치 변경
    correlation_fixed = np.zeros((10, 10))
    for i, w_imp in enumerate(weight_range):
        for j, w_beh in enumerate(weight_range):
            # Expert elements는 고정 가중치로 계산
            expert_scores_fixed = {}
            for exp in EXPERIMENT_NUMBERS:
                expert_elem = element_scores_expert.get(exp, {})
                if expert_elem:
                    # Calculate with fixed weights (5, 2, 1)
                    from evaluator import PSYCHE_RUBRIC
                    total = sum(
                        expert_elem.get(k, {}).get('score', 0) * (5 if PSYCHE_RUBRIC[k].get('type') == 'impulsivity' 
                                                                   else 2 if PSYCHE_RUBRIC[k].get('type') == 'behavior' 
                                                                   else 1)
                        for k in expert_elem.keys() if k in PSYCHE_RUBRIC
                    )
                    expert_scores_fixed[exp] = total
            
            # PSYCHE elements는 변경된 가중치로 계산
            psyche_scores_weighted = {}
            for exp in EXPERIMENT_NUMBERS:
                psyche_elem = element_scores_psyche.get(exp, {})
                if psyche_elem:
                    from evaluator import PSYCHE_RUBRIC
                    total = sum(
                        psyche_elem.get(k, {}).get('score', 0) * (w_imp if PSYCHE_RUBRIC[k].get('type') == 'impulsivity' 
                                                                   else w_beh if PSYCHE_RUBRIC[k].get('type') == 'behavior' 
                                                                   else 1)
                        for k in psyche_elem.keys() if k in PSYCHE_RUBRIC
                    )
                    psyche_scores_weighted[exp] = total
            
            # Correlation 계산
            x = [psyche_scores_weighted[exp] for exp in EXPERIMENT_NUMBERS if exp in psyche_scores_weighted and exp in expert_scores_fixed]
            y = [expert_scores_fixed[exp] for exp in EXPERIMENT_NUMBERS if exp in psyche_scores_weighted and exp in expert_scores_fixed]
            
            if len(x) >= 2:
                corr, _ = stats.pearsonr(x, y)
                correlation_fixed[9-i, j] = corr  # y축 반전
            else:
                correlation_fixed[9-i, j] = 0
    
    # Figure 생성
    fig, axes = plt.subplots(1, 2, figsize=(20, 8))
    
    # Heatmap 1
    ax1 = axes[0]
    im1 = ax1.imshow(correlation_equal, cmap='Greens', aspect='auto',
                     extent=[1, 10, 1, 10], origin='lower')
    cbar1 = plt.colorbar(im1, ax=ax1)
    cbar1.ax.set_ylabel('Correlation', fontsize=24, family='Helvetica')
    cbar1.ax.tick_params(labelsize=24)
    
    ax1.set_xlabel('$w_{Behavior}$', fontsize=32, family='Helvetica')
    ax1.set_ylabel('$w_{Impulsivity}$', fontsize=32, family='Helvetica')
    ax1.set_title('Equal weights', fontsize=32, family='Helvetica')
    ax1.set_xticks(range(1, 11))
    ax1.set_yticks(range(1, 11))
    ax1.tick_params(labelsize=22)
    ax1.grid(False)
    ax1.plot(2, 5, 'rs', markersize=10, label='(5, 2, 1)')
    
    for spine in ax1.spines.values():
        spine.set_color('black')
        spine.set_linewidth(1)
    
    # Heatmap 2
    ax2 = axes[1]
    im2 = ax2.imshow(correlation_fixed, cmap='Greens', aspect='auto',
                     extent=[1, 10, 1, 10], origin='lower')
    cbar2 = plt.colorbar(im2, ax=ax2)
    cbar2.ax.set_ylabel('Correlation', fontsize=24, family='Helvetica')
    cbar2.ax.tick_params(labelsize=24)
    
    ax2.set_xlabel('$w_{Behavior}$', fontsize=32, family='Helvetica')
    ax2.set_ylabel('$w_{Impulsivity}$', fontsize=32, family='Helvetica')
    ax2.set_title('Expert weights fixed at (5,2,1)', fontsize=32, family='Helvetica')
    ax2.set_xticks(range(1, 11))
    ax2.set_yticks(range(1, 11))
    ax2.tick_params(labelsize=22)
    ax2.grid(False)
    ax2.plot(2, 5, 'rs', markersize=10, label='(5, 2, 1)')
    
    for spine in ax2.spines.values():
        spine.set_color('black')
        spine.set_linewidth(1)
    
    plt.tight_layout()
    return fig

# ================================
# Figure 3: SP Validation Heatmap
# ================================
def load_sp_validation_data(root_data):
    """Load SP validation data for heatmap."""
    # SP validation 데이터 구조: sp_quantitative_{validator_name}_{client}_{page}
    # VALIDATION_ELEMENTS 24개
    
    SP_SEQUENCE = [
        (1, 6201), (2, 6202), (3, 6203), (4, 6204), (5, 6205), (6, 6206), (7, 6207),
        (8, 6203), (9, 6201), (10, 6204), (11, 6207), (12, 6202), (13, 6206), (14, 6205),
    ]
    
    VALIDATION_ELEMENTS = [
        "Chief complaint", "Symptom name", "Alleviating factor", "Exacerbating factor",
        "Triggering factor", "Stressor", "Diagnosis", "Substance use", "Current family structure",
        "Suicidal ideation", "Self mutilating behavior risk", "Homicide risk",
        "Suicidal plan", "Suicidal attempt", "Mood", "Verbal productivity", "Insight",
        "Affect", "Perception", "Thought process", "Thought content", "Spontaneity",
        "Social judgement", "Reliability"
    ]
    
    # Element별로 평가자들의 "Appropriate" 비율 계산
    element_conformity = {elem: [] for elem in VALIDATION_ELEMENTS}
    
    # 모든 validator 데이터 수집
    validators_found = set()
    for key in (root_data or {}).keys():
        if key.startswith("sp_quantitative_"):
            parts = key.split("_")
            if len(parts) >= 4:
                validators_found.add(parts[2])  # validator name
    
    # 각 SP case별로 데이터 수집
    for page, client in SP_SEQUENCE:
        for validator in validators_found:
            key = f"sp_quantitative_{validator}_{client}_{page}"
            data = (root_data or {}).get(key, {})
            
            if 'quantitative_responses' in data:
                responses = data['quantitative_responses']
                for elem in VALIDATION_ELEMENTS:
                    if elem in responses:
                        value = responses[elem]
                        # "적절함" = 1, "부적절함" = 0
                        if value == "적절함":
                            element_conformity[elem].append(1)
                        elif value == "부적절함":
                            element_conformity[elem].append(0)
    
    # 평균 계산 (%)
    conformity_percent = {}
    for elem, values in element_conformity.items():
        if values:
            conformity_percent[elem] = (sum(values) / len(values)) * 100
        else:
            conformity_percent[elem] = 0
    
    return conformity_percent

def create_sp_validation_heatmap(conformity_data):
    """Figure 3: Heatmap by elements (SP validation)."""
    if not conformity_data:
        return None
    
    # DataFrame 생성 (element별로 한 행)
    elements = list(conformity_data.keys())
    conformities = list(conformity_data.values())
    
    df = pd.DataFrame({
        'Element': elements,
        'Conformity': conformities
    })
    
    # Transpose for vertical display
    df_pivot = df.set_index('Element').T
    
    # Figure 생성
    fig, ax = plt.subplots(figsize=(16, 6))
    
    # Heatmap
    sns.heatmap(df_pivot, cmap='Blues', vmin=0, vmax=100, 
                linewidths=0.5, cbar=True, annot=True, fmt='.0f',
                annot_kws={"fontsize": 10, "family": "Helvetica"},
                ax=ax, cbar_kws={'label': 'Conformity (%)'})
    
    # 축 라벨 설정
    plt.xticks(rotation=90, ha='center', fontsize=12, family='Helvetica')
    plt.yticks(rotation=0, fontsize=14, family='Helvetica')
    
    plt.title('Conformity Heatmap by Elements', fontsize=24, pad=20, family='Helvetica')
    
    # 컬러바 폰트 설정
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=12)
    cbar.set_label('Conformity (%)', fontsize=14, family='Helvetica')
    
    plt.tight_layout()
    return fig

# ================================
# Download Helper
# ================================
def fig_to_bytes(fig, dpi=300):
    """Convert matplotlib figure to high-quality PNG bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
    buf.seek(0)
    return buf.getvalue()

# ================================
# Main Application
# ================================
def main():
    plt.close('all')
    
    st.title("📊 Publication Figure Generator")
    st.markdown("---")
    
    st.info("""
    **논문용 Figure 생성**
    - 모든 폰트: Helvetica
    - 고해상도 PNG (300 DPI)
    - Figure 1: PSYCHE-Expert Correlation (3가지 버전)
    - Figure 2: Weight-Correlation Analysis (2개 heatmap)
    - Figure 3: SP Validation Heatmap
    """)
    
    # Load data
    with st.spinner("데이터 로딩 중..."):
        firebase_ref = get_firebase_ref()
        root_snapshot = firebase_ref.get() or {}
        expert_data = load_expert_scores(root_snapshot)
        psyche_scores = load_psyche_scores(root_snapshot)
        avg_expert_scores = calculate_average_expert_scores(expert_data)
        
        # Element-level scores for weight analysis
        element_scores_psyche = load_element_scores(root_snapshot)
        # Element-level scores for expert (from validation data)
        element_scores_expert = {}
        for validator in VALIDATORS:
            sanitized_name = sanitize_firebase_key(validator)
            for client_num, exp_num in EXPERIMENT_NUMBERS:
                key = f"expert_{sanitized_name}_{client_num}_{exp_num}"
                data = (root_snapshot or {}).get(key, {}) or {}
                if 'elements' in data:
                    if (client_num, exp_num) not in element_scores_expert:
                        element_scores_expert[(client_num, exp_num)] = {}
                    # 첫 번째 validator 데이터 사용 (또는 평균 계산 가능)
                    if not element_scores_expert[(client_num, exp_num)]:
                        element_scores_expert[(client_num, exp_num)] = data['elements']
        
        # SP validation data
        sp_conformity_data = load_sp_validation_data(root_snapshot)
    
    st.success("✅ 데이터 로딩 완료")
    
    # ================================
    # Figure 1: PSYCHE-Expert Correlation
    # ================================
    st.markdown("## 📈 Figure 1: PSYCHE-Expert Correlation")
    
    tab1, tab2, tab3 = st.tabs(["Average Expert", "Individual Validators", "By Disorder"])
    
    with tab1:
        st.markdown("### Figure 1-1: Average Expert Score")
        fig1_1 = create_correlation_plot_average(psyche_scores, avg_expert_scores)
        st.pyplot(fig1_1)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download PNG (300 DPI)",
                data=fig_to_bytes(fig1_1),
                file_name="Fig1_1_PSYCHE_Expert_Correlation_Average.png",
                mime="image/png"
            )
        with col2:
            st.download_button(
                label="📥 Download PNG (600 DPI)",
                data=fig_to_bytes(fig1_1, dpi=600),
                file_name="Fig1_1_PSYCHE_Expert_Correlation_Average_600dpi.png",
                mime="image/png"
            )
        plt.close(fig1_1)
    
    with tab2:
        st.markdown("### Figure 1-2: Individual Validators")
        fig1_2 = create_correlation_plot_by_validator(psyche_scores, expert_data)
        st.pyplot(fig1_2)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download PNG (300 DPI)",
                data=fig_to_bytes(fig1_2),
                file_name="Fig1_2_PSYCHE_Expert_Correlation_Validators.png",
                mime="image/png"
            )
        with col2:
            st.download_button(
                label="📥 Download PNG (600 DPI)",
                data=fig_to_bytes(fig1_2, dpi=600),
                file_name="Fig1_2_PSYCHE_Expert_Correlation_Validators_600dpi.png",
                mime="image/png"
            )
        plt.close(fig1_2)
    
    with tab3:
        st.markdown("### Figure 1-3: By Disorder")
        fig1_3 = create_correlation_plot_by_disorder(psyche_scores, avg_expert_scores)
        st.pyplot(fig1_3)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download PNG (300 DPI)",
                data=fig_to_bytes(fig1_3),
                file_name="Fig1_3_PSYCHE_Expert_Correlation_Disorders.png",
                mime="image/png"
            )
        with col2:
            st.download_button(
                label="📥 Download PNG (600 DPI)",
                data=fig_to_bytes(fig1_3, dpi=600),
                file_name="Fig1_3_PSYCHE_Expert_Correlation_Disorders_600dpi.png",
                mime="image/png"
            )
        plt.close(fig1_3)
    
    st.markdown("---")
    
    # ================================
    # Figure 2: Weight-Correlation Analysis
    # ================================
    st.markdown("## 🔥 Figure 2: Weight-Correlation Analysis")
    st.caption("가중치 변화에 따른 correlation 변화 분석")
    
    if element_scores_psyche and element_scores_expert:
        fig2 = create_weight_correlation_heatmaps(element_scores_psyche, element_scores_expert)
        st.pyplot(fig2)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download PNG (300 DPI)",
                data=fig_to_bytes(fig2),
                file_name="Fig2_Weight_Correlation_Heatmaps.png",
                mime="image/png"
            )
        with col2:
            st.download_button(
                label="📥 Download PNG (600 DPI)",
                data=fig_to_bytes(fig2, dpi=600),
                file_name="Fig2_Weight_Correlation_Heatmaps_600dpi.png",
                mime="image/png"
            )
        plt.close(fig2)
    else:
        st.warning("Element-level scores not available. Cannot generate weight correlation heatmaps.")
    
    st.markdown("---")
    
    # ================================
    # Figure 3: SP Validation Heatmap
    # ================================
    st.markdown("## 🔵 Figure 3: SP Validation Heatmap")
    st.caption("Element별 Conformity 평균")
    
    if sp_conformity_data:
        fig3 = create_sp_validation_heatmap(sp_conformity_data)
        if fig3:
            st.pyplot(fig3)
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📥 Download PNG (300 DPI)",
                    data=fig_to_bytes(fig3),
                    file_name="Fig3_SP_Validation_Heatmap.png",
                    mime="image/png"
                )
            with col2:
                st.download_button(
                    label="📥 Download PNG (600 DPI)",
                    data=fig_to_bytes(fig3, dpi=600),
                    file_name="Fig3_SP_Validation_Heatmap_600dpi.png",
                    mime="image/png"
                )
            plt.close(fig3)
        else:
            st.warning("Failed to create SP validation heatmap.")
    else:
        st.info("SP validation 데이터가 없습니다. 02_가상환자에_대한_전문가_검증.py에서 검증을 완료해주세요.")

if __name__ == "__main__":
    main()
