import streamlit as st
import os
import json
import pandas as pd

st.set_page_config(page_title="Viewer",
                   page_icon="👁️", layout="wide")


def load_client_data(client_number, form_version):
    base_path = f"./data/output/client_{client_number}"
    profile_path = f"{base_path}/profile_client_{client_number}_version{form_version}.json"
    history_path = f"{base_path}/history_client_{client_number}_version{form_version}.txt"

    data = {"profile": None, "history": None, "conversation": None}

    if os.path.exists(profile_path):
        with open(profile_path, 'r') as f:
            data["profile"] = json.load(f)

    if os.path.exists(history_path):
        with open(history_path, 'r') as f:
            data["history"] = f.read()

    # Find the most recent conversation file
    conversation_files = [f for f in os.listdir(base_path) if f.startswith(
        f"conversation_client_{client_number}_") and f.endswith(".xlsx")]
    if conversation_files:
        # Sort files by modification time (most recent first)
        conversation_files.sort(key=lambda x: os.path.getmtime(
            os.path.join(base_path, x)), reverse=True)
        conversation_path = os.path.join(base_path, conversation_files[0])
        data["conversation"] = pd.read_excel(conversation_path)

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
                f"<div style='background-color: #E6E6FA; padding: 10px; border-radius: 10px; margin-bottom: 10px; max-width: 80%; float: left;'>{row['human']}</div>", unsafe_allow_html=True)
            st.markdown("<div style='clear: both;'></div>",
                        unsafe_allow_html=True)

            # AI message
            st.markdown(
                f"<div style='background-color: #F0FFF0; padding: 10px; border-radius: 10px; margin-bottom: 10px; max-width: 80%; float: right;'>{row['simulated client']}</div>", unsafe_allow_html=True)
            st.markdown("<div style='clear: both;'></div>",
                        unsafe_allow_html=True)

            st.markdown("---")
    else:
        st.write("No conversation data available.")


def main():
    st.title("Client Data Viewer")

    # Sidebar for client selection
    st.sidebar.header("Client Selection")
    client_number = st.sidebar.number_input(
        "Enter Client Number", min_value=1, value=1, step=1)
    form_version = st.sidebar.number_input(
        "Form Version", min_value=1.0, value=1.0, step=0.1, format="%.1f")

    if st.sidebar.button("Load Client Data"):
        client_data = load_client_data(client_number, form_version)

        if any(client_data.values()):
            tab1, tab2, tab3 = st.tabs(["Profile", "History", "Conversation"])

            with tab1:
                display_profile(client_data["profile"])

            with tab2:
                display_history(client_data["history"])

            with tab3:
                # Check for multiple conversation files
                base_path = f"./data/output/client_{client_number}"
                conversation_files = [f for f in os.listdir(base_path) if f.startswith(
                    f"conversation_client_{client_number}_") and f.endswith(".xlsx")]

                if len(conversation_files) > 1:
                    selected_file = st.selectbox(
                        "Select conversation file:", conversation_files)
                    conversation_path = os.path.join(base_path, selected_file)
                    conversation_data = pd.read_excel(conversation_path)
                else:
                    conversation_data = client_data["conversation"]

                display_conversation(conversation_data)
        else:
            st.warning(
                f"No data found for Client {client_number} with Form Version {form_version}")


if __name__ == "__main__":
    main()
