import streamlit as st
import plotly.graph_objects as go
from firebase_config import get_firebase_ref
from SP_utils import sanitize_key
from Home import check_participant

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
    """Create a plotly scatter plot on a single axis (PSYCHE score)"""
    
    fig = go.Figure()
    
    # Add traces for each disorder-model combination
    for disorder in ['MDD', 'BD', 'OCD']:
        for model_type in ['gpt_basic', 'gpt_guided', 'claude_basic', 'claude_guided']:
            # Filter data for this combination
            filtered = [s for s in scores_data 
                       if s['disorder'] == disorder and s['model'] == model_type]
            
            if not filtered:
                continue
            
            # Extract scores
            scores = [s['psyche_score'] for s in filtered]
            
            # Y-axis is constant (we want a single line)
            # Add small random jitter to avoid perfect overlap
            import random
            y_values = [0 + random.uniform(-0.1, 0.1) for _ in scores]
            
            # Hover text
            hover_texts = [
                f"Disorder: {disorder}<br>"
                f"Model: {MODEL_NAMES[model_type]}<br>"
                f"Client: {s['client_num']}<br>"
                f"Exp: {s['exp_num']}<br>"
                f"PSYCHE Score: {s['psyche_score']:.2f}"
                for s in filtered
            ]
            
            # Add trace
            fig.add_trace(go.Scatter(
                x=scores,
                y=y_values,
                mode='markers',
                name=f"{disorder} - {MODEL_NAMES[model_type]}",
                marker=dict(
                    symbol=MARKER_SHAPES[model_type],
                    size=15,
                    color=DISORDER_COLORS[disorder],
                    line=dict(width=1, color='white')
                ),
                text=hover_texts,
                hovertemplate='%{text}<extra></extra>'
            ))
    
    # Update layout
    fig.update_layout(
        title={
            'text': 'PACA Performance: PSYCHE Scores by Disorder and Model',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        xaxis=dict(
            title='PSYCHE Score',
            titlefont=dict(size=16),
            showgrid=True,
            gridcolor='lightgray',
            range=[0, max([s['psyche_score'] for s in scores_data]) * 1.1] if scores_data else [0, 100]
        ),
        yaxis=dict(
            showticklabels=False,
            showgrid=False,
            range=[-0.5, 0.5]
        ),
        height=600,
        hovermode='closest',
        plot_bgcolor='white',
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(size=10)
        ),
        margin=dict(r=200)  # Make room for legend
    )
    
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
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed data table
    st.markdown("---")
    st.markdown("### 📋 상세 데이터")
    
    import pandas as pd
    
    df = pd.DataFrame(scores_data)
    df['model_name'] = df['model'].map(MODEL_NAMES)
    df = df[['disorder', 'model_name', 'client_num', 'exp_num', 'psyche_score']]
    df.columns = ['질환', '모델', 'Client 번호', 'Exp 번호', 'PSYCHE Score']
    df = df.sort_values(['질환', '모델', 'Client 번호', 'Exp 번호'])
    
    st.dataframe(df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
