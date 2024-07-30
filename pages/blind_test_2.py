import re
import streamlit as st
import time
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferMemory
from firebase_config import get_firebase_ref
from Home import check_password

st.set_page_config(
    page_title="Blind Test (2)",
    page_icon="🔬",
)

# Preset values (hidden from the user)
PRESET_CLIENT_NUMBER = 2002
PRESET_AGE = 40
PRESET_GENDER = "Female"
PRESET_NATIONALITY = "South Korea"
PRESET_DIAGNOSIS = "Major Depressive Disorder"

# Initialize Firebase
firebase_ref = get_firebase_ref()
if firebase_ref is None:
    st.error(
        "Firebase initialization failed. Please check your configuration and try again.")
    st.stop()

# Initialize session state
if 'agent_and_memory' not in st.session_state:
    st.session_state.agent_and_memory = None
if 'test_completed' not in st.session_state:
    st.session_state.test_completed = False
if 'utterance_count' not in st.session_state:
    st.session_state.utterance_count = 0


def create_base_model_agent():
    given_information = f"""
    <Given information>
    Age : {PRESET_AGE}
    Gender : {PRESET_GENDER}
    Nationality: {PRESET_NATIONALITY}
    Diagnosis : {PRESET_DIAGNOSIS}
    </Given information>
    """

    system_prompt = f"""
    You are a psychiatric patient undergoing an interview with a clinician.

    Converse with clinician to align with <Given information>.

    {given_information}
    """

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

    st.title("Blind Test (2)")
    st.write(
        "시뮬레이션 환자와 대화합니다. Start 버튼을 눌러주세요. \n한글로 대화해주세요. \n최초 환자와 대화했던 발화수와 비슷하게 맞춰주세요.")

    if st.session_state.test_completed:
        st.warning(
            "This blind test has been completed. Thank you for participating.")
        return

    if st.session_state.agent_and_memory is None:
        if st.button("Start Blind Test"):
            with st.spinner("Preparing the simulated patient..."):
                st.session_state.agent_and_memory = create_base_model_agent()
                st.success(
                    "준비가 완료되었습니다. Start 버튼을 다시 눌러주세요.")
    else:
        display_conversation()

    if st.session_state.agent_and_memory and st.button("End Test"):
        end_test()


def display_conversation():
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
        # Increment utterance count after each exchange
        st.session_state.utterance_count += 1
        st.sidebar.markdown(
            f"<h1 style='text-align: right;'>발화수: {st.session_state.utterance_count}</h1>", unsafe_allow_html=True)


def end_test():
    if st.session_state.agent_and_memory:
        _, memory = st.session_state.agent_and_memory
        save_conversation_to_firebase(
            firebase_ref,
            PRESET_CLIENT_NUMBER,
            memory.chat_memory.messages
        )
        st.success(
            "Test completed and conversation saved. Thank you for participating.")
        st.session_state.test_completed = True
        st.session_state.agent_and_memory = None
    else:
        st.error(
            "No conversation to save. Please start and conduct a conversation first.")


if __name__ == "__main__":
    main()
