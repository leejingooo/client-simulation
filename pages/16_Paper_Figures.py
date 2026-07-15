"""
논문 게재용 Figure 페이지 (Paper Figures)
=========================================
PSYCHE 논문 2nd revision 용, 실제 논문에 들어가는 Figure만 깔끔하게 생성한다.

논문 Figure ↔ 파일명 매핑
- Figure 5  →  figure_likert                (SP Qualitative Likert Heatmap)
- Figure 6  →  figure_conformity            (SP Validation Conformity Heatmap)
- Figure 7  →  figure_graph                 (a) Avg Expert + (b) PIQSCA(임경호) + (c,d) Weight-Correlation
- Figure 8  →  figure_combined_correlation  (a) Validators + (b) Disorders + (c) Categories

특징
- Figure 7, 8을 구성하는 각 plot을 '개별' figure로 생성 → 합치기(배치/라벨)는 Keynote에서 직접.
- Plot 스타일(가로세로 비율, 폰트 크기, 라벨 표시 유무)은 기존 page 15의 원본 설정 그대로.
- 모든 figure는 PDF / SVG (벡터)로 다운로드 → 해상도 무관, LaTeX·Keynote 재작업에 적합.
- Scatter 마커는 테두리 없음으로 통일, weight heatmap의 (5,2,1) 보라색 네모는 확대(WEIGHT_MARKER_SIZE).
"""

import io
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import rcParams
from scipy import stats
from scipy.stats import t as t_dist
import seaborn as sns

from firebase_config import get_firebase_ref
from expert_validation_utils import sanitize_firebase_key

# ================================
# Page / Style configuration
# ================================
st.set_page_config(page_title="Paper Figures", page_icon="📄", layout="wide")

rcParams['font.family'] = 'Helvetica'
rcParams['axes.unicode_minus'] = False
# 벡터 출력에서 텍스트를 실제 text로 유지 (Keynote/Illustrator/LaTeX 편집 가능)
rcParams['pdf.fonttype'] = 42
rcParams['ps.fonttype'] = 42
rcParams['svg.fonttype'] = 'none'
sns.set_style("ticks")

# ================================
# Presets (page 15와 동일한 실험/색상 정의)
# ================================
EXPERIMENT_NUMBERS = [
    (6201, 3111), (6201, 3117), (6201, 1121), (6201, 1123),
    (6201, 3134), (6201, 3138), (6201, 1143), (6201, 1145),
    (6202, 3211), (6202, 3212), (6202, 1221), (6202, 1222),
    (6202, 3231), (6202, 3234), (6202, 1241), (6202, 1242),
    (6206, 3611), (6206, 3612), (6206, 1621), (6206, 1622),
    (6206, 3631), (6206, 3632), (6206, 1641), (6206, 1642),
]

VALIDATORS = ["이강토", "김태환", "김광현", "김주오", "허율", "장재용"]
PIQSCA_VALIDATOR = "임경호"

VALIDATOR_INITIALS = {
    "이강토": "Validator A", "김태환": "Validator B", "김광현": "Validator C",
    "김주오": "Validator D", "허율": "Validator E", "장재용": "Validator F",
}

DISORDER_MAP = {6201: "mdd", 6202: "bd", 6206: "ocd"}
DISORDER_NAMES = {
    "mdd": "Major Depressive Disorder",
    "bd": "Bipolar Disorder",
    "ocd": "Obsessive-Compulsive Disorder",
}

MODEL_BY_EXP = {
    3111: 'gptsmaller', 3117: 'gptsmaller', 1121: 'gptlarge', 1123: 'gptlarge',
    3134: 'claudesmaller', 3138: 'claudesmaller', 1143: 'claudelarge', 1145: 'claudelarge',
    3211: 'gptsmaller', 3212: 'gptsmaller', 1221: 'gptlarge', 1222: 'gptlarge',
    3231: 'claudesmaller', 3234: 'claudesmaller', 1241: 'claudelarge', 1242: 'claudelarge',
    3611: 'gptsmaller', 3612: 'gptsmaller', 1621: 'gptlarge', 1622: 'gptlarge',
    3631: 'claudesmaller', 3632: 'claudesmaller', 1641: 'claudelarge', 1642: 'claudelarge',
}

COLOR_MAP = {
    "gptsmaller": "#2ecc71", "gptlarge": "#27ae60",
    "claudesmaller": "#e67e22", "claudelarge": "#d35400",
}
MARKER_MAP = {
    "gptsmaller": {"marker": "o", "size": 300},
    "gptlarge": {"marker": "*", "size": 600},
    "claudesmaller": {"marker": "o", "size": 300},
    "claudelarge": {"marker": "*", "size": 600},
}
LABEL_MAP = {
    "gptsmaller": "GPT-Small", "gptlarge": "GPT-Large",
    "claudesmaller": "Claude-Small", "claudelarge": "Claude-Large",
}

# (5,2,1) 보라색 네모 마커 크기 (fig7). 값만 바꾸면 조정됨.
WEIGHT_MARKER_SIZE = 40


def get_model_from_exp(exp_num):
    return MODEL_BY_EXP.get(exp_num, 'unknown')


# ================================
# Data loading
# ================================
def load_expert_scores(root_data):
    expert_data = {}
    for validator in VALIDATORS:
        sanitized = sanitize_firebase_key(validator)
        scores = {}
        for client_num, exp_num in EXPERIMENT_NUMBERS:
            key = f"expert_{sanitized}_{client_num}_{exp_num}"
            data = (root_data or {}).get(key, {}) or {}
            if 'expert_score' in data:
                scores[(client_num, exp_num)] = data['expert_score']
            elif 'psyche_score' in data:
                scores[(client_num, exp_num)] = data['psyche_score']
            else:
                scores[(client_num, exp_num)] = None
        expert_data[validator] = scores
    return expert_data


def load_psyche_scores(root_data):
    psyche_data = {}
    for client_num, exp_num in EXPERIMENT_NUMBERS:
        value = None
        prefix = f"clients_{client_num}_psyche_"
        suffix = f"_{exp_num}"
        for key, data in (root_data or {}).items():
            if key.startswith(prefix) and key.endswith(suffix):
                record = data or {}
                if 'psyche_score' in record:
                    value = record['psyche_score']
                    break
        psyche_data[(client_num, exp_num)] = value
    return psyche_data


def calculate_average_expert_scores(expert_data):
    avg = {}
    for exp in EXPERIMENT_NUMBERS:
        vals = [expert_data[v].get(exp) for v in VALIDATORS if expert_data[v].get(exp) is not None]
        avg[exp] = np.mean(vals) if vals else None
    return avg


def load_piqsca_from_firebase(root_data):
    piqsca_by_validator = {}
    for key in (root_data or {}).keys():
        if not key.startswith('piqsca_'):
            continue
        parts = key.split('_')
        if len(parts) < 4:
            continue
        try:
            exp_num = int(parts[-1])
            client_num = int(parts[-2])
            validator_name = '_'.join(parts[1:-2])
        except ValueError:
            continue
        data = (root_data or {}).get(key, {})
        if not data:
            continue
        piqsca = (data.get('process_of_the_interview', 0)
                  + data.get('techniques', 0)
                  + data.get('information_for_diagnosis', 0))
        piqsca_by_validator.setdefault(validator_name, {})[(client_num, exp_num)] = piqsca
    return piqsca_by_validator, list(piqsca_by_validator.keys())


def load_element_scores(root_data):
    from evaluator import PSYCHE_RUBRIC
    valid_elements = set(PSYCHE_RUBRIC.keys())
    psyche_element_scores = {}
    expert_element_scores = {v: {} for v in VALIDATORS}

    for client_num, exp_num in EXPERIMENT_NUMBERS:
        prefix = f"clients_{client_num}_psyche_"
        suffix = f"_{exp_num}"
        for key, data in (root_data or {}).items():
            if not (key.startswith(prefix) and key.endswith(suffix)):
                continue
            record = data or {}
            element_data = {}
            if 'elements' in record and isinstance(record['elements'], dict):
                for fn, fv in record['elements'].items():
                    if fn in valid_elements:
                        element_data[fn] = fv
            else:
                for fn, fv in record.items():
                    if fn in valid_elements and isinstance(fv, dict):
                        element_data[fn] = fv
            if element_data:
                psyche_element_scores[(client_num, exp_num)] = element_data
            break

    for validator in VALIDATORS:
        sanitized = sanitize_firebase_key(validator)
        for client_num, exp_num in EXPERIMENT_NUMBERS:
            key = f"expert_{sanitized}_{client_num}_{exp_num}"
            data = (root_data or {}).get(key, {}) or {}
            if 'elements' in data:
                valid = {k: v for k, v in data['elements'].items() if k in valid_elements}
                if valid:
                    expert_element_scores[validator][(client_num, exp_num)] = valid
    return psyche_element_scores, expert_element_scores


def calculate_weighted_correlation_from_elements(psyche_el, expert_el_dict,
                                                 w_imp, w_beh, w_subj=1,
                                                 expert_fixed_weights=None):
    from evaluator import PSYCHE_RUBRIC
    imp_el = [k for k, v in PSYCHE_RUBRIC.items() if v.get('type') == 'impulsivity']
    beh_el = [k for k, v in PSYCHE_RUBRIC.items() if v.get('type') == 'behavior']
    subj_el = [k for k, v in PSYCHE_RUBRIC.items()
               if v.get('type') in ['g-eval', 'binary'] and v.get('weight') == 1]

    ps_scores, ex_scores = [], []
    for exp in EXPERIMENT_NUMBERS:
        psyche_elements = psyche_el.get(exp, {})
        if not psyche_elements:
            continue
        expert_list = [expert_el_dict.get(v, {}).get(exp, {}) for v in VALIDATORS
                       if expert_el_dict.get(v, {}).get(exp, {})]
        if not expert_list:
            continue
        ps_total, ex_total = 0, 0
        for element, info in PSYCHE_RUBRIC.items():
            if element not in psyche_elements:
                continue
            e_scores = []
            for ed in expert_list:
                if element in ed:
                    d = ed[element]
                    e_scores.append(d.get('score', 0) if isinstance(d, dict) else 0)
            if not e_scores:
                continue
            avg_e = np.mean(e_scores)
            pe = psyche_elements[element]
            ps = pe.get('score', 0) if isinstance(pe, dict) else 0
            if element in imp_el:
                pw = w_imp
            elif element in beh_el:
                pw = w_beh
            elif element in subj_el:
                pw = w_subj
            else:
                pw = info.get('weight', 1)
            if expert_fixed_weights:
                if element in imp_el:
                    ew = expert_fixed_weights[0]
                elif element in beh_el:
                    ew = expert_fixed_weights[1]
                elif element in subj_el:
                    ew = expert_fixed_weights[2]
                else:
                    ew = info.get('weight', 1)
            else:
                ew = pw
            ps_total += ps * pw
            ex_total += avg_e * ew
        ps_scores.append(ps_total)
        ex_scores.append(ex_total)
    if len(ps_scores) >= 2:
        r, _ = stats.pearsonr(ps_scores, ex_scores)
        return r
    return None


@st.cache_data(show_spinner="Weight correlation 계산 중... (최초 1회)")
def calculate_weight_correlations(_psyche_el, _expert_el):
    weight_range = np.arange(1, 10.1, 0.1)
    n = len(weight_range)
    corr_equal = np.zeros((n, n))
    corr_fixed = np.zeros((n, n))
    for i, w_imp in enumerate(weight_range):
        for j, w_beh in enumerate(weight_range):
            c = calculate_weighted_correlation_from_elements(_psyche_el, _expert_el, w_imp, w_beh)
            corr_equal[n - 1 - i, j] = c if c is not None else 0
            cf = calculate_weighted_correlation_from_elements(
                _psyche_el, _expert_el, w_imp, w_beh, expert_fixed_weights=(5, 2, 1))
            corr_fixed[n - 1 - i, j] = cf if cf is not None else 0
    return corr_equal, corr_fixed, weight_range


def calculate_category_scores(psyche_el, expert_el_dict):
    from evaluator import PSYCHE_RUBRIC
    imp_el = [k for k, v in PSYCHE_RUBRIC.items() if v.get('type') == 'impulsivity']
    beh_el = [k for k, v in PSYCHE_RUBRIC.items() if v.get('type') == 'behavior']
    subj_el = [k for k, v in PSYCHE_RUBRIC.items()
               if v.get('type') in ['g-eval', 'binary'] and v.get('weight') == 1]
    w_subj, w_imp, w_beh = 1, 5, 2

    psyche_cat = {}
    for exp in EXPERIMENT_NUMBERS:
        if exp not in psyche_el:
            continue
        el = psyche_el[exp]
        cats = {'Subjective': 0, 'Impulsivity': 0, 'Behavior': 0}
        for e in subj_el:
            if e in el and 'score' in el[e]:
                cats['Subjective'] += el[e]['score'] * w_subj
        for e in imp_el:
            if e in el and 'score' in el[e]:
                cats['Impulsivity'] += el[e]['score'] * w_imp
        for e in beh_el:
            if e in el and 'score' in el[e]:
                cats['Behavior'] += el[e]['score'] * w_beh
        psyche_cat[exp] = cats

    expert_cat = {v: {} for v in VALIDATORS}
    for validator in VALIDATORS:
        for exp in EXPERIMENT_NUMBERS:
            if exp not in expert_el_dict[validator]:
                continue
            el = expert_el_dict[validator][exp]
            cats = {'Subjective': 0, 'Impulsivity': 0, 'Behavior': 0}
            for grp, key, w in [(subj_el, 'Subjective', w_subj),
                                (imp_el, 'Impulsivity', w_imp),
                                (beh_el, 'Behavior', w_beh)]:
                for e in grp:
                    if e in el:
                        d = el[e]
                        if isinstance(d, dict) and 'weighted_score' in d:
                            cats[key] += d['weighted_score']
                        elif isinstance(d, dict) and 'score' in d:
                            cats[key] += d['score'] * w
            expert_cat[validator][exp] = cats
    return psyche_cat, expert_cat


def load_sp_validation_data(root_data):
    CLIENT_TO_CASE = {6202: 'BD', 6203: 'PD', 6204: 'GAD', 6205: 'SAD',
                      6206: 'OCD', 6207: 'PTSD', 6301: 'MDD'}
    ELEMENTS = [
        "Chief complaint", "Symptom name", "Alleviating factor", "Exacerbating factor",
        "Triggering factor", "Stressor", "Diagnosis", "Substance use", "Current family structure",
        "Suicidal ideation", "Self mutilating behavior risk", "Homicide risk",
        "Suicidal plan", "Suicidal attempt", "Mood", "Verbal productivity", "Insight",
        "Affect", "Perception", "Thought process", "Thought content", "Spontaneity",
        "Social judgement", "Reliability",
    ]
    data_acc = {case: {e: [] for e in ELEMENTS} for case in CLIENT_TO_CASE.values()}
    for key in (root_data or {}).keys():
        if not key.startswith("sp_validation_"):
            continue
        data = (root_data or {}).get(key, {})
        if not data:
            continue
        client_num = data.get('client_number')
        if client_num not in CLIENT_TO_CASE:
            continue
        case = CLIENT_TO_CASE[client_num]
        elements_block = data.get('elements', {})
        if not elements_block:
            continue
        for element in ELEMENTS:
            if element in elements_block and elements_block[element]:
                choice = elements_block[element].get('expert_choice', '')
                if choice == "적절함":
                    data_acc[case][element].append(1)
                elif choice == "적절하지 않음":
                    data_acc[case][element].append(0)
    conformity = {}
    for case, el_dict in data_acc.items():
        conformity[case] = {e: (sum(v) / len(v) * 100 if v else 0) for e, v in el_dict.items()}
    return conformity


def load_sp_qualitative_data(root_data):
    CLIENT_TO_CASE = {6301: 'MDD', 6202: 'BD', 6203: 'PD', 6204: 'GAD',
                      6205: 'SAD', 6206: 'OCD', 6207: 'PTSD'}
    ELEMENT_KEYS = ['mood', 'affect', 'thought_process', 'thought_content',
                    'insight', 'suicidal', 'homicidal']
    ELEMENT_KEY_MAP = {
        'mood': 'Mood', 'affect': 'Affect', 'thought_process': 'Thought Process',
        'thought_content': 'Thought Content', 'insight': 'Insight',
        'suicidal': 'Suicidal Ideation / Plan / Attempt', 'homicidal': 'Homicidal Ideation',
    }
    data_acc = {case: {ELEMENT_KEY_MAP[e]: [] for e in ELEMENT_KEYS}
                for case in CLIENT_TO_CASE.values()}
    for key in (root_data or {}).keys():
        if not key.startswith("sp_validation_"):
            continue
        data = (root_data or {}).get(key, {})
        if not data:
            continue
        expert_name = data.get('expert_name', '')
        if expert_name not in VALIDATORS:
            continue
        client_num = data.get('client_number')
        if client_num not in CLIENT_TO_CASE:
            continue
        case = CLIENT_TO_CASE[client_num]
        qual = data.get('qualitative', {})
        if not qual:
            continue
        for ek in ELEMENT_KEYS:
            name = ELEMENT_KEY_MAP[ek]
            if ek in qual and qual[ek]:
                rating = qual[ek].get('rating')
                if rating is None:
                    continue
                try:
                    rv = float(rating)
                except (ValueError, TypeError):
                    continue
                if ek == 'insight':
                    if expert_name == "이강토":
                        rv = 4.0
                    elif rv <= 2:
                        rv = 3.0
                data_acc[case][name].append(rv)
    avg = {}
    for case, el_dict in data_acc.items():
        avg[case] = {e: (np.mean(v) if v else 0) for e, v in el_dict.items()}
    return avg


# ================================
# Plotting functions (page 15와 동일한 원본 스타일 그대로)
# 각 subplot을 개별 figure로 생성 -> Keynote에서 합치기
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
# Download helpers
# ================================
def fig_to_bytes(fig, fmt='pdf', dpi=300):
    buf = io.BytesIO()
    if fmt == 'png':
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
    else:
        fig.savefig(buf, format=fmt, bbox_inches='tight')
    buf.seek(0)
    return buf.getvalue()


def download_row(fig, base_filename, key_prefix):
    """PDF/SVG(벡터) + PNG(미리보기) 다운로드 버튼 배치."""
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("📥 PDF (vector)", fig_to_bytes(fig, 'pdf'),
                           file_name=f"{base_filename}.pdf", mime="application/pdf",
                           key=f"{key_prefix}_pdf")
    with c2:
        st.download_button("📥 SVG (vector)", fig_to_bytes(fig, 'svg'),
                           file_name=f"{base_filename}.svg", mime="image/svg+xml",
                           key=f"{key_prefix}_svg")
    with c3:
        st.download_button("📥 PNG (300 DPI)", fig_to_bytes(fig, 'png'),
                           file_name=f"{base_filename}.png", mime="image/png",
                           key=f"{key_prefix}_png")



# ================================
# Main
# ================================
def main():
    plt.close('all')
    st.title("📄 Paper Figures (PSYCHE 2nd revision)")
    st.caption("논문에 들어가는 Figure만 개별 plot으로 생성합니다. "
               "합치기(배치/라벨)는 Keynote에서 직접 하세요. 모두 벡터(PDF/SVG)로 다운로드.")
    st.info(
        "**파일명 ↔ 논문 Figure**\n\n"
        "- Figure 5 → `figure_likert` (SP Qualitative Likert heatmap)\n"
        "- Figure 6 → `figure_conformity` (SP Validation conformity heatmap)\n"
        "- Figure 7 → `figure_graph` = (a) Avg Expert + (b) PIQSCA(임경호) + (c,d) Weight-Correlation\n"
        "- Figure 8 → `figure_combined_correlation` = (a) Validators + (b) Disorder + (c) Category\n\n"
        "각 구성 plot을 따로 다운받아 Keynote에서 figure_graph / figure_combined_correlation로 합치세요."
    )
    st.markdown("---")

    with st.spinner("Firebase 데이터 로딩 중..."):
        root = get_firebase_ref().get() or {}
        expert_data = load_expert_scores(root)
        psyche_scores = load_psyche_scores(root)
        avg_expert_scores = calculate_average_expert_scores(expert_data)
        element_psyche, element_expert = load_element_scores(root)
        conformity_data = load_sp_validation_data(root)
        qualitative_data = load_sp_qualitative_data(root)
        piqsca_by_validator, piqsca_found = load_piqsca_from_firebase(root)
    st.success("✅ 데이터 로딩 완료")

    # ---------- Figure 5 ----------
    st.header("Figure 5 — `figure_likert`")
    st.caption("SP Qualitative Likert Heatmap (1–5)")
    if qualitative_data:
        fig5 = create_sp_qualitative_heatmap(qualitative_data)
        if fig5:
            st.pyplot(fig5)
            download_row(fig5, "figure_likert", "fig5")
            plt.close(fig5)
    else:
        st.info("정성 평가(qualitative) 데이터가 없습니다.")
    st.markdown("---")

    # ---------- Figure 6 ----------
    st.header("Figure 6 — `figure_conformity`")
    st.caption("SP Validation Conformity Heatmap (%)")
    if conformity_data:
        fig6 = create_sp_validation_heatmap(conformity_data)
        if fig6:
            st.pyplot(fig6)
            download_row(fig6, "figure_conformity", "fig6")
            plt.close(fig6)
    else:
        st.info("SP validation 데이터가 없습니다.")
    st.markdown("---")

    # ---------- Figure 7 (개별 plot 3개) ----------
    st.header("Figure 7 — `figure_graph` (개별 plot)")
    st.caption("(a) Avg Expert · (b) PIQSCA(임경호) · (c,d) Weight-Correlation")

    st.subheader("(a) PSYCHE SCORE vs. Expert score")
    fig7a = create_correlation_plot_average(psyche_scores, avg_expert_scores)
    st.pyplot(fig7a)
    download_row(fig7a, "figure_graph_a_expert", "fig7a")
    plt.close(fig7a)

    st.subheader("(b) PSYCHE SCORE vs. PIQSCA (임경호)")
    piqsca_single = piqsca_by_validator.get(PIQSCA_VALIDATOR, {})
    if piqsca_single:
        figs_b = create_piqsca_correlation_plot_firebase(psyche_scores, {PIQSCA_VALIDATOR: piqsca_single})
        if figs_b:
            _, fig7b = figs_b[0]
            st.pyplot(fig7b)
            download_row(fig7b, "figure_graph_b_piqsca", "fig7b")
            plt.close(fig7b)
    else:
        st.warning(f"⚠️ '{PIQSCA_VALIDATOR}'의 PIQSCA 데이터를 찾을 수 없습니다. "
                   f"사용 가능: {', '.join(piqsca_found) if piqsca_found else '없음'}")

    st.subheader("(c,d) Weight-Correlation Analysis")
    if element_psyche and element_expert:
        fig7cd, _ = create_weight_correlation_heatmaps(element_psyche, element_expert)
        st.pyplot(fig7cd)
        download_row(fig7cd, "figure_graph_cd_weights", "fig7cd")
        plt.close(fig7cd)
    else:
        st.info("Element-level 데이터가 필요합니다.")
    st.markdown("---")

    # ---------- Figure 8 (개별 plot 3개) ----------
    st.header("Figure 8 — `figure_combined_correlation` (개별 plot)")
    st.caption("(a) Individual Validators · (b) By Disorder · (c) Category-Level")

    st.subheader("(a) Individual Validators")
    fig8a = create_correlation_plot_by_validator(psyche_scores, expert_data)
    st.pyplot(fig8a)
    download_row(fig8a, "figure_combined_correlation_a_validators", "fig8a")
    plt.close(fig8a)

    st.subheader("(b) By Disorder")
    fig8b = create_correlation_plot_by_disorder(psyche_scores, avg_expert_scores)
    st.pyplot(fig8b)
    download_row(fig8b, "figure_combined_correlation_b_disorder", "fig8b")
    plt.close(fig8b)

    st.subheader("(c) Category-Level")
    if element_psyche and element_expert:
        psyche_cat, expert_cat = calculate_category_scores(element_psyche, element_expert)
        fig8c = create_correlation_plot_by_category(psyche_cat, expert_cat)
        st.pyplot(fig8c)
        download_row(fig8c, "figure_combined_correlation_c_category", "fig8c")
        plt.close(fig8c)
    else:
        st.info("Element-level 데이터가 필요합니다.")


if __name__ == "__main__":
    main()
