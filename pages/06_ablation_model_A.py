import streamlit as st
import json
import time
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferMemory
from firebase_config import get_firebase_ref
from Home import check_password
import re

st.set_page_config(
    page_title="Ablation (Base)",
    page_icon="🧪",
)

CLIENT_NUMBER = 8881


# Initialize Firebase
firebase_ref = get_firebase_ref()
if firebase_ref is None:
    st.error(
        "Firebase initialization failed. Please check your configuration and try again.")
    st.stop()
else:
    st.success("Firebase initialized successfully")

# Initialize session state
if 'agent_and_memory' not in st.session_state:
    st.session_state.agent_and_memory = None
if 'client_number' not in st.session_state:
    st.session_state.client_number = None


def create_base_model_agent(client_number, system_prompt):
    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{human_input}")
    ])

    memory = ConversationBufferMemory(
        return_messages=True, memory_key="chat_history")

    llm = ChatOpenAI(
        temperature=0.7,
        model="gpt-4o",
        streaming=True,
        callbacks=[StreamingStdOutCallbackHandler()]
    )

    chain = chat_prompt | llm

    def agent(human_input):
        response = chain.invoke({
            "chat_history": memory.chat_memory.messages,
            "human_input": human_input
        })

        memory.chat_memory.add_user_message(human_input)
        memory.chat_memory.add_ai_message(response.content)

        return response.content

    return agent, memory


def sanitize_key(key):
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[$#\[\]/.]', '_', str(key))
    # Ensure the key is not empty
    return sanitized if sanitized else '_'


def sanitize_dict(data):
    if isinstance(data, dict):
        return {sanitize_key(k): sanitize_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_dict(item) for item in data]
    else:
        return data


def save_conversation_to_firebase(firebase_ref, client_number, messages):
    conversation_data = []
    for i in range(0, len(messages), 2):
        human_message = messages[i].content if i < len(messages) else ""
        ai_message = messages[i+1].content if i+1 < len(messages) else ""
        conversation_data.append({
            'human': human_message,
            'simulated_client': ai_message
        })

    timestamp = int(time.time())
    conversation_id = f"conversation_{timestamp}"

    content = {
        'version': 'base',
        'timestamp': timestamp,
        'data': conversation_data
    }

    sanitized_path = sanitize_key(f"clients/{client_number}/{conversation_id}")
    sanitized_content = sanitize_dict(content)

    try:
        firebase_ref.child(sanitized_path).set(sanitized_content)
        st.success(f"Conversation saved with ID: {conversation_id}")
        return conversation_id
    except Exception as e:
        st.error(f"Failed to save conversation to Firebase: {str(e)}")
        return None


def main():
    if not check_password():
        st.stop()

    st.title("Base Model Simulation")

    st.sidebar.header("Settings")
    new_client_number = CLIENT_NUMBER

    if st.session_state.client_number != new_client_number:
        st.session_state.client_number = new_client_number
        st.session_state.agent_and_memory = None

    given_information = f"""
        <Given information>
        Diagnosis : Post-traumatic stress disorder
        Age : 30
        Sex : Female
        Nationality: South Korea
        </Given information>
        """

    system_prompt = f"""
    You are a psychiatric patient undergoing an interview with a clinician.

    Converse with clinician to align with <Given information>.

    {given_information}
    """

    if st.sidebar.button("Generate Simulated Patient", key="generate_patient_button"):
        with st.spinner("Generating simulated patient..."):
            st.session_state.agent_and_memory = create_base_model_agent(
                st.session_state.client_number, system_prompt)
            st.success("Simulated patient generated successfully!")

    st.header("Conversation with Simulated Patient")

    if st.session_state.agent_and_memory:
        agent, memory = st.session_state.agent_and_memory
        for message in memory.chat_memory.messages:
            with st.chat_message("user" if message.type == "human" else "assistant"):
                st.markdown(message.content)

        if prompt := st.chat_input("Interviewer:"):
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = agent(prompt)
                message_placeholder.markdown(full_response)
    else:
        st.warning("Please generate a simulated patient first.")

    if st.button("Start New Conversation"):
        if st.session_state.agent_and_memory:
            # Reset the memory of the existing agent
            agent, memory = st.session_state.agent_and_memory
            memory.chat_memory.clear()
            st.success("New conversation started with the same patient data.")
            st.rerun()
        else:
            st.error(
                "Please generate a simulated patient first before starting a new conversation.")

    if st.button("End/Save Conversation", key="end_save_conversation_button"):
        if st.session_state.client_number is not None and st.session_state.agent_and_memory is not None:
            _, memory = st.session_state.agent_and_memory

            save_conversation_to_firebase(
                firebase_ref,
                st.session_state.client_number,
                memory.chat_memory.messages
            )
            st.success(
                f"Conversation saved to Firebase for Client {st.session_state.client_number}!")
        else:
            st.error(
                "Unable to save conversation. Client number is not set or no conversation has taken place.")


if __name__ == "__main__":
    main()
