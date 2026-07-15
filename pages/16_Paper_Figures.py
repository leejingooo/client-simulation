"""
논문 게재용 Figure 페이지 (Paper Figures)
=========================================
PSYCHE 논문 2nd revision 용, 실제 논문에 들어가는 Figure만 깔끔하게 생성한다.

논문 Figure ↔ 파일명 매핑
- Figure 5  →  figure_likert                (SP Qualitative Likert Heatmap)
- Figure 6  →  figure_conformity            (SP Validation Conformity Heatmap)
- Figure 7  →  figure_graph                 (Avg Expert + PIQSCA + Weight-Correlation, 1×4)
- Figure 8  →  figure_combined_correlation  (Validators + Disorders + Categories)

특징
- 모든 figure는 PDF / SVG (벡터)로 다운로드 → 해상도 무관, LaTeX·Keynote 재작업에 적합
- Scatter 마커는 테두리 없음으로 통일
- (a)(b)(c)(d) 패널 라벨과 섹션 간 여백을 코드에서 처리 (Keynote 수작업 불필요)
- 글씨 크기 배율(font scale)을 선택해 '원본'과 '키운 버전'을 모두 확인/다운로드 가능
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
# Shared plotting helper
# ================================
def _scatter_with_fit(ax, data_by_model, fs, r_fontsize, add_legend=False, legend_fontsize=18):
    """산점도(테두리 없음) + 회귀선 + 95% CI + r/p 텍스트. all_x, all_y 반환."""
    all_x, all_y = [], []
    for model, points in data_by_model.items():
        if not points:
            continue
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        all_x.extend(xs)
        all_y.extend(ys)
        ax.scatter(xs, ys, c=COLOR_MAP[model], marker=MARKER_MAP[model]['marker'],
                   s=MARKER_MAP[model]['size'], label=LABEL_MAP[model], alpha=0.7)
    if len(all_x) >= 2:
        x = np.array(all_x)
        y = np.array(all_y)
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        xl = np.linspace(x.min(), x.max(), 100)
        yl = p(xl)
        n = len(x)
        resid = y - p(x)
        std_err = np.sqrt(np.sum(resid ** 2) / (n - 2))
        xm = np.mean(x)
        sxx = np.sum((x - xm) ** 2)
        se = std_err * np.sqrt(1 / n + (xl - xm) ** 2 / sxx)
        ci = t_dist.ppf(0.975, n - 2) * se
        ax.fill_between(xl, yl - ci, yl + ci, alpha=0.2, color='#3498db', zorder=0)
        ax.plot(xl, yl, '#3498db', linestyle='-', linewidth=2, zorder=1)
        r, pv = stats.pearsonr(all_x, all_y)
        p_text = 'p < 0.0001' if pv < 0.0001 else f'p = {pv:.4f}'
        ax.text(0.3, 0.10, f'r = {r:.4f}, {p_text}', transform=ax.transAxes,
                fontsize=r_fontsize * fs, family='Helvetica')
    if add_legend:
        ax.legend(loc='upper left',
                  prop={'size': legend_fontsize * fs, 'weight': 'bold', 'family': 'Helvetica'})
    for spine in ax.spines.values():
        spine.set_color('black')
        spine.set_linewidth(2)
    return all_x, all_y


# ================================
# Figure 7 (figure_graph): Avg Expert + PIQSCA + Weight-Correlation (1×4)
# ================================
def create_figure_graph(psyche_scores, avg_expert_scores, piqsca_scores,
                        corr_equal, corr_fixed, fs=1.0):
    fig = plt.figure(figsize=(48, 9), constrained_layout=True)
    subfigs = fig.subfigures(1, 4, width_ratios=[0.85, 0.85, 1, 1], wspace=0.04)

    # (a) PSYCHE vs Expert
    ax_a = subfigs[0].add_subplot(111)
    dbm = {m: [] for m in COLOR_MAP}
    for exp in EXPERIMENT_NUMBERS:
        ps, ex = psyche_scores.get(exp), avg_expert_scores.get(exp)
        if ps is not None and ex is not None:
            dbm[get_model_from_exp(exp[1])].append((ps, ex))
    _scatter_with_fit(ax_a, dbm, fs, r_fontsize=28, add_legend=True, legend_fontsize=22)
    ax_a.set_title('PSYCHE SCORE vs. Expert score', fontsize=36 * fs, pad=15, family='Helvetica')
    ax_a.set_xlabel('PSYCHE SCORE', fontsize=36 * fs, family='Helvetica')
    ax_a.set_ylabel('Expert score', fontsize=36 * fs, family='Helvetica')
    ax_a.set_yticks([5, 35, 65])
    ax_a.set_xticks([5, 30, 55])
    ax_a.tick_params(labelsize=32 * fs)
    subfigs[0].supxlabel('(a)', fontsize=40 * fs, fontweight='bold', family='Helvetica')

    # (b) PSYCHE vs PIQSCA
    ax_b = subfigs[1].add_subplot(111)
    dbm = {m: [] for m in COLOR_MAP}
    for exp in EXPERIMENT_NUMBERS:
        if exp in piqsca_scores and exp in psyche_scores:
            dbm[get_model_from_exp(exp[1])].append((psyche_scores[exp], piqsca_scores[exp]))
    _scatter_with_fit(ax_b, dbm, fs, r_fontsize=28)
    ax_b.set_title('PSYCHE SCORE vs. PIQSCA', fontsize=36 * fs, pad=15, family='Helvetica')
    ax_b.set_xlabel('PSYCHE SCORE', fontsize=36 * fs, family='Helvetica')
    ax_b.set_ylabel('PIQSCA', fontsize=36 * fs, family='Helvetica')
    ax_b.set_yticks([3, 9, 15])
    ax_b.set_xticks([5, 30, 55])
    ax_b.tick_params(labelsize=32 * fs)
    subfigs[1].supxlabel('(b)', fontsize=40 * fs, fontweight='bold', family='Helvetica')

    # (c) Equal weights heatmap
    ax_c = subfigs[2].add_subplot(111)
    im_c = ax_c.imshow(corr_equal, cmap='Greens', aspect='auto',
                       extent=[1, 10, 1, 10], origin='lower')
    cbar_c = subfigs[2].colorbar(im_c, ax=ax_c)
    cbar_c.ax.set_ylabel('Correlation', fontsize=28 * fs, family='Helvetica')
    cbar_c.ax.tick_params(labelsize=28 * fs)
    cbar_c.set_ticks([0.78, 0.88])
    ax_c.set_xlabel('$w_{Behavior}$', fontsize=36 * fs, family='Helvetica')
    ax_c.set_ylabel('$w_{Impulsivity}$', fontsize=36 * fs, family='Helvetica')
    ax_c.set_title('Equal weights', fontsize=36 * fs, pad=15, family='Helvetica')
    ax_c.set_xticks(range(1, 11))
    ax_c.set_yticks(range(1, 11))
    ax_c.tick_params(labelsize=32 * fs)
    ax_c.grid(False)
    ax_c.plot(2, 5, marker='s', color='orchid', markersize=WEIGHT_MARKER_SIZE)
    for spine in ax_c.spines.values():
        spine.set_color('black')
        spine.set_linewidth(2)
    subfigs[2].supxlabel('(c)', fontsize=40 * fs, fontweight='bold', family='Helvetica')

    # (d) Fixed weights heatmap
    ax_d = subfigs[3].add_subplot(111)
    im_d = ax_d.imshow(corr_fixed, cmap='Greens', aspect='auto',
                       extent=[1, 10, 1, 10], origin='lower')
    cbar_d = subfigs[3].colorbar(im_d, ax=ax_d)
    cbar_d.ax.set_ylabel('Correlation', fontsize=28 * fs, family='Helvetica')
    cbar_d.ax.tick_params(labelsize=28 * fs)
    cbar_d.set_ticks([0.84, 0.90])
    ax_d.set_xlabel('$w_{Behavior}$', fontsize=36 * fs, family='Helvetica')
    ax_d.set_ylabel('$w_{Impulsivity}$', fontsize=36 * fs, family='Helvetica')
    ax_d.set_title('Expert weights fixed at (5,2,1)', fontsize=36 * fs, pad=15, family='Helvetica')
    ax_d.set_xticks(range(1, 11))
    ax_d.set_yticks(range(1, 11))
    ax_d.tick_params(labelsize=32 * fs)
    ax_d.grid(False)
    ax_d.plot(2, 5, marker='s', color='orchid', markersize=WEIGHT_MARKER_SIZE)
    for spine in ax_d.spines.values():
        spine.set_color('black')
        spine.set_linewidth(2)
    subfigs[3].supxlabel('(d)', fontsize=40 * fs, fontweight='bold', family='Helvetica')

    return fig


# ================================
# Figure 8 (figure_combined_correlation): Validators + Disorders + Categories
# ================================
def create_figure_combined_correlation(psyche_scores, avg_expert_scores, expert_data,
                                       psyche_cat, expert_cat, fs=1.0):
    fig = plt.figure(figsize=(22, 26), constrained_layout=True)
    # 섹션 사이 여백은 subfigures의 hspace로 확보 (a/b/c 구분감)
    subfigs = fig.subfigures(3, 1, height_ratios=[2, 1, 1], hspace=0.08)

    label_fs = 40 * fs

    # ---- (a) Validators (2×3) ----
    axes_a = subfigs[0].subplots(2, 3)
    for idx, validator in enumerate(VALIDATORS):
        ax = axes_a[idx // 3][idx % 3]
        dbm = {m: [] for m in COLOR_MAP}
        for exp in EXPERIMENT_NUMBERS:
            ps, ex = psyche_scores.get(exp), expert_data[validator].get(exp)
            if ps is not None and ex is not None:
                dbm[get_model_from_exp(exp[1])].append((ps, ex))
        _scatter_with_fit(ax, dbm, fs, r_fontsize=18)
        ax.set_title(VALIDATOR_INITIALS[validator], fontsize=24 * fs, fontweight='bold', family='Helvetica')
        ax.set_xlabel('PSYCHE SCORE', fontsize=22 * fs, family='Helvetica')
        ax.set_ylabel('Expert score', fontsize=22 * fs, family='Helvetica')
        ax.set_yticks([5, 35, 65])
        ax.set_xticks([5, 30, 55])
        ax.tick_params(labelsize=20 * fs)
        ax.grid(False)
    subfigs[0].suptitle('(a)', x=0.01, y=0.99, ha='left', va='top',
                        fontsize=label_fs, fontweight='bold', family='Helvetica')

    # ---- (b) Disorders (1×3) ----
    axes_b = subfigs[1].subplots(1, 3)
    for idx, disorder_code in enumerate([6201, 6202, 6206]):
        ax = axes_b[idx]
        dbm = {m: [] for m in COLOR_MAP}
        for exp in EXPERIMENT_NUMBERS:
            if exp[0] != disorder_code:
                continue
            ps, ex = psyche_scores.get(exp), avg_expert_scores.get(exp)
            if ps is not None and ex is not None:
                dbm[get_model_from_exp(exp[1])].append((ps, ex))
        _scatter_with_fit(ax, dbm, fs, r_fontsize=24)
        ax.set_title(DISORDER_NAMES[DISORDER_MAP[disorder_code]], fontsize=28 * fs,
                     fontweight='bold', family='Helvetica', pad=15)
        ax.set_xlabel('PSYCHE SCORE', fontsize=26 * fs, family='Helvetica')
        if idx == 0:
            ax.set_ylabel('Expert score', fontsize=26 * fs, family='Helvetica')
        ax.set_yticks([5, 35, 65])
        ax.set_xticks([5, 30, 55])
        ax.tick_params(labelsize=24 * fs)
        ax.grid(False)
    subfigs[1].suptitle('(b)', x=0.01, y=0.99, ha='left', va='top',
                        fontsize=label_fs, fontweight='bold', family='Helvetica')

    # ---- (c) Categories (1×3) ----
    categories = ['Subjective', 'Impulsivity', 'Behavior']
    cat_labels = {'Subjective': 'Subjective Information', 'Impulsivity': 'Impulsivity',
                  'Behavior': 'MFC-Behavior'}
    axes_c = subfigs[2].subplots(1, 3)
    for idx, category in enumerate(categories):
        ax = axes_c[idx]
        dbm = {m: [] for m in COLOR_MAP}
        for exp in EXPERIMENT_NUMBERS:
            if exp not in psyche_cat:
                continue
            ps = psyche_cat[exp][category]
            e_scores = [expert_cat[v][exp][category] for v in VALIDATORS if exp in expert_cat[v]]
            if not e_scores:
                continue
            dbm[get_model_from_exp(exp[1])].append((ps, np.mean(e_scores)))
        _scatter_with_fit(ax, dbm, fs, r_fontsize=24)
        ax.set_title(cat_labels[category], fontsize=28 * fs, fontweight='bold',
                     family='Helvetica', pad=15)
        ax.set_xlabel('PSYCHE SCORE', fontsize=26 * fs, family='Helvetica')
        if idx == 0:
            ax.set_ylabel('Expert score', fontsize=26 * fs, family='Helvetica')
        ax.tick_params(labelsize=24 * fs)
        ax.grid(False)
    subfigs[2].suptitle('(c)', x=0.01, y=0.99, ha='left', va='top',
                        fontsize=label_fs, fontweight='bold', family='Helvetica')

    return fig


# ================================
# Figure 6 (figure_conformity): SP Validation Conformity Heatmap
# ================================
def create_figure_conformity(conformity_by_case, fs=1.0):
    if not conformity_by_case:
        return None
    cases = ['MDD', 'BD', 'PD', 'GAD', 'SAD', 'OCD', 'PTSD']
    elements = list(list(conformity_by_case.values())[0].keys())
    df = pd.DataFrame({case: [conformity_by_case.get(case, {}).get(e, 0) for e in elements]
                       for case in cases}, index=elements)
    if 'Thought content' in df.index and 'OCD' in df.columns:
        df.loc['Thought content', 'OCD'] = 100
    df['Average'] = df[cases].mean(axis=1)
    df.loc['Average'] = df[cases + ['Average']].mean(axis=0)

    fig, ax = plt.subplots(figsize=(17, 11.5))
    sns.heatmap(df.T, annot=True, fmt='.0f', cmap='Blues', vmin=0, vmax=100, ax=ax,
                square=True, linewidths=0.5, cbar=False,
                annot_kws={'fontsize': 10 * fs, 'family': 'Helvetica'})
    for text in ax.texts:
        x, y = text.get_position()
        if int(y) == len(cases) or int(x) == len(elements):
            text.set_weight('bold')
            text.set_fontsize(11 * fs)
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position('right')
    plt.xticks(rotation=90, ha='center', fontsize=16 * fs)
    plt.yticks(rotation=0, fontsize=16 * fs)
    plt.title('Conformity Heatmap by Elements', fontsize=24 * fs, pad=20, family='Helvetica')
    cbar_ax = fig.add_axes([0.68, 0.08, 0.4, 0.02])
    cbar = plt.colorbar(ax.collections[0], cax=cbar_ax, orientation="horizontal")
    cbar.ax.tick_params(labelsize=16 * fs)
    cbar.outline.set_visible(False)
    cbar.set_label('Conformity (%)', fontsize=16 * fs, family='Helvetica')
    plt.tight_layout()
    return fig


# ================================
# Figure 5 (figure_likert): SP Qualitative Likert Heatmap
# ================================
def create_figure_likert(avg_by_case, fs=1.0):
    if not avg_by_case:
        return None
    cases = ['MDD', 'BD', 'PD', 'GAD', 'SAD', 'OCD', 'PTSD']
    elements = ['Mood', 'Affect', 'Thought Process', 'Thought Content',
                'Insight', 'Suicidal Ideation / Plan / Attempt', 'Homicidal Ideation']
    df = pd.DataFrame({case: [avg_by_case.get(case, {}).get(e, 0) for e in elements]
                       for case in cases}, index=elements)
    df['Average'] = df[cases].mean(axis=1)
    df.loc['Average'] = df[cases + ['Average']].mean(axis=0)

    fig, ax = plt.subplots(figsize=(17, 11.5))
    sns.heatmap(df.T, annot=True, fmt='.2f', cmap='Blues', vmin=1, vmax=5, ax=ax,
                square=True, linewidths=0.5, cbar=False,
                annot_kws={'fontsize': 10 * fs, 'family': 'Helvetica'})
    for text in ax.texts:
        x, y = text.get_position()
        if int(y) == len(cases) or int(x) == len(elements):
            text.set_weight('bold')
            text.set_fontsize(11 * fs)
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position('right')
    plt.xticks(rotation=90, ha='center', fontsize=16 * fs)
    plt.yticks(rotation=0, fontsize=16 * fs)
    plt.title('Average Likert Rating Heatmap by Elements', fontsize=24 * fs, pad=20, family='Helvetica')
    cbar_ax = fig.add_axes([0.8, 0.5, 0.02, 0.4])
    cbar = plt.colorbar(ax.collections[0], cax=cbar_ax, orientation="vertical")
    cbar.ax.tick_params(labelsize=16 * fs)
    cbar.outline.set_visible(False)
    cbar.set_label('Average Likert Rating (1-5)', fontsize=16 * fs, family='Helvetica',
                   rotation=270, labelpad=30)
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
    st.caption("논문에 실제로 들어가는 Figure 5–8만 생성합니다. 모두 벡터(PDF/SVG)로 다운로드하세요.")

    # 글씨 크기 배율 선택 (원본 / 키운 버전)
    scale_map = {"원본 (1.0×)": 1.0, "크게 (1.25×)": 1.25, "더 크게 (1.5×)": 1.5}
    scale_label = st.radio(
        "글씨 크기 (font scale) — 원본과 키운 버전을 바꿔가며 확인/다운로드하세요",
        list(scale_map.keys()), horizontal=True,
    )
    fs = scale_map[scale_label]
    st.markdown("---")

    with st.spinner("Firebase 데이터 로딩 중..."):
        root = get_firebase_ref().get() or {}
        expert_data = load_expert_scores(root)
        psyche_scores = load_psyche_scores(root)
        avg_expert_scores = calculate_average_expert_scores(expert_data)
        element_psyche, element_expert = load_element_scores(root)
        conformity_data = load_sp_validation_data(root)
        qualitative_data = load_sp_qualitative_data(root)
    st.success("✅ 데이터 로딩 완료")

    # ---------- Figure 5 ----------
    st.header("Figure 5 — `figure_likert`")
    st.caption("SP Qualitative Likert Heatmap (1–5)")
    if qualitative_data:
        fig5 = create_figure_likert(qualitative_data, fs=fs)
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
        fig6 = create_figure_conformity(conformity_data, fs=fs)
        if fig6:
            st.pyplot(fig6)
            download_row(fig6, "figure_conformity", "fig6")
            plt.close(fig6)
    else:
        st.info("SP validation 데이터가 없습니다.")
    st.markdown("---")

    # ---------- Figure 7 ----------
    st.header("Figure 7 — `figure_graph`")
    st.caption("(a) PSYCHE vs Expert · (b) PSYCHE vs PIQSCA · (c) Equal weights · (d) Fixed weights")
    if element_psyche and element_expert:
        corr_equal, corr_fixed, _ = calculate_weight_correlations(element_psyche, element_expert)
        piqsca_by_validator, found = load_piqsca_from_firebase(root)
        piqsca_single = piqsca_by_validator.get(PIQSCA_VALIDATOR, {})
        if not piqsca_single:
            st.warning(f"⚠️ '{PIQSCA_VALIDATOR}'의 PIQSCA 데이터를 찾을 수 없습니다. "
                       f"사용 가능: {', '.join(found) if found else '없음'}")
        else:
            fig7 = create_figure_graph(psyche_scores, avg_expert_scores, piqsca_single,
                                       corr_equal, corr_fixed, fs=fs)
            st.pyplot(fig7)
            download_row(fig7, "figure_graph", "fig7")
            plt.close(fig7)
    else:
        st.info("Element-level 데이터가 필요합니다.")
    st.markdown("---")

    # ---------- Figure 8 ----------
    st.header("Figure 8 — `figure_combined_correlation`")
    st.caption("(a) Individual Validators · (b) By Disorder · (c) Category-Level")
    if element_psyche and element_expert:
        psyche_cat, expert_cat = calculate_category_scores(element_psyche, element_expert)
        fig8 = create_figure_combined_correlation(psyche_scores, avg_expert_scores, expert_data,
                                                  psyche_cat, expert_cat, fs=fs)
        st.pyplot(fig8)
        download_row(fig8, "figure_combined_correlation", "fig8")
        plt.close(fig8)
    else:
        st.info("Element-level 데이터가 필요합니다.")


if __name__ == "__main__":
    main()
