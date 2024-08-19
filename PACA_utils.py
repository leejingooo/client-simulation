import json
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, AIMessage
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferMemory
import streamlit as st
from SP_utils import create_conversational_agent, save_conversation_to_firebase
from firebase_config import get_firebase_ref

# Initialize the language models
paca_llm = ChatOpenAI(
    temperature=0.7,
    model="gpt-4",
    streaming=True,
    callbacks=[StreamingStdOutCallbackHandler()]
)

firebase_ref = get_firebase_ref()


def load_paca_prompt():
    with open("data/prompts/paca_system_prompt/paca_system_prompt_version1.0.txt", "r") as f:
        return f.read()


def create_paca_agent():
    system_prompt = load_paca_prompt()

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{human_input}")
    ])

    chain = chat_prompt | paca_llm

    def paca_agent(human_input):
        response = chain.invoke({"human_input": human_input})
        return response.content

    return paca_agent


def simulate_conversation(paca_agent, sp_agent, sp_memory, initial_prompt, max_turns=100):
    conversation = []
    current_speaker = "PACA"

    for _ in range(max_turns):
        if current_speaker == "PACA":
            if not conversation:
                response = paca_agent(initial_prompt)
            else:
                response = paca_agent(conversation[-1][1])
            conversation.append(("PACA", response))
            current_speaker = "SP"
        else:
            response = sp_agent(conversation[-1][1])
            conversation.append(("SP", response))
            current_speaker = "PACA"

        yield conversation[-1]

    return conversation


def save_ai_conversation_to_firebase(firebase_ref, client_number, conversation, paca_version, sp_version):
    conversation_data = [
        {'speaker': speaker, 'message': message}
        for speaker, message in conversation
    ]

    content = {
        'paca_version': paca_version,
        'sp_version': sp_version,
        'data': conversation_data
    }

    conversation_id = f"ai_conversation_paca{paca_version}_sp{sp_version}"
    save_conversation_to_firebase(
        firebase_ref, client_number, conversation_id, content)

    return conversation_id
