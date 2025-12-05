import streamlit as st
import json
from evaluator import evaluate_paca_performance
from SP_utils import load_from_firebase, get_firebase_ref, check_client_exists, save_to_firebase
from json2csv_converter import psyche_json_to_csv
import time


def evaluation_page():
    st.set_page_config(page_title="PACA Evaluation",
                       page_icon="📊", layout="wide")
    st.title("PACA Evaluation - PSYCHE RUBRIC")
    
    st.write("""
    This evaluation tool compares SP (Standard Profile) and PACA (Psychiatric Assessment Conversational Agent)
    constructs using the PSYCHE RUBRIC scoring system.
    
    **How to use:**
    1. Enter the Client Number (e.g., 6101)
    2. Enter the Experiment Number that was used when saving the constructs
    3. Click "Start Evaluation" to compare SP and PACA constructs
    """)

    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error(
            "Firebase initialization failed. Please check your configuration and try again.")
        st.stop()

    # Input section
    col1, col2, col3 = st.columns(3)
    with col1:
        client_number = st.text_input("Enter Client Number", placeholder="e.g., 6101")
    with col2:
        exp_number = st.text_input("Enter Experiment Number", placeholder="e.g., 1")
    with col3:
        # Determine diagnosis and model from client number and page context
        diagnosis = st.selectbox("Diagnosis", ["MDD", "BD", "OCD"], help="Select the diagnosis type")
        model_name = st.text_input("Model Name", placeholder="e.g., gptbasic", help="e.g., gptbasic, claudebasic, gptguided")
    
    # Show available experiments if client number is entered
    if client_number and check_client_exists(firebase_ref, client_number):
        with st.expander("🔍 View Available Experiments"):
            st.info("Searching for saved experiments...")
            available_experiments = []
            
            # Check for experiment numbers 1-100 (you can adjust this range)
            for num in range(1, 101):
                sp_key = f"construct_sp_{client_number}_{num}"
                paca_key = f"construct_paca_{client_number}_{num}"
                conv_key = f"conversation_log_{client_number}_{num}"
                
                sp_exists = load_from_firebase(firebase_ref, client_number, sp_key) is not None
                paca_exists = load_from_firebase(firebase_ref, client_number, paca_key) is not None
                conv_exists = load_from_firebase(firebase_ref, client_number, conv_key) is not None
                
                if sp_exists or paca_exists or conv_exists:
                    available_experiments.append({
                        'Exp #': num,
                        'SP': '✅' if sp_exists else '❌',
                        'PACA': '✅' if paca_exists else '❌',
                        'Conv': '✅' if conv_exists else '❌'
                    })
            
            if available_experiments:
                st.success(f"Found {len(available_experiments)} experiment(s)")
                st.table(available_experiments)
            else:
                st.warning("No experiments found for this client")

    if st.button("Start Evaluation", use_container_width=True):
        if not client_number or not exp_number:
            st.error("Please enter both Client Number and Experiment Number")
            st.stop()
        
        if not model_name:
            st.error("Please enter Model Name")
            st.stop()

        if not check_client_exists(firebase_ref, client_number):
            st.error(f"Client {client_number} does not exist.")
            st.stop()

        with st.spinner("Evaluating constructs..."):
            try:
                # Load constructs using new naming convention
                sp_construct_key = f"construct_sp_{client_number}_{exp_number}"
                paca_construct_key = f"construct_paca_{client_number}_{exp_number}"
                
                sp_construct = load_from_firebase(
                    firebase_ref, client_number, sp_construct_key)
                paca_construct = load_from_firebase(
                    firebase_ref, client_number, paca_construct_key)

                if not sp_construct or not paca_construct:
                    st.error(f"Failed to load constructs for experiment number {exp_number}. Check if the data exists.")
                    st.info(f"Looking for:\n- {sp_construct_key}\n- {paca_construct_key}")
                    st.stop()

                # Evaluate PACA performance
                field_scores, field_methods, psyche_score, evaluation_table, detailed_results = evaluate_paca_performance(
                    client_number, sp_construct, paca_construct)

                # Display results
                st.success("Evaluation Complete!")
                
                st.header("Evaluation Results")
                st.metric("PSYCHE Score (Sum of Weighted Scores)", f"{psyche_score:.2f}", help="Sum of all weighted scores")

                st.subheader("Detailed Field Scores")
                st.dataframe(evaluation_table, use_container_width=True)
                
                # Create evaluation data structure for saving/downloading
                evaluation_data = {}
                for element_name, details in detailed_results.items():
                    evaluation_data[element_name] = {
                        'sp_content': details['sp_content'],
                        'paca_content': details['paca_content'],
                        'score': details['score'],
                        'weight': details['weight'],
                        'weighted_score': details['weighted_score']
                    }
                evaluation_data['psyche_score'] = psyche_score
                
                # Buttons for saving and downloading
                col1, col2 = st.columns(2)
                
                with col1:
                    # Save evaluation results button
                    if st.button("💾 Save to Firebase", use_container_width=True):
                        try:
                            # Create key: psyche_질환명_모델명_experiment number
                            eval_key = f"psyche_{diagnosis.lower()}_{model_name.lower()}_{exp_number}"
                            save_to_firebase(firebase_ref, client_number, eval_key, evaluation_data)
                            st.success(f"✅ Evaluation results saved!\n\nKey: {eval_key}")
                        except Exception as e:
                            st.error(f"Failed to save evaluation results: {e}")
                
                with col2:
                    # Download as CSV button
                    try:
                        csv_data = psyche_json_to_csv(evaluation_data)
                        csv_filename = f"psyche_{diagnosis.lower()}_{model_name.lower()}_{exp_number}.csv"
                        st.download_button(
                            label="📥 Download CSV",
                            data=csv_data,
                            file_name=csv_filename,
                            mime="text/csv",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Failed to generate CSV: {e}")

                # Display constructs side by side
                st.subheader("Constructs Comparison")
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("SP Construct")
                    st.json(sp_construct)
                with col2:
                    st.subheader("PACA Construct")
                    st.json(paca_construct)

            except ValueError as e:
                st.error(f"Evaluation Error: {str(e)}")
            except Exception as e:
                st.error(f"An error occurred during evaluation: {str(e)}")
                st.exception(e)


if __name__ == "__main__":
    evaluation_page()
