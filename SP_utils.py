import json
import os
import re
# from langchain.chat_models import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
# from langchain.prompts import ChatPromptTemplate, PromptTemplate, MessagesPlaceholder
# from langchain.schema import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.chat_history import InMemoryChatMessageHistory
import streamlit as st
import pandas as pd
from typing import Tuple
from firebase_config import get_firebase_ref
import time
from collections import OrderedDict

# Initialize the language models
llm = ChatOpenAI(
    temperature=0.7,
    model="gpt-5-nano",
)

chat_llm = ChatOpenAI(
    temperature=0.7,
    model="gpt-5-nano",
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
        client_path = f"clients_{client_number}_given_information"
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


def load_prompt_and_get_version(module_name: str, version: float, diagnosis: str = None) -> Tuple[str, str]:
    folder_path = f"data/prompts/{module_name}_system_prompt"
    file_list = get_file_list(folder_path)
    formatted_version = format_version(version)

    # First, try to find a diagnosis-specific file
    if diagnosis:
        diagnosis_file = f"{module_name}_system_prompt_version{formatted_version}_{diagnosis}.txt"
        if diagnosis_file in file_list:
            file_path = os.path.join(folder_path, diagnosis_file)
            prompt_content = load_prompt(file_path)
            actual_version = extract_version(diagnosis_file)
            return prompt_content, actual_version

    # If no diagnosis-specific file found, fall back to the general file
    matching_files = [
        f for f in file_list if f"{module_name}_system_prompt_version{formatted_version}" in f
        # Exclude diagnosis-specific files
        and not f.endswith(f"_{diagnosis}.txt")
    ]

    if matching_files:
        file_path = os.path.join(folder_path, matching_files[0])
        prompt_content = load_prompt(file_path)
        actual_version = extract_version(matching_files[0])
        return prompt_content, actual_version
    else:
        st.error(
            f"No matching {module_name} prompt file found for version {formatted_version}")
        return None, None


def get_diag_from_given_information(given_information):
    diagnosis_match = re.search(r'Diagnosis\s*:\s*(.+)', given_information)
    if diagnosis_match:
        diagnosis = diagnosis_match.group(1).strip()
        if "Major depressive disorder" in diagnosis:
            return "MDD"
        elif "Bipolar 1 disorder" in diagnosis:
            return "BD"
        elif "Panic disorder" in diagnosis:
            return "PD"
        elif "Generalized anxiety disorder" in diagnosis:
            return "GAD"
        elif "Social anxiety disorder" in diagnosis:
            return "SAD"
        elif "Obsessive-compulsive disorder" in diagnosis:
            return "OCD"
        elif "Post-traumatic stress disorder" in diagnosis:
            return "PTSD"
        elif "Specific phobia" in diagnosis:
            return "SP"
    return None


@st.cache_data
def profile_maker(profile_version, given_information, client_number, prompt):
    diag = get_diag_from_given_information(given_information)
    if diag is None:
        st.error("Invalid or unsupported diagnosis in given information.")
        return None

    profile_form_path_dsa = f"data/profile_form/profile_form_version{format_version(profile_version)}_{diag}.json"
    if not os.path.exists(profile_form_path_dsa):
        st.error(
            f"Profile form version {format_version(profile_version)} not found.")
        return None

    try:
        with open(profile_form_path_dsa, "r") as f:
            profile_form_content = f.read()
        profile_form = json.loads(profile_form_content)
    except json.JSONDecodeError as e:
        st.error(f"Error parsing profile form JSON: {str(e)}")
        st.error(f"Profile form content: {profile_form_content}")
        return None
    except Exception as e:
        st.error(f"Error reading profile form: {str(e)}")
        return None

    chat_prompt = PromptTemplate.from_template(prompt)
    chain = chat_prompt | llm

    try:
        result = chain.invoke({
            "current_date": FIXED_DATE,
            "given_information": given_information,
            "profile_form": json.dumps(profile_form, indent=2),
        })
    except KeyError as e:
        st.error(f"Error: Missing key in prompt template: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

    try:
        # Remove any prefix before the actual JSON content
        result_content = re.sub(
            r'^.*?(\{)', r'\1', result.content, flags=re.DOTALL)
        # Remove any suffix after the JSON content
        result_content = re.sub(
            r'(\})[^}]*$', r'\1', result_content, flags=re.DOTALL)

        # Parse the JSON content
        parsed_json = json.loads(result_content, object_pairs_hook=OrderedDict)

        # Clean the data
        cleaned_result = clean_data(parsed_json)

        # Convert back to JSON string
        json_string = json.dumps(cleaned_result, indent=2)

        # Parse again to ensure it's valid JSON
        parsed_result = json.loads(json_string, object_pairs_hook=OrderedDict)
    except json.JSONDecodeError as e:
        st.error(f"Error parsing JSON: {str(e)}")
        st.error(f"Problematic content: {result_content}")
        return None
    except Exception as e:
        st.error(
            f"An unexpected error occurred while processing the result: {str(e)}")
        return None

    save_to_firebase(firebase_ref, client_number,
                     f"profile_version{profile_version}", parsed_result)
    return parsed_result


@st.cache_data
def history_maker(profile_version, client_number, prompt):
    profile_json = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version}")

    if profile_json is None:
        st.error(
            "Failed to load profile data from Firebase. Unable to generate history.")
        return None

    chat_prompt = PromptTemplate.from_template(prompt)

    chain = chat_prompt | llm

    result = chain.invoke({
        "current_date": FIXED_DATE,
        "profile_json": json.dumps(profile_json, indent=2)
    })

    save_to_firebase(firebase_ref, client_number,
                     f"history_version{profile_version}", result.content)

    return result.content


@st.cache_data
def beh_dir_maker(profile_version, beh_dir_version, client_number, prompt, given_information):
    profile_json = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version}")
    history = load_from_firebase(
        firebase_ref, client_number, f"history_version{profile_version}")

    chat_prompt = PromptTemplate.from_template(prompt)

    chain = chat_prompt | llm

    diag = get_diag_from_given_information(given_information)
    if diag is None:
        st.error("Invalid or unsupported diagnosis in given information.")
        return None

    mse_few_shot_path = f"data/prompts/mse_few_shot/mse_{diag}.txt"

    instruction_form_path = f"data/prompts/instruction_form/instruction_form_{diag}.txt"

    try:
        with open(mse_few_shot_path, "r") as f:
            mse_few_shot_content = f.read()
        with open(instruction_form_path, "r") as f:
            instruction_form_content = f.read()
    except FileNotFoundError as e:
        st.error(f"Error: Required file not found - {e}")
        return None
    except Exception as e:
        st.error(f"Error reading required files: {str(e)}")
        return None

    result = chain.invoke({
        "given_information": given_information,
        "profile_json": json.dumps(profile_json, indent=2),
        "history": history,
        "mse_few_shot": mse_few_shot_content,
        "instruction_form": instruction_form_content
    })

    save_to_firebase(firebase_ref, client_number,
                     f"beh_dir_version{beh_dir_version}", result.content)

    return result.content


@st.cache_resource
def create_conversational_agent(profile_version, beh_dir_version, client_number, system_prompt):
    given_information = load_from_firebase(
        firebase_ref, client_number, "given_information")
    profile_json = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version}")
    history = load_from_firebase(
        firebase_ref, client_number, f"history_version{profile_version}")
    behavioral_instruction = load_from_firebase(
        firebase_ref, client_number, f"beh_dir_version{beh_dir_version}")

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{human_input}")
    ])

    # Switch to langchain_core InMemoryChatMessageHistory
    memory = InMemoryChatMessageHistory()

    chain = chat_prompt | chat_llm

    def agent(human_input):
        # Create a list to pass to the chain with current memory state
        messages = list(memory.messages) if memory.messages else []
        
        response = chain.invoke({
            "given_information": given_information,
            "current_date": FIXED_DATE,
            "profile_json": json.dumps(profile_json, indent=2),
            "history": history,
            "behavioral_instruction": behavioral_instruction,
            "chat_history": messages,
            "human_input": human_input
        })
        memory.add_user_message(human_input)
        memory.add_ai_message(response.content)
        return response.content

    return agent, memory


def save_conversation_to_firebase(firebase_ref, client_number, messages, con_agent_version, participant_name):
    conversation_data = []
    for i in range(0, len(messages), 2):
        human_message = messages[i].content if i < len(messages) else ""
        ai_message = messages[i+1].content if i+1 < len(messages) else ""
        conversation_data.append({
            'human': human_message,
            'simulated_client': ai_message
        })

    timestamp = int(time.time())

    conversation_id = f"conversation_{con_agent_version}_{participant_name}_{timestamp}"

    content = {
        'version': con_agent_version,
        'timestamp': timestamp,
        'participant': participant_name,
        'data': conversation_data
    }

    save_to_firebase(firebase_ref, client_number, conversation_id, content)

    st.success(f"Conversation saved with ID: {conversation_id}")
    return conversation_id
