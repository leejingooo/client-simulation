import json
import os
import re
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, SystemMessage
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferMemory
import streamlit as st
import pandas as pd
from typing import Tuple
from firebase_config import get_firebase_ref
import time
from collections import OrderedDict

# Initialize the language models
llm = ChatOpenAI(
    temperature=0.7,
    model="gpt-4o",
)

chat_llm = ChatOpenAI(
    temperature=0.7,
    model="gpt-4o",
    streaming=True,
    callbacks=[StreamingStdOutCallbackHandler()]
)

firebase_ref = get_firebase_ref()

# Fixed date
FIXED_DATE = "01/07/2024"


def sanitize_key(key):
    sanitized = re.sub(r'[$#\[\]/.]', '_', str(key))
    return sanitized if sanitized else '_'


def sanitize_dict(data):
    if isinstance(data, dict):
        return {sanitize_key(k): sanitize_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_dict(item) for item in data]
    else:
        return data


def save_to_firebase(firebase_ref, client_number, data_type, content):
    if firebase_ref is not None:
        try:
            if "version" in data_type:
                version_part = data_type.split("version")[1]
                formatted_version = version_part.replace(".", "_")
                data_type = f"{data_type.split('version')[0]}version{formatted_version}"

            sanitized_path = sanitize_key(
                f"clients/{client_number}/{data_type}")
            sanitized_content = sanitize_dict(content)
            firebase_ref.child(sanitized_path).set(sanitized_content)
        except Exception as e:
            st.error(f"Failed to save data to Firebase: {str(e)}")
    else:
        st.error("Firebase reference is not available. Data not saved.")


def load_from_firebase(firebase_ref, client_number, data_type):
    if firebase_ref is not None:
        try:
            if "version" in data_type:
                version_part = data_type.split("version")[1]
                formatted_version = version_part.replace(".", "_")
                data_type = f"{data_type.split('version')[0]}version{formatted_version}"

            sanitized_path = sanitize_key(
                f"clients/{client_number}/{data_type}")
            return firebase_ref.child(sanitized_path).get()
        except Exception as e:
            st.error(f"Error loading data from Firebase: {str(e)}")
    return None


def check_client_exists(firebase_ref, client_number):
    try:
        client_path = f"clients/{client_number}"
        client_data = firebase_ref.child(client_path).get()
        return client_data is not None
    except Exception as e:
        st.error(f"Error checking client existence: {str(e)}")
        return False


def clean_data(data):
    if isinstance(data, dict):
        return {k: clean_data(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [clean_data(v) for v in data if v is not None]
    elif isinstance(data, str):
        return data.strip()
    else:
        return data


@st.cache_data
def load_prompt(selected_file):
    if os.path.exists(selected_file):
        try:
            with open(selected_file, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            st.error(f"Error reading the file: {e}")
            return ""
    else:
        st.error("File does not exist.")
        return ""


def get_file_list(folder_path):
    try:
        file_list = os.listdir(folder_path)
        return [file for file in file_list if os.path.isfile(os.path.join(folder_path, file))]
    except Exception as e:
        st.error(f"Error: {e}")
        return []


def format_version(version):
    return "{:.1f}".format(float(version))


def extract_version(filename):
    match = re.search(r'version(\d+\.\d)', filename)
    return match.group(1) if match else None


def load_prompt_and_get_version(module_name: str, version: float) -> Tuple[str, str]:
    folder_path = f"data/prompts/{module_name}_system_prompt"
    file_list = get_file_list(folder_path)
    formatted_version = format_version(version)
    matching_files = [
        f for f in file_list if f"{module_name}_system_prompt_version{formatted_version}" in f]

    if matching_files:
        file_path = os.path.join(folder_path, matching_files[0])
        prompt_content = load_prompt(file_path)
        actual_version = extract_version(matching_files[0])
        return prompt_content, actual_version
    else:
        st.error(
            f"No matching {module_name} prompt file found for version {formatted_version}")
        return None, None


@st.cache_data
def profile_maker(profile_version, given_information, client_number, system_prompt):
    profile_form_path = f"data/profile_form/profile_form_version{format_version(profile_version)}.json"
    if not os.path.exists(profile_form_path):
        st.error(
            f"Profile form version {format_version(profile_version)} not found.")
        return None

    try:
        with open(profile_form_path, "r") as f:
            profile_form_content = f.read()
        profile_form = json.loads(profile_form_content)
    except json.JSONDecodeError as e:
        st.error(f"Error parsing profile form JSON: {str(e)}")
        st.error(f"Profile form content: {profile_form_content}")
        return None
    except Exception as e:
        st.error(f"Error reading profile form: {str(e)}")
        return None

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", given_information)
    ])

    chain = chat_prompt | llm

    try:
        result = chain.invoke({
            "current_date": FIXED_DATE,
            "profile_form": json.dumps(profile_form, indent=2),
            "given_information": given_information
        })
    except Exception as e:
        st.error(f"Error invoking language model: {str(e)}")
        return None

    try:
        cleaned_result = clean_data(json.loads(
            result.content, object_pairs_hook=OrderedDict))
        if isinstance(cleaned_result, str):
            cleaned_result = re.sub(r'<\/?JSON>', '', cleaned_result).strip()
        json_string = json.dumps(cleaned_result, indent=2)
    except json.JSONDecodeError as e:
        st.error(f"Error parsing result JSON: {str(e)}")
        st.error(f"Raw result content: {result.content}")
        return None

    try:
        parsed_result = json.loads(json_string, object_pairs_hook=OrderedDict)
    except json.JSONDecodeError as e:
        st.error(f"Error parsing final JSON: {str(e)}")
        st.error(f"Processed JSON string: {json_string}")
        return None

    save_to_firebase(firebase_ref, client_number,
                     f"profile_version{profile_version}", parsed_result)
    return parsed_result


@st.cache_data
def history_maker(profile_version, client_number, system_prompt):
    profile_json = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version}")

    if profile_json is None:
        st.error(
            "Failed to load profile data from Firebase. Unable to generate history.")
        return None

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", """
            <Profile_JSON>
            {profile_json}
            </Profile_JSON>
        """)
    ])

    chain = chat_prompt | llm

    result = chain.invoke({
        "current_date": FIXED_DATE,
        "profile_json": json.dumps(profile_json, indent=2)
    })

    save_to_firebase(firebase_ref, client_number,
                     f"history_version{profile_version}", result.content)

    return result.content


@st.cache_data
def beh_dir_maker(profile_version, beh_dir_version, client_number, system_prompt):
    profile_json = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version}")
    history = load_from_firebase(
        firebase_ref, client_number, f"history_version{profile_version}")

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", """
        """)
    ])

    chain = chat_prompt | llm

    result = chain.invoke({
        "profile_json": json.dumps(profile_json, indent=2),
        "history": history
    })

    save_to_firebase(firebase_ref, client_number,
                     f"beh_dir_version{beh_dir_version}", result.content)

    return result.content


@st.cache_resource
def create_conversational_agent(profile_version, beh_dir_version, client_number, system_prompt):
    profile_json = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version}")
    history = load_from_firebase(
        firebase_ref, client_number, f"history_version{profile_version}")
    behavioral_direction = load_from_firebase(
        firebase_ref, client_number, f"beh_dir_version{beh_dir_version}")

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{human_input}")
    ])

    memory = ConversationBufferMemory(
        return_messages=True, memory_key="chat_history")

    chain = chat_prompt | chat_llm

    def agent(human_input):
        response = chain.invoke({
            "current_date": FIXED_DATE,
            "profile_json": json.dumps(profile_json, indent=2),
            "history": history,
            "behavioral_direction": behavioral_direction,
            "chat_history": memory.chat_memory.messages,
            "human_input": human_input
        })

        memory.chat_memory.add_user_message(human_input)
        memory.chat_memory.add_ai_message(response.content)

        return response.content

    return agent, memory


def save_conversation_to_firebase(firebase_ref, client_number, messages, con_agent_version):
    conversation_data = []
    for i in range(0, len(messages), 2):
        human_message = messages[i].content if i < len(messages) else ""
        ai_message = messages[i+1].content if i+1 < len(messages) else ""
        conversation_data.append({
            'human': human_message,
            'simulated_client': ai_message
        })

    timestamp = int(time.time())
    conversation_id = f"conversation_{con_agent_version}_{timestamp}"

    content = {
        'version': con_agent_version,
        'timestamp': timestamp,
        'data': conversation_data
    }

    save_to_firebase(firebase_ref, client_number, conversation_id, content)

    st.success(f"Conversation saved with ID: {conversation_id}")
    return conversation_id
