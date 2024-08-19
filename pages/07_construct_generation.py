import streamlit as st
import json
from construct_generator import load_form, create_construct_generator, generate_construct
from firebase_config import get_firebase_ref


def construct_generation_page():
    st.set_page_config(page_title="PACA Construct Generation", page_icon="🤖")
    st.title("PACA Construct Generation")

    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error(
            "Firebase initialization failed. Please check your configuration and try again.")
        st.stop()

    # Load conversations
    conversations = firebase_ref.child("clients").get()
    if not conversations:
        st.error("No conversations found in the database.")
        st.stop()

    # Select client
    selected_client = st.selectbox(
        "Select a client", list(conversations.keys()))

    if selected_client:
        client_data = conversations[selected_client]

        # Filter for AI conversations
        ai_conversations = {
            k: v for k, v in client_data.items() if k.startswith('ai_conversation')}

        if not ai_conversations:
            st.error("No AI conversations found for the selected client.")
            st.stop()

        # Select conversation
        selected_conversation = st.selectbox(
            "Select a conversation", list(ai_conversations.keys()))

        if selected_conversation:
            conversation_data = ai_conversations[selected_conversation]
            ai_conversation = conversation_data.get('data', [])

            if not ai_conversation:
                st.error("No data found in the selected conversation.")
                st.stop()

            # Format the transcript
            transcript = [
                {"Doctor": turn['message'] if turn['speaker'] == 'PACA' else "",
                 "Patient": turn['message'] if turn['speaker'] == 'SP' else ""}
                for turn in ai_conversation
            ]

            # Load the form
            form_path = "data/prompts/paca_system_prompt/given_form_version1.0.json"
            form = load_form(form_path)

            # Create the construct generator
            generator = create_construct_generator()

            # Generate the construct
            if st.button("Generate Construct"):
                with st.spinner("Generating construct..."):
                    result = generate_construct(generator, transcript, form)

                # Display input prompt
                st.subheader("Input Prompt")
                st.text_area("", generator.prompt.format(
                    given_transcript=json.dumps(transcript, indent=2),
                    given_form=json.dumps(form, indent=2)
                ), height=300)

                # Display output
                st.subheader("Generated Construct")
                st.text_area("", result, height=300)


if __name__ == "__main__":
    construct_generation_page()
