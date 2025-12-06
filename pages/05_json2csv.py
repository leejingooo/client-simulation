import streamlit as st
from SP_utils import load_from_firebase, get_firebase_ref, check_client_exists
from json2csv_converter import psyche_json_to_csv, expert_validation_json_to_csv
from expert_validation_utils import sanitize_firebase_key
import pandas as pd


def json2csv_page():
    st.set_page_config(page_title="JSON to CSV Converter",
                       page_icon="📊", layout="wide")
    st.title("JSON to CSV Converter")
    
    # Add tabs for different conversion types
    tab1, tab2 = st.tabs(["PSYCHE Evaluation", "Expert Validation"])
    
    with tab1:
        psyche_evaluation_converter()
    
    with tab2:
        expert_validation_converter()


def psyche_evaluation_converter():
    """Convert PSYCHE evaluation results to CSV"""
    st.header("PSYCHE Evaluation JSON to CSV Converter")
    
    st.write("""
    This tool helps you convert saved PSYCHE evaluation results from Firebase to CSV format.
    
    **How to use:**
    1. Enter the Client Number
    2. Click "Search PSYCHE Evaluations" to find all saved evaluations
    3. Select an evaluation from the list
    4. Download as CSV
    """)

    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error(
            "Firebase initialization failed. Please check your configuration and try again.")
        st.stop()

    # Initialize session state
    if 'available_psyche_files' not in st.session_state:
        st.session_state.available_psyche_files = []
    if 'selected_psyche_file' not in st.session_state:
        st.session_state.selected_psyche_file = None

    # Input section
    st.subheader("1️⃣ Enter Client Number")
    client_number = st.text_input("Client Number", placeholder="e.g., 6101")
    
    # Search button
    if client_number:
        if st.button("🔍 Search PSYCHE Evaluations", use_container_width=True, type="primary"):
            with st.spinner("Searching for PSYCHE evaluation files..."):
                available_files = []
                
                try:
                    # Get all keys from Firebase
                    all_data = firebase_ref.get()
                    
                    if all_data:
                        # Search for psyche_ files
                        for key in all_data.keys():
                            # Keys are stored as: clients_{client_number}_psyche_{diagnosis}_{model}_{exp_number}
                            if key.startswith(f"clients_{client_number}_psyche_"):
                                # Extract the file info
                                # Format: clients_6101_psyche_mdd_gptbasic_1
                                parts = key.replace(f"clients_{client_number}_", "").split("_")
                                if len(parts) >= 4 and parts[0] == "psyche":
                                    diagnosis = parts[1]
                                    model = parts[2]
                                    exp_number = parts[3]
                                    
                                    file_name = f"psyche_{diagnosis}_{model}_{exp_number}"
                                    
                                    available_files.append({
                                        'File Name': file_name,
                                        'Diagnosis': diagnosis.upper(),
                                        'Model': model,
                                        'Exp #': exp_number,
                                        'Firebase Key': file_name
                                    })
                        
                        st.session_state.available_psyche_files = available_files
                    else:
                        st.warning("No data found in Firebase")
                        
                except Exception as e:
                    st.error(f"Error searching PSYCHE files: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        # Display available files
        if st.session_state.available_psyche_files:
            st.success(f"Found {len(st.session_state.available_psyche_files)} PSYCHE evaluation file(s)")
            
            # Create DataFrame for display
            df = pd.DataFrame(st.session_state.available_psyche_files)
            st.dataframe(df[['File Name', 'Diagnosis', 'Model', 'Exp #']], use_container_width=True, hide_index=True)
            
            # Selection
            st.markdown("---")
            st.subheader("2️⃣ Select File to Convert")
            
            file_options = [f"{file['File Name']}" for file in st.session_state.available_psyche_files]
            selected = st.selectbox(
                "Choose a PSYCHE evaluation file:",
                file_options,
                key="file_select"
            )
            
            if selected:
                # Find the selected file info
                selected_file = next(
                    (f for f in st.session_state.available_psyche_files if f['File Name'] == selected),
                    None
                )
                
                if selected_file:
                    st.session_state.selected_psyche_file = selected_file
                    st.info(f"Selected: **{selected}**")
                    
                    # Load and preview the data
                    st.markdown("---")
                    st.subheader("3️⃣ Preview and Download")
                    
                    try:
                        # Load from Firebase
                        psyche_data = load_from_firebase(
                            firebase_ref,
                            client_number,
                            selected_file['Firebase Key']
                        )
                        
                        if psyche_data:
                            # Display preview
                            with st.expander("📋 Preview JSON Data"):
                                st.json(psyche_data)
                            
                            # Show PSYCHE score if available
                            if 'psyche_score' in psyche_data:
                                st.metric(
                                    "PSYCHE Score",
                                    f"{psyche_data['psyche_score']:.2f}",
                                    help="Sum of all weighted scores"
                                )
                            
                            # Convert to CSV and show preview
                            try:
                                csv_data = psyche_json_to_csv(psyche_data)
                                
                                # Show CSV preview
                                with st.expander("📊 Preview CSV Data"):
                                    # Convert CSV string back to DataFrame for preview
                                    import io
                                    csv_df = pd.read_csv(io.StringIO(csv_data))
                                    st.dataframe(csv_df, use_container_width=True)
                                
                                # Download button
                                st.download_button(
                                    label="📥 Download as CSV",
                                    data=csv_data,
                                    file_name=f"{selected}.csv",
                                    mime="text/csv",
                                    use_container_width=True,
                                    type="primary"
                                )
                                
                            except Exception as e:
                                st.error(f"Failed to convert to CSV: {e}")
                                import traceback
                                st.code(traceback.format_exc())
                        else:
                            st.error(f"Failed to load data for {selected}")
                            
                    except Exception as e:
                        st.error(f"Error loading PSYCHE data: {e}")
                        import traceback
                        st.code(traceback.format_exc())
        
        elif client_number and check_client_exists(firebase_ref, client_number):
            st.info("Click 'Search PSYCHE Evaluations' to find saved evaluation files")
        else:
            st.warning("No PSYCHE evaluation files found for this client")


def expert_validation_converter():
    """Convert expert validation results to CSV"""
    st.header("Expert Validation JSON to CSV Converter")
    
    st.write("""
    This tool helps you convert saved expert validation results from Firebase to CSV format.
    
    **How to use:**
    1. Enter the Expert Name
    2. Click "Search Validation Results" to find all saved validations
    3. Select a validation from the list
    4. Download as CSV
    """)
    
    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error(
            "Firebase initialization failed. Please check your configuration and try again.")
        st.stop()
    
    # Initialize session state
    if 'available_expert_files' not in st.session_state:
        st.session_state.available_expert_files = []
    if 'selected_expert_file' not in st.session_state:
        st.session_state.selected_expert_file = None
    
    # Input section
    st.subheader("1️⃣ Enter Expert Name")
    expert_name = st.text_input("Expert Name", placeholder="e.g., 김민수", key="expert_name_input")
    
    # Search button
    if expert_name:
        if st.button("🔍 Search Validation Results", use_container_width=True, type="primary", key="search_expert"):
            with st.spinner("Searching for expert validation files..."):
                available_files = []
                
                try:
                    # Sanitize expert name for Firebase key search
                    sanitized_expert_name = sanitize_firebase_key(expert_name)
                    
                    # Get all keys from Firebase
                    all_data = firebase_ref.get()
                    
                    if all_data:
                        # Search for expert_ files
                        for key in all_data.keys():
                            # Keys are stored as: expert_{sanitized_expert_name}_{client_number}_{exp_number}
                            if key.startswith(f"expert_{sanitized_expert_name}_"):
                                # Extract the file info
                                parts = key.replace(f"expert_{sanitized_expert_name}_", "").split("_")
                                
                                if len(parts) >= 2:
                                    client_number = parts[0]
                                    exp_number = parts[1]
                                    
                                    file_name = f"expert_{expert_name}_{client_number}_{exp_number}"
                                    
                                    # Get timestamp and other info if available
                                    file_data = all_data[key]
                                    timestamp = file_data.get('timestamp', 'N/A') if isinstance(file_data, dict) else 'N/A'
                                    
                                    available_files.append({
                                        'File Name': file_name,
                                        'Expert': expert_name,
                                        'Client #': client_number,
                                        'Exp #': exp_number,
                                        'Timestamp': timestamp,
                                        'Firebase Key': key
                                    })
                        
                        st.session_state.available_expert_files = available_files
                    else:
                        st.warning("No data found in Firebase")
                        
                except Exception as e:
                    st.error(f"Error searching expert validation files: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        # Display available files
        if st.session_state.available_expert_files:
            st.success(f"Found {len(st.session_state.available_expert_files)} expert validation file(s)")
            
            # Create DataFrame for display
            df = pd.DataFrame(st.session_state.available_expert_files)
            st.dataframe(df[['File Name', 'Expert', 'Client #', 'Exp #', 'Timestamp']], use_container_width=True, hide_index=True)
            
            # Selection
            st.markdown("---")
            st.subheader("2️⃣ Select File to Convert")
            
            file_options = [f"{file['File Name']}" for file in st.session_state.available_expert_files]
            selected = st.selectbox(
                "Choose an expert validation file:",
                file_options,
                key="expert_file_select"
            )
            
            if selected:
                # Find the selected file info
                selected_file = next(
                    (f for f in st.session_state.available_expert_files if f['File Name'] == selected),
                    None
                )
                
                if selected_file:
                    st.session_state.selected_expert_file = selected_file
                    st.info(f"Selected: **{selected}**")
                    
                    # Load and preview the data
                    st.markdown("---")
                    st.subheader("3️⃣ Preview and Download")
                    
                    try:
                        # Load from Firebase directly using key
                        expert_data = firebase_ref.child(selected_file['Firebase Key']).get()
                        
                        if expert_data:
                            # Display preview
                            with st.expander("📋 Preview JSON Data"):
                                st.json(expert_data)
                            
                            # Show scores if available
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Show PSYCHE score if available (primary score)
                                if 'psyche_score' in expert_data:
                                    st.metric(
                                        "PSYCHE Score",
                                        f"{expert_data['psyche_score']:.2f}",
                                        help="Sum of all weighted scores from PSYCHE RUBRIC"
                                    )
                            
                            with col2:
                                # Show PIQSCA score if available
                                quality_assessment = expert_data.get('quality_assessment', {})
                                if quality_assessment:
                                    piqsca_total = sum([
                                        quality_assessment.get('Process of the Interview', 0),
                                        quality_assessment.get('Techniques', 0),
                                        quality_assessment.get('Information for Diagnosis', 0)
                                    ])
                                    st.metric(
                                        "PIQSCA Score",
                                        f"{piqsca_total}",
                                        help="PACA Interview Quality SCore Assessment (Total: 3-15)"
                                    )
                            
                            # Show individual quality scores if available
                            if quality_assessment:
                                st.markdown("**Quality Assessment Breakdown:**")
                                qual_cols = st.columns(3)
                                
                                with qual_cols[0]:
                                    st.caption("Process")
                                    st.write(f"⭐ {quality_assessment.get('Process of the Interview', 'N/A')}/5")
                                
                                with qual_cols[1]:
                                    st.caption("Techniques")
                                    st.write(f"⭐ {quality_assessment.get('Techniques', 'N/A')}/5")
                                
                                with qual_cols[2]:
                                    st.caption("Information")
                                    st.write(f"⭐ {quality_assessment.get('Information for Diagnosis', 'N/A')}/5")
                            
                            # Convert to CSV and show preview
                            try:
                                csv_data = expert_validation_json_to_csv(expert_data)
                                
                                # Show CSV preview
                                with st.expander("📊 Preview CSV Data"):
                                    # Convert CSV string back to DataFrame for preview
                                    import io
                                    csv_df = pd.read_csv(io.StringIO(csv_data))
                                    st.dataframe(csv_df, use_container_width=True)
                                
                                # Download button
                                st.download_button(
                                    label="📥 Download as CSV",
                                    data=csv_data,
                                    file_name=f"{selected}.csv",
                                    mime="text/csv",
                                    use_container_width=True,
                                    type="primary"
                                )
                                
                            except Exception as e:
                                st.error(f"Failed to convert to CSV: {e}")
                                import traceback
                                st.code(traceback.format_exc())
                        else:
                            st.error(f"Failed to load data for {selected}")
                            
                    except Exception as e:
                        st.error(f"Error loading expert validation data: {e}")
                        import traceback
                        st.code(traceback.format_exc())
        
        else:
            st.info("Click 'Search Validation Results' to find saved validation files")


if __name__ == "__main__":
    json2csv_page()
