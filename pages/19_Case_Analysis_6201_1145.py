"""
Case Analysis: Client 6201, Experiment 1145
Error Analysis - Expert Score vs PSYCHE Score Discrepancy

Target: Largest discrepancy case for discussion section
Client: 6201 (MDD)
Experiment: 1145 (claudelarge)
Validators: 이강토, 김태환, 김광현, 김주오, 허율, 장재용
"""

import streamlit as st
import pandas as pd
import numpy as np
from firebase_config import get_firebase_ref
from expert_validation_utils import sanitize_firebase_key
import matplotlib.pyplot as plt
import matplotlib
from evaluator import PSYCHE_RUBRIC
import json

# ================================
# Configuration
# ================================
st.set_page_config(
    page_title="Case Analysis: 6201-1145",
    page_icon="🔍",
    layout="wide"
)

# 한글 폰트 설정
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
matplotlib.rcParams['axes.unicode_minus'] = False

# ================================
# Constants
# ================================
CLIENT_NUM = 6201
EXP_NUM = 1145
DISORDER = "mdd"
MODEL = "claudelarge"

VALIDATORS = ["이강토", "김태환", "김광현", "김주오", "허율", "장재용"]

VALIDATOR_INITIALS = {
    "이강토": "K.T. Lee",
    "김태환": "T.H. Kim",
    "김광현": "K.H. Kim",
    "김주오": "J.O. Kim",
    "허율": "Y. Heo",
    "장재용": "J.Y. Jang"
}

# ================================
# Helper Functions
# ================================

@st.cache_data
def load_expert_scores(_firebase_ref, validators, client_num, exp_num):
    """Load expert validation scores for all validators"""
    expert_data = {}
    
    for validator in validators:
        sanitized_name = sanitize_firebase_key(validator)
        key = f"expert_{sanitized_name}_{client_num}_{exp_num}"
        
        try:
            data = _firebase_ref.child(key).get()
            if data:
                expert_data[validator] = data
            else:
                st.warning(f"⚠️ No data found for {validator}")
        except Exception as e:
            st.error(f"❌ Error loading data for {validator}: {str(e)}")
    
    return expert_data

@st.cache_data
def load_psyche_score(_firebase_ref, client_num, disorder, model, exp_num):
    """Load PSYCHE automated score"""
    key = f"clients_{client_num}_psyche_{disorder}_{model}_{exp_num}"
    
    try:
        data = _firebase_ref.child(key).get()
        return data
    except Exception as e:
        st.error(f"❌ Error loading PSYCHE score: {str(e)}")
        return None

@st.cache_data
def load_conversation_log(_firebase_ref, client_num, exp_num):
    """Load PACA-SP conversation log"""
    key = f"clients/{client_num}/conversation_log_{client_num}_{exp_num}"
    
    try:
        data = _firebase_ref.child(key).get()
        return data
    except Exception as e:
        st.error(f"❌ Error loading conversation log: {str(e)}")
        return None

def get_element_weight(element_name):
    """Get weight for PSYCHE RUBRIC element"""
    if element_name in PSYCHE_RUBRIC:
        return PSYCHE_RUBRIC[element_name].get("weight", 1)
    return 1

def create_comparison_dataframe(expert_data, psyche_data):
    """Create comparison dataframe for all validators vs PSYCHE"""
    
    if not expert_data or not psyche_data:
        return None
    
    # Get all elements from first expert
    first_expert = list(expert_data.values())[0]
    elements = []
    
    if 'elements' in first_expert:
        elements = list(first_expert['elements'].keys())
    
    # Create dataframe
    data = []
    
    for element in elements:
        row = {
            'Element': element, 
            'Weight': get_element_weight(element)
        }
        
        # Add expert scores
        for validator, expert_result in expert_data.items():
            if 'elements' in expert_result and element in expert_result['elements']:
                elem_data = expert_result['elements'][element]
                score = elem_data.get('score', 0)
                weighted = elem_data.get('weighted_score', 0)
                choice = elem_data.get('expert_choice', 'N/A')
                row[validator] = f"{weighted:.1f} ({choice})"
            else:
                row[validator] = "N/A"
        
        # Add PSYCHE score with method
        if 'elements' in psyche_data and element in psyche_data['elements']:
            psyche_elem = psyche_data['elements'][element]
            psyche_score = psyche_elem.get('score', 0)
            psyche_weighted = psyche_elem.get('weighted_score', 0)
            psyche_method = psyche_elem.get('method', 'N/A')
            row['PSYCHE Score'] = f"{psyche_weighted:.2f}"
            row['PSYCHE Method'] = psyche_method
        else:
            row['PSYCHE Score'] = "N/A"
            row['PSYCHE Method'] = "N/A"
        
        # Calculate expert average for comparison
        expert_scores = []
        for validator in expert_data.keys():
            if validator in row and row[validator] != "N/A":
                try:
                    # Extract weighted score from "X.X (Choice)" format
                    weighted_str = row[validator].split('(')[0].strip()
                    expert_scores.append(float(weighted_str))
                except:
                    pass
        
        if expert_scores:
            row['Expert Avg'] = f"{np.mean(expert_scores):.2f}"
            
            # Calculate discrepancy
            if row['PSYCHE Score'] != "N/A":
                try:
                    psyche_val = float(row['PSYCHE Score'])
                    expert_avg_val = np.mean(expert_scores)
                    discrepancy = abs(expert_avg_val - psyche_val)
                    row['Discrepancy'] = f"{discrepancy:.2f}"
                except:
                    row['Discrepancy'] = "N/A"
            else:
                row['Discrepancy'] = "N/A"
        else:
            row['Expert Avg'] = "N/A"
            row['Discrepancy'] = "N/A"
        
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Reorder columns for better readability
    col_order = ['Element', 'Weight'] + VALIDATORS + ['Expert Avg', 'PSYCHE Score', 'PSYCHE Method', 'Discrepancy']
    df = df[col_order]
    
    return df

def calculate_expert_average(expert_data):
    """Calculate average expert score across all validators"""
    
    if not expert_data:
        return None
    
    element_scores = {}
    
    # Aggregate scores per element
    for validator, expert_result in expert_data.items():
        if 'elements' in expert_result:
            for element, elem_data in expert_result['elements'].items():
                score = elem_data.get('score', 0)
                weighted_score = elem_data.get('weighted_score', 0)
                
                if element not in element_scores:
                    element_scores[element] = []
                element_scores[element].append(weighted_score)
    
    # Calculate averages
    avg_scores = {}
    for element, scores in element_scores.items():
        avg_scores[element] = np.mean(scores)
    
    total_avg = sum(avg_scores.values())
    
    return {
        'element_averages': avg_scores,
        'total_score': total_avg
    }

# ================================
# Main App
# ================================

st.title("🔍 Case Analysis: Error Analysis")
st.markdown(f"**Client:** {CLIENT_NUM} (MDD) | **Experiment:** {EXP_NUM} ({MODEL})")
st.markdown("---")

# Initialize Firebase
firebase_ref = get_firebase_ref()

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Score Comparison", 
    "👥 Expert Evaluations", 
    "💬 Conversation Log",
    "📈 Visualization"
])

# ================================
# Tab 1: Score Comparison
# ================================
with tab1:
    st.header("Score Comparison: Expert vs PSYCHE")
    
    # Load data
    expert_data = load_expert_scores(firebase_ref, VALIDATORS, CLIENT_NUM, EXP_NUM)
    psyche_data = load_psyche_score(firebase_ref, CLIENT_NUM, DISORDER, MODEL, EXP_NUM)
    
    if expert_data and psyche_data:
        # Calculate average expert score
        expert_avg = calculate_expert_average(expert_data)
        psyche_score = psyche_data.get('psyche_score', 0)
        
        # Display summary
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Average Expert Score",
                f"{expert_avg['total_score']:.2f}",
                delta=None
            )
        
        with col2:
            st.metric(
                "PSYCHE Score",
                f"{psyche_score:.2f}",
                delta=None
            )
        
        with col3:
            discrepancy = expert_avg['total_score'] - psyche_score
            st.metric(
                "Discrepancy",
                f"{abs(discrepancy):.2f}",
                delta=f"{discrepancy:.2f}",
                delta_color="inverse"
            )
        
        st.markdown("---")
        
        # Create comparison table
        st.subheader("Element-by-Element Comparison")
        st.markdown("""
        **표 설명:**
        - **Weight**: PSYCHE RUBRIC 가중치 (Subjective=1, Impulsivity=5, Behavior=2)
        - **Expert 점수**: Weighted score (Choice) 형식으로 표시
        - **Expert Avg**: 6명 검증자의 weighted score 평균
        - **PSYCHE Score**: 자동 평가 weighted score
        - **PSYCHE Method**: 채점 방법 (g-eval, binary, impulsivity, behavior)
        - **Discrepancy**: |Expert Avg - PSYCHE Score| (절대값)
        """)
        
        df_comparison = create_comparison_dataframe(expert_data, psyche_data)
        
        if df_comparison is not None:
            # Highlight high discrepancy rows
            def highlight_discrepancy(row):
                try:
                    disc = float(row['Discrepancy'])
                    if disc > 2.0:
                        return ['background-color: #ffcccc'] * len(row)
                    elif disc > 1.0:
                        return ['background-color: #fff4cc'] * len(row)
                except:
                    pass
                return [''] * len(row)
            
            # Display with highlighting
            st.dataframe(
                df_comparison.style.apply(highlight_discrepancy, axis=1),
                use_container_width=True,
                height=600
            )
            
            st.info("🔴 빨간색: Discrepancy > 2.0 | 🟡 노란색: Discrepancy > 1.0")
            
            # Summary statistics
            st.markdown("---")
            st.subheader("Discrepancy Statistics")
            
            try:
                disc_values = df_comparison['Discrepancy'].apply(lambda x: float(x) if x != 'N/A' else np.nan).dropna()
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Mean Discrepancy", f"{disc_values.mean():.2f}")
                col2.metric("Max Discrepancy", f"{disc_values.max():.2f}")
                col3.metric("Std Dev", f"{disc_values.std():.2f}")
                col4.metric("High Disc. Count", f"{(disc_values > 1.0).sum()}")
            except:
                st.warning("Could not calculate discrepancy statistics")
            
            # Download button
            csv = df_comparison.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"case_analysis_{CLIENT_NUM}_{EXP_NUM}.csv",
                mime="text/csv"
            )
    else:
        st.error("❌ Could not load necessary data for comparison")

# ================================
# Tab 2: Expert Evaluations vs PSYCHE
# ================================
with tab2:
    st.header("Expert Evaluations vs PSYCHE Scoring")
    
    if expert_data and psyche_data:
        # Create validator selection (including PSYCHE)
        validator_options = VALIDATORS + ["🤖 PSYCHE (Automated)"]
        selected_validator = st.selectbox(
            "Select Validator",
            validator_options,
            format_func=lambda x: f"{x} ({VALIDATOR_INITIALS.get(x, 'Automated Scoring')})" if x in VALIDATOR_INITIALS else x
        )
        
        st.markdown("---")
        
        # Determine which data to display
        is_psyche = selected_validator == "🤖 PSYCHE (Automated)"
        
        if is_psyche:
            result_data = psyche_data
            total_score = psyche_data.get('psyche_score', 0)
            st.metric("PSYCHE Total Score", f"{total_score:.2f} / 55.0")
        else:
            if selected_validator in expert_data:
                result_data = expert_data[selected_validator]
                total_score = result_data.get('psyche_score', 0)
                
                # Show comparison with PSYCHE
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Expert Score", f"{total_score:.2f} / 55.0")
                with col2:
                    psyche_total = psyche_data.get('psyche_score', 0)
                    st.metric("PSYCHE Score", f"{psyche_total:.2f} / 55.0")
                with col3:
                    diff = total_score - psyche_total
                    st.metric("Difference", f"{diff:.2f}", delta=f"{diff:.2f}", delta_color="off")
            else:
                st.warning(f"No data found for {selected_validator}")
                result_data = None
        
        if result_data:
            st.markdown("---")
            
            # Display element-by-element
            st.subheader("Element-by-Element Scoring")
            
            if 'elements' in result_data:
                # Group by category
                categories = {
                    "Subjective": [],
                    "Impulsivity": [],
                    "Behavior": [],
                    "Other": []
                }
                
                for element, elem_data in result_data['elements'].items():
                    weight = get_element_weight(element)
                    
                    if weight == 1:
                        category = "Subjective"
                    elif weight == 5:
                        category = "Impulsivity"
                    elif weight == 2:
                        category = "Behavior"
                    else:
                        category = "Other"
                    
                    # Get PSYCHE score for comparison (if viewing expert)
                    psyche_elem_score = None
                    psyche_elem_weighted = None
                    if not is_psyche and 'elements' in psyche_data and element in psyche_data['elements']:
                        psyche_elem_score = psyche_data['elements'][element].get('score', 0)
                        psyche_elem_weighted = psyche_data['elements'][element].get('weighted_score', 0)
                    
                    item = {
                        'Element': element,
                        'Weight': weight,
                        'PACA Content': elem_data.get('paca_content', 'N/A'),
                        'SP Content': elem_data.get('sp_content', 'N/A')
                    }
                    
                    if is_psyche:
                        # PSYCHE scoring details
                        item['Score'] = elem_data.get('score', 0)
                        item['Weighted Score'] = elem_data.get('weighted_score', 0)
                        item['Scoring Method'] = elem_data.get('method', 'N/A')
                        item['Similarity'] = elem_data.get('similarity', 'N/A')
                    else:
                        # Expert scoring
                        item['Expert Choice'] = elem_data.get('expert_choice', 'N/A')
                        item['Expert Score'] = elem_data.get('score', 0)
                        item['Expert Weighted'] = elem_data.get('weighted_score', 0)
                        item['PSYCHE Score'] = psyche_elem_score
                        item['PSYCHE Weighted'] = psyche_elem_weighted
                    
                    categories[category].append(item)
                
                # Display by category
                for category, items in categories.items():
                    if items:
                        with st.expander(f"**{category}** ({len(items)} elements)", expanded=True):
                            for item in items:
                                st.markdown(f"### {item['Element']}")
                                
                                if is_psyche:
                                    # PSYCHE view
                                    col1, col2, col3, col4 = st.columns(4)
                                    col1.metric("Score", f"{item['Score']:.2f}")
                                    col2.metric("Weight", item['Weight'])
                                    col3.metric("Weighted Score", f"{item['Weighted Score']:.2f}")
                                    col4.metric("Method", item['Scoring Method'])
                                    
                                    if item['Similarity'] != 'N/A':
                                        st.info(f"🔍 Similarity: {item['Similarity']}")
                                else:
                                    # Expert view with PSYCHE comparison
                                    col1, col2, col3, col4 = st.columns(4)
                                    col1.metric("Expert Choice", item['Expert Choice'])
                                    col2.metric("Expert Score", f"{item['Expert Score']:.1f}")
                                    col3.metric("PSYCHE Score", f"{item['PSYCHE Score']:.2f}" if item['PSYCHE Score'] is not None else "N/A")
                                    
                                    # Highlight discrepancy
                                    if item['PSYCHE Score'] is not None:
                                        weighted_diff = item['Expert Weighted'] - item['PSYCHE Weighted']
                                        col4.metric("Δ Weighted", f"{weighted_diff:.2f}", delta=f"{weighted_diff:.2f}", delta_color="off")
                                    else:
                                        col4.metric("Weight", item['Weight'])
                                
                                st.markdown("**PACA Content:**")
                                st.info(item['PACA Content'])
                                
                                if item['SP Content'] != 'N/A':
                                    st.markdown("**SP (Ground Truth):**")
                                    st.success(item['SP Content'])
                                
                                st.markdown("---")
    else:
        st.error("❌ Could not load necessary data for evaluation comparison")

# ================================
# Tab 3: Conversation Log
# ================================
with tab3:
    st.header("PACA-SP Conversation")
    
    conversation = load_conversation_log(firebase_ref, CLIENT_NUM, EXP_NUM)
    
    if conversation:
        st.info(f"📝 Total messages: {len(conversation)}")
        
        # Display conversation
        for i, msg in enumerate(conversation):
            if isinstance(msg, dict):
                speaker = msg.get('speaker', 'Unknown')
                message = msg.get('message', '')
            elif isinstance(msg, (list, tuple)) and len(msg) >= 2:
                speaker, message = msg[0], msg[1]
            else:
                st.warning(f"⚠️ Message {i} format unexpected: {msg}")
                continue
            
            if speaker == "PACA":
                st.markdown(f"**🤖 PACA (Clinician):**")
                st.success(message)
            else:
                st.markdown(f"**🧑 SP (Patient):**")
                st.warning(message)
            
            st.markdown("")
        
        # Download conversation
        if st.button("📥 Download Conversation as TXT"):
            conversation_text = ""
            for i, msg in enumerate(conversation):
                if isinstance(msg, dict):
                    speaker = msg.get('speaker', 'Unknown')
                    message = msg.get('message', '')
                elif isinstance(msg, (list, tuple)) and len(msg) >= 2:
                    speaker, message = msg[0], msg[1]
                else:
                    continue
                
                conversation_text += f"{speaker}: {message}\n\n"
            
            st.download_button(
                label="Download",
                data=conversation_text.encode('utf-8'),
                file_name=f"conversation_{CLIENT_NUM}_{EXP_NUM}.txt",
                mime="text/plain"
            )
    else:
        st.error("❌ Could not load conversation log")

# ================================
# Tab 4: Visualization
# ================================
with tab4:
    st.header("Score Discrepancy Visualization")
    
    if expert_data and psyche_data:
        expert_avg = calculate_expert_average(expert_data)
        
        # Create comparison chart
        elements = list(expert_avg['element_averages'].keys())
        expert_scores = [expert_avg['element_averages'][e] for e in elements]
        psyche_scores = []
        
        for element in elements:
            if 'elements' in psyche_data and element in psyche_data['elements']:
                psyche_scores.append(psyche_data['elements'][element].get('weighted_score', 0))
            else:
                psyche_scores.append(0)
        
        # Create bar chart
        fig, ax = plt.subplots(figsize=(12, 8))
        
        x = np.arange(len(elements))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, expert_scores, width, label='Expert Average', alpha=0.8)
        bars2 = ax.bar(x + width/2, psyche_scores, width, label='PSYCHE', alpha=0.8)
        
        ax.set_xlabel('PSYCHE Elements')
        ax.set_ylabel('Weighted Score')
        ax.set_title(f'Expert vs PSYCHE Score Comparison (Client {CLIENT_NUM}, Exp {EXP_NUM})')
        ax.set_xticks(x)
        ax.set_xticklabels(elements, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        st.pyplot(fig)
        
        # Discrepancy analysis
        st.markdown("---")
        st.subheader("Top Discrepancies")
        
        discrepancies = []
        for i, element in enumerate(elements):
            diff = abs(expert_scores[i] - psyche_scores[i])
            discrepancies.append({
                'Element': element,
                'Expert Score': expert_scores[i],
                'PSYCHE Score': psyche_scores[i],
                'Discrepancy': diff
            })
        
        df_disc = pd.DataFrame(discrepancies)
        df_disc = df_disc.sort_values('Discrepancy', ascending=False)
        
        st.dataframe(
            df_disc,
            use_container_width=True,
            height=400
        )
    else:
        st.error("❌ Could not load necessary data for visualization")

# ================================
# Footer
# ================================
st.markdown("---")
st.markdown("""
### Analysis Notes
이 페이지는 Expert Score와 PSYCHE Score 간의 가장 큰 차이를 보인 케이스에 대한 상세 분석을 제공합니다.

**분석 목적:**
- Error pattern 파악
- PSYCHE Score 자동화 평가의 한계점 식별
- Discussion section을 위한 insight 도출

**검증자:** 6명의 정신과 전문의
- 이강토, 김태환, 김광현, 김주오, 허율, 장재용
""")
