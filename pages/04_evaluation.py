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
    2. Select an available experiment from the list
    3. Enter Diagnosis and Model Name (used for saving file names)
    4. Click "Start Evaluation" to compare SP and PACA constructs
    """)

    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error(
            "Firebase initialization failed. Please check your configuration and try again.")
        st.stop()

    # Initialize session state
    if 'selected_exp_number' not in st.session_state:
        st.session_state.selected_exp_number = None
    if 'available_experiments' not in st.session_state:
        st.session_state.available_experiments = []

    # Input section
    st.subheader("1️⃣ Select Client and Experiment")
    client_number = st.text_input("Enter Client Number", placeholder="e.g., 6101")
    
    # Show available experiments if client number is entered
    if client_number and check_client_exists(firebase_ref, client_number):
        if st.button("🔍 Search Available Experiments") or st.session_state.available_experiments:
            with st.spinner("Searching for saved experiments..."):
                available_experiments = []
                
                # Get all keys for this client from Firebase
                try:
                    # Try to get data directly using the path structure
                    all_data = firebase_ref.get()
                    
                    if all_data:
                        # Extract experiment numbers from all keys
                        exp_numbers = set()
                        
                        # Search through all keys in Firebase
                        for key in all_data.keys():
                            # Keys are stored as: clients_{client_number}_{data_type}
                            if key.startswith(f"clients_{client_number}_construct_"):
                                parts = key.split("_")
                                # Format: clients_CLIENTNUM_construct_sp_CLIENTNUM_EXPNUM or
                                # Format: clients_CLIENTNUM_construct_paca_CLIENTNUM_EXPNUM
                                if len(parts) >= 5:
                                    try:
                                        exp_num = int(parts[-1])
                                        exp_numbers.add(exp_num)
                                    except (ValueError, IndexError):
                                        continue
                        
                        # Check each experiment number
                        for num in sorted(exp_numbers):
                            sp_key = f"construct_sp_{client_number}_{num}"
                            paca_key = f"construct_paca_{client_number}_{num}"
                            
                            sp_exists = load_from_firebase(firebase_ref, client_number, sp_key) is not None
                            paca_exists = load_from_firebase(firebase_ref, client_number, paca_key) is not None
                            
                            # Only show if both constructs exist
                            if sp_exists and paca_exists:
                                available_experiments.append({
                                    'exp_number': num,
                                    'SP': '✅',
                                    'PACA': '✅',
                                    'Status': '✅ Ready'
                                })
                            elif sp_exists or paca_exists:
                                available_experiments.append({
                                    'exp_number': num,
                                    'SP': '✅' if sp_exists else '❌',
                                    'PACA': '✅' if paca_exists else '❌',
                                    'Status': '⚠️ Incomplete'
                                })
                        
                        st.session_state.available_experiments = available_experiments
                    else:
                        st.warning("No data found in Firebase")
                        
                except Exception as e:
                    st.error(f"Error searching experiments: {e}")
                    import traceback
                    st.code(traceback.format_exc())
            
            if st.session_state.available_experiments:
                st.success(f"Found {len(st.session_state.available_experiments)} experiment(s)")
                
                # Create a table view
                import pandas as pd
                df = pd.DataFrame(st.session_state.available_experiments)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Radio button to select experiment
                st.markdown("### Select Experiment to Evaluate:")
                ready_experiments = [exp for exp in st.session_state.available_experiments if exp['Status'] == '✅ Ready']
                
                if ready_experiments:
                    exp_options = [f"Experiment #{exp['exp_number']}" for exp in ready_experiments]
                    selected = st.radio(
                        "Choose an experiment:",
                        exp_options,
                        key="exp_radio"
                    )
                    if selected:
                        st.session_state.selected_exp_number = int(selected.split("#")[1])
                        st.info(f"Selected: **Experiment #{st.session_state.selected_exp_number}**")
                else:
                    st.warning("No complete experiment sets found (both SP and PACA constructs required)")
            else:
                st.warning("No experiments found for this client")
    
    # Evaluation metadata inputs
    st.markdown("---")
    st.subheader("2️⃣ Enter Evaluation Metadata")
    st.info("💡 These values are used to generate the save file name: `psyche_{diagnosis}_{model_name}_{exp_number}`")
    
    col1, col2 = st.columns(2)
    with col1:
        diagnosis = st.selectbox(
            "Diagnosis (for file name)", 
            ["mdd", "bd", "ocd"],
            help="Will be used in save file name: psyche_{diagnosis}_..."
        )
    with col2:
        model_name = st.text_input(
            "Model Name (for file name)", 
            placeholder="e.g., gptbasic, claudeguided",
            help="Will be used in save file name: psyche_..._{model_name}_..."
        )
    
    # Preview file name
    if st.session_state.selected_exp_number and model_name:
        preview_filename = f"psyche_{diagnosis}_{model_name.lower()}_{st.session_state.selected_exp_number}"
        st.success(f"📄 Save file name will be: **`{preview_filename}`**")

    # Start Evaluation button
    st.markdown("---")
    st.subheader("3️⃣ Start Evaluation")
    
    if st.button("🚀 Start Evaluation", use_container_width=True, type="primary"):
        if not client_number:
            st.error("Please enter Client Number")
            st.stop()
        
        if not st.session_state.selected_exp_number:
            st.error("Please select an experiment from the list above")
            st.stop()
        
        if not model_name:
            st.error("Please enter Model Name (used for file naming)")
            st.stop()

        exp_number = st.session_state.selected_exp_number

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
                    st.error(f"Failed to load constructs for experiment number {exp_number}.")
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
                            eval_key = f"psyche_{diagnosis}_{model_name.lower()}_{exp_number}"
                            save_to_firebase(firebase_ref, client_number, eval_key, evaluation_data)
                            st.success(f"✅ Evaluation results saved!\n\nKey: {eval_key}")
                        except Exception as e:
                            st.error(f"Failed to save evaluation results: {e}")
                
                with col2:
                    # Download as CSV button
                    try:
                        csv_data = psyche_json_to_csv(evaluation_data)
                        csv_filename = f"psyche_{diagnosis}_{model_name.lower()}_{exp_number}.csv"
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
