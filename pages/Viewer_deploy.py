import streamlit as st
import pandas as pd
from firebase_config import get_firebase_ref

st.set_page_config(page_title="Firebase Viewer", page_icon="👁️", layout="wide")


def load_client_data(firebase_ref, client_number, form_version):
    data = {"profile": None, "history": None, "conversation": None}

    # Load profile
    profile_path = f"clients/{client_number}/profile_version{form_version}"
    data["profile"] = firebase_ref.child(profile_path).get()

    # Load history
    history_path = f"clients/{client_number}/history_version{form_version}"
    data["history"] = firebase_ref.child(history_path).get()

    # Load conversation
    conversation_path = f"clients/{client_number}"
    conversations = firebase_ref.child(conversation_path).get()
    if conversations:
        conversation_keys = [k for k in conversations.keys(
        ) if k.startswith("conversation_sysprompt_")]
        if conversation_keys:
            latest_conversation = conversations[max(conversation_keys)]
            data["conversation"] = pd.DataFrame(latest_conversation)

    return data


def display_profile(profile):
    st.subheader("Profile")
    if profile:
        for category, items in profile.items():
            st.markdown(f"**[{category}]**")
            if isinstance(items, dict):
                for key, value in items.items():
                    if isinstance(value, dict):
                        st.markdown(f"- **{key}:**")
                        for sub_key, sub_value in value.items():
                            st.markdown(f"  * {sub_key}: {sub_value}")
                    else:
                        st.markdown(f"- {key}: {value}")
            elif isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        for sub_key, sub_value in item.items():
                            st.markdown(f"- **{sub_key}:** {sub_value}")
                        st.markdown("")  # Add a blank line between list items
                    else:
                        st.markdown(f"- {item}")
            else:
                st.markdown(f"- {items}")
            st.markdown("---")
    else:
        st.write("No profile data available.")


def display_history(history):
    st.subheader("History")
    if history:
        st.write(history)
    else:
        st.write("No history data available.")


def display_conversation(conversation):
    st.subheader("Conversation")
    if conversation is not None and not conversation.empty:
        for index, row in conversation.iterrows():
            # Human message
            st.markdown(
                f"<div style='background-color: #E6E6FA; padding: 10px; border-radius: 10px; margin-bottom: 10px; max-width: 80%; float: left;'>{row['human']}</div>",
                unsafe_allow_html=True
            )
            st.markdown("<div style='clear: both;'></div>",
                        unsafe_allow_html=True)

            # AI message
            st.markdown(
                f"<div style='background-color: #F0FFF0; padding: 10px; border-radius: 10px; margin-bottom: 10px; max-width: 80%; float: right;'>{row['simulated client']}</div>",
                unsafe_allow_html=True
            )
            st.markdown("<div style='clear: both;'></div>",
                        unsafe_allow_html=True)

            st.markdown("---")
    else:
        st.write("No conversation data available.")


def main():
    st.title("Firebase Client Data Viewer")

    # Initialize Firebase
    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error("Firebase initialization failed. Please check your configuration.")
        return

    # Initialize session state
    if 'client_data' not in st.session_state:
        st.session_state.client_data = None
    if 'conversation_keys' not in st.session_state:
        st.session_state.conversation_keys = []

    # Sidebar for client selection
    st.sidebar.header("Client Selection")
    client_number = st.sidebar.number_input(
        "Enter Client Number", min_value=1, value=1, step=1)
    form_version = st.sidebar.number_input(
        "Form Version", min_value=1.0, value=1.0, step=0.1, format="%.1f")

    if st.sidebar.button("Load Client Data") or st.session_state.client_data is not None:
        if st.session_state.client_data is None:
            st.session_state.client_data = load_client_data(
                firebase_ref, client_number, form_version)
            conversation_path = f"clients/{client_number}"
            conversations = firebase_ref.child(conversation_path).get()
            if conversations:
                st.session_state.conversation_keys = [
                    k for k in conversations.keys() if k.startswith("conversation_sysprompt_")
                ]

        if any(st.session_state.client_data.values()):
            tab1, tab2, tab3 = st.tabs(["Profile", "History", "Conversation"])

            with tab1:
                display_profile(st.session_state.client_data["profile"])

            with tab2:
                display_history(st.session_state.client_data["history"])

            with tab3:
                if len(st.session_state.conversation_keys) > 1:
                    selected_key = st.selectbox(
                        "Select conversation:", st.session_state.conversation_keys)
                    conversation_data = pd.DataFrame(
                        firebase_ref.child(
                            f"clients/{client_number}/{selected_key}").get()
                    )
                else:
                    conversation_data = st.session_state.client_data["conversation"]

                display_conversation(conversation_data)
        else:
            st.warning(
                f"No data found for Client {client_number} with Form Version {form_version}")

    # Add a button to clear the session state and reset the viewer
    if st.sidebar.button("Reset Viewer"):
        st.session_state.client_data = None
        st.session_state.conversation_keys = []
        st.experimental_rerun()


if __name__ == "__main__":
    main()
