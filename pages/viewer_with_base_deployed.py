import streamlit as st
import pandas as pd
from firebase_config import get_firebase_ref
from playwright.sync_api import sync_playwright
import base64
import os


st.set_page_config(page_title="Firebase Viewer", page_icon="👁️", layout="wide")

instructions = """
<style>
    .orange-text {
        color: orange;
    }
</style>
<div class="orange-text">


    1. 원하는 Client를 좌측 사이드바에서 선택하세요. 가능한 Client만 Selecbox에 표시됩니다.

    2. Load Client Data를 눌러주세요.

    3. Profile / History / Beh-Direction / Conversation을 확인 할 수 있습니다.

    4. 같은 Client로 Conversation을 여러 번 진행했다면, 여러 가지의 Conversation 내역이 존재할 수 있습니다. Selectbox로 선택할 수 있습니다.
    
    5. 새로운 Client number를 불러오고 싶다면 Reset Viewer를 먼저 누르고 진행해주세요.
</div>
"""


def list_all_clients(firebase_ref):
    clients = firebase_ref.get()
    if clients:
        client_numbers = set()
        for key, value in clients.items():
            if key.startswith("clients/"):
                client_number = key.split("/")[1]
                client_numbers.add(client_number)
                # Check for base model tests
                if any(conv.get('version') == 'base' for conv in value.values() if isinstance(conv, dict)):
                    client_numbers.add(f"{client_number}_base")
        return sorted(client_numbers)
    else:
        st.write("No clients found in the database.")
        return []


def load_client_data(firebase_ref, client_number, profile_version, beh_dir_version):
    data = {"profile": None, "history": None,
            "beh_dir": None, "conversations": {}}

    # Handle base model test case
    is_base_model = client_number.endswith("_base")
    actual_client_number = client_number[:-
                                         5] if is_base_model else client_number

    # Format version numbers, replacing decimal point with underscore
    profile_version_formatted = f"{profile_version:.1f}".replace(".", "_")
    beh_dir_version_formatted = f"{beh_dir_version:.1f}".replace(".", "_")

    # Load profile
    profile_path = f"clients_{actual_client_number}_profile_version{profile_version_formatted}"
    data["profile"] = firebase_ref.child(profile_path).get()

    # Load history
    history_path = f"clients_{actual_client_number}_history_version{profile_version_formatted}"
    data["history"] = firebase_ref.child(history_path).get()

    # Load behavioral direction
    beh_dir_path = f"clients_{actual_client_number}_beh_dir_version{beh_dir_version_formatted}"
    data["beh_dir"] = firebase_ref.child(beh_dir_path).get()

    # Load conversations
    all_data = firebase_ref.child(f"clients/{actual_client_number}").get()
    if all_data:
        if is_base_model:
            # Only load conversations with 'version': 'base'
            data["conversations"] = {k: v for k, v in all_data.items()
                                     if isinstance(v, dict) and v.get('version') == 'base'}
        else:
            # Load all conversations except those with 'version': 'base'
            data["conversations"] = {k: v for k, v in all_data.items()
                                     if isinstance(v, dict) and v.get('version') != 'base'}

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


def display_beh_dir(beh_dir):
    st.subheader("Behavioral Direction")
    if beh_dir:
        sections = beh_dir.split('\n\n')
        for section in sections:
            lines = section.split('\n')
            if lines:
                st.markdown(f"### {lines[0]}")
                for line in lines[1:]:
                    st.markdown(f"- {line}")
            st.markdown("---")
    else:
        st.write("No behavioral direction data available.")


def get_conversation_html(conversation):
    html = """
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
            body { 
                font-family: 'Noto Sans KR', Arial, sans-serif; 
                font-size: 14px;
                line-height: 1.6;
            }
            .message { 
                padding: 10px; 
                border-radius: 10px; 
                margin-bottom: 10px; 
                max-width: 80%; 
                word-wrap: break-word;
            }
            .human { 
                background-color: #E6E6FA; 
                float: left; 
                clear: both; 
            }
            .ai { 
                background-color: #F0FFF0; 
                float: right; 
                clear: both; 
            }
        </style>
    </head>
    <body>
    """
    for entry in conversation['data']:
        if 'human' in entry and 'simulated_client' in entry:
            html += f'<div class="message human">{entry["human"]}</div>'
            html += f'<div class="message ai">{entry["simulated_client"]}</div>'
    html += "</body></html>"
    return html


def capture_conversation_screenshot(conversation_html):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(conversation_html)
        page.set_viewport_size({"width": 1000, "height": 800})
        # Wait for fonts to load
        page.wait_for_load_state('networkidle')
        screenshot = page.screenshot(full_page=True)
        browser.close()
        return screenshot


def display_conversation(conversation):
    st.subheader("Conversation")
    if conversation and 'data' in conversation:
        for entry in conversation['data']:
            if 'human' in entry and 'simulated_client' in entry:
                st.markdown(
                    f"<div style='background-color: #E6E6FA; padding: 10px; border-radius: 10px; margin-bottom: 10px; max-width: 80%; float: left;'>{entry['human']}</div>",
                    unsafe_allow_html=True
                )
                st.markdown("<div style='clear: both;'></div>",
                            unsafe_allow_html=True)
                st.markdown(
                    f"<div style='background-color: #F0FFF0; padding: 10px; border-radius: 10px; margin-bottom: 10px; max-width: 80%; float: right;'>{entry['simulated_client']}</div>",
                    unsafe_allow_html=True
                )
                st.markdown("<div style='clear: both;'></div>",
                            unsafe_allow_html=True)
                st.markdown("---")

        # Add download button
        if st.button("Download Conversation as Image"):
            html = get_conversation_html(conversation)
            screenshot = capture_conversation_screenshot(html)
            b64 = base64.b64encode(screenshot).decode()
            href = f'<a href="data:image/png;base64,{b64}" download="conversation.png">Download Image</a>'
            st.markdown(href, unsafe_allow_html=True)
    else:
        st.write(
            "No conversation data available or conversation data is not in the expected format.")
        st.write("Debug: Conversation data structure:")
        st.json(conversation)


def main():
    st.title("Client Data Viewer")
    st.write(instructions, unsafe_allow_html=True)

    # Initialize Firebase
    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error("Firebase initialization failed. Please check your configuration.")
        return

    # List all clients
    available_clients = list_all_clients(firebase_ref)

    # Initialize session state
    if 'client_data' not in st.session_state:
        st.session_state.client_data = None

    # Sidebar for client selection
    st.sidebar.header("Client Selection")
    if available_clients:
        client_number = st.sidebar.selectbox(
            "Select Client", available_clients,
            format_func=lambda x: f"{x} (Base Model Test)" if x.endswith(
                "_base") else x
        )
    else:
        st.warning(
            "No clients found in the database. Please create a client using the simulation page first.")
        return

    profile_version = st.sidebar.number_input(
        "Profile Version", min_value=1.0, value=4.0, step=0.1, format="%.1f")
    beh_dir_version = st.sidebar.number_input(
        "Behavioral Direction Version", min_value=1.0, value=4.0, step=0.1, format="%.1f")

    if st.sidebar.button("Load Client Data") or st.session_state.client_data is not None:
        if st.session_state.client_data is None:
            st.session_state.client_data = load_client_data(
                firebase_ref, client_number, profile_version, beh_dir_version)

        if any(st.session_state.client_data.values()):
            st.success("Data loaded successfully!")
            tab1, tab2, tab3, tab4 = st.tabs(
                ["Profile", "History", "Behavioral Direction", "Conversation"])

            with tab1:
                display_profile(st.session_state.client_data.get("profile"))

            with tab2:
                display_history(st.session_state.client_data.get("history"))

            with tab3:
                display_beh_dir(st.session_state.client_data.get("beh_dir"))

            with tab4:
                conversations = st.session_state.client_data.get(
                    "conversations")
                if conversations:
                    conversation_keys = list(conversations.keys())
                    selected_key = st.selectbox(
                        "Select conversation:", conversation_keys, format_func=lambda x: f"Conversation {x.split('_')[-1]}")
                    conversation_data = conversations[selected_key]
                    display_conversation(conversation_data)
                else:
                    st.write("No conversation data available.")
        else:
            st.warning(
                f"No data found for Client {client_number} with Profile Version {profile_version} and Behavioral Direction Version {beh_dir_version}")
            st.write("Debugging information:")
            st.json(st.session_state.client_data)

    # Add a button to clear the session state and reset the viewer
    if st.sidebar.button("Reset Viewer"):
        st.session_state.client_data = None
        st.experimental_rerun()


if __name__ == "__main__":
    main()
