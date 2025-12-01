import streamlit as st
import json
from evaluator import evaluate_paca_performance
from SP_utils import load_from_firebase, get_firebase_ref, check_client_exists


def evaluation_page():
    st.set_page_config(page_title="PACA Evaluation",
                       page_icon="📊", layout="wide")
    st.title("PACA Evaluation - PSYCHE RUBRIC")
    
    st.write("""
    This evaluation tool compares SP (Standard Profile) and PACA (Psychiatric Assessment Conversational Agent)
    constructs using the PSYCHE RUBRIC scoring system.
    """)

    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error(
            "Firebase initialization failed. Please check your configuration and try again.")
        st.stop()

    # Input section
    col1, col2 = st.columns(2)
    with col1:
        client_number = st.text_input("Enter Client Number", placeholder="e.g., 1")
    with col2:
        construct_version = st.text_input("Enter Construct Version", placeholder="e.g., 3.0")

    if st.button("Start Evaluation", use_container_width=True):
        if not client_number or not construct_version:
            st.error("Please enter both Client Number and Construct Version")
            st.stop()

        if not check_client_exists(firebase_ref, client_number):
            st.error(f"Client {client_number} does not exist.")
            st.stop()

        with st.spinner("Evaluating constructs..."):
            try:
                # Load constructs
                sp_construct = load_from_firebase(
                    firebase_ref, client_number, f"sp_construct_version{construct_version}")
                paca_construct = load_from_firebase(
                    firebase_ref, client_number, f"paca_construct_version{construct_version}")

                if not sp_construct or not paca_construct:
                    st.error(f"Failed to load constructs. Check if version {construct_version} exists.")
                    st.stop()

                # Evaluate PACA performance
                field_scores, field_methods, weighted_score, evaluation_table = evaluate_paca_performance(
                    client_number, sp_construct, paca_construct)

                # Display results
                st.success("Evaluation Complete!")
                
                st.header("Evaluation Results")
                st.metric("Overall Weighted Score", f"{weighted_score:.2f}", help="Score out of 1.0 based on PSYCHE RUBRIC weights")

                st.subheader("Detailed Field Scores")
                st.dataframe(evaluation_table, use_container_width=True)

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
