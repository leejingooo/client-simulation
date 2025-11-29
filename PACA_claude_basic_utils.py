import json
# from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain_anthropic import ChatAnthropic
# from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferMemory
import streamlit as st
from SP_utils import create_conversational_agent, save_to_firebase
from firebase_config import get_firebase_ref
import time
import pandas as pd
import io


paca_llm_claude = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    temperature=0.7,
    streaming=True,
)

firebase_ref = get_firebase_ref()

basic_prompt = """
You are a psychiatrist conducting an initial interview with a new patient. Your goal is to gather relevant information about the patient's mental health, symptoms, and background. Ask open-ended questions and follow up on the patient's responses to gain a comprehensive understanding of their situation. When starting the conversation, begin with exactly these words: "안녕하세요, 저는 정신과 의사 김민수입니다. 이름이 어떻게 되시나요?". Proceed in Korean. Ask questions one at a time, at most.

After the interview with the patient is complete, someone will come to ask you about the patient. As an experienced psychiatrist, use appropriate reasoning, your professional judgment, and the information you've gathered during the interview to answer their questions. If you cannot determine something even with appropriate reasoning and your expertise, respond with "I don't know".
"""


def create_paca_agent(paca_version):
    system_prompt = basic_prompt

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{human_input}")
    ])

    memory = ConversationBufferMemory(
        return_messages=True, memory_key="chat_history")

    def paca_agent(human_input):
        chain = chat_prompt | paca_llm_claude
        response = chain.invoke({
            "chat_history": memory.chat_memory.messages,
            "human_input": human_input,
        })
        memory.chat_memory.add_user_message(human_input)
        memory.chat_memory.add_ai_message(response.content)
        return response.content

    return paca_agent, memory, paca_version


def simulate_conversation(paca_agent, sp_agent, max_turns=100):
    # 대화 시작
    initial_user_input = "대화 시작"
    paca_response = paca_agent(initial_user_input)
    yield ("PACA", paca_response)

    current_speaker = "SP"
    current_message = paca_response

    for _ in range(max_turns - 1):
        if current_speaker == "SP":
            response = sp_agent(current_message)
            yield ("SP", response)
            current_speaker = "PACA"
        else:
            response = paca_agent(current_message)
            yield ("PACA", response)
            current_speaker = "SP"

        current_message = response


def save_conversation_to_csv(conversation):
    df = pd.DataFrame(conversation, columns=["Speaker", "Message"])
    paca_messages = df[df["Speaker"] == "PACA"]["Message"]
    sp_messages = df[df["Speaker"] == "SP"]["Message"]

    result_df = pd.DataFrame({
        "PACA": paca_messages.reset_index(drop=True),
        "SP": sp_messages.reset_index(drop=True)
    })

    csv_buffer = io.BytesIO()
    result_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    csv_buffer.seek(0)

    return csv_buffer.getvalue()


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
