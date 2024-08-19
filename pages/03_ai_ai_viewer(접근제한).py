import streamlit as st
import pandas as pd
from firebase_config import get_firebase_ref
from playwright.sync_api import sync_playwright
import base64
import os

st.set_page_config(page_title="AI-AI Conversation Viewer",
                   page_icon="🤖", layout="wide")

instructions = """
<style>
    .orange-text {
        color: orange;
    }
</style>
<div class="orange-text">
    1. 원하는 Client를 좌측 사이드바에서 선택하세요. 가능한 Client만 Selectbox에 표시됩니다.

    2. Load Client Data를 눌러주세요.

    3. AI-AI Conversation을 확인할 수 있습니다.

    4. 같은 Client로 AI-AI Conversation을 여러 번 진행했다면, 여러 가지의 Conversation 내역이 존재할 수 있습니다. Selectbox로 선택할 수 있습니다.
    
    5. 새로운 Client number를 불러오고 싶다면 Reset Viewer를 먼저 누르고 진행해주세요.
</div>
"""


def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True


def list_all_clients(firebase_ref):
    clients = firebase_ref.get()
    if clients:
        client_numbers = []
        for key in clients.keys():
            if key.startswith("clients_"):
                client_number = key.split("_")[1]
                if client_number not in client_numbers:
                    client_numbers.append(client_number)
        return client_numbers
    else:
        st.write("No clients found in the database.")
        return []


def load_ai_ai_conversations(firebase_ref, client_number):
    all_data = firebase_ref.get()
    if all_data:
        conversations = {k: v for k, v in all_data.items() if k.startswith(
            f"clients_{client_number}_ai_conversation_")}
        return conversations
    return {}


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
            .paca { 
                background-color: #E6E6FA; 
                float: left; 
                clear: both; 
            }
            .sp { 
                background-color: #F0FFF0; 
                float: right; 
                clear: both; 
            }
        </style>
    </head>
    <body>
    """
    for entry in conversation['data']:
        html += f'<div class="message {entry["speaker"].lower()}">{entry["message"]}</div>'
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


def display_ai_ai_conversation(conversation):
    st.subheader("AI-AI Conversation")
    if conversation and 'data' in conversation:
        for entry in conversation['data']:
            if 'speaker' in entry and 'message' in entry:
                color = "#E6E6FA" if entry['speaker'] == "PACA" else "#F0FFF0"
                alignment = "left" if entry['speaker'] == "PACA" else "right"
                st.markdown(
                    f"<div style='background-color: {color}; padding: 10px; border-radius: 10px; margin-bottom: 10px; max-width: 80%; float: {alignment};'><strong>{entry['speaker']}:</strong> {entry['message']}</div>",
                    unsafe_allow_html=True
                )
                st.markdown("<div style='clear: both;'></div>",
                            unsafe_allow_html=True)

        # Add download button
        if st.button("Download Conversation as Image"):
            html = get_conversation_html(conversation)
            screenshot = capture_conversation_screenshot(html)
            b64 = base64.b64encode(screenshot).decode()
            href = f'<a href="data:image/png;base64,{b64}" download="ai_ai_conversation.png">Download Image</a>'
            st.markdown(href, unsafe_allow_html=True)
    else:
        st.write(
            "No AI-AI conversation data available or conversation data is not in the expected format.")
        st.write("Debug: Conversation data structure:")
        st.json(conversation)


def main():
    if not check_password():
        st.stop()
    st.title("AI-AI Conversation Viewer")
    st.write(instructions, unsafe_allow_html=True)

    # Initialize Firebase
    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error("Firebase initialization failed. Please check your configuration.")
        return

    # List all clients
    available_clients = list_all_clients(firebase_ref)

    # Initialize session state
    if 'ai_ai_conversations' not in st.session_state:
        st.session_state.ai_ai_conversations = None

    # Sidebar for client selection
    st.sidebar.header("Client Selection")
    if available_clients:
        client_number = st.sidebar.selectbox(
            "Select Client", available_clients)
    else:
        st.warning(
            "No clients found in the database. Please create a client using the simulation page first.")
        return

    if st.sidebar.button("Load AI-AI Conversations") or st.session_state.ai_ai_conversations is not None:
        if st.session_state.ai_ai_conversations is None:
            st.session_state.ai_ai_conversations = load_ai_ai_conversations(
                firebase_ref, client_number)

        if st.session_state.ai_ai_conversations:
            st.success("AI-AI conversations loaded successfully!")
            conversation_keys = list(
                st.session_state.ai_ai_conversations.keys())
            selected_key = st.selectbox(
                "Select conversation:",
                conversation_keys,
                format_func=lambda x: f"AI-AI Conversation {x.split('_')[-1]}"
            )
            conversation_data = st.session_state.ai_ai_conversations[selected_key]
            display_ai_ai_conversation(conversation_data)
        else:
            st.warning(
                f"No AI-AI conversation data found for Client {client_number}")
            st.write("Debugging information:")
            st.json(st.session_state.ai_ai_conversations)

    # Add a button to clear the session state and reset the viewer
    if st.sidebar.button("Reset Viewer"):
        st.session_state.ai_ai_conversations = None
        st.experimental_rerun()


if __name__ == "__main__":
    main()
