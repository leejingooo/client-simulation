import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from firebase_config import get_firebase_ref
from SP_utils import sanitize_key
from Home import check_participant
import numpy as np

# ================================
# Configuration
# ================================

# Experiment numbers mapping
EXPERIMENTS = {
    'MDD': {
        'gpt_basic': [(6201, 1111), (6201, 1112)],
        'gpt_guided': [(6201, 1121), (6201, 1122)],
        'claude_basic': [(6201, 1131), (6201, 1132)],
        'claude_guided': [(6201, 1141), (6201, 1142)],
    },
    'BD': {
        'gpt_basic': [(6202, 1211), (6202, 1212)],
        'gpt_guided': [(6202, 1221), (6202, 1222)],
        'claude_basic': [(6202, 1231), (6202, 1232)],
        'claude_guided': [(6202, 1241), (6202, 1242)],
    },
    'OCD': {
        'gpt_basic': [(6206, 1611), (6206, 1612)],
        'gpt_guided': [(6206, 1621), (6206, 1622)],
        'claude_basic': [(6206, 1631), (6206, 1632)],
        'claude_guided': [(6206, 1641), (6206, 1642)],
    }
}

# Color mapping for disorders
DISORDER_COLORS = {
    'MDD': '#FF6B6B',  # Red
    'BD': '#4ECDC4',   # Teal
    'OCD': '#FFE66D',  # Yellow
}

# Marker shapes for models
MARKER_SHAPES = {
    'gpt_basic': 'circle',           # 동그라미
    'gpt_guided': 'star',            # 별
    'claude_basic': 'triangle-up',   # 세모
    'claude_guided': 'diamond',      # 마름모
}

# Model display names
MODEL_NAMES = {
    'gpt_basic': 'GPT Basic',
    'gpt_guided': 'GPT Guided',
    'claude_basic': 'Claude Basic',
    'claude_guided': 'Claude Guided',
}


# ================================
# Data Loading Functions
# ================================

def load_psyche_scores(firebase_ref, expert_name):
    """Load PSYCHE scores from Firebase for all experiments"""
    scores_data = []
    
    for disorder, models in EXPERIMENTS.items():
        for model_type, experiments in models.items():
            for client_num, exp_num in experiments:
                # Load validation data
                validation_key = f"expert_{sanitize_key(expert_name)}_{client_num}_{exp_num}"
                data = firebase_ref.child(validation_key).get()
                
                if data and 'psyche_score' in data:
                    psyche_score = data['psyche_score']
                    scores_data.append({
                        'disorder': disorder,
                        'model': model_type,
                        'client_num': client_num,
                        'exp_num': exp_num,
                        'psyche_score': psyche_score
                    })
    
    return scores_data


# ================================
# Plotting Function
# ================================

def create_psyche_plot(scores_data):
    """Create a matplotlib scatter plot on a single axis (PSYCHE score)"""
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Marker mapping
    marker_map = {
        'gpt_basic': 'o',      # circle
        'gpt_guided': '*',     # star
        'claude_basic': '^',   # triangle
        'claude_guided': 'D',  # diamond
    }
    
    # Plot each disorder-model combination
    for disorder in ['MDD', 'BD', 'OCD']:
        for model_type in ['gpt_basic', 'gpt_guided', 'claude_basic', 'claude_guided']:
            # Filter data
            filtered = [s for s in scores_data 
                       if s['disorder'] == disorder and s['model'] == model_type]
            
            if not filtered:
                continue
            
            # Extract scores
            scores = [s['psyche_score'] for s in filtered]
            
            # Y-axis with small jitter to avoid overlap
            y_values = [0 + np.random.uniform(-0.15, 0.15) for _ in scores]
            
            # Plot
            ax.scatter(
                scores,
                y_values,
                c=DISORDER_COLORS[disorder],
                marker=marker_map[model_type],
                s=200,  # size
                alpha=0.7,
                edgecolors='white',
                linewidths=1.5,
                label=f"{disorder} - {MODEL_NAMES[model_type]}"
            )
    
    # Styling
    ax.set_xlabel('PSYCHE Score', fontsize=14, fontweight='bold')
    ax.set_title('PACA Performance: PSYCHE Scores by Disorder and Model', 
                 fontsize=16, fontweight='bold', pad=20)
    
    # Remove y-axis
    ax.set_yticks([])
    ax.set_ylabel('')
    
    # Grid
    ax.grid(True, axis='x', alpha=0.3, linestyle='--')
    ax.set_ylim(-0.5, 0.5)
    
    # Set x-axis range
    if scores_data:
        max_score = max([s['psyche_score'] for s in scores_data])
        ax.set_xlim(0, max_score * 1.1)
    else:
        ax.set_xlim(0, 100)
    
    # Legend
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', 
             frameon=True, fontsize=9, ncol=1)
    
    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    plt.tight_layout()
    
    return fig


# ================================
# Main Page
# ================================

def main():
    st.set_page_config(
        page_title="PSYCHE Score Plot",
        page_icon="📊",
        layout="wide"
    )
    
    # Check authentication
    if not check_participant():
        st.stop()
    
    # Get expert name
    if 'name' in st.session_state and st.session_state.get('name_correct', False):
        expert_name = st.session_state['name']
    else:
        st.error("로그인이 필요합니다.")
        st.stop()
    
    # Firebase connection
    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error("Firebase 초기화 실패")
        st.stop()
    
    # Page Header
    st.title("📊 PACA Performance Visualization")
    st.markdown(f"**검증자:** {expert_name}")
    st.markdown("---")
    
    # Info box
    with st.expander("ℹ️ 그래프 설명", expanded=True):
        st.markdown("""
        이 그래프는 **PACA(Psychiatric Assessment Conversational Agent)**의 성능을 
        **PSYCHE Score**로 시각화한 것입니다.
        
        ### 구성 요소:
        
        **색상 (질환)**:
        - 🔴 **빨강**: Major Depressive Disorder (MDD)
        - 🔵 **청록색**: Bipolar Disorder (BD)
        - 🟡 **노랑**: Obsessive-Compulsive Disorder (OCD)
        
        **모양 (모델)**:
        - ⭕ **동그라미**: GPT Basic
        - ⭐ **별**: GPT Guided
        - 🔺 **세모**: Claude Basic
        - 💎 **마름모**: Claude Guided
        
        ### PSYCHE Score:
        - X축은 PSYCHE Score (0-100점)를 나타냅니다
        - 점수가 높을수록 PACA의 성능이 우수함을 의미합니다
        - 각 모델-질환 조합마다 2개의 실험 결과가 표시됩니다
        """)
    
    # Load data
    with st.spinner("데이터를 불러오는 중..."):
        scores_data = load_psyche_scores(firebase_ref, expert_name)
    
    if not scores_data:
        st.warning("⚠️ 아직 검증된 데이터가 없습니다. Expert Validation을 먼저 진행해주세요.")
        st.stop()
    
    # Display statistics
    st.markdown("### 📈 요약 통계")
    col1, col2, col3, col4 = st.columns(4)
    
    all_scores = [s['psyche_score'] for s in scores_data]
    
    with col1:
        st.metric("검증 완료", f"{len(scores_data)}/24")
    with col2:
        st.metric("평균 점수", f"{sum(all_scores)/len(all_scores):.2f}")
    with col3:
        st.metric("최고 점수", f"{max(all_scores):.2f}")
    with col4:
        st.metric("최저 점수", f"{min(all_scores):.2f}")
    
    st.markdown("---")
    
    # Create and display plot
    fig = create_psyche_plot(scores_data)
    st.pyplot(fig)
    
    # Detailed data table
    st.markdown("---")
    st.markdown("### 📋 상세 데이터")
    
    df = pd.DataFrame(scores_data)
    df['model_name'] = df['model'].map(MODEL_NAMES)
    df = df[['disorder', 'model_name', 'client_num', 'exp_num', 'psyche_score']]
    df.columns = ['질환', '모델', 'Client 번호', 'Exp 번호', 'PSYCHE Score']
    df = df.sort_values(['질환', '모델', 'Client 번호', 'Exp 번호'])
    
    st.dataframe(df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
