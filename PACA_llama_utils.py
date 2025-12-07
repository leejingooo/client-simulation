import json
# from langchain.chat_models import ChatOpenAI, ChatAnthropic
# from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.chat_history import InMemoryChatMessageHistory
import streamlit as st
from SP_utils import create_conversational_agent, save_to_firebase
from firebase_config import get_firebase_ref
import time
import pandas as pd
import io

# Initialize the language models
paca_llm_gpt = ChatOllama(
    temperature=0.7,
    model="llama3.2:3b",
    streaming=True,
    callbacks=[StreamingStdOutCallbackHandler()]
)


firebase_ref = get_firebase_ref()

basic_prompt = """
You are a psychiatrist conducting an initial interview with a new patient. Your goal is to gather relevant information about the patient's mental health, symptoms, and background. Ask open-ended questions and follow up on the patient's responses to gain a comprehensive understanding of their situation.

After the interview with the patient is complete, someone will come to ask you about the patient. As an experienced psychiatrist, use appropriate reasoning, your professional judgment, and the information you've gathered during the interview to answer their questions. If you cannot determine something even with appropriate reasoning and your expertise, respond with "I don't know".
"""

# advanced_prompt = """
# You are an experienced psychiatrist conducting an initial interview with a new patient. Your goal is to gather comprehensive information about the patient's mental health, symptoms, background, and potential diagnoses. Use a combination of open-ended questions, specific inquiries, and follow-up questions to explore the patient's situation in depth. Pay attention to both verbal and non-verbal cues, and use your expertise to guide the conversation towards areas that may be particularly relevant for diagnosis and treatment planning.

# After the interview with the patient is complete, someone will come to ask you about the patient. As an experienced psychiatrist, use appropriate reasoning and your professional judgment to answer their questions. If you cannot determine something even with appropriate reasoning and your expertise, respond with "I don't know".
# """

guided_prompt = """
You are an experienced psychiatrist conducting an initial interview with a new patient. Your goal is to gather comprehensive information about the patient's mental health, symptoms, background, and potential diagnoses. Use a combination of open-ended questions, specific inquiries, and follow-up questions to explore the patient's situation in depth. Pay attention to both verbal and non-verbal cues, and use your expertise to guide the conversation towards areas that may be particularly relevant for diagnosis.

The following aspects need to be assessed in the patient: Chief complaint, Present illness, Symptoms, Alleviating factors, Exacerbating factors, Symptom duration, Triggering factors (why the patient decided to visit the hospital today), Stressors, Family history (including diagnoses and substance use), Current family structure, Suicidal ideation, Suicide risk, Self-harming behavior risk, Homicide risk, Suicidal plans, Suicide attempts, Mood, Affect, Verbal productivity, Insight, Perception, Thought process, Thought content, Spontaneity, Social judgment, and Reliability.

After the interview with the patient is complete, someone will come to ask you about the patient. As an experienced psychiatrist, use appropriate reasoning, your professional judgment, and the information you've gathered during the interview to answer their questions. If you cannot determine something even with appropriate reasoning and your expertise, respond with "I don't know".
"""

# basic_prompt = """
# You are a psychiatrist conducting an initial interview with a new patient. Your goal is to gather relevant information about the patient's mental health, symptoms, and background. Ask open-ended questions and follow up on the patient's responses to gain a comprehensive understanding of their situation.
# """

# advanced_prompt = """
# You are an experienced psychiatrist conducting an initial interview with a new patient. Your goal is to gather comprehensive information about the patient's mental health, symptoms, background, and potential diagnoses. Use a combination of open-ended questions, specific inquiries, and follow-up questions to explore the patient's situation in depth. Pay attention to both verbal and non-verbal cues, and use your expertise to guide the conversation towards areas that may be particularly relevant for diagnosis and treatment planning.
# """

# guided_prompt = """
# You are an experienced psychiatrist conducting an initial interview with a new patient. Your goal is to gather comprehensive information about the patient's mental health, symptoms, background, and potential diagnoses. Use a combination of open-ended questions, specific inquiries, and follow-up questions to explore the patient's situation in depth. Pay attention to both verbal and non-verbal cues, and use your expertise to guide the conversation towards areas that may be particularly relevant for diagnosis.

# The following aspects need to be assessed in the patient: Chief complaint, Present illness, Symptoms, Alleviating factors, Exacerbating factors, Symptom duration, Triggering factors (why the patient decided to visit the hospital today), Stressors, Family history (including diagnoses and substance use), Current family structure, Suicidal ideation, Suicide risk, Self-harming behavior risk, Homicide risk, Suicidal plans, Suicide attempts, Mood, Affect, Verbal productivity, Insight, Perception, Thought process, Thought content, Spontaneity, Social judgment, and Reliability.
# """


def create_paca_agent(paca_version):

    system_prompt = st.selectbox("Select PACA system prompt", [
                                 basic_prompt, guided_prompt])

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{human_input}")
    ])

    memory = InMemoryChatMessageHistory()

    def paca_agent(human_input, is_initial_prompt=False):

        chain = chat_prompt | paca_llm_gpt

        response = chain.invoke({
            "chat_history": memory.messages,
            "human_input": human_input,
        })
        if is_initial_prompt:
            memory.add_ai_message(human_input)
        else:
            memory.add_user_message(human_input)
        memory.add_ai_message(response.content)
        return response.content

    return paca_agent, memory, paca_version


def simulate_conversation(paca_agent, sp_agent, max_turns=300):
    initial_prompt = "Hello, I'm Dr. Kim Min-soo, a psychiatrist. What is your name?"

    current_speaker = "SP"
    current_message = initial_prompt

    # Add initial prompt to PACA's memory
    paca_agent(initial_prompt, is_initial_prompt=True)
    yield ("PACA", initial_prompt)

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


# import json
# from langchain.chat_models import ChatOpenAI
# from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain.schema import HumanMessage, AIMessage
# from langchain.callbacks import StreamingStdOutCallbackHandler
# from langchain.memory import ConversationBufferMemory
# import streamlit as st
# from SP_utils import create_conversational_agent, save_to_firebase
# from firebase_config import get_firebase_ref
# import time

# # Initialize the language models
# paca_llm_gpt = ChatOpenAI(
#     temperature=0.7,
#     model="gpt-4o",
#     streaming=True,
#     callbacks=[StreamingStdOutCallbackHandler()]
# )

# paca_llm_claude = (코드를 완성시켜라, model = "claude-3.5-sonnet")

# firebase_ref = get_firebase_ref()

# # def load_paca_prompt(paca_version):
# #     with open(f"data/prompts/paca_system_prompt/paca_system_prompt_version{paca_version}.txt", "r") as f:
# #         system_prompt = f.read()

# #     with open(f"data/prompts/paca_system_prompt/given_form_version{paca_version}.json", "r") as f:
# #         given_form = f.read()

# #     return system_prompt, given_form

# basic_prompt = """

# """


# advanced_prompt = """

# """


# def create_paca_agent(paca_version):
#     system_prompt = st.selectbox(코드를 완성시켜라, basic prompt, advanced prompt)

#     chat_prompt = ChatPromptTemplate.from_messages([
#         ("system", system_prompt),
#         MessagesPlaceholder(variable_name="chat_history"),
#         ("human", "{human_input}")
#     ])

#     memory = ConversationBufferMemory(
#         return_messages=True, memory_key="chat_history")

#     chain = chat_prompt | paca_llm_(gpt 또는 claude)

#     def paca_agent(human_input, is_initial_prompt=False):
#         response = chain.invoke({
#             "chat_history": memory.chat_memory.messages,
#             "human_input": human_input,
#         })
#         if is_initial_prompt:
#             memory.chat_memory.add_ai_message(human_input)
#         else:
#             memory.chat_memory.add_user_message(human_input)
#         memory.chat_memory.add_ai_message(response.content)
#         return response.content

#     return paca_agent, memory, paca_version


# def simulate_conversation(paca_agent, sp_agent, max_turns=100):
#     initial_prompt = "안녕하세요, 저는 정신과 의사 김민수입니다. 이름이 어떻게 되시나요?"

#     current_speaker = "SP"
#     current_message = initial_prompt

#     # Add initial prompt to PACA's memory
#     paca_agent(initial_prompt, is_initial_prompt=True)
#     yield ("PACA", initial_prompt)

#     for _ in range(max_turns):
#         if current_speaker == "SP":
#             response = sp_agent(current_message)
#             yield ("SP", response)
#             current_speaker = "PACA"
#         else:
#             response = paca_agent(current_message)
#             yield ("PACA", response)
#             current_speaker = "SP"

#         current_message = response

#     return


# def 대화내역을 csv로 저장하는 함수 (streamlit에서 다운로드 가능하게 만들 것, column1은 PACA, column2는 SP로 만들 것)


# # def save_ai_conversation_to_firebase(firebase_ref, client_number, conversation, paca_version, sp_version):
# #     conversation_data = [
# #         {'speaker': speaker, 'message': message}
# #         for speaker, message in conversation
# #     ]

# #     timestamp = int(time.time())

# #     content = {
# #         'paca_version': paca_version,
# #         'sp_version': sp_version,
# #         'timestamp': timestamp,
# #         'data': conversation_data
# #     }

# #     conversation_id = f"ai_conversation_paca{paca_version}_sp{sp_version}_{timestamp}"
# #     save_to_firebase(
# #         firebase_ref, client_number, conversation_id, content)

# #     return conversation_id
