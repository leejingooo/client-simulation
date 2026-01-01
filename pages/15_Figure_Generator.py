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
    "gptsmaller": "GPT-Small",
    "gptlarge": "GPT-Large",
    "claudesmaller": "Claude-Small",
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
               transform=ax.transAxes, fontsize=22, family='Helvetica')
    
    # 스타일링
    ax.set_title('PSYCHE SCORE vs. Expert score', fontsize=36, pad=20, family='Helvetica')
    ax.set_xlabel('PSYCHE SCORE', fontsize=36, family='Helvetica')
    ax.set_ylabel('Expert score', fontsize=36, family='Helvetica')
    ax.set_yticks([5, 35, 65])
    ax.set_xticks([5, 30, 55])
    ax.tick_params(labelsize=32)
    ax.legend(loc='upper left', prop={'size': 18, 'weight': 'bold', 'family': 'Helvetica'})
    
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
                          s=MARKER_MAP[model]["size"],
                          alpha=0.7)
        
        # 회귀선 및 correlation
        if len(validator_x) >= 2:
            z = np.polyfit(validator_x, validator_y, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(validator_x), max(validator_x), 100)
            ax.plot(x_line, p(x_line), '#3498db', linestyle='-', linewidth=2)
            
            correlation, p_value = stats.pearsonr(validator_x, validator_y)
            p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
            ax.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
                   transform=ax.transAxes, fontsize=18, family='Helvetica')
        
        # 스타일링
        ax.set_title(VALIDATOR_INITIALS[validator], fontsize=24, fontweight='bold', family='Helvetica')
        ax.set_xlabel('PSYCHE SCORE', fontsize=22, family='Helvetica')
        ax.set_ylabel('Expert score', fontsize=22, family='Helvetica')
        ax.set_yticks([5, 35, 65])
        ax.set_xticks([5, 30, 55])
        ax.tick_params(labelsize=20)
        ax.grid(False)
        
        for spine in ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(2)
    
    plt.tight_layout()
    return fig

def create_correlation_plot_by_disorder(psyche_scores, avg_expert_scores):
    """Figure 1-3: Disorder-specific correlation plots."""
    fig, axes = plt.subplots(1, 3, figsize=(24, 8))
    
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
                          s=MARKER_MAP[model]["size"],
                          alpha=0.7)
        
        # 회귀선
        if len(all_x) >= 2:
            z = np.polyfit(all_x, all_y, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(all_x), max(all_x), 100)
            ax.plot(x_line, p(x_line), '#3498db', linestyle='-', linewidth=2)
            
            correlation, p_value = stats.pearsonr(all_x, all_y)
            p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
            ax.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
                   transform=ax.transAxes, fontsize=32, family='Helvetica')
        
        # 스타일링 (1-1과 동일)
        ax.set_title(DISORDER_NAMES[DISORDER_MAP[disorder_code]], fontsize=36, fontweight='bold', family='Helvetica', pad=20)
        ax.set_xlabel('PSYCHE SCORE', fontsize=36, family='Helvetica')
        ax.set_ylabel('Expert score', fontsize=36, family='Helvetica')
        ax.set_yticks([5, 35, 65])
        ax.set_xticks([5, 30, 55])
        ax.tick_params(labelsize=32)
        ax.grid(False)
        
        for spine in ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(2)
    
    plt.tight_layout()
    return fig

# ================================
# Figure 2: Weight-Correlation Analysis
# ================================
def load_element_scores(root_data):
    """Load element-level scores for weight analysis.
    
    Returns:
    - psyche_element_scores: {(client_num, exp_num): {element_name: {score: float}}}
    - expert_element_scores: {validator_name: {(client_num, exp_num): {element_name: {score: float}}}}
    """
    from evaluator import PSYCHE_RUBRIC
    
    psyche_element_scores = {}
    expert_element_scores = {validator: {} for validator in VALIDATORS}
    
    # Get valid element names from PSYCHE_RUBRIC
    valid_elements = set(PSYCHE_RUBRIC.keys())
    
    # Debug: collect all matching keys
    psyche_keys_found = []
    
    # Load PSYCHE element scores
    for client_num, exp_num in EXPERIMENT_NUMBERS:
        target_prefix = f"clients_{client_num}_psyche_"
        target_suffix = f"_{exp_num}"
        
        for key, data in (root_data or {}).items():
            if not key.startswith(target_prefix):
                continue
            if not key.endswith(target_suffix):
                continue
            
            psyche_keys_found.append(key)
            record = data or {}
            
            # Extract element scores directly from record (no 'elements' layer)
            # Filter out metadata fields like 'psyche_score', 'timestamp', etc.
            element_data = {}
            for field_name, field_value in record.items():
                if field_name in valid_elements and isinstance(field_value, dict):
                    element_data[field_name] = field_value
            
            if element_data:
                psyche_element_scores[(client_num, exp_num)] = element_data
            break
    
    # Store found keys for debugging
    psyche_element_scores['_debug_keys'] = psyche_keys_found
    
    # Load Expert element scores (still uses 'elements' layer)
    for validator in VALIDATORS:
        sanitized_name = sanitize_firebase_key(validator)
        for client_num, exp_num in EXPERIMENT_NUMBERS:
            key = f"expert_{sanitized_name}_{client_num}_{exp_num}"
            data = (root_data or {}).get(key, {}) or {}
            if 'elements' in data:
                expert_element_scores[validator][(client_num, exp_num)] = data['elements']
    
    return psyche_element_scores, expert_element_scores

def calculate_weighted_correlation_from_elements(element_scores_psyche, element_scores_expert_dict, 
                                                  weight_impulsivity, weight_behavior, weight_subjective=1,
                                                  expert_fixed_weights=None):
    """
    Element별 가중치를 변경하여 correlation 재계산
    
    Parameters:
    - element_scores_psyche: {(client_num, exp_num): {element_name: {score: float}}}
    - element_scores_expert_dict: {validator_name: {(client_num, exp_num): {element_name: {score: float}}}}
    - weight_impulsivity: Impulsivity category weight (default: 5)
    - weight_behavior: Behavior category weight (default: 2)
    - weight_subjective: Subjective category weight (fixed: 1)
    - expert_fixed_weights: (imp, beh, subj) tuple for fixed expert weights, or None for variable
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
        if not psyche_elements:
            continue
        
        # Average expert scores across validators
        expert_elements_list = []
        for validator in VALIDATORS:
            expert_exp_data = element_scores_expert_dict.get(validator, {}).get(exp, {})
            if expert_exp_data:
                expert_elements_list.append(expert_exp_data)
        
        if not expert_elements_list:
            continue
        
        psyche_total = 0
        expert_total = 0
        
        # Calculate weighted scores
        for element, rubric_info in PSYCHE_RUBRIC.items():
            if element not in psyche_elements:
                continue
            
            # Check if all experts have this element
            expert_scores_for_element = []
            for expert_elem_dict in expert_elements_list:
                if element in expert_elem_dict:
                    elem_data = expert_elem_dict[element]
                    score = elem_data.get('score', 0) if isinstance(elem_data, dict) else 0
                    expert_scores_for_element.append(score)
            
            if not expert_scores_for_element:
                continue
            
            # Average expert score for this element
            avg_expert_score = np.mean(expert_scores_for_element)
            
            # Get PSYCHE score
            psyche_elem = psyche_elements[element]
            psyche_score = psyche_elem.get('score', 0) if isinstance(psyche_elem, dict) else 0
            
            # Apply weights for PSYCHE
            if element in impulsivity_elements:
                psyche_weight = weight_impulsivity
            elif element in behavior_elements:
                psyche_weight = weight_behavior
            elif element in subjective_elements:
                psyche_weight = weight_subjective
            else:
                psyche_weight = rubric_info.get('weight', 1)
            
            # Apply weights for Expert (fixed or variable)
            if expert_fixed_weights:
                if element in impulsivity_elements:
                    expert_weight = expert_fixed_weights[0]
                elif element in behavior_elements:
                    expert_weight = expert_fixed_weights[1]
                elif element in subjective_elements:
                    expert_weight = expert_fixed_weights[2]
                else:
                    expert_weight = rubric_info.get('weight', 1)
            else:
                # Use same variable weights as PSYCHE
                expert_weight = psyche_weight
            
            psyche_total += psyche_score * psyche_weight
            expert_total += avg_expert_score * expert_weight
        
        weighted_psyche_scores.append(psyche_total)
        weighted_expert_scores.append(expert_total)
    
    # Calculate correlation
    if len(weighted_psyche_scores) >= 2:
        correlation, _ = stats.pearsonr(weighted_psyche_scores, weighted_expert_scores)
        return correlation
    return None

def create_weight_correlation_heatmaps(element_scores_psyche, element_scores_expert_dict):
    """Figure 2: Weight-correlation analysis heatmaps."""
    # 0.1 간격으로 1부터 10까지 (총 91개 포인트)
    weight_range = np.arange(1, 10.1, 0.1)
    n_weights = len(weight_range)
    
    # Heatmap 1: Equal weights (PSYCHE와 Expert 모두 가중치 변경)
    correlation_equal = np.zeros((n_weights, n_weights))
    for i, w_imp in enumerate(weight_range):
        for j, w_beh in enumerate(weight_range):
            corr = calculate_weighted_correlation_from_elements(
                element_scores_psyche, element_scores_expert_dict, w_imp, w_beh
            )
            correlation_equal[n_weights-1-i, j] = corr if corr is not None else 0  # y축 반전
    
    # Heatmap 2: Fixed expert weights at (5, 2, 1)
    # Expert는 (5,2,1) 고정, PSYCHE만 가중치 변경
    correlation_fixed = np.zeros((n_weights, n_weights))
    for i, w_imp in enumerate(weight_range):
        for j, w_beh in enumerate(weight_range):
            corr = calculate_weighted_correlation_from_elements(
                element_scores_psyche, element_scores_expert_dict, w_imp, w_beh,
                expert_fixed_weights=(5, 2, 1)  # Fixed expert weights
            )
            correlation_fixed[n_weights-1-i, j] = corr if corr is not None else 0
    
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
    """Load SP validation data for heatmap.
    
    Returns:
    - dict: {case_name: {element: conformity_percent}}
    """
    # SP validation 데이터 구조: sp_validation_{validator_name}_{client}_{page}
    # VALIDATION_ELEMENTS 24개
    
    SP_SEQUENCE = [
        (1, 6201), (2, 6202), (3, 6203), (4, 6204), (5, 6205), (6, 6206), (7, 6207),
        (8, 6203), (9, 6201), (10, 6204), (11, 6207), (12, 6202), (13, 6206), (14, 6205),
    ]
    
    CLIENT_TO_CASE = {
        6201: 'MDD',
        6202: 'BD',
        6203: 'PD',
        6204: 'GAD',
        6205: 'SAD',
        6206: 'OCD',
        6207: 'PTSD'
    }
    
    VALIDATION_ELEMENTS = [
        "Chief complaint", "Symptom name", "Alleviating factor", "Exacerbating factor",
        "Triggering factor", "Stressor", "Diagnosis", "Substance use", "Current family structure",
        "Suicidal ideation", "Self mutilating behavior risk", "Homicide risk",
        "Suicidal plan", "Suicidal attempt", "Mood", "Verbal productivity", "Insight",
        "Affect", "Perception", "Thought process", "Thought content", "Spontaneity",
        "Social judgement", "Reliability"
    ]
    
    # Case별, Element별로 데이터 수집
    case_element_data = {case: {elem: [] for elem in VALIDATION_ELEMENTS} for case in CLIENT_TO_CASE.values()}
    
    # 모든 sp_validation_ 키 수집
    for key in (root_data or {}).keys():
        if not key.startswith("sp_validation_"):
            continue
        
        data = (root_data or {}).get(key, {})
        if not data:
            continue
        
        # Get client number to determine case
        client_num = data.get('client_number')
        if client_num not in CLIENT_TO_CASE:
            continue
        
        case_name = CLIENT_TO_CASE[client_num]
        
        # Get elements data
        elements_block = data.get('elements', {})
        if not elements_block:
            continue
        
        # Process each element
        for element in VALIDATION_ELEMENTS:
            if element in elements_block:
                elem_data = elements_block[element]
                if elem_data:
                    choice = elem_data.get('expert_choice', '')
                    # "적절함" = 1, "적절하지 않음" = 0
                    if choice == "적절함":
                        case_element_data[case_name][element].append(1)
                    elif choice == "적절하지 않음":
                        case_element_data[case_name][element].append(0)
    
    # Case별로 평균 계산 (%)
    conformity_by_case = {}
    for case, element_dict in case_element_data.items():
        conformity_by_case[case] = {}
        for elem, values in element_dict.items():
            if values:
                conformity_by_case[case][elem] = (sum(values) / len(values)) * 100
            else:
                conformity_by_case[case][elem] = 0
    
    return conformity_by_case

def create_sp_validation_heatmap(conformity_by_case):
    """Figure 3: SP Validation conformity heatmap (Case × Element).
    
    Args:
        conformity_by_case: {case_name: {element: conformity_percent}}
    """
    if not conformity_by_case:
        return None
    
    # Case 7개 순서
    cases = ['MDD', 'BD', 'PD', 'GAD', 'SAD', 'OCD', 'PTSD']
    
    # DataFrame 생성 - 각 case가 row, 각 element가 column
    # Get all elements from first case
    first_case = list(conformity_by_case.values())[0]
    elements = list(first_case.keys())
    
    # Build dataframe: index=elements, columns=cases
    df_data = {}
    for case in cases:
        if case in conformity_by_case:
            df_data[case] = [conformity_by_case[case].get(elem, 0) for elem in elements]
        else:
            df_data[case] = [0] * len(elements)
    
    df = pd.DataFrame(df_data, index=elements)
    
    # Figure 생성 (example code 스타일)
    fig, ax = plt.subplots(figsize=(16, 11))
    
    # Heatmap - Element가 x축 (column), Case가 y축 (row)
    sns.heatmap(df.T, annot=True, fmt='.0f', cmap='Blues', 
                vmin=0, vmax=100, ax=ax, square=True,
                linewidths=0.5, cbar=False,
                annot_kws={'fontsize': 10, 'family': 'Helvetica'})
    
    # y축 라벨 위치 조정 (오른쪽으로)
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position('right')
    
    # 축 라벨 스타일링 (example code 스타일)
    plt.xticks(rotation=90, ha='center', fontsize=16)
    plt.yticks(rotation=0, fontsize=16)
    
    plt.title('Conformity Heatmap by Elements', fontsize=24, pad=20, family='Helvetica')
    
    # 가로 컬러바 추가 (하단)
    # [left, bottom, width, height]
    cbar_ax = fig.add_axes([0.7, 0.08, 0.4, 0.02])
    cbar = plt.colorbar(ax.collections[0], cax=cbar_ax, orientation="horizontal")
    
    # 컬러바 스타일 조정
    cbar.ax.tick_params(labelsize=16)
    cbar.outline.set_visible(False)  # 테두리 제거
    cbar.set_label('Conformity (%)', fontsize=16, family='Helvetica')
    
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
        element_scores_psyche, element_scores_expert = load_element_scores(root_snapshot)
        
        # SP validation data
        sp_conformity_data = load_sp_validation_data(root_snapshot)
    
    st.success("✅ 데이터 로딩 완료")
    
    # Debug info
    with st.expander("🔍 데이터 로딩 상태 확인"):
        st.write(f"PSYCHE scores: {len(psyche_scores)} experiments")
        st.write(f"Expert data: {len(expert_data)} validators")
        
        # Check for debug keys
        psyche_elem_count = len([k for k in element_scores_psyche.keys() if k != '_debug_keys'])
        st.write(f"Element-level PSYCHE scores: {psyche_elem_count} experiments")
        if '_debug_keys' in element_scores_psyche:
            st.write(f"PSYCHE keys found: {element_scores_psyche['_debug_keys'][:5]}")
        
        st.write(f"Element-level Expert scores: {len(element_scores_expert)} validators")
        if element_scores_expert:
            for validator, data in element_scores_expert.items():
                st.write(f"  - {validator}: {len(data)} experiments")
        
        st.write(f"SP conformity data: {len(sp_conformity_data)} cases")
        if sp_conformity_data:
            for case, elem_dict in sp_conformity_data.items():
                st.write(f"  - {case}: {len(elem_dict)} elements")
        
        # Show sample data
        if psyche_elem_count > 0:
            sample_keys = [k for k in element_scores_psyche.keys() if k != '_debug_keys'][:3]
            st.write("Sample PSYCHE element data:", sample_keys)
        if element_scores_expert:
            sample_validator = list(element_scores_expert.keys())[0]
            st.write(f"Sample Expert element data ({sample_validator}):", list(element_scores_expert[sample_validator].keys())[:3])
        if sp_conformity_data:
            first_case = list(sp_conformity_data.keys())[0]
            st.write(f"Sample SP conformity ({first_case}):", list(sp_conformity_data[first_case].items())[:3])
    
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
        # Check if there's actual data (exclude _debug_keys)
        psyche_count = len([k for k in element_scores_psyche.keys() if k != '_debug_keys'])
        expert_count = sum(len(v) for v in element_scores_expert.values())
        
        st.info(f"PSYCHE element data: {psyche_count} experiments, Expert element data: {expert_count} total entries")
        
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
