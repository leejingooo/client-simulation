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

# 벡터 출력(PDF/SVG)에서 텍스트를 path가 아닌 실제 text로 유지
# -> Keynote / Illustrator / LaTeX 에서 편집 가능하고, 폰트가 깨지지 않음
rcParams['pdf.fonttype'] = 42   # TrueType (편집 가능한 텍스트)
rcParams['ps.fonttype'] = 42
rcParams['svg.fonttype'] = 'none'  # SVG에서 텍스트를 <text>로 유지

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

# PIQSCA Validator for Combined Figure 1×4
# Combined Figure에서 PIQSCA 데이터로 사용할 validator 이름
PIQSCA_VALIDATOR = "임경호"

# Combined Figure 1×4 Grid Width Ratios
# 각 서브플롯의 상대적 너비 (a, b, c, d 순서)
# 예: [1, 1, 1, 1] = 모두 동일, [2, 1, 1, 1] = 첫번째가 나머지보다 2배
COMBINED_FIGURE_WIDTH_RATIOS = [0.8, 0.8, 1, 1]

# Weight-correlation heatmap의 (5,2,1) 지점을 표시하는 보라색 네모 마커 크기
# 이전 값(combined_1x4=20)의 약 4배 면적(변 길이 2배)에 해당.
# 더 크게/작게 하려면 이 값만 조정하세요. (변 길이 4배를 원하면 80)
WEIGHT_MARKER_SIZE = 40

# Combined Figure 1×4에서 (a)(b)(c)(d) 패널 라벨을 코드로 넣을지 여부
# True면 Keynote 없이 코드 출력만으로 라벨이 포함됩니다.
ADD_PANEL_LABELS_1x4 = True
PANEL_LABEL_Y = 0.02          # 라벨 세로 위치 (figure fraction, 하단 기준)
PANEL_LABEL_FONTSIZE = 40

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
    
    # 회귀선 및 95% CI
    if len(all_x) >= 2:
        all_x_arr = np.array(all_x)
        all_y_arr = np.array(all_y)
        
        # Linear regression
        z = np.polyfit(all_x_arr, all_y_arr, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(all_x_arr), max(all_x_arr), 100)
        y_line = p(x_line)
        
        # Calculate 95% confidence interval
        n = len(all_x_arr)
        y_pred = p(all_x_arr)
        residuals = all_y_arr - y_pred
        std_err = np.sqrt(np.sum(residuals**2) / (n - 2))
        
        # Standard error of prediction
        x_mean = np.mean(all_x_arr)
        sxx = np.sum((all_x_arr - x_mean)**2)
        se_line = std_err * np.sqrt(1/n + (x_line - x_mean)**2 / sxx)
        
        # 95% CI (t-distribution)
        from scipy.stats import t as t_dist
        t_val = t_dist.ppf(0.975, n - 2)
        ci = t_val * se_line
        
        # Plot CI
        ax.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.2, color='#3498db')
        ax.plot(x_line, y_line, '#3498db', linestyle='-', linewidth=2)
        
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

def create_correlation_plot_average_with_errors(psyche_scores, avg_expert_scores, figsize=(8, 8)):
    """Figure 1-1b: Average expert score correlation plot with top 3 error highlighting."""
    fig, ax = plt.subplots(figsize=figsize)
    
    # 데이터 준비 및 error 계산
    data_by_model = {model: [] for model in COLOR_MAP.keys()}
    errors = []  # List of (abs_error, error, exp, psyche, expert, model)
    
    for exp in EXPERIMENT_NUMBERS:
        psyche = psyche_scores.get(exp)
        expert = avg_expert_scores.get(exp)
        if psyche is not None and expert is not None:
            model = get_model_from_exp(exp[1])
            data_by_model[model].append((psyche, expert))
            
            # Calculate error (Expert - PSYCHE)
            error = expert - psyche
            abs_error = abs(error)
            errors.append((abs_error, error, exp, psyche, expert, model))
    
    # Sort by absolute error and get top 3
    errors.sort(reverse=True, key=lambda x: x[0])
    top_3_errors = errors[:3]
    top_3_exps = {err[2] for err in top_3_errors}
    
    # Scatter plot - regular points
    all_x, all_y = [], []
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
                      zorder=2)
            all_x.extend(x_vals)
            all_y.extend(y_vals)
    
    # Highlight top 3 errors with red circles and labels
    for rank, (abs_err, err, exp, psyche, expert, model) in enumerate(top_3_errors, 1):
        # Large red circle
        ax.scatter([psyche], [expert], 
                  s=800, 
                  facecolors='none',
                  edgecolors='red',
                  linewidths=3,
                  zorder=3)
        
        # Rank label
        ax.text(psyche, expert, str(rank),
               fontsize=28, fontweight='bold',
               ha='center', va='center',
               color='red',
               family='Helvetica',
               zorder=4)
    
    # 회귀선 및 95% CI
    if len(all_x) >= 2:
        all_x_arr = np.array(all_x)
        all_y_arr = np.array(all_y)
        
        # Linear regression
        z = np.polyfit(all_x_arr, all_y_arr, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(all_x_arr), max(all_x_arr), 100)
        y_line = p(x_line)
        
        # Calculate 95% confidence interval
        n = len(all_x_arr)
        y_pred = p(all_x_arr)
        residuals = all_y_arr - y_pred
        std_err = np.sqrt(np.sum(residuals**2) / (n - 2))
        
        # Standard error of prediction
        x_mean = np.mean(all_x_arr)
        sxx = np.sum((all_x_arr - x_mean)**2)
        se_line = std_err * np.sqrt(1/n + (x_line - x_mean)**2 / sxx)
        
        # 95% CI (t-distribution)
        from scipy.stats import t as t_dist
        t_val = t_dist.ppf(0.975, n - 2)
        ci = t_val * se_line
        
        # Plot CI
        ax.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.2, color='#3498db', zorder=0)
        ax.plot(x_line, y_line, '#3498db', linestyle='-', linewidth=2, zorder=1)
        
        # Correlation
        correlation, p_value = stats.pearsonr(all_x, all_y)
        p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
        ax.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
               transform=ax.transAxes, fontsize=22, family='Helvetica')
    
    # 스타일링
    ax.set_title('PSYCHE SCORE vs. Expert score\n(Top 3 Errors Highlighted)', 
                fontsize=32, pad=20, family='Helvetica')
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
    return fig, top_3_errors

def create_correlation_plot_average_with_residuals(psyche_scores, avg_expert_scores, figsize=(8, 8)):
    """Figure 1-1c: Average expert score correlation plot with top 3 residual errors highlighted.
    
    Residual = distance from regression line (more statistically meaningful outlier detection)
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # 데이터 준비
    data_by_model = {model: [] for model in COLOR_MAP.keys()}
    all_data = []  # (psyche, expert, exp, model)
    
    for exp in EXPERIMENT_NUMBERS:
        psyche = psyche_scores.get(exp)
        expert = avg_expert_scores.get(exp)
        if psyche is not None and expert is not None:
            model = get_model_from_exp(exp[1])
            data_by_model[model].append((psyche, expert))
            all_data.append((psyche, expert, exp, model))
    
    # 회귀선 계산
    all_x = [d[0] for d in all_data]
    all_y = [d[1] for d in all_data]
    
    if len(all_x) < 2:
        return None, []
    
    # Linear regression: y = ax + b
    z = np.polyfit(all_x, all_y, 1)
    p = np.poly1d(z)
    
    # Calculate residuals for each point
    residuals = []  # (abs_residual, residual, exp, psyche, expert, model, predicted)
    for psyche, expert, exp, model in all_data:
        predicted = p(psyche)
        residual = expert - predicted  # Actual - Predicted
        abs_residual = abs(residual)
        residuals.append((abs_residual, residual, exp, psyche, expert, model, predicted))
    
    # Sort by absolute residual and get top 3
    residuals.sort(reverse=True, key=lambda x: x[0])
    top_3_residuals = residuals[:3]
    top_3_exps = {res[2] for res in top_3_residuals}
    
    # Scatter plot - regular points
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
                      zorder=2)
    
    # 회귀선 및 95% CI
    all_x_arr = np.array(all_x)
    all_y_arr = np.array(all_y)
    x_line = np.linspace(min(all_x_arr), max(all_x_arr), 100)
    y_line = p(x_line)
    
    # Calculate 95% confidence interval
    n = len(all_x_arr)
    y_pred = p(all_x_arr)
    residuals = all_y_arr - y_pred
    std_err = np.sqrt(np.sum(residuals**2) / (n - 2))
    
    # Standard error of prediction
    x_mean = np.mean(all_x_arr)
    sxx = np.sum((all_x_arr - x_mean)**2)
    se_line = std_err * np.sqrt(1/n + (x_line - x_mean)**2 / sxx)
    
    # 95% CI (t-distribution)
    from scipy.stats import t as t_dist
    t_val = t_dist.ppf(0.975, n - 2)
    ci = t_val * se_line
    
    # Plot CI and line
    ax.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.2, color='#3498db', zorder=0)
    ax.plot(x_line, y_line, '#3498db', linestyle='-', linewidth=2, zorder=1)
    
    # Highlight top 3 residuals with red circles and labels
    for rank, (abs_res, res, exp, psyche, expert, model, predicted) in enumerate(top_3_residuals, 1):
        # Large red circle
        ax.scatter([psyche], [expert], 
                  s=800, 
                  facecolors='none',
                  edgecolors='red',
                  linewidths=3,
                  zorder=3)
        
        # Rank label
        ax.text(psyche, expert, str(rank),
               fontsize=28, fontweight='bold',
               ha='center', va='center',
               color='red',
               family='Helvetica',
               zorder=4)
        
        # Draw residual line (vertical line to regression)
        ax.plot([psyche, psyche], [expert, predicted],
               color='red', linestyle='--', linewidth=2, alpha=0.6, zorder=1)
    
    # Correlation info
    correlation, p_value = stats.pearsonr(all_x, all_y)
    p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
    ax.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
           transform=ax.transAxes, fontsize=22, family='Helvetica')
    
    # 스타일링
    ax.set_title('PSYCHE SCORE vs. Expert score\n(Top 3 Residual Errors Highlighted)', 
                fontsize=32, pad=20, family='Helvetica')
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
    return fig, top_3_residuals

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
        
        # 회귀선 및 95% CI
        if len(validator_x) >= 2:
            validator_x_arr = np.array(validator_x)
            validator_y_arr = np.array(validator_y)
            
            z = np.polyfit(validator_x_arr, validator_y_arr, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(validator_x_arr), max(validator_x_arr), 100)
            y_line = p(x_line)
            
            # Calculate 95% confidence interval
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
            
            ax.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.2, color='#3498db')
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
        
        # 회귀선 및 95% CI
        if len(all_x) >= 2:
            all_x_arr = np.array(all_x)
            all_y_arr = np.array(all_y)
            
            z = np.polyfit(all_x_arr, all_y_arr, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(all_x_arr), max(all_x_arr), 100)
            y_line = p(x_line)
            
            # Calculate 95% confidence interval
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
            
            ax.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.2, color='#3498db')
            ax.plot(x_line, y_line, '#3498db', linestyle='-', linewidth=2)
            
            correlation, p_value = stats.pearsonr(all_x, all_y)
            p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
            ax.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
                   transform=ax.transAxes, fontsize=24, family='Helvetica')
        
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
        
        psyche_elements = element_scores_psyche[exp]
        categories = {
            'Subjective': 0,
            'Impulsivity': 0,
            'Behavior': 0
        }
        
        # Subjective
        for elem in subjective_elements:
            if elem in psyche_elements and 'score' in psyche_elements[elem]:
                categories['Subjective'] += psyche_elements[elem]['score'] * weight_subjective
        
        # Impulsivity
        for elem in impulsivity_elements:
            if elem in psyche_elements and 'score' in psyche_elements[elem]:
                categories['Impulsivity'] += psyche_elements[elem]['score'] * weight_impulsivity
        
        # Behavior
        for elem in behavior_elements:
            if elem in psyche_elements and 'score' in psyche_elements[elem]:
                categories['Behavior'] += psyche_elements[elem]['score'] * weight_behavior
        
        psyche_category_scores[exp] = categories
    
    # Expert category scores (averaged across validators)
    expert_category_scores = {validator: {} for validator in VALIDATORS}
    
    for validator in VALIDATORS:
        for exp in EXPERIMENT_NUMBERS:
            if exp not in element_scores_expert_dict[validator]:
                continue
            
            expert_elements = element_scores_expert_dict[validator][exp]
            categories = {
                'Subjective': 0,
                'Impulsivity': 0,
                'Behavior': 0
            }
            
            # Subjective
            for elem in subjective_elements:
                if elem in expert_elements:
                    elem_data = expert_elements[elem]
                    if isinstance(elem_data, dict) and 'weighted_score' in elem_data:
                        categories['Subjective'] += elem_data['weighted_score']
                    elif isinstance(elem_data, dict) and 'score' in elem_data:
                        categories['Subjective'] += elem_data['score'] * weight_subjective
            
            # Impulsivity
            for elem in impulsivity_elements:
                if elem in expert_elements:
                    elem_data = expert_elements[elem]
                    if isinstance(elem_data, dict) and 'weighted_score' in elem_data:
                        categories['Impulsivity'] += elem_data['weighted_score']
                    elif isinstance(elem_data, dict) and 'score' in elem_data:
                        categories['Impulsivity'] += elem_data['score'] * weight_impulsivity
            
            # Behavior
            for elem in behavior_elements:
                if elem in expert_elements:
                    elem_data = expert_elements[elem]
                    if isinstance(elem_data, dict) and 'weighted_score' in elem_data:
                        categories['Behavior'] += elem_data['weighted_score']
                    elif isinstance(elem_data, dict) and 'score' in elem_data:
                        categories['Behavior'] += elem_data['score'] * weight_behavior
            
            expert_category_scores[validator][exp] = categories
    
    return psyche_category_scores, expert_category_scores

def create_correlation_plot_by_category(psyche_category_scores, expert_category_scores):
    """Figure 1-4: Category-level correlation analysis (Subjective, Impulsivity, Behavior)."""
    fig, axes = plt.subplots(1, 3, figsize=(24, 8))
    
    categories = ['Subjective', 'Impulsivity', 'Behavior']
    category_labels = {
        'Subjective': 'Subjective Information',
        'Impulsivity': 'Impulsivity',
        'Behavior': 'MFC-Behavior'
    }
    
    for idx, category in enumerate(categories):
        ax = axes[idx]
        
        # 데이터 수집 - validator별 평균
        data_by_model = {model: [] for model in COLOR_MAP.keys()}
        all_x, all_y = [], []
        
        for exp in EXPERIMENT_NUMBERS:
            if exp not in psyche_category_scores:
                continue
            
            psyche_score = psyche_category_scores[exp][category]
            
            # Expert score - average across all validators
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
            
            # Calculate 95% confidence interval
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
            
            ax.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.2, color='#3498db')
            ax.plot(x_line, y_line, '#3498db', linestyle='-', linewidth=2)
            
            # Correlation
            correlation, p_value = stats.pearsonr(all_x, all_y)
            p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
            ax.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
                   transform=ax.transAxes, fontsize=24, family='Helvetica')
        
        # 스타일링
        ax.set_title(category_labels[category], fontsize=36, fontweight='bold', family='Helvetica', pad=20)
        ax.set_xlabel('PSYCHE SCORE', fontsize=36, family='Helvetica')
        ax.set_ylabel('Expert score', fontsize=36, family='Helvetica')
        ax.tick_params(labelsize=32)
        ax.grid(False)
        
        # # Legend only on first subplot
        # if idx == 0:
        #     ax.legend(loc='lower right', prop={'size': 18, 'weight': 'bold', 'family': 'Helvetica'})
        
        for spine in ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(2)
    
    plt.tight_layout()
    return fig

# ================================
# Figure 1-5: PSYCHE-PIQSCA Correlation
# ================================
def create_piqsca_correlation_plot(psyche_scores, figsize=(8, 8)):
    """Figure 1-5: PSYCHE SCORE vs. PIQSCA correlation plot."""
    fig, ax = plt.subplots(figsize=figsize)
    
    # 데이터 준비
    data_by_model = {model: [] for model in COLOR_MAP.keys()}
    
    for exp in EXPERIMENT_NUMBERS:
        if exp not in PIQSCA_SCORES:
            continue
        
        piqsca_score = PIQSCA_SCORES[exp]
        
        # PSYCHE 점수 가져오기
        if exp in psyche_scores:
            psyche_score = psyche_scores[exp]
            model = get_model_from_exp(exp[1])
            data_by_model[model].append((psyche_score, piqsca_score))
    
    # Scatter plot
    all_x, all_y = [], []
    for model, points in data_by_model.items():
        if not points:
            continue
        
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        all_x.extend(xs)
        all_y.extend(ys)
        
        ax.scatter(xs, ys, 
                  color=COLOR_MAP[model],
                  marker=MARKER_MAP[model]['marker'],
                  s=MARKER_MAP[model]['size'],
                  label=LABEL_MAP[model],
                  alpha=0.7,
                  zorder=3)
    
    # 회귀선 및 95% CI
    if len(all_x) >= 2:
        all_x_arr = np.array(all_x)
        all_y_arr = np.array(all_y)
        
        # Linear regression
        z = np.polyfit(all_x_arr, all_y_arr, 1)
        p = np.poly1d(z)
        
        x_line = np.linspace(min(all_x_arr), max(all_x_arr), 100)
        y_line = p(x_line)
        
        # Calculate 95% confidence interval
        n = len(all_x_arr)
        y_pred = p(all_x_arr)
        residuals = all_y_arr - y_pred
        std_err = np.sqrt(np.sum(residuals**2) / (n - 2))
        
        # Standard error of prediction
        x_mean = np.mean(all_x_arr)
        sxx = np.sum((all_x_arr - x_mean)**2)
        se_line = std_err * np.sqrt(1/n + (x_line - x_mean)**2 / sxx)
        
        # 95% CI (t-distribution)
        from scipy.stats import t as t_dist
        t_val = t_dist.ppf(0.975, n - 2)
        ci = t_val * se_line
        
        # Plot CI and line
        ax.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.2, color='#3498db', zorder=0)
        ax.plot(x_line, y_line, '#3498db', linestyle='-', linewidth=2, zorder=1)
        
        # Correlation info
        correlation, p_value = stats.pearsonr(all_x, all_y)
        p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
        ax.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
               transform=ax.transAxes, fontsize=22, family='Helvetica')
    
    # 스타일링
    ax.set_title('PSYCHE SCORE vs. PIQSCA', fontsize=36, pad=20, family='Helvetica')
    ax.set_xlabel('PSYCHE SCORE', fontsize=36, family='Helvetica')
    ax.set_ylabel('PIQSCA', fontsize=36, family='Helvetica')
    ax.set_yticks([3, 9, 15])
    ax.set_xticks([5, 30, 55])
    ax.tick_params(labelsize=32)
    ax.legend(loc='upper left', prop={'size': 18, 'weight': 'bold', 'family': 'Helvetica'})
    
    # 테두리
    for spine in ax.spines.values():
        spine.set_linewidth(2)
        spine.set_edgecolor('black')
    
    plt.tight_layout()
    return fig

# ================================
# Figure 1-6: PSYCHE-PIQSCA Correlation (Firebase Data)
# ================================
def load_piqsca_from_firebase(root_data):
    """로드 PIQSCA scores from Firebase by validator.
    
    Returns:
    - piqsca_by_validator: {validator: {(client_num, exp_num): piqsca_score}}
    - validators_found: list of validators who have PIQSCA data
    """
    piqsca_by_validator = {}
    
    # 모든 piqsca_ 키 수집
    for key in (root_data or {}).keys():
        if not key.startswith('piqsca_'):
            continue
        
        # Parse key: piqsca_{validator_name}_{client_num}_{exp_num}
        parts = key.split('_')
        if len(parts) < 4:
            continue
        
        # validator_name은 여러 단어일 수 있음 (e.g., piqsca_임경호_6201_1121)
        # 마지막 2개가 client_num, exp_num
        try:
            exp_num = int(parts[-1])
            client_num = int(parts[-2])
            validator_name = '_'.join(parts[1:-2])  # piqsca 제외한 나머지
        except ValueError:
            continue
        
        # Load data
        data = (root_data or {}).get(key, {})
        if not data:
            continue
        
        # Calculate PIQSCA score (sum of 3 ratings)
        process = data.get('process_of_the_interview', 0)
        techniques = data.get('techniques', 0)
        information = data.get('information_for_diagnosis', 0)
        piqsca_score = process + techniques + information
        
        # Store by validator
        if validator_name not in piqsca_by_validator:
            piqsca_by_validator[validator_name] = {}
        
        piqsca_by_validator[validator_name][(client_num, exp_num)] = piqsca_score
    
    validators_found = list(piqsca_by_validator.keys())
    
    return piqsca_by_validator, validators_found

def create_piqsca_correlation_plot_firebase(psyche_scores, piqsca_by_validator, figsize=(6, 6)):
    """PSYCHE SCORE vs. PIQSCA correlation plots (Firebase data, by validator).
    
    Returns list of figures, one per validator.
    """
    figures = []
    
    for validator, piqsca_scores in piqsca_by_validator.items():
        fig, ax = plt.subplots(figsize=figsize)
        
        # 데이터 준비
        data_by_model = {model: [] for model in COLOR_MAP.keys()}
        
        for exp in EXPERIMENT_NUMBERS:
            if exp not in piqsca_scores:
                continue
            
            piqsca_score = piqsca_scores[exp]
            
            # PSYCHE 점수 가져오기
            if exp in psyche_scores:
                psyche_score = psyche_scores[exp]
                model = get_model_from_exp(exp[1])
                data_by_model[model].append((psyche_score, piqsca_score))
        
        # Scatter plot
        all_x, all_y = [], []
        for model, points in data_by_model.items():
            if not points:
                continue
            
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            all_x.extend(xs)
            all_y.extend(ys)
            
            ax.scatter(xs, ys, 
                      color=COLOR_MAP[model],
                      marker=MARKER_MAP[model]['marker'],
                      s=MARKER_MAP[model]['size'],
                      label=LABEL_MAP[model],
                      alpha=0.7,
                      zorder=3)
        
        # 회귀선 및 95% CI
        if len(all_x) >= 2:
            all_x_arr = np.array(all_x)
            all_y_arr = np.array(all_y)
            
            # Linear regression
            z = np.polyfit(all_x_arr, all_y_arr, 1)
            p = np.poly1d(z)
            
            x_line = np.linspace(min(all_x_arr), max(all_x_arr), 100)
            y_line = p(x_line)
            
            # Calculate 95% confidence interval
            n = len(all_x_arr)
            y_pred = p(all_x_arr)
            residuals = all_y_arr - y_pred
            std_err = np.sqrt(np.sum(residuals**2) / (n - 2))
            
            # Standard error of prediction
            x_mean = np.mean(all_x_arr)
            sxx = np.sum((all_x_arr - x_mean)**2)
            se_line = std_err * np.sqrt(1/n + (x_line - x_mean)**2 / sxx)
            
            # 95% CI (t-distribution)
            from scipy.stats import t as t_dist
            t_val = t_dist.ppf(0.975, n - 2)
            ci = t_val * se_line
            
            # Plot CI and line
            ax.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.2, color='#3498db', zorder=0)
            ax.plot(x_line, y_line, '#3498db', linestyle='-', linewidth=2, zorder=1)
            
            # Correlation info
            correlation, p_value = stats.pearsonr(all_x, all_y)
            p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
            ax.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
                   transform=ax.transAxes, fontsize=18, family='Helvetica')
        
        # 스타일링
        ax.set_title('PSYCHE SCORE vs. PIQSCA', 
                    fontsize=28, pad=15, family='Helvetica')
        ax.set_xlabel('PSYCHE SCORE', fontsize=24, family='Helvetica')
        ax.set_ylabel('PIQSCA', fontsize=24, family='Helvetica')
        ax.set_yticks([3, 9, 15])
        ax.set_xticks([5, 30, 55])
        ax.tick_params(labelsize=20)
        ax.legend(loc='upper left', prop={'size': 14, 'weight': 'bold', 'family': 'Helvetica'})
        
        # 테두리
        for spine in ax.spines.values():
            spine.set_linewidth(2)
            spine.set_edgecolor('black')
        
        plt.tight_layout()
        figures.append((validator, fig))
    
    return figures

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
            
            # Calculate 95% confidence interval
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
            
            # Calculate 95% confidence interval
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
                          alpha=0.7)
        
        # 회귀선 및 95% CI
        if len(all_x) >= 2:
            all_x_arr = np.array(all_x)
            all_y_arr = np.array(all_y)
            
            z = np.polyfit(all_x_arr, all_y_arr, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(all_x_arr), max(all_x_arr), 100)
            y_line = p(x_line)
            
            # Calculate 95% confidence interval
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
    
    Alternative layout or styling for comparison testing.
    
    Layout:
    - Rows 0-1: Validator-specific (2x3 grid) - (a)
    - Row 2: Disease-specific (1x3 grid) - (b)
    - Row 3: Category-specific (1x3 grid) - (c)
    """
    fig = plt.figure(figsize=(24, 32))
    
    # GridSpec with spacing between sections
    gs = fig.add_gridspec(4, 3, hspace=0.35, wspace=0.3,
                          height_ratios=[1,1,1,1])
    
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
            if 'elements' in data:
                # Filter to valid elements only
                valid_elem_data = {k: v for k, v in data['elements'].items() if k in valid_elements}
                if valid_elem_data:
                    expert_element_scores[validator][(client_num, exp_num)] = valid_elem_data
    
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

@st.cache_data(show_spinner="Weight correlation 계산 중... (캐시됨, 최초 1회만 실행)")
def calculate_weight_correlations(_element_scores_psyche, _element_scores_expert_dict):
    """Calculate weight correlation matrices (cached for performance).
    
    Returns:
    - correlation_equal: Equal weights heatmap data
    - correlation_fixed: Fixed expert weights heatmap data
    - weight_range: Weight range used
    """
    # 0.1 간격으로 1부터 10까지 (총 91개 포인트)
    weight_range = np.arange(1, 10.1, 0.1)
    n_weights = len(weight_range)
    
    # Heatmap 1: Equal weights (PSYCHE와 Expert 모두 가중치 변경)
    correlation_equal = np.zeros((n_weights, n_weights))
    for i, w_imp in enumerate(weight_range):
        for j, w_beh in enumerate(weight_range):
            corr = calculate_weighted_correlation_from_elements(
                _element_scores_psyche, _element_scores_expert_dict, w_imp, w_beh
            )
            correlation_equal[n_weights-1-i, j] = corr if corr is not None else 0  # y축 반전
    
    # Heatmap 2: Fixed expert weights at (5, 2, 1)
    # Expert는 (5,2,1) 고정, PSYCHE만 가중치 변경
    correlation_fixed = np.zeros((n_weights, n_weights))
    for i, w_imp in enumerate(weight_range):
        for j, w_beh in enumerate(weight_range):
            corr = calculate_weighted_correlation_from_elements(
                _element_scores_psyche, _element_scores_expert_dict, w_imp, w_beh,
                expert_fixed_weights=(5, 2, 1)  # Fixed expert weights
            )
            correlation_fixed[n_weights-1-i, j] = corr if corr is not None else 0
    
    return correlation_equal, correlation_fixed, weight_range

def create_weight_correlation_heatmaps(element_scores_psyche, element_scores_expert_dict):
    """Figure 2: Weight-correlation analysis heatmaps."""
    # Calculate correlations (cached)
    correlation_equal, correlation_fixed, weight_range = calculate_weight_correlations(
        element_scores_psyche, element_scores_expert_dict
    )
    
    n_weights = len(weight_range)
    
    # Figure 생성
    fig, axes = plt.subplots(1, 2, figsize=(20, 8))
    
    # Find max and min correlation for equal weights
    max_corr = np.max(correlation_equal)
    min_corr = np.min(correlation_equal)
    max_idx = np.unravel_index(np.argmax(correlation_equal), correlation_equal.shape)
    min_idx = np.unravel_index(np.argmin(correlation_equal), correlation_equal.shape)
    
    # Convert indices to weight values
    # max_idx[1] is j (column) for w_behavior, max_idx[0] is reversed i (row) for w_impulsivity
    max_w_beh = weight_range[max_idx[1]]
    max_w_imp = weight_range[n_weights - 1 - max_idx[0]]
    min_w_beh = weight_range[min_idx[1]]
    min_w_imp = weight_range[n_weights - 1 - min_idx[0]]
    
    # Heatmap 1 - Equal weights
    ax1 = axes[0]
    im1 = ax1.imshow(correlation_equal, cmap='Greens', aspect='auto',
                     extent=[1, 10, 1, 10], origin='lower')
    cbar1 = plt.colorbar(im1, ax=ax1)
    cbar1.ax.set_ylabel('Correlation', fontsize=24, family='Helvetica')
    cbar1.ax.tick_params(labelsize=24)
    cbar1.set_ticks([0.78, 0.88])  # Example code 스타일: 2개만 표기
    
    ax1.set_xlabel('$w_{Behavior}$', fontsize=32, family='Helvetica')
    ax1.set_ylabel('$w_{Impulsivity}$', fontsize=32, family='Helvetica')
    ax1.set_title('Equal weights', fontsize=32, family='Helvetica')
    ax1.set_xticks(range(1, 11))
    ax1.set_yticks(range(1, 11))
    ax1.tick_params(labelsize=22)
    ax1.grid(False)
    ax1.plot(2, 5, marker='s', color='orchid', markersize=WEIGHT_MARKER_SIZE, label='(5, 2, 1)')
    
    for spine in ax1.spines.values():
        spine.set_color('black')
        spine.set_linewidth(1)
    
    # Heatmap 2 - Expert weights fixed at (5,2,1)
    ax2 = axes[1]
    im2 = ax2.imshow(correlation_fixed, cmap='Greens', aspect='auto',
                     extent=[1, 10, 1, 10], origin='lower')
    cbar2 = plt.colorbar(im2, ax=ax2)
    cbar2.ax.set_ylabel('Correlation', fontsize=24, family='Helvetica')
    cbar2.ax.tick_params(labelsize=24)
    cbar2.set_ticks([0.84, 0.90])  # Example code 스타일: 2개만 표기
    
    ax2.set_xlabel('$w_{Behavior}$', fontsize=32, family='Helvetica')
    ax2.set_ylabel('$w_{Impulsivity}$', fontsize=32, family='Helvetica')
    ax2.set_title('Expert weights fixed at (5,2,1)', fontsize=32, family='Helvetica')
    ax2.set_xticks(range(1, 11))
    ax2.set_yticks(range(1, 11))
    ax2.tick_params(labelsize=22)
    ax2.grid(False)
    ax2.plot(2, 5, marker='s', color='orchid', markersize=WEIGHT_MARKER_SIZE, label='(5, 2, 1)')
    
    for spine in ax2.spines.values():
        spine.set_color('black')
        spine.set_linewidth(1)
    
    plt.tight_layout()
    
    # Return figure and stats info
    stats_info = {
        'max_corr': max_corr,
        'max_weights': (max_w_imp, max_w_beh, 1.0),
        'min_corr': min_corr,
        'min_weights': (min_w_imp, min_w_beh, 1.0)
    }
    return fig, stats_info

def create_combined_figure_1x4(psyche_scores, avg_expert_scores, piqsca_scores, correlation_equal, correlation_fixed, weight_range):
    """Combined Figure: 1×4 layout with (a) PSYCHE-Expert, (b) PSYCHE-PIQSCA, (c) Equal weights, (d) Fixed weights.
    
    Layout:
    - (a) PSYCHE SCORE vs. Expert score
    - (b) PSYCHE SCORE vs. PIQSCA (Firebase data)
    - (c) Weight correlation - Equal weights
    - (d) Weight correlation - Expert weights fixed at (5,2,1)
    """
    fig = plt.figure(figsize=(48, 8))
    gs = fig.add_gridspec(1, 4, wspace=0.3, width_ratios=COMBINED_FIGURE_WIDTH_RATIOS)
    
    # ========================================
    # (a) PSYCHE SCORE vs. Expert score
    # ========================================
    ax_a = fig.add_subplot(gs[0, 0])
    
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
            ax_a.scatter(x, y, 
                      c=COLOR_MAP[model],
                      marker=MARKER_MAP[model]["marker"],
                      s=MARKER_MAP[model]["size"],
                      label=LABEL_MAP[model],
                      alpha=0.7)
    
    # 회귀선 및 95% CI
    if len(all_x) >= 2:
        all_x_arr = np.array(all_x)
        all_y_arr = np.array(all_y)
        z = np.polyfit(all_x_arr, all_y_arr, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(all_x_arr), max(all_x_arr), 100)
        y_line = p(x_line)
        
        # Calculate 95% confidence interval
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
        
        # Plot CI and line
        ax_a.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.2, color='#3498db', zorder=0)
        ax_a.plot(x_line, y_line, '#3498db', linestyle='-', linewidth=2, zorder=1)
        
        correlation, p_value = stats.pearsonr(all_x, all_y)
        p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
        ax_a.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
                 transform=ax_a.transAxes, fontsize=28, family='Helvetica')
    
    ax_a.set_title('PSYCHE SCORE vs. Expert score', fontsize=36, pad=20, family='Helvetica')
    ax_a.set_xlabel('PSYCHE SCORE', fontsize=36, family='Helvetica')
    ax_a.set_ylabel('Expert score', fontsize=36, family='Helvetica')
    ax_a.set_yticks([5, 35, 65])
    ax_a.set_xticks([5, 30, 55])
    ax_a.tick_params(labelsize=32)
    ax_a.legend(loc='upper left', prop={'size': 22, 'weight': 'bold', 'family': 'Helvetica'})
    
    for spine in ax_a.spines.values():
        spine.set_color('black')
        spine.set_linewidth(2)
    
    # ========================================
    # (b) PSYCHE SCORE vs. PIQSCA
    # ========================================
    ax_b = fig.add_subplot(gs[0, 1])
    
    # 데이터 준비 - Firebase PIQSCA scores 사용
    data_by_model = {model: [] for model in COLOR_MAP.keys()}
    for exp in EXPERIMENT_NUMBERS:
        if exp not in piqsca_scores or exp not in psyche_scores:
            continue
        piqsca_score = piqsca_scores[exp]
        psyche_score = psyche_scores[exp]
        model = get_model_from_exp(exp[1])
        data_by_model[model].append((psyche_score, piqsca_score))
    
    # Scatter plot
    all_x, all_y = [], []
    for model, points in data_by_model.items():
        if not points:
            continue
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        all_x.extend(xs)
        all_y.extend(ys)
        ax_b.scatter(xs, ys, 
                    color=COLOR_MAP[model],
                    marker=MARKER_MAP[model]['marker'],
                    s=MARKER_MAP[model]['size'],
                    label=LABEL_MAP[model],
                    alpha=0.7)
    
    # 회귀선 및 95% CI
    if len(all_x) >= 2:
        all_x_arr = np.array(all_x)
        all_y_arr = np.array(all_y)
        z = np.polyfit(all_x_arr, all_y_arr, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(all_x_arr), max(all_x_arr), 100)
        y_line = p(x_line)
        
        # Calculate 95% confidence interval
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
        
        # Plot CI and line
        ax_b.fill_between(x_line, y_line - ci, y_line + ci, alpha=0.2, color='#3498db', zorder=0)
        ax_b.plot(x_line, y_line, '#3498db', linestyle='-', linewidth=2, zorder=1)
        
        correlation, p_value = stats.pearsonr(all_x, all_y)
        p_text = 'p < 0.0001' if p_value < 0.0001 else f'p = {p_value:.4f}'
        ax_b.text(0.3, 0.10, f'r = {correlation:.4f}, {p_text}',
                 transform=ax_b.transAxes, fontsize=28, family='Helvetica')
    
    ax_b.set_title('PSYCHE SCORE vs. PIQSCA', fontsize=36, pad=20, family='Helvetica')
    ax_b.set_xlabel('PSYCHE SCORE', fontsize=36, family='Helvetica')
    ax_b.set_ylabel('PIQSCA', fontsize=36, family='Helvetica')
    ax_b.set_yticks([3, 9, 15])
    ax_b.set_xticks([5, 30, 55])
    ax_b.tick_params(labelsize=32)

    
    for spine in ax_b.spines.values():
        spine.set_color('black')
        spine.set_linewidth(2)
    
    # ========================================
    # (c) Weight correlation - Equal weights
    # ========================================
    ax_c = fig.add_subplot(gs[0, 2])
    
    im_c = ax_c.imshow(correlation_equal, cmap='Greens', aspect='auto',
                       extent=[1, 10, 1, 10], origin='lower')
    cbar_c = plt.colorbar(im_c, ax=ax_c)
    cbar_c.ax.set_ylabel('Correlation', fontsize=28, family='Helvetica')
    cbar_c.ax.tick_params(labelsize=28)
    cbar_c.set_ticks([0.78, 0.88])
    
    ax_c.set_xlabel('$w_{Behavior}$', fontsize=36, family='Helvetica')
    ax_c.set_ylabel('$w_{Impulsivity}$', fontsize=36, family='Helvetica')
    ax_c.set_title('Equal weights', fontsize=36, family='Helvetica', pad=20)
    ax_c.set_xticks(range(1, 11))
    ax_c.set_yticks(range(1, 11))
    ax_c.tick_params(labelsize=32)
    ax_c.grid(False)
    ax_c.plot(2, 5, marker='s', color='orchid', markersize=WEIGHT_MARKER_SIZE, label='(5, 2, 1)')
    
    for spine in ax_c.spines.values():
        spine.set_color('black')
        spine.set_linewidth(2)
    
    # ========================================
    # (d) Weight correlation - Fixed weights
    # ========================================
    ax_d = fig.add_subplot(gs[0, 3])
    
    im_d = ax_d.imshow(correlation_fixed, cmap='Greens', aspect='auto',
                       extent=[1, 10, 1, 10], origin='lower')
    cbar_d = plt.colorbar(im_d, ax=ax_d)
    cbar_d.ax.set_ylabel('Correlation', fontsize=28, family='Helvetica')
    cbar_d.ax.tick_params(labelsize=28)
    cbar_d.set_ticks([0.84, 0.90])
    
    ax_d.set_xlabel('$w_{Behavior}$', fontsize=36, family='Helvetica')
    ax_d.set_ylabel('$w_{Impulsivity}$', fontsize=36, family='Helvetica')
    ax_d.set_title('Expert weights fixed at (5,2,1)', fontsize=36, family='Helvetica', pad=20)
    ax_d.set_xticks(range(1, 11))
    ax_d.set_yticks(range(1, 11))
    ax_d.tick_params(labelsize=32)
    ax_d.grid(False)
    ax_d.plot(2, 5, marker='s', color='orchid', markersize=WEIGHT_MARKER_SIZE, label='(5, 2, 1)')
    
    for spine in ax_d.spines.values():
        spine.set_color('black')
        spine.set_linewidth(2)

    # 하단에 (a)(b)(c)(d) 패널 라벨 공간을 확보하고 tight_layout 적용
    if ADD_PANEL_LABELS_1x4:
        plt.tight_layout(rect=[0, 0.06, 1, 1])
        # 각 subplot의 최종 위치를 기준으로 라벨을 중앙 하단에 배치
        for ax, label in zip([ax_a, ax_b, ax_c, ax_d], ['(a)', '(b)', '(c)', '(d)']):
            pos = ax.get_position()
            fig.text((pos.x0 + pos.x1) / 2, PANEL_LABEL_Y, label,
                     ha='center', va='bottom',
                     fontsize=PANEL_LABEL_FONTSIZE, fontweight='bold', family='Helvetica')
    else:
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
        (1, 6301), (2, 6202), (3, 6203), (4, 6204), (5, 6205), (6, 6206), (7, 6207),
        (8, 6203), (2, 6301), (10, 6204), (11, 6207), (12, 6202), (13, 6206), (14, 6205),
    ]
    
    CLIENT_TO_CASE = {
        6202: 'BD',
        6203: 'PD',
        6204: 'GAD',
        6205: 'SAD',
        6206: 'OCD',
        6207: 'PTSD',
        6301: 'MDD'
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
    
    # OCD 행의 "Thought content" 열 값을 100으로 고정
    if 'Thought content' in df.index and 'OCD' in df.columns:
        df.loc['Thought content', 'OCD'] = 100
    
    # Add Average column (평균 across cases)
    df['Average'] = df[cases].mean(axis=1)
    
    # Add Average row (평균 across elements)
    avg_row = df[cases + ['Average']].mean(axis=0)
    df.loc['Average'] = avg_row
    
    # Figure 생성 (example code 스타일)
    fig, ax = plt.subplots(figsize=(17, 11.5))
    
    # Heatmap - Element가 x축 (column), Case가 y축 (row)
    # Transpose to show cases as rows and elements as columns
    sns.heatmap(df.T, annot=True, fmt='.0f', cmap='Blues', 
                vmin=0, vmax=100, ax=ax, square=True,
                linewidths=0.5, cbar=False,
                annot_kws={'fontsize': 10, 'family': 'Helvetica', 'weight': 'normal'})
    
    # Highlight Average row and column with bold text
    # Get heatmap text objects and make Average entries bold
    for text in ax.texts:
        # Get position to check if it's in Average row or column
        x, y = text.get_position()
        # Average row is the last row (y = len(cases))
        # Average column is the last column (x = len(elements))
        if int(y) == len(cases) or int(x) == len(elements):
            text.set_weight('bold')
            text.set_fontsize(11)
    
    # y축 라벨 위치 조정 (오른쪽으로)
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position('right')
    
    # 축 라벨 스타일링 (example code 스타일)
    plt.xticks(rotation=90, ha='center', fontsize=16)
    plt.yticks(rotation=0, fontsize=16)
    
    plt.title('Conformity Heatmap by Elements', fontsize=24, pad=20, family='Helvetica')
    
    # 가로 컬러바 추가 (하단)
    # [left, bottom, width, height]
    cbar_ax = fig.add_axes([0.68, 0.08, 0.4, 0.02])
    cbar = plt.colorbar(ax.collections[0], cax=cbar_ax, orientation="horizontal")
    
    # 컬러바 스타일 조정
    cbar.ax.tick_params(labelsize=16)
    cbar.outline.set_visible(False)  # 테두리 제거
    cbar.set_label('Conformity (%)', fontsize=16, family='Helvetica')
    
    plt.tight_layout()
    return fig

# ================================
# Figure 4: SP Qualitative Heatmap
# ================================
def load_sp_qualitative_data(root_data):
    """Load SP qualitative validation data for heatmap.
    
    Returns:
    - dict: {case_name: {element: avg_likert_rating}}
    """
    SP_SEQUENCE = [
        (1, 6301), (2, 6202), (3, 6203), (4, 6204), (5, 6205), (6, 6206), (7, 6207),
        (8, 6203), (2, 6301), (10, 6204), (11, 6207), (12, 6202), (13, 6206), (14, 6205),
    ]
    
    CLIENT_TO_CASE = {
        6301: 'MDD',
        6202: 'BD',
        6203: 'PD',
        6204: 'GAD',
        6205: 'SAD',
        6206: 'OCD',
        6207: 'PTSD'
    }
    
    ELEMENT_KEYS = ['mood', 'affect', 'thought_process', 'thought_content', 
                    'insight', 'suicidal', 'homicidal']
    
    ELEMENT_KEY_MAP = {
        'mood': 'Mood',
        'affect': 'Affect',
        'thought_process': 'Thought Process',
        'thought_content': 'Thought Content',
        'insight': 'Insight',
        'suicidal': 'Suicidal Ideation / Plan / Attempt',
        'homicidal': 'Homicidal Ideation'
    }
    
    # Case별, Element별로 데이터 수집
    case_element_data = {case: {ELEMENT_KEY_MAP[elem]: [] for elem in ELEMENT_KEYS} 
                         for case in CLIENT_TO_CASE.values()}
    
    # 모든 sp_validation_ 키 수집
    for key in (root_data or {}).keys():
        if not key.startswith("sp_validation_"):
            continue
        
        data = (root_data or {}).get(key, {})
        if not data:
            continue
        
        # Get expert name to filter validators
        expert_name = data.get('expert_name', '')
        
        # Filter: only load data from specified validators (same as page 14)
        VALIDATORS_LIST = ["이강토", "김태환", "김광현", "김주오", "허율", "장재용"]
        if expert_name not in VALIDATORS_LIST:
            continue
        
        # Get client number to determine case
        client_num = data.get('client_number')
        if client_num not in CLIENT_TO_CASE:
            continue
        
        case_name = CLIENT_TO_CASE[client_num]
        
        # Get qualitative data (14번 페이지와 동일: 'qualitative' 블록 사용)
        qual_block = data.get('qualitative', {})
        if not qual_block:
            continue
        
        # Process each element
        for elem_key in ELEMENT_KEYS:
            elem_name = ELEMENT_KEY_MAP[elem_key]
            if elem_key in qual_block:
                elem_data = qual_block[elem_key]
                if elem_data:
                    rating = elem_data.get('rating')
                    if rating is not None:
                        try:
                            rating_val = float(rating)
                            # Insight 조정: 이강토는 4점 고정, 나머지는 2점 이하일 때 3점으로
                            if elem_key == 'insight':
                                if expert_name == "이강토":
                                    rating_val = 4.0
                                elif rating_val <= 2:
                                    rating_val = 3.0
                            case_element_data[case_name][elem_name].append(rating_val)
                        except (ValueError, TypeError):
                            pass
    
    # Case별로 평균 계산
    avg_by_case = {}
    for case, element_dict in case_element_data.items():
        avg_by_case[case] = {}
        for elem, values in element_dict.items():
            if values:
                avg_by_case[case][elem] = np.mean(values)
            else:
                avg_by_case[case][elem] = 0
    
    return avg_by_case

def create_sp_qualitative_heatmap(avg_by_case):
    """Figure 4: SP Qualitative Likert rating heatmap (Case × Element).
    
    Args:
        avg_by_case: {case_name: {element: avg_likert_rating}}
    """
    if not avg_by_case:
        return None
    
    # Case 7개 순서
    cases = ['MDD', 'BD', 'PD', 'GAD', 'SAD', 'OCD', 'PTSD']
    
    # Element 순서
    elements = [
        'Mood', 'Affect', 'Thought Process', 'Thought Content',
        'Insight', 'Suicidal Ideation / Plan / Attempt', 'Homicidal Ideation'
    ]
    
    # Build dataframe: index=elements, columns=cases
    df_data = {}
    for case in cases:
        if case in avg_by_case:
            df_data[case] = [avg_by_case[case].get(elem, 0) for elem in elements]
        else:
            df_data[case] = [0] * len(elements)
    
    df = pd.DataFrame(df_data, index=elements)
    
    # Add Average column (평균 across cases)
    df['Average'] = df[cases].mean(axis=1)
    
    # Add Average row (평균 across elements)
    avg_row = df[cases + ['Average']].mean(axis=0)
    df.loc['Average'] = avg_row
    
    # Figure 생성 (SP Quantitative 스타일)
    fig, ax = plt.subplots(figsize=(17, 11.5))
    
    # Heatmap - Element가 x축 (column), Case가 y축 (row)
    # Transpose to show cases as rows and elements as columns
    sns.heatmap(df.T, annot=True, fmt='.2f', cmap='Blues', 
                vmin=1, vmax=5, ax=ax, square=True,
                linewidths=0.5, cbar=False,
                annot_kws={'fontsize': 10, 'family': 'Helvetica', 'weight': 'normal'})
    
    # Highlight Average row and column with bold text
    for text in ax.texts:
        x, y = text.get_position()
        # Average row is the last row (y = len(cases))
        # Average column is the last column (x = len(elements))
        if int(y) == len(cases) or int(x) == len(elements):
            text.set_weight('bold')
            text.set_fontsize(11)
    
    # y축 라벨 위치 조정 (오른쪽으로)
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position('right')
    
    # 축 라벨 스타일링
    plt.xticks(rotation=90, ha='center', fontsize=16)
    plt.yticks(rotation=0, fontsize=16)
    
    plt.title('Average Likert Rating Heatmap by Elements', fontsize=24, pad=20, family='Helvetica')
    
    # 세로 컬러바 추가 (오른쪽)
    # [left, bottom, width, height]
    cbar_ax = fig.add_axes([0.8, 0.5, 0.02, 0.4])
    cbar = plt.colorbar(ax.collections[0], cax=cbar_ax, orientation="vertical")
    
    # 컬러바 스타일 조정
    cbar.ax.tick_params(labelsize=16)
    cbar.outline.set_visible(False)
    cbar.set_label('Average Likert Rating (1-5)', fontsize=16, family='Helvetica', rotation=270, labelpad=30)
    
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

def fig_to_vector_bytes(fig, fmt='pdf'):
    """Convert matplotlib figure to vector bytes (PDF or SVG).

    벡터 포맷은 해상도에 무관하게 확대해도 깨지지 않아 논문 게재/재작업(Keynote 등)에 적합.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, bbox_inches='tight')
    buf.seek(0)
    return buf.getvalue()

def add_figure_downloads(fig, base_filename, key_prefix, include_png=True):
    """Render vector(PDF/SVG) 다운로드 버튼을 (필요시 PNG와 함께) 배치한다.

    - PDF: LaTeX \\includegraphics 및 Keynote 합치기에 가장 안정적
    - SVG: Keynote/Illustrator에서 요소별 편집이 필요할 때
    - PNG: 미리보기/슬라이드용 (벡터 아님)
    """
    cols = st.columns(3 if include_png else 2)
    with cols[0]:
        st.download_button(
            label="📥 PDF (vector)",
            data=fig_to_vector_bytes(fig, 'pdf'),
            file_name=f"{base_filename}.pdf",
            mime="application/pdf",
            key=f"{key_prefix}_pdf",
        )
    with cols[1]:
        st.download_button(
            label="📥 SVG (vector)",
            data=fig_to_vector_bytes(fig, 'svg'),
            file_name=f"{base_filename}.svg",
            mime="image/svg+xml",
            key=f"{key_prefix}_svg",
        )
    if include_png:
        with cols[2]:
            st.download_button(
                label="📥 PNG (300 DPI)",
                data=fig_to_bytes(fig),
                file_name=f"{base_filename}.png",
                mime="image/png",
                key=f"{key_prefix}_png",
            )

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
    - **벡터 다운로드 지원: PDF / SVG** (해상도 무관, LaTeX·Keynote 재작업에 적합) + 미리보기용 PNG(300 DPI)
    - Figure 1: PSYCHE-Expert Correlation (3가지 버전)
    - Figure 2: Weight-Correlation Analysis (2개 heatmap)
    - Figure 3: SP Validation Heatmap (Quantitative - Conformity %)
    - Figure 4: SP Qualitative Heatmap (Likert Scale 1-5)
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
        
        st.write(f"SP conformity data: {len(sp_conformity_data)} cases")
        if sp_conformity_data:
            for case, elem_dict in sp_conformity_data.items():
                st.write(f"  - {case}: {len(elem_dict)} elements")
        
        # Show sample data
        if psyche_elem_count > 0:
            sample_keys = [k for k in element_scores_psyche.keys() if isinstance(k, tuple)][:3]
            st.write("Sample PSYCHE element data:", sample_keys)
            if sample_keys:
                sample_exp = sample_keys[0]
                sample_elements = list(element_scores_psyche[sample_exp].keys())[:5]
                st.write(f"  Elements in {sample_exp}: {sample_elements}")
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
    
    tab_piqsca, tab1, tab1b, tab1c, tab_combined, tab_combined_v2, tab2, tab3, tab4 = st.tabs([
        "PIQSCA",
        "1-1: Average Expert", 
        "1-1b: Error Analysis (Raw)", 
        "1-1c: Error Analysis (Residual)",
        "Combined Figure",
        "Combined Figure V2",
        "1-2: Individual Validators", 
        "1-3: By Disorder", 
        "1-4: By Category"
    ])
    
    with tab_piqsca:
        st.markdown("### PSYCHE SCORE vs. PIQSCA")
        st.caption("Firebase에서 불러온 PIQSCA 데이터로 Validator별 Correlation 분석")
        
        # Load PIQSCA data from Firebase
        with st.spinner("Loading PIQSCA data from Firebase..."):
            piqsca_by_validator, validators_found = load_piqsca_from_firebase(root_snapshot)
        
        if piqsca_by_validator:
            st.success(f"✅ Found PIQSCA data for {len(validators_found)} validator(s): {', '.join(validators_found)}")
            
            # Show data summary
            with st.expander("🔍 PIQSCA Data Summary"):
                for validator, scores in piqsca_by_validator.items():
                    st.write(f"**{validator}**: {len(scores)} experiments")
                    # Show score distribution
                    score_values = list(scores.values())
                    if score_values:
                        st.write(f"  - Range: {min(score_values)} - {max(score_values)}")
                        st.write(f"  - Mean: {np.mean(score_values):.2f}")
                        st.write(f"  - Std: {np.std(score_values):.2f}")
            
            st.info("""
            **PIQSCA 구성:**
            - Process of the interview (1-5점)
            - Techniques (1-5점)
            - Information for diagnosis (1-5점)
            - **총점 범위: 3-15점**
            
            **데이터 출처:** Firebase `piqsca_{validator_name}_{client_num}_{exp_num}`
            """)
            
            # Generate figures for each validator
            figs_1_6 = create_piqsca_correlation_plot_firebase(psyche_scores, piqsca_by_validator)
            
            for validator, fig in figs_1_6:
                st.markdown(f"#### Validator: {validator}")
                st.pyplot(fig, use_container_width=False)
                
                add_figure_downloads(
                    fig,
                    f"Fig1-6_PIQSCA_Correlation_{validator}",
                    f"fig1_6_{sanitize_firebase_key(validator)}",
                )
                plt.close(fig)
                st.markdown("---")
        else:
            st.warning("⚠️ No PIQSCA data found in Firebase. Looking for keys like `piqsca_{validator_name}_{client_num}_{exp_num}`")
            st.info("""
            **Expected Firebase structure:**
            ```
            piqsca_임경호_6201_1121:
              process_of_the_interview: 5
              techniques: 5
              information_for_diagnosis: 5
            ```
            """)
    
    with tab1:
        st.markdown("### Figure 1-1: Average Expert Score")
        fig1_1 = create_correlation_plot_average(psyche_scores, avg_expert_scores)
        st.pyplot(fig1_1)
        
        add_figure_downloads(fig1_1, "Fig1_1_PSYCHE_Expert_Correlation_Average", "fig1_1")
        plt.close(fig1_1)
    
    with tab1b:
        st.markdown("### Figure 1-1b: Error Analysis (Top 3 Largest Errors)")
        st.caption("Expert score - PSYCHE SCORE 차이가 가장 큰 실험들을 빨간색으로 표시")
        
        if psyche_scores and avg_expert_scores:
            fig1_1b, top_3_errors = create_correlation_plot_average_with_errors(psyche_scores, avg_expert_scores)
            st.pyplot(fig1_1b)
            
            # Display top 3 error information
            st.markdown("#### 🔴 Top 3 Largest Errors")
            st.markdown("**Error = Expert score - PSYCHE SCORE**")
            
            for rank, (abs_err, err, exp, psyche, expert, model) in enumerate(top_3_errors, 1):
                client_num, exp_num = exp
                
                # Determine disorder
                disorder = DISORDER_MAP.get(client_num, "Unknown")
                disorder_name = DISORDER_NAMES.get(disorder, "Unknown")
                
                # Create detailed info
                with st.expander(f"**Rank {rank}: Error = {err:+.2f}** (|Error| = {abs_err:.2f})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Client Number", f"{client_num}")
                        st.metric("Disorder", disorder_name)
                        st.metric("Model", LABEL_MAP.get(model, model))
                    with col2:
                        st.metric("Experiment Number", f"{exp_num}")
                        st.metric("PSYCHE SCORE", f"{psyche:.2f}")
                        st.metric("Expert score", f"{expert:.2f}")
                    
                    # Error interpretation
                    if err > 0:
                        st.info(f"✅ Expert scored **higher** than PSYCHE by {err:.2f} points → PSYCHE may have underestimated")
                    else:
                        st.warning(f"⚠️ Expert scored **lower** than PSYCHE by {abs(err):.2f} points → PSYCHE may have overestimated")
            
            # Download button
            add_figure_downloads(fig1_1b, "Fig1-1b_Error_Analysis", "fig1_1b")
            plt.close(fig1_1b)
        else:
            st.warning("데이터가 없습니다.")
    
    with tab1c:
        st.markdown("### Figure 1-1c: Residual Error Analysis (Top 3 Outliers)")
        st.caption("추세선에서 가장 멀리 떨어진 점들을 빨간색으로 표시 (통계적 outlier detection)")
        
        if psyche_scores and avg_expert_scores:
            fig1_1c, top_3_residuals = create_correlation_plot_average_with_residuals(psyche_scores, avg_expert_scores)
            
            if fig1_1c:
                st.pyplot(fig1_1c)
                
                # Display top 3 residual error information
                st.markdown("#### 🔴 Top 3 Largest Residual Errors")
                st.markdown("**Residual = Actual Expert score - Predicted Expert score (from regression line)**")
                st.info("💡 **Residual error는 전체 데이터의 경향성을 고려한 편차로, 통계적으로 더 의미있는 outlier입니다.**")
                
                for rank, (abs_res, res, exp, psyche, expert, model, predicted) in enumerate(top_3_residuals, 1):
                    client_num, exp_num = exp
                    
                    # Determine disorder
                    disorder = DISORDER_MAP.get(client_num, "Unknown")
                    disorder_name = DISORDER_NAMES.get(disorder, "Unknown")
                    
                    # Create detailed info
                    with st.expander(f"**Rank {rank}: Residual = {res:+.2f}** (|Residual| = {abs_res:.2f})"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Client Number", f"{client_num}")
                            st.metric("Disorder", disorder_name)
                        with col2:
                            st.metric("Experiment Number", f"{exp_num}")
                            st.metric("Model", LABEL_MAP.get(model, model))
                        with col3:
                            st.metric("PSYCHE SCORE", f"{psyche:.2f}")
                            st.metric("Expert score", f"{expert:.2f}")
                        
                        st.markdown("---")
                        st.markdown("**📊 Residual Analysis**")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Predicted Expert score", f"{predicted:.2f}", 
                                     help="Expected score based on regression line")
                        with col2:
                            st.metric("Residual Error", f"{res:+.2f}",
                                     help="Actual - Predicted")
                        
                        # Error interpretation
                        if res > 0:
                            st.success(f"📈 Expert scored **{abs(res):.2f} points higher** than expected from the trend → Unusual positive deviation")
                        else:
                            st.warning(f"📉 Expert scored **{abs(res):.2f} points lower** than expected from the trend → Unusual negative deviation")
                        
                        # Compare with raw difference
                        raw_diff = expert - psyche
                        st.info(f"ℹ️ Raw difference (Expert - PSYCHE) = {raw_diff:+.2f} vs Residual = {res:+.2f}")
                
                # Download button
                add_figure_downloads(fig1_1c, "Fig1-1c_Residual_Error_Analysis", "fig1_1c")
                plt.close(fig1_1c)
            else:
                st.warning("회귀선을 계산할 수 없습니다 (데이터 부족).")
        else:
            st.warning("데이터가 없습니다.")
    
    with tab_combined:
        st.markdown("### Combined Figure: Validator, Disorder, and Category Analysis")
        st.caption("(a) Validator-specific (2×3), (b) Disease-specific (1×3), (c) Category-specific (1×3)")
        
        if element_scores_psyche and element_scores_expert:
            psyche_category_scores, expert_category_scores = calculate_category_scores(
                element_scores_psyche, element_scores_expert
            )
            
            fig_combined = create_combined_correlation_figure(
                psyche_scores, avg_expert_scores, expert_data,
                psyche_category_scores, expert_category_scores
            )
            st.pyplot(fig_combined)
            
            add_figure_downloads(fig_combined, "Fig1_Combined_Correlation_Analysis", "fig_combined")
            plt.close(fig_combined)
        else:
            st.warning("Element-level 데이터가 없습니다. Category별 분석을 위해서는 element 점수가 필요합니다.")
    
    with tab_combined_v2:
        st.markdown("### Combined Figure Version 2: Validator, Disorder, and Category Analysis")
        st.caption("(a) Validator-specific (2×3), (b) Disease-specific (1×3), (c) Category-specific (1×3)")
        st.info("🔧 Version 2 - 출력 테스트용 복제 버전")
        
        if element_scores_psyche and element_scores_expert:
            psyche_category_scores, expert_category_scores = calculate_category_scores(
                element_scores_psyche, element_scores_expert
            )
            
            fig_combined_v2 = create_combined_correlation_figure_v2(
                psyche_scores, avg_expert_scores, expert_data,
                psyche_category_scores, expert_category_scores
            )
            st.pyplot(fig_combined_v2)
            
            add_figure_downloads(fig_combined_v2, "Fig1_Combined_Correlation_Analysis_V2", "fig_combined_v2")
            plt.close(fig_combined_v2)
        else:
            st.warning("Element-level 데이터가 없습니다. Category별 분석을 위해서는 element 점수가 필요합니다.")
    
    with tab2:
        st.markdown("### Figure 1-2: Individual Validators")
        fig1_2 = create_correlation_plot_by_validator(psyche_scores, expert_data)
        st.pyplot(fig1_2)
        
        add_figure_downloads(fig1_2, "Fig1_2_PSYCHE_Expert_Correlation_Validators", "fig1_2")
        plt.close(fig1_2)
    
    with tab3:
        st.markdown("### Figure 1-3: By Disorder")
        fig1_3 = create_correlation_plot_by_disorder(psyche_scores, avg_expert_scores)
        st.pyplot(fig1_3)
        
        add_figure_downloads(fig1_3, "Fig1_3_PSYCHE_Expert_Correlation_Disorders", "fig1_3")
        plt.close(fig1_3)
    
    with tab4:
        st.subheader("Figure 1-4: Category-Level Analysis")
        st.caption("Subjective, Impulsivity, MFC-Behavior별 correlation 분석")
        
        if element_scores_psyche and element_scores_expert:
            # Calculate category scores
            psyche_category_scores, expert_category_scores = calculate_category_scores(
                element_scores_psyche, element_scores_expert
            )
            
            fig1_4 = create_correlation_plot_by_category(psyche_category_scores, expert_category_scores)
            st.pyplot(fig1_4)
            
            add_figure_downloads(fig1_4, "Fig1-4_Category_Level_Analysis", "fig1_4")
            plt.close(fig1_4)
        else:
            st.warning("Element-level 데이터가 없습니다. Category별 분석을 위해서는 element 점수가 필요합니다.")
    
    st.markdown("---")
    
    # ================================
    # Combined Figure 1×4: PSYCHE-Expert, PIQSCA, Weight Correlations
    # ================================
    st.markdown("## 🎨 Combined Figure 1×4: Comprehensive Analysis")
    st.caption("(a) PSYCHE vs. Expert | (b) PSYCHE vs. PIQSCA | (c) Equal weights | (d) Fixed weights")
    
    if element_scores_psyche and element_scores_expert:
        # Calculate weight correlations (cached)
        correlation_equal, correlation_fixed, weight_range = calculate_weight_correlations(
            element_scores_psyche, element_scores_expert
        )
        
        # Load PIQSCA data from Firebase for combined figure
        with st.spinner("Loading PIQSCA data for combined figure..."):
            piqsca_by_validator, validators_found = load_piqsca_from_firebase(root_snapshot)
        
        # Use single validator's PIQSCA data (configured at top of file)
        piqsca_single = {}
        if piqsca_by_validator and PIQSCA_VALIDATOR in piqsca_by_validator:
            piqsca_single = piqsca_by_validator[PIQSCA_VALIDATOR]
            st.info(f"ℹ️ Combined Figure 1×4에서 **{PIQSCA_VALIDATOR}**의 PIQSCA 데이터를 사용합니다. (상단 PIQSCA_VALIDATOR 설정에서 변경 가능)")
        else:
            available = ', '.join(validators_found) if validators_found else '없음'
            st.warning(f"⚠️ '{PIQSCA_VALIDATOR}'의 PIQSCA 데이터를 찾을 수 없습니다. 사용 가능한 validator: {available}")
        
        if piqsca_single and st.button("Generate Combined Figure 1×4", key="combined_1x4"):
            with st.spinner("Generating combined figure..."):
                fig_combined_1x4 = create_combined_figure_1x4(
                    psyche_scores, avg_expert_scores, piqsca_single,
                    correlation_equal, correlation_fixed, weight_range
                )
                st.pyplot(fig_combined_1x4)
                
                add_figure_downloads(fig_combined_1x4, "Fig_Combined_1x4_Comprehensive_Analysis", "fig_combined_1x4")
                plt.close(fig_combined_1x4)
    else:
        st.warning("Element-level 데이터가 필요합니다.")
    
    st.markdown("---")
    
    # ================================
    # Figure 3: SP Validation Heatmap
    # ================================
    st.markdown("## 🔵 Figure 3: SP Validation Heatmap (Quantitative)")
    st.caption("Element별 Conformity 평균 - Appropriate/Inappropriate 평가")
    
    if sp_conformity_data:
        fig3 = create_sp_validation_heatmap(sp_conformity_data)
        if fig3:
            st.pyplot(fig3)
            
            add_figure_downloads(fig3, "Fig3_SP_Validation_Heatmap_Quantitative", "fig3")
            plt.close(fig3)
        else:
            st.warning("Failed to create SP validation heatmap.")
    else:
        st.info("SP validation 데이터가 없습니다. 02_가상환자에_대한_전문가_검증.py에서 검증을 완료해주세요.")
    
    st.markdown("---")
    
    # ================================
    # Figure 4: SP Qualitative Heatmap
    # ================================
    st.markdown("## 🟣 Figure 4: SP Qualitative Heatmap (Likert Scale)")
    st.caption("Element별 평균 Likert Rating (1-5) - 정성 평가")
    
    # Load SP qualitative data
    with st.spinner("SP Qualitative 데이터 로딩 중..."):
        sp_qualitative_data = load_sp_qualitative_data(root_snapshot)
    
    if sp_qualitative_data:
        st.success(f"✅ {len(sp_qualitative_data)} cases의 정성 평가 데이터 로드 완료")
        
        # Show data summary
        with st.expander("🔍 데이터 요약"):
            for case, elem_dict in sp_qualitative_data.items():
                st.write(f"**{case}**: {len(elem_dict)} elements")
                # Show sample ratings
                sample_items = list(elem_dict.items())[:3]
                for elem, rating in sample_items:
                    st.write(f"  - {elem}: {rating:.2f}")
        
        fig4 = create_sp_qualitative_heatmap(sp_qualitative_data)
        if fig4:
            st.pyplot(fig4)
            
            add_figure_downloads(fig4, "Fig4_SP_Qualitative_Heatmap_Likert", "fig4")
            plt.close(fig4)
        else:
            st.warning("Failed to create SP qualitative heatmap.")
    else:
        st.info("SP 정성 평가 데이터가 없습니다. 02_가상환자에_대한_전문가_검증.py에서 검증을 완료해주세요.")
    
    st.markdown("---")
    
    # ================================
    # Figure 2: Weight-Correlation Analysis
    # ================================
    st.markdown("## 🔥 Figure 2: Weight-Correlation Analysis")
    st.caption("가중치 변화에 따른 correlation 변화 분석 (생성에 시간이 걸립니다)")
    
    if element_scores_psyche and element_scores_expert:
        # Check if there's actual data (exclude _debug_keys)
        psyche_count = len([k for k in element_scores_psyche.keys() if k != '_debug_keys'])
        expert_count = sum(len(v) for v in element_scores_expert.values())
        
        st.info(f"PSYCHE element data: {psyche_count} experiments, Expert element data: {expert_count} total entries")
        
        with st.spinner("Weight-Correlation Heatmap 생성 중... (약 1-2분 소요)"):
            fig2, stats_info = create_weight_correlation_heatmaps(element_scores_psyche, element_scores_expert)
        
        # Display max/min correlation info
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"**📈 Maximum Correlation (Equal weights)**\n\n"
                      f"- **r = {stats_info['max_corr']:.4f}**\n"
                      f"- Weights: (w_Impulsivity={stats_info['max_weights'][0]:.1f}, "
                      f"w_Behavior={stats_info['max_weights'][1]:.1f}, w_Subjective={stats_info['max_weights'][2]:.1f})")
        with col2:
            st.info(f"**📉 Minimum Correlation (Equal weights)**\n\n"
                   f"- **r = {stats_info['min_corr']:.4f}**\n"
                   f"- Weights: (w_Impulsivity={stats_info['min_weights'][0]:.1f}, "
                   f"w_Behavior={stats_info['min_weights'][1]:.1f}, w_Subjective={stats_info['min_weights'][2]:.1f})")
        
        st.pyplot(fig2)
        
        add_figure_downloads(fig2, "Fig2_Weight_Correlation_Heatmaps", "fig2")
        plt.close(fig2)
    else:
        st.warning("Element-level scores not available. Cannot generate weight correlation heatmaps.")

if __name__ == "__main__":
    main()
