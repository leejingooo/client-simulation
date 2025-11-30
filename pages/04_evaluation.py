import streamlit as st
import json
from evaluator import evaluate_paca_performance
from SP_utils import load_from_firebase, get_firebase_ref, check_client_exists


def evaluation_page():
    st.set_page_config(page_title="PACA Evaluation",
                       page_icon="📊", layout="wide")
    st.title("PACA Evaluation")

    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error(
            "Firebase initialization failed. Please check your configuration and try again.")
        st.stop()

    # Client selection
    client_number = st.sidebar.text_input("Enter Client Number")

    if client_number:
        if not check_client_exists(firebase_ref, client_number):
            st.error(f"Client {client_number} does not exist.")
            st.stop()

        # Version selection
        paca_construct_version = st.sidebar.text_input(
            "Enter PACA Version (e.g., 3.0)")
        sp_construct_version = st.sidebar.text_input(
            "Enter MFC Version (e.g., 6.0)")
        given_form_path = f"data/prompts/paca_system_prompt/given_form_version{sp_construct_version}.json"

        if st.sidebar.button("Start Evaluation") and sp_construct_version and paca_construct_version and given_form_path:
            try:
                st.write("Starting evaluation...")
                # Evaluate PACA performance
                scores, overall_score, evaluation_table = evaluate_paca_performance(
                    client_number, sp_construct_version, paca_construct_version, given_form_path)

                # Display results
                st.header("Evaluation Results")
                st.subheader(f"Overall Score: {overall_score:.2f}")

                st.subheader("Detailed Scores")
                st.dataframe(evaluation_table)

                # Display constructs
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("SP Construct")
                    sp_construct = load_from_firebase(
                        firebase_ref, client_number, f"sp_construct_version{sp_construct_version}")
                    st.json(sp_construct)
                with col2:
                    st.subheader("PACA Construct")
                    paca_construct = load_from_firebase(
                        firebase_ref, client_number, f"paca_construct_version{paca_construct_version}")
                    st.json(paca_construct)

            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"An error occurred during evaluation: {str(e)}")


if __name__ == "__main__":
    evaluation_page()
