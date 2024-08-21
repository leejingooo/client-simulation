import streamlit as st
import json
from construct_generator import *
from firebase_config import get_firebase_ref
from SP_utils import save_to_firebase


# PRESET
given_form_version = 2.0
profile_version = "5.0"
instruction_version = "5.0"


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


def construct_generation_page():
    st.set_page_config(page_title="PACA Construct Generation",
                       page_icon="🤖", layout="wide")
    st.title("PACA Construct Generation")

    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error(
            "Firebase initialization failed. Please check your configuration and try again.")
        st.stop()

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

    # Input for construct version
    construct_version = given_form_version

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

            # Format the transcript
            transcript = [
                {"Doctor": turn['message'] if turn['speaker'] == 'PACA' else "",
                 "Patient": turn['message'] if turn['speaker'] == 'SP' else ""}
                for turn in conversation_data['data']
            ]

            # Load the form
            given_form_path = f"data/prompts/paca_system_prompt/given_form_version{given_form_version}.json"
            form = load_form(given_form_path)

            # Create the construct generator
            generator = create_construct_generator()

            # Generate the construct
            if st.button("Generate Construct"):
                with st.spinner("Generating construct..."):
                    result = generate_construct(generator, transcript, form)

                # Display input prompt
                st.subheader("Input Prompt")
                formatted_transcript = json.dumps(
                    transcript, ensure_ascii=False, indent=2)
                formatted_form = json.dumps(form, ensure_ascii=False, indent=2)
                input_prompt = generator.prompt.format(
                    given_transcript=formatted_transcript,
                    given_form=formatted_form
                )
                st.text_area("", input_prompt, height=300)

                # Display output
                st.subheader("Generated Construct")
                st.text_area("", result, height=300)

                # Parse the result JSON
                try:
                    parsed_result = json.loads(result)
                    # Save the construct to Firebase
                    save_to_firebase(
                        firebase_ref, client_number, f"paca_construct_version{construct_version}", parsed_result)
                    st.success(
                        f"Construct version {construct_version} saved to Firebase for client {client_number}")
                except json.JSONDecodeError:
                    st.error(
                        "Failed to parse the generated construct as JSON. The construct was not saved to Firebase.")
        else:
            st.warning(
                f"No AI-AI conversation data found for Client {client_number}")

    if st.sidebar.button("Create SP-Construct"):
        sp_construct = create_sp_construct(
            client_number, profile_version, instruction_version, given_form_path)

        # Save the SP construct to Firebase
        save_to_firebase(get_firebase_ref(), client_number,
                         f"sp_construct_version{given_form_version}", sp_construct)

        st.success("SP-Construct generated/saved successfully!")

    # Add a button to clear the session state and reset the viewer
    if st.sidebar.button("Reset Viewer"):
        st.session_state.ai_ai_conversations = None
        st.rerun()


if __name__ == "__main__":
    construct_generation_page()
