import json
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferMemory
import streamlit as st
from SP_utils import create_conversational_agent, save_to_firebase
from firebase_config import get_firebase_ref
import time

# Initialize the language models
paca_llm = ChatOpenAI(
    temperature=0.7,
    model="gpt-4",
    streaming=True,
    callbacks=[StreamingStdOutCallbackHandler()]
)

firebase_ref = get_firebase_ref()


def load_paca_prompt(paca_version):
    with open(f"data/prompts/paca_system_prompt/paca_system_prompt_version{paca_version}.txt", "r") as f:
        system_prompt = f.read()

    with open(f"data/prompts/paca_system_prompt/given_form_version{paca_version}.json", "r") as f:
        given_form = f.read()

    return system_prompt, given_form


def create_paca_agent(paca_version):
    system_prompt, given_form = load_paca_prompt(paca_version)

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{human_input}")
    ])

    memory = ConversationBufferMemory(
        return_messages=True, memory_key="chat_history")

    chain = chat_prompt | paca_llm

    def paca_agent(human_input):
        response = chain.invoke({
            "chat_history": memory.chat_memory.messages,
            "human_input": human_input,
            "given_form": given_form
        })
        memory.chat_memory.add_user_message(human_input)
        memory.chat_memory.add_ai_message(response.content)
        return response.content

    return paca_agent, memory, paca_version


def simulate_conversation(paca_agent, sp_agent, initial_prompt, max_turns=100):
    # Start with SP (patient) responding to the initial prompt
    current_speaker = "SP"
    current_message = initial_prompt

    yield ("PACA", initial_prompt)  # First, yield the doctor's initial prompt

    for _ in range(max_turns):
        if current_speaker == "SP":
            response = sp_agent(current_message)
            yield ("SP", response)
            current_speaker = "PACA"
        else:
            response = paca_agent(current_message)
            yield ("PACA", response)
            current_speaker = "SP"

        current_message = response

    return


def save_ai_conversation_to_firebase(firebase_ref, client_number, conversation, paca_version, sp_version):
    conversation_data = [
        {'speaker': speaker, 'message': message}
        for speaker, message in conversation
    ]

    timestamp = int(time.time())

    content = {
        'paca_version': paca_version,
        'sp_version': sp_version,
        'timestamp': timestamp,
        'data': conversation_data
    }

    conversation_id = f"ai_conversation_paca{paca_version}_sp{sp_version}_{timestamp}"
    save_to_firebase(
        firebase_ref, client_number, conversation_id, content)

    return conversation_id
