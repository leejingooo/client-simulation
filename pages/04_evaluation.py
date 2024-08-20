import streamlit as st
import json
from evaluator import evaluate_paca_performance
from firebase_config import get_firebase_ref


def load_from_firebase(firebase_ref, client_number, data_type):
    if firebase_ref is not None:
        try:
            sanitized_path = f"clients/{client_number}/{data_type}"
            return firebase_ref.child(sanitized_path).get()
        except Exception as e:
            st.error(f"Error loading data from Firebase: {str(e)}")
    return None


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
        # Load SP construct
        sp_construct = load_from_firebase(
            firebase_ref, client_number, "profile_version5.0")
        if sp_construct is None:
            st.error("Failed to load SP construct from Firebase.")
            st.stop()

        # Load PACA construct
        paca_construct = load_from_firebase(
            firebase_ref, client_number, "construct_version1.0")
        if paca_construct is None:
            st.error("Failed to load PACA construct from Firebase.")
            st.stop()

        # Evaluate PACA performance
        scores, overall_score = evaluate_paca_performance(
            sp_construct, paca_construct)

        # Display results
        st.header("Evaluation Results")
        st.subheader(f"Overall Score: {overall_score:.2f}")

        st.subheader("Detailed Scores")
        for key, score in scores.items():
            st.write(f"{key}: {score:.2f}")

        # Display constructs
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("SP Construct")
            st.json(sp_construct)
        with col2:
            st.subheader("PACA Construct")
            st.json(paca_construct)


if __name__ == "__main__":
    evaluation_page()
