import streamlit as st
import time
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferMemory
from firebase_config import get_firebase_ref
from Home import check_password

st.set_page_config(
    page_title="Blind Test (Test-Base)",
    page_icon="🔬",
)

# Preset values (hidden from the user)
PRESET_CLIENT_NUMBER = 3011
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


if 'client_number' not in st.session_state:
    st.session_state.client_number = None


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
    conversation_id = f"conversation_{timestamp}"  # Remove 'base_' from here

    content = {
        'version': 'base',
        'timestamp': timestamp,
        'data': conversation_data
    }

    firebase_ref.child(
        f"clients/{client_number}/{conversation_id}").set(content)

    st.success(f"Conversation saved with ID: {conversation_id}")
    return conversation_id


def main():
    if not check_password():
        st.stop()

    st.title("Blind Test (Test-Base)")
    st.write("시뮬레이션 환자와 대화합니다. 한글로 대화해주세요.")

    if st.session_state.client_number is None:
        st.session_state.client_number = st.number_input(
            "Enter Client Number", min_value=1, step=1)

    if st.session_state.test_completed:
        st.warning(
            "This blind test has been completed. Thank you for participating.")
        return

    if st.session_state.agent_and_memory is None:
        if st.button("Start Blind Test"):
            with st.spinner("Preparing the simulated patient..."):
                st.session_state.agent_and_memory = create_base_model_agent()
                st.success(
                    "Simulated patient is ready. You can start the conversation.")
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


def end_test():
    if st.session_state.agent_and_memory:
        _, memory = st.session_state.agent_and_memory
        save_conversation_to_firebase(
            firebase_ref,
            st.session_state.client_number,
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
