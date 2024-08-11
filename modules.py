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
from Home import check_password
from firebase_config import get_firebase_ref
import json
import time
from collections import OrderedDict

# Initialize the language model
llm = ChatOpenAI(
    temperature=0.7,
    model="gpt-4o",
)

# 나중에 cover_agent는 이걸로 교체
chat_llm = ChatOpenAI(
    temperature=0.7,
    model="gpt-4o",
    streaming=True,
    callbacks=[StreamingStdOutCallbackHandler()]
)

# Fixed date
FIXED_DATE = "01/07/2024"

# Initialize Firebase
firebase_ref = get_firebase_ref()
if firebase_ref is None:
    st.error(
        "Firebase initialization failed. Please check your configuration and try again.")
    st.stop()
else:
    st.success("Firebase initialized successfully")


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


def save_to_firebase(firebase_ref, client_number, data_type, content):
    if firebase_ref is not None:
        try:
            # Replace decimal point with underscore in data_type if it contains a version number
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
            # Replace decimal point with underscore in data_type if it contains a version number
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


# Load prompts from files
@st.cache_data
def load_prompt(selected_file):
    prompt_path = selected_file
    if os.path.exists(prompt_path):
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            st.error(f"Error reading the file: {e}")
            return ""
    else:
        st.error("File does not exist.")
        return ""

# Function to get a list of files in a folder


def get_file_list(folder_path):
    try:
        file_list = os.listdir(folder_path)
        return [file for file in file_list if os.path.isfile(os.path.join(folder_path, file))]
    except Exception as e:
        st.error(f"Error: {e}")
        return []


def select_prompt(module_name, new_or_loaded):
    # Folder path
    folder_path = f"data/prompts/{module_name}_system_prompt"
    # Get list of files in the folder
    file_list = get_file_list(folder_path)

    if file_list:
        # Display the list of files in a selectbox
        selected_file = st.selectbox(
            f"Select a {module_name} SYSTEM prompt For {new_or_loaded}:", file_list, key=f"{module_name}_system_prompt_for_{new_or_loaded}")

        if selected_file:
            selected_file_path = os.path.join(folder_path, selected_file)
            return load_prompt(selected_file_path)
    else:
        st.warning("No files found in the selected folder.")

    return ""


def display_loaded_versions(profile_maker_version, history_maker_version, con_agent_version):
    st.success(
        f"Profile-maker version {profile_maker_version} successfully loaded")
    st.success(
        f"History-maker version {history_maker_version} successfully loaded")
    st.success(
        f"Con-agent version {con_agent_version} successfully loaded")


def format_version(version):
    """Format version to one decimal place"""
    return "{:.1f}".format(float(version))


def extract_version(filename):
    match = re.search(r'version(\d+\.\d)', filename)
    return match.group(1) if match else st.error("extract_version error")


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


def load_existing_client_data(client_number, profile_version, beh_dir_version):
    profile_version_formatted = f"{profile_version:.1f}".replace(".", "_")
    beh_dir_version_formatted = f"{beh_dir_version:.1f}".replace(".", "_")

    profile = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version_formatted}")
    history = load_from_firebase(
        firebase_ref, client_number, f"history_version{profile_version_formatted}")
    beh_dir = load_from_firebase(
        firebase_ref, client_number, f"beh_dir_version{beh_dir_version_formatted}")

    if all([profile, history, beh_dir]):
        st.session_state.profile = profile
        st.session_state.history = history
        st.session_state.beh_dir = beh_dir
        return True
    else:
        st.error(
            f"Could not find existing client data or the specified prompt versions.")
        return False

# Module 1: Profile-maker


@st.cache_data
def profile_maker(profile_version, given_information, client_number, system_prompt):
    profile_form_path = "data/profile_form/profile_form_version{}.json".format(
        format_version(profile_version))
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

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                system_prompt
            ),
            (
                "human",
                given_information
            )
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

        # Check if cleaned_result is a string before applying re.sub
        if isinstance(cleaned_result, str):
            # Remove <JSON> and </JSON> tags if they exist
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

# Module 2: History-maker


@st.cache_data
def history_maker(profile_version, client_number, system_prompt):
    profile_json = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version}")

    if profile_json is None:
        st.error(
            "Failed to load profile data from Firebase. Unable to generate history.")
        return None

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                system_prompt
            ),
            (
                "human",
                """
                <Profile_JSON>
                {profile_json}
                </Profile_JSON>
                """
            )
        ]
    )

    chain = chat_prompt | llm

    result = chain.invoke({
        "current_date": FIXED_DATE,
        "profile_json": json.dumps(profile_json, indent=2)
    })

    save_to_firebase(
        firebase_ref, client_number, f"history_version{profile_version}", result.content)

    return result.content

# Add this function after the history_maker function


@st.cache_data
def beh_dir_maker(profile_version, beh_dir_version, client_number, system_prompt):
    profile_json = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version}")
    history = load_from_firebase(
        firebase_ref, client_number, f"history_version{profile_version}")

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                system_prompt
            ),
            (
                "human",
                """
                <Profile_JSON>
                {profile_json}
                </Profile_JSON>
                <History>
                {history}
                </History>
                """
            )
        ]
    )

    chain = chat_prompt | llm

    result = chain.invoke({
        "profile_json": json.dumps(profile_json, indent=2),
        "history": history
    })

    # Save the result
    save_to_firebase(
        firebase_ref, client_number, f"beh_dir_version{beh_dir_version}", result.content)

    return result.content


# Module 3: Conversational agent
# Initialize session state
if 'agent_and_memory' not in st.session_state:
    st.session_state.agent_and_memory = None
if 'client_number' not in st.session_state:
    st.session_state.client_number = None
if 'profile_version' not in st.session_state:
    st.session_state.profile_version = None


@st.cache_resource
def create_conversational_agent(profile_version, beh_dir_version, client_number, system_prompt):
    profile_json = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version}")
    history = load_from_firebase(
        firebase_ref, client_number, f"history_version{profile_version}")
    behavioral_direction = load_from_firebase(
        firebase_ref, client_number, f"beh_dir_version{beh_dir_version}")

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{human_input}")
        ]
    )

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
# Save conversation to Excel


def save_conversation_to_firebase(firebase_ref, client_number, messages, con_agent_version):
    conversation_data = []
    for i in range(0, len(messages), 2):
        human_message = messages[i].content if i < len(messages) else ""
        ai_message = messages[i+1].content if i+1 < len(messages) else ""
        conversation_data.append({
            'human': human_message,
            'simulated_client': ai_message
        })

    # Create a unique identifier for this conversation
    timestamp = int(time.time())
    conversation_id = f"conversation_{con_agent_version}_{timestamp}"

    # Prepare the content to be saved
    content = {
        'version': con_agent_version,
        'timestamp': timestamp,
        'data': conversation_data
    }

    # Save the conversation data to Firebase
    save_to_firebase(firebase_ref, client_number, conversation_id, content)

    st.success(f"Conversation saved with ID: {conversation_id}")
    return conversation_id