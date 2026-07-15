"""
논문용 Figure 생성 페이지 (Lite Version)
Publication-quality figures for PSYCHE framework paper

경량 버전: Combined Figure만 생성 (Weight Correlation과 SP Validation 제외)
모든 폰트는 Helvetica로 통일
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
    page_title="Publication Figures (Lite)",
    page_icon="📊",
    layout="wide"
)

# Helvetica 폰트 설정
rcParams['font.family'] = 'Helvetica'
rcParams['axes.unicode_minus'] = False

# 벡터 출력(PDF/SVG)에서 텍스트를 실제 text로 유지 (Keynote/Illustrator/LaTeX 편집 가능)
rcParams['pdf.fonttype'] = 42
rcParams['ps.fonttype'] = 42
rcParams['svg.fonttype'] = 'none'

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
    "이강토": "Validator A",
    "김태환": "Validator B",
    "김광현": "Validator C",
    "김주오": "Validator D",
    "허율": "Validator E",
    "장재용": "Validator F"
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

def load_element_scores(root_data):
    """Load element-level scores for category analysis.
    
    Returns:
    - psyche_element_scores: {(client_num, exp_num): {element_name: {score: float}}}
    - expert_element_scores: {validator_name: {(client_num, exp_num): {element_name: {score: float}}}}
    """
    from evaluator import PSYCHE_RUBRIC
    
    psyche_element_scores = {}
    expert_element_scores = {validator: {} for validator in VALIDATORS}
    
    # Get valid element names from PSYCHE_RUBRIC
    valid_elements = set(PSYCHE_RUBRIC.keys())
    
    # Debug info
    psyche_keys_found = []
    psyche_data_structure_sample = None
    
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
            
            # Save sample structure for debugging
            if psyche_data_structure_sample is None:
                psyche_data_structure_sample = {
                    'key': key,
                    'top_level_keys': list(record.keys())[:10],
                    'has_elements': 'elements' in record
                }
            
            # Try 'elements' layer first (standard structure)
            element_data = {}
            if 'elements' in record and isinstance(record['elements'], dict):
                for field_name, field_value in record['elements'].items():
                    if field_name in valid_elements:
                        element_data[field_name] = field_value
            else:
                # Fallback: extract element scores directly from record
                for field_name, field_value in record.items():
                    if field_name in valid_elements and isinstance(field_value, dict):
                        element_data[field_name] = field_value
            
            if element_data:
                psyche_element_scores[(client_num, exp_num)] = element_data
            break
    
    # Store debug info
    psyche_element_scores['_debug_keys'] = psyche_keys_found
    psyche_element_scores['_debug_structure'] = psyche_data_structure_sample
    
    # Load Expert element scores
    for validator in VALIDATORS:
        sanitized_name = sanitize_firebase_key(validator)
        for client_num, exp_num in EXPERIMENT_NUMBERS:
            key = f"expert_{sanitized_name}_{client_num}_{exp_num}"
            data = (root_data or {}).get(key, {}) or {}
            elements = data.get('elements', {})
            if elements:
                valid_elem_data = {k: v for k, v in elements.items() if k in valid_elements}
                if valid_elem_data:
                    expert_element_scores[validator][(client_num, exp_num)] = valid_elem_data
    
    return psyche_element_scores, expert_element_scores

def calculate_category_scores(element_scores_psyche, element_scores_expert_dict):
    """Calculate category-level scores (Subjective, Impulsivity, Behavior) for correlation analysis.
    
    Returns:
    - psyche_category_scores: {(client_num, exp_num): {'Subjective': float, 'Impulsivity': float, 'Behavior': float}}
    - expert_category_scores: {validator: {(client_num, exp_num): {'Subjective': float, 'Impulsivity': float, 'Behavior': float}}}
    """
    from evaluator import PSYCHE_RUBRIC
    
    # Category별 element 분류
    impulsivity_elements = [k for k, v in PSYCHE_RUBRIC.items() if v.get('type') == 'impulsivity']
    behavior_elements = [k for k, v in PSYCHE_RUBRIC.items() if v.get('type') == 'behavior']
    subjective_elements = [k for k, v in PSYCHE_RUBRIC.items() if v.get('type') in ['g-eval', 'binary'] and v.get('weight') == 1]
    
    # Weights
    weight_subjective = 1
    weight_impulsivity = 5
    weight_behavior = 2
    
    # PSYCHE category scores
    psyche_category_scores = {}
    for exp in EXPERIMENT_NUMBERS:
        if exp not in element_scores_psyche:
            continue
        
        elements = element_scores_psyche[exp]
        
        # Subjective
        subj_scores = []
        for elem in subjective_elements:
            if elem in elements:
                score = elements[elem].get('score', 0) if isinstance(elements[elem], dict) else 0
                subj_scores.append(score)
        subj_total = sum(subj_scores) * weight_subjective if subj_scores else 0
        
        # Impulsivity
        imp_scores = []
        for elem in impulsivity_elements:
            if elem in elements:
                score = elements[elem].get('score', 0) if isinstance(elements[elem], dict) else 0
                imp_scores.append(score)
        imp_total = sum(imp_scores) * weight_impulsivity if imp_scores else 0
        
        # Behavior
        beh_scores = []
        for elem in behavior_elements:
            if elem in elements:
                score = elements[elem].get('score', 0) if isinstance(elements[elem], dict) else 0
                beh_scores.append(score)
        beh_total = sum(beh_scores) * weight_behavior if beh_scores else 0
        
        psyche_category_scores[exp] = {
            'Subjective': subj_total,
            'Impulsivity': imp_total,
            'Behavior': beh_total
        }
    
    # Expert category scores
    expert_category_scores = {validator: {} for validator in VALIDATORS}
    
    for validator in VALIDATORS:
        validator_elements = element_scores_expert_dict.get(validator, {})
        
        for exp in EXPERIMENT_NUMBERS:
            if exp not in validator_elements:
                continue
            
            elements = validator_elements[exp]
            
            # Subjective
            subj_scores = []
            for elem in subjective_elements:
                if elem in elements:
                    score = elements[elem].get('score', 0) if isinstance(elements[elem], dict) else 0
                    subj_scores.append(score)
            subj_total = sum(subj_scores) * weight_subjective if subj_scores else 0
            
            # Impulsivity
            imp_scores = []
            for elem in impulsivity_elements:
                if elem in elements:
                    score = elements[elem].get('score', 0) if isinstance(elements[elem], dict) else 0
                    imp_scores.append(score)
            imp_total = sum(imp_scores) * weight_impulsivity if imp_scores else 0
            
            # Behavior
            beh_scores = []
            for elem in behavior_elements:
                if elem in elements:
                    score = elements[elem].get('score', 0) if isinstance(elements[elem], dict) else 0
                    beh_scores.append(score)
            beh_total = sum(beh_scores) * weight_behavior if beh_scores else 0
            
            expert_category_scores[validator][exp] = {
                'Subjective': subj_total,
                'Impulsivity': imp_total,
                'Behavior': beh_total
            }
    
    return psyche_category_scores, expert_category_scores

# ================================
# Combined Correlation Figure
# ================================
def create_combined_correlation_figure(psyche_scores, avg_expert_scores, expert_data, psyche_category_scores, expert_category_scores):
    """Combined Figure: Validator-specific, Disease-specific, and Category-specific correlation plots.
    
    Layout:
    - Rows 0-1: Validator-specific (2x3 grid) - (a)
    - Row 2: Disease-specific (1x3 grid) - (b)
    - Row 3: Category-specific (1x3 grid) - (c)
    """
    fig = plt.figure(figsize=(24, 32))
    
    # GridSpec with spacing between sections
    gs = fig.add_gridspec(4, 3, hspace=0.35, wspace=0.3,
                          height_ratios=[1, 1, 1.2, 1.2])
    
    # ========================================
    # (a) Validator-specific: Rows 0-1 (2x3)
    # ========================================
    for idx, validator in enumerate(VALIDATORS):
        row = idx // 3
        col = idx % 3
        ax = fig.add_subplot(gs[row, col])
        
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
        
        # 회귀선 및 95% CI
        if len(validator_x) >= 2:
            validator_x_arr = np.array(validator_x)
            validator_y_arr = np.array(validator_y)
            
            z = np.polyfit(validator_x_arr, validator_y_arr, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(validator_x_arr), max(validator_x_arr), 100)
            y_line = p(x_line)
            
            n = len(validator_x_arr)
            y_pred = p(validator_x_arr)
            residuals = validator_y_arr - y_pred
            std_err = np.sqrt(np.sum(residuals**2) / (n - 2))
            
            x_mean = np.mean(validator_x_arr)
            sxx = np.sum((validator_x_arr - x_mean)**2)
            se_line = std_err * np.sqrt(1/n + (x_line - x_mean)**2 / sxx)
            
            from scipy.stats import t as t_dist
            t_val = t_dist.ppf(0.975, n - 2)
            ci = t_val * se_line
            
            ax.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.15, color='#3498db')
            ax.plot(x_line, y_line, '#3498db', linestyle='-', linewidth=2)
            
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
    
    # (a) 마커 추가 - 왼쪽 상단
    fig.text(0.02, 0.95, '(a)', fontsize=32, fontweight='bold', family='Helvetica')
    
    # ========================================
    # (b) Disease-specific: Row 2 (1x3)
    # ========================================
    for idx, (disorder_code, disorder_name) in enumerate([(6201, "MDD"), (6202, "BD"), (6206, "OCD")]):
        ax = fig.add_subplot(gs[2, idx])
        
        # 데이터 필터링
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
        
        # 회귀선 및 95% CI
        if len(all_x) >= 2:
            all_x_arr = np.array(all_x)
            all_y_arr = np.array(all_y)
            
            z = np.polyfit(all_x_arr, all_y_arr, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(all_x_arr), max(all_x_arr), 100)
            y_line = p(x_line)
            
            n = len(all_x_arr)
            y_pred = p(all_x_arr)
            residuals = all_y_arr - y_pred
            std_err = np.sqrt(np.sum(residuals**2) / (n - 2))
            
            x_mean = np.mean(all_x_arr)
            sxx = np.sum((all_x_arr - x_mean)**2)
            se_line = std_err * np.sqrt(1/n + (x_line - x_mean)**2 / sxx)
            
            from scipy.stats import t as t_dist
            t_val = t_dist.ppf(0.975, n - 2)
            ci = t_val * se_line
            
            ax.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.15, color='#3498db')
            ax.plot(x_line, y_line, '#3498db', linestyle='-', linewidth=2)
            
            correlation, p_value = stats.pearsonr(all_x, all_y)
            p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
            ax.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
                   transform=ax.transAxes, fontsize=24, family='Helvetica')
        
        # 스타일링
        ax.set_title(DISORDER_NAMES[DISORDER_MAP[disorder_code]], fontsize=30, fontweight='bold', family='Helvetica', pad=20)
        ax.set_xlabel('PSYCHE SCORE', fontsize=28, family='Helvetica')
        ax.set_ylabel('Expert score', fontsize=28, family='Helvetica')
        ax.set_yticks([5, 35, 65])
        ax.set_xticks([5, 30, 55])
        ax.tick_params(labelsize=26)
        ax.grid(False)
        
        for spine in ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(2)
    
    # (b) 마커 추가
    fig.text(0.02, 0.48, '(b)', fontsize=32, fontweight='bold', family='Helvetica')
    
    # ========================================
    # (c) Category-specific: Row 3 (1x3)
    # ========================================
    categories = ['Subjective', 'Impulsivity', 'Behavior']
    category_labels = {
        'Subjective': 'Subjective Information',
        'Impulsivity': 'Impulsivity',
        'Behavior': 'MFC-Behavior'
    }
    
    for idx, category in enumerate(categories):
        ax = fig.add_subplot(gs[3, idx])
        
        # 데이터 수집
        data_by_model = {model: [] for model in COLOR_MAP.keys()}
        all_x, all_y = [], []
        
        for exp in EXPERIMENT_NUMBERS:
            if exp not in psyche_category_scores:
                continue
            
            psyche_score = psyche_category_scores[exp][category]
            
            # Expert score - average across validators
            expert_scores = []
            for validator in VALIDATORS:
                if exp in expert_category_scores[validator]:
                    expert_scores.append(expert_category_scores[validator][exp][category])
            
            if not expert_scores:
                continue
            
            expert_score = np.mean(expert_scores)
            model = get_model_from_exp(exp[1])
            
            data_by_model[model].append((psyche_score, expert_score))
            all_x.append(psyche_score)
            all_y.append(expert_score)
        
        # Scatter plot
        for model, points in data_by_model.items():
            if points:
                x_vals = [p[0] for p in points]
                y_vals = [p[1] for p in points]
                ax.scatter(x_vals, y_vals, 
                          color=COLOR_MAP[model],
                          label=LABEL_MAP[model],
                          s=MARKER_MAP[model]['size'],
                          marker=MARKER_MAP[model]['marker'],
                          alpha=0.7,
                          edgecolors='black',
                          linewidths=1.5)
        
        # 회귀선 및 95% CI
        if len(all_x) >= 2:
            all_x_arr = np.array(all_x)
            all_y_arr = np.array(all_y)
            
            z = np.polyfit(all_x_arr, all_y_arr, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(all_x_arr), max(all_x_arr), 100)
            y_line = p(x_line)
            
            n = len(all_x_arr)
            y_pred = p(all_x_arr)
            residuals = all_y_arr - y_pred
            std_err = np.sqrt(np.sum(residuals**2) / (n - 2))
            
            x_mean = np.mean(all_x_arr)
            sxx = np.sum((all_x_arr - x_mean)**2)
            se_line = std_err * np.sqrt(1/n + (x_line - x_mean)**2 / sxx)
            
            from scipy.stats import t as t_dist
            t_val = t_dist.ppf(0.975, n - 2)
            ci = t_val * se_line
            
            ax.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.15, color='#3498db')
            ax.plot(x_line, y_line, '#3498db', linestyle='-', linewidth=2)
            
            correlation, p_value = stats.pearsonr(all_x, all_y)
            p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
            ax.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
                   transform=ax.transAxes, fontsize=24, family='Helvetica')
        
        # 스타일링
        ax.set_title(category_labels[category], fontsize=30, fontweight='bold', family='Helvetica', pad=20)
        ax.set_xlabel('PSYCHE SCORE', fontsize=28, family='Helvetica')
        ax.set_ylabel('Expert score', fontsize=28, family='Helvetica')
        ax.tick_params(labelsize=26)
        ax.grid(False)
        
        for spine in ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(2)
    
    # (c) 마커 추가
    fig.text(0.02, 0.23, '(c)', fontsize=32, fontweight='bold', family='Helvetica')
    
    return fig

def create_combined_correlation_figure_v2(psyche_scores, avg_expert_scores, expert_data, psyche_category_scores, expert_category_scores):
    """Combined Figure Version 2: Validator-specific, Disease-specific, and Category-specific correlation plots.
    
    V2: 왼쪽 가장자리와 아래쪽 가장자리에만 xlabel, ylabel 표시
    
    Layout:
    - Rows 0-1: Validator-specific (2x3 grid) - (a)
    - Row 2: Disease-specific (1x3 grid) - (b)
    - Row 3: Category-specific (1x3 grid) - (c)
    """
    fig = plt.figure(figsize=(24, 32))
    
    # GridSpec with spacing between sections
    gs = fig.add_gridspec(4, 3, hspace=0.35, wspace=0.3,
                          height_ratios=[1, 1, 1, 1])
    
    # ========================================
    # (a) Validator-specific: Rows 0-1 (2x3)
    # ========================================
    for idx, validator in enumerate(VALIDATORS):
        row = idx // 3
        col = idx % 3
        ax = fig.add_subplot(gs[row, col])
        
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
                          alpha=0.7,
                          label=LABEL_MAP[model] if idx == 0 else None)
        
        # 회귀선 및 95% CI
        if len(validator_x) >= 2:
            validator_x_arr = np.array(validator_x)
            validator_y_arr = np.array(validator_y)
            
            z = np.polyfit(validator_x_arr, validator_y_arr, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(validator_x_arr), max(validator_x_arr), 100)
            y_line = p(x_line)
            
            n = len(validator_x_arr)
            y_pred = p(validator_x_arr)
            residuals = validator_y_arr - y_pred
            std_err = np.sqrt(np.sum(residuals**2) / (n - 2))
            
            x_mean = np.mean(validator_x_arr)
            sxx = np.sum((validator_x_arr - x_mean)**2)
            se_line = std_err * np.sqrt(1/n + (x_line - x_mean)**2 / sxx)
            
            from scipy.stats import t as t_dist
            t_val = t_dist.ppf(0.975, n - 2)
            ci = t_val * se_line
            
            ax.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.15, color='#3498db')
            ax.plot(x_line, y_line, '#3498db', linestyle='-', linewidth=2)
            
            correlation, p_value = stats.pearsonr(validator_x, validator_y)
            p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
            ax.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
                   transform=ax.transAxes, fontsize=22, family='Helvetica')
        
        # 스타일링
        ax.set_title(VALIDATOR_INITIALS[validator], fontsize=30, fontweight='bold', family='Helvetica')
        # xlabel은 아래쪽 행(row==1)만 표시
        if row == 1:
            ax.set_xlabel('PSYCHE SCORE', fontsize=28, family='Helvetica')
        # ylabel은 왼쪽 열(col==0)만 표시
        if col == 0:
            ax.set_ylabel('Expert score', fontsize=28, family='Helvetica')
        ax.set_yticks([5, 35, 65])
        ax.set_xticks([5, 30, 55])
        ax.tick_params(labelsize=26)
        ax.grid(False)
        
        # Legend는 첫 번째 plot (맨 왼쪽 맨 상단)에만 표시
        if idx == 0:
            ax.legend(loc='upper left', prop={'size': 18, 'weight': 'bold', 'family': 'Helvetica'})
        
        for spine in ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(2)
    
    # (a) 마커 추가 - 왼쪽 상단
    fig.text(0.02, 0.95, '(a)', fontsize=32, fontweight='bold', family='Helvetica')
    
    # ========================================
    # (b) Disease-specific: Row 2 (1x3)
    # ========================================
    for idx, (disorder_code, disorder_name) in enumerate([(6201, "MDD"), (6202, "BD"), (6206, "OCD")]):
        ax = fig.add_subplot(gs[2, idx])
        
        # 데이터 필터링
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
        
        # 회귀선 및 95% CI
        if len(all_x) >= 2:
            all_x_arr = np.array(all_x)
            all_y_arr = np.array(all_y)
            
            z = np.polyfit(all_x_arr, all_y_arr, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(all_x_arr), max(all_x_arr), 100)
            y_line = p(x_line)
            
            n = len(all_x_arr)
            y_pred = p(all_x_arr)
            residuals = all_y_arr - y_pred
            std_err = np.sqrt(np.sum(residuals**2) / (n - 2))
            
            x_mean = np.mean(all_x_arr)
            sxx = np.sum((all_x_arr - x_mean)**2)
            se_line = std_err * np.sqrt(1/n + (x_line - x_mean)**2 / sxx)
            
            from scipy.stats import t as t_dist
            t_val = t_dist.ppf(0.975, n - 2)
            ci = t_val * se_line
            
            ax.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.15, color='#3498db')
            ax.plot(x_line, y_line, '#3498db', linestyle='-', linewidth=2)
            
            correlation, p_value = stats.pearsonr(all_x, all_y)
            p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
            ax.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
                   transform=ax.transAxes, fontsize=22, family='Helvetica')
        
        # 스타일링
        ax.set_title(DISORDER_NAMES[DISORDER_MAP[disorder_code]], fontsize=30, fontweight='bold', family='Helvetica', pad=20)
        # xlabel은 모두 표시 (아래쪽 가장자리)
        ax.set_xlabel('PSYCHE SCORE', fontsize=28, family='Helvetica')
        # ylabel은 왼쪽 첫 번째만 표시
        if idx == 0:
            ax.set_ylabel('Expert score', fontsize=28, family='Helvetica')
        ax.set_yticks([5, 35, 65])
        ax.set_xticks([5, 30, 55])
        ax.tick_params(labelsize=26)
        ax.grid(False)
        
        for spine in ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(2)
    
    # (b) 마커 추가
    fig.text(0.02, 0.48, '(b)', fontsize=32, fontweight='bold', family='Helvetica')
    
    # ========================================
    # (c) Category-specific: Row 3 (1x3)
    # ========================================
    categories = ['Subjective', 'Impulsivity', 'Behavior']
    category_labels = {
        'Subjective': 'Subjective Information',
        'Impulsivity': 'Impulsivity',
        'Behavior': 'MFC-Behavior'
    }
    
    for idx, category in enumerate(categories):
        ax = fig.add_subplot(gs[3, idx])
        
        # 데이터 수집
        data_by_model = {model: [] for model in COLOR_MAP.keys()}
        all_x, all_y = [], []
        
        for exp in EXPERIMENT_NUMBERS:
            if exp not in psyche_category_scores:
                continue
            
            psyche_score = psyche_category_scores[exp][category]
            
            # Expert score - average across validators
            expert_scores = []
            for validator in VALIDATORS:
                if exp in expert_category_scores[validator]:
                    expert_scores.append(expert_category_scores[validator][exp][category])
            
            if not expert_scores:
                continue
            
            expert_score = np.mean(expert_scores)
            model = get_model_from_exp(exp[1])
            
            data_by_model[model].append((psyche_score, expert_score))
            all_x.append(psyche_score)
            all_y.append(expert_score)
        
        # Scatter plot
        for model, points in data_by_model.items():
            if points:
                x_vals = [p[0] for p in points]
                y_vals = [p[1] for p in points]
                ax.scatter(x_vals, y_vals,
                          color=COLOR_MAP[model],
                          label=LABEL_MAP[model],
                          s=MARKER_MAP[model]['size'],
                          marker=MARKER_MAP[model]['marker'],
                          alpha=0.7)

        # 회귀선 및 95% CI
        if len(all_x) >= 2:
            all_x_arr = np.array(all_x)
            all_y_arr = np.array(all_y)

            z = np.polyfit(all_x_arr, all_y_arr, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(all_x_arr), max(all_x_arr), 100)
            y_line = p(x_line)

            n = len(all_x_arr)
            y_pred = p(all_x_arr)
            residuals = all_y_arr - y_pred
            std_err = np.sqrt(np.sum(residuals**2) / (n - 2))

            x_mean = np.mean(all_x_arr)
            sxx = np.sum((all_x_arr - x_mean)**2)
            se_line = std_err * np.sqrt(1/n + (x_line - x_mean)**2 / sxx)

            from scipy.stats import t as t_dist
            t_val = t_dist.ppf(0.975, n - 2)
            ci = t_val * se_line

            ax.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.15, color='#3498db')
            ax.plot(x_line, y_line, '#3498db', linestyle='-', linewidth=2)

            correlation, p_value = stats.pearsonr(all_x, all_y)
            p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
            ax.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
                   transform=ax.transAxes, fontsize=22, family='Helvetica')

        # 스타일링
        ax.set_title(category_labels[category], fontsize=30, fontweight='bold', family='Helvetica', pad=20)
        # xlabel은 모두 표시 (아래쪽 가장자리)
        ax.set_xlabel('PSYCHE SCORE', fontsize=28, family='Helvetica')
        # ylabel은 왼쪽 첫 번째만 표시
        if idx == 0:
            ax.set_ylabel('Expert score', fontsize=28, family='Helvetica')
        ax.tick_params(labelsize=26)
        ax.grid(False)

        for spine in ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(2)

    # (c) 마커 추가
    fig.text(0.02, 0.23, '(c)', fontsize=32, fontweight='bold', family='Helvetica')

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

def fig_to_vector_bytes(fig, fmt='pdf'):
    """Convert matplotlib figure to vector bytes (PDF or SVG)."""
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, bbox_inches='tight')
    buf.seek(0)
    return buf.getvalue()

def download_row(fig, base_filename, key_prefix):
    """PDF/SVG(벡터) + PNG(미리보기) 다운로드 버튼 배치."""
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("📥 PDF (vector)", fig_to_vector_bytes(fig, 'pdf'),
                           file_name=f"{base_filename}.pdf", mime="application/pdf",
                           key=f"{key_prefix}_pdf")
    with c2:
        st.download_button("📥 SVG (vector)", fig_to_vector_bytes(fig, 'svg'),
                           file_name=f"{base_filename}.svg", mime="image/svg+xml",
                           key=f"{key_prefix}_svg")
    with c3:
        st.download_button("📥 PNG (300 DPI)", fig_to_bytes(fig),
                           file_name=f"{base_filename}.png", mime="image/png",
                           key=f"{key_prefix}_png")

# ================================
# Main Application
# ================================
def main():
    plt.close('all')
    
    st.title("📊 Publication Figure Generator (Lite)")
    st.markdown("---")
    
    st.info("""
    **논문용 Combined Figure 생성 (경량 버전)**
    - 모든 폰트: Helvetica
    - 고해상도 PNG (300 DPI)
    - Combined Figure: Validator, Disease, Category 분석
    - V2: 축 레이블 최적화 (왼쪽/아래쪽 가장자리만 표시)
    
    ⚡ Weight Correlation과 SP Validation은 제외됨 (로딩 속도 최적화)
    """)
    
    # Load data
    with st.spinner("데이터 로딩 중..."):
        firebase_ref = get_firebase_ref()
        root_snapshot = firebase_ref.get() or {}
        expert_data = load_expert_scores(root_snapshot)
        psyche_scores = load_psyche_scores(root_snapshot)
        avg_expert_scores = calculate_average_expert_scores(expert_data)
        
        # Element-level scores for category analysis
        element_scores_psyche, element_scores_expert = load_element_scores(root_snapshot)
    
    st.success("✅ 데이터 로딩 완료")
    
    # Debug info
    with st.expander("🔍 데이터 로딩 상태 확인"):
        st.write(f"PSYCHE scores: {len(psyche_scores)} experiments")
        st.write(f"Expert data: {len(expert_data)} validators")
        
        psyche_elem_count = len([k for k in element_scores_psyche.keys() if isinstance(k, tuple)])
        st.write(f"Element-level PSYCHE scores: {psyche_elem_count} experiments")
        
        if '_debug_keys' in element_scores_psyche:
            debug_keys = element_scores_psyche['_debug_keys']
            st.write(f"PSYCHE keys found: {len(debug_keys)} total")
            if debug_keys:
                st.write(f"Sample keys: {debug_keys[:3]}")
        
        if '_debug_structure' in element_scores_psyche:
            st.write("**PSYCHE data structure sample:**")
            st.json(element_scores_psyche['_debug_structure'])
        
        st.write(f"Element-level Expert scores: {len(element_scores_expert)} validators")
        if element_scores_expert:
            for validator, data in element_scores_expert.items():
                st.write(f"  - {validator}: {len(data)} experiments")
        
        # Show sample data with more details
        if psyche_elem_count > 0:
            sample_keys = [k for k in element_scores_psyche.keys() if isinstance(k, tuple)][:3]
            st.write("Sample PSYCHE element data:", sample_keys)
            if sample_keys:
                sample_exp = sample_keys[0]
                sample_elements = list(element_scores_psyche[sample_exp].keys())[:5]
                st.write(f"  Elements in {sample_exp}: {sample_elements}")
        else:
            st.warning("⚠️ No PSYCHE element-level data found!")
        
        if element_scores_expert:
            sample_validator = list(element_scores_expert.keys())[0]
            validator_data = element_scores_expert[sample_validator]
            st.write(f"Sample Expert element data ({sample_validator}): {len(validator_data)} experiments")
            if validator_data:
                sample_exp = list(validator_data.keys())[0]
                sample_elements = list(validator_data[sample_exp].keys())[:5]
                st.write(f"  Elements in {sample_exp}: {sample_elements}")
        else:
            st.warning("⚠️ No Expert element-level data found!")
    
    # ================================
    # Combined Figure
    # ================================
    st.markdown("## 📈 Combined Correlation Figure")
    
    tab_combined, tab_combined_v2 = st.tabs([
        "Combined Figure (Original)",
        "Combined Figure V2 (Optimized Labels)"
    ])
    
    with tab_combined:
        st.markdown("### Combined Figure: Validator, Disorder, and Category Analysis")
        st.caption("(a) Validator-specific (2×3), (b) Disease-specific (1×3), (c) Category-specific (1×3)")
        
        if element_scores_psyche and element_scores_expert:
            with st.spinner("Combined Figure 생성 중..."):
                psyche_category_scores, expert_category_scores = calculate_category_scores(
                    element_scores_psyche, element_scores_expert
                )
                
                fig_combined = create_combined_correlation_figure(
                    psyche_scores, avg_expert_scores, expert_data,
                    psyche_category_scores, expert_category_scores
                )
                st.pyplot(fig_combined)
                
                st.download_button(
                    label="📥 Download PNG (300 DPI)",
                    data=fig_to_bytes(fig_combined),
                    file_name="Fig1_Combined_Correlation_Analysis.png",
                    mime="image/png"
                )
                plt.close(fig_combined)
        else:
            st.warning("Element-level 데이터가 없습니다. Category별 분석을 위해서는 element 점수가 필요합니다.")
    
    with tab_combined_v2:
        st.markdown("### Combined Figure V2: Validator, Disorder, and Category Analysis")
        st.caption("(a) Validator-specific (2×3), (b) Disease-specific (1×3), (c) Category-specific (1×3)")
        st.info("🔧 V2 - 축 레이블 최적화: 왼쪽과 아래쪽 가장자리에만 xlabel/ylabel 표시")
        
        if element_scores_psyche and element_scores_expert:
            with st.spinner("Combined Figure V2 생성 중..."):
                psyche_category_scores, expert_category_scores = calculate_category_scores(
                    element_scores_psyche, element_scores_expert
                )
                
                fig_combined_v2 = create_combined_correlation_figure_v2(
                    psyche_scores, avg_expert_scores, expert_data,
                    psyche_category_scores, expert_category_scores
                )
                st.pyplot(fig_combined_v2)

                download_row(fig_combined_v2, "Fig1_Combined_Correlation_Analysis_V2", "fig_combined_v2")
                plt.close(fig_combined_v2)
        else:
            st.warning("Element-level 데이터가 없습니다. Category별 분석을 위해서는 element 점수가 필요합니다.")

if __name__ == "__main__":
    main()
