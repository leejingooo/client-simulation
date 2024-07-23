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

st.set_page_config(
    page_title="All-in-one",
    page_icon="🔥",
)

st.title("All-in-one")


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

firebase_ref = get_firebase_ref()
if firebase_ref is None:
    st.error(
        "Firebase initialization failed. Please check your configuration and try again.")
    st.stop()


def save_to_firebase(ref, client_number, data_type, content):
    if ref is not None:
        try:
            ref.child(f"clients/{client_number}/{data_type}").set(content)
            st.success(f"Data saved successfully for client {client_number}")
        except Exception as e:
            st.error(f"Failed to save data to Firebase: {str(e)}")
    else:
        st.error("Firebase reference is not available. Data not saved.")


def load_from_firebase(ref, client_number, data_type):
    if ref is not None:
        try:
            return ref.child(f"clients/{client_number}/{data_type}").get()
        except Exception as e:
            st.error(f"Error loading data from Firebase: {str(e)}")
    return None


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


# Check if client number already exists
def client_exists(client_number):
    return os.path.exists(f"data/output/client_{client_number}")


def display_loaded_versions(profile_maker_version, history_maker_version, con_agent_version):
    st.success(
        f"Profile-maker version {profile_maker_version} successfully loaded")
    st.success(
        f"History-maker version {history_maker_version} successfully loaded")
    st.success(f"Con-agent version {con_agent_version} successfully loaded")


def format_version(version):
    """Format version to one decimal place"""
    return "{:.1f}".format(float(version))


def extract_version(filename):
    match = re.search(r'version(\d+\.\d)', filename)
    return match.group(1) if match else "1.0"


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


def load_existing_client_data(client_number, profile_version, con_agent_version):
    profile = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version}")
    history = load_from_firebase(
        firebase_ref, client_number, f"history_version{profile_version}")
    beh_dir = load_from_firebase(
        firebase_ref, client_number, f"beh_dir_version{profile_version}")
    con_agent_system_prompt = load_from_firebase(
        firebase_ref, "prompts", f"con_agent_version{con_agent_version}")

    if all([profile, history, beh_dir, con_agent_system_prompt]):
        st.session_state.profile = profile
        st.session_state.history = history
        st.session_state.beh_dir = beh_dir
        return True, con_agent_system_prompt
    else:
        st.error(
            f"Could not find existing client data or the specified prompt versions.")
        return False, None

# Module 1: Profile-maker


@st.cache_data
def profile_maker(form_version, given_information, client_number, system_prompt):
    profile_form_path = "data/profile_form/profile_form_version{}.json".format(
        format_version(form_version))
    if not os.path.exists(profile_form_path):
        st.error(
            f"Profile form version {format_version(form_version)} not found.")
        return None

    try:
        with open(profile_form_path, "r") as f:
            profile_form_content = f.read()

        # Print the content of the file for debugging
        st.write("Profile Form Content:", profile_form_content)

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
        cleaned_result = clean_data(json.loads(result.content))
        json_string = json.dumps(cleaned_result, indent=2)
    except json.JSONDecodeError as e:
        st.error(f"Error parsing result JSON: {str(e)}")
        st.error(f"Raw result content: {result.content}")
        return None

    # Remove <JSON> and </JSON> tags if they exist
    json_string = re.sub(r'<\/?JSON>', '', json_string).strip()

    try:
        parsed_result = json.loads(json_string)
    except json.JSONDecodeError as e:
        st.error(f"Error parsing final JSON: {str(e)}")
        st.error(f"Processed JSON string: {json_string}")
        return None

    save_to_firebase(firebase_ref, client_number,
                     f"profile_version{form_version}", parsed_result)
    return parsed_result
# Module 2: History-maker


@st.cache_data
def history_maker(form_version, client_number, system_prompt):
    profile_json = load_from_firebase(
        firebase_ref, client_number, f"profile_version{form_version}")

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
                <JSON>
                {profile_json}
                </JSON>
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
        firebase_ref, client_number, f"history_version{form_version}", result.content)

    return result.content

# Add this function after the history_maker function


@st.cache_data
def beh_dir_maker(form_version, client_number, system_prompt):
    profile_json = load_from_firebase(
        firebase_ref, client_number, f"profile_version{form_version}")
    history = load_from_firebase(
        firebase_ref, client_number, f"history_version{form_version}")

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
        firebase_ref, client_number, f"beh_dir_version{form_version}", result.content)

    return result.content


# Module 3: Conversational agent
# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'agent_and_memory' not in st.session_state:
    st.session_state.agent_and_memory = None
if 'client_number' not in st.session_state:
    st.session_state.client_number = None
if 'form_version' not in st.session_state:
    st.session_state.form_version = None


@st.cache_resource
def create_conversational_agent(profile_version, client_number, system_prompt):
    profile_json = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version}")
    history = load_from_firebase(
        firebase_ref, client_number, f"history_version{profile_version}")
    behavioral_direction = load_from_firebase(
        firebase_ref, client_number, f"beh_dir_version{profile_version}")

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


def save_conversation_to_firebase(client_number, messages, con_agent_system_prompt_version):
    conversation_data = []
    for i in range(0, len(messages), 2):
        human_message = messages[i].content if i < len(messages) else ""
        ai_message = messages[i+1].content if i+1 < len(messages) else ""
        conversation_data.append({
            'human': human_message,
            'simulated client': ai_message
        })

    # Save to Firebase
    save_to_firebase(
        firebase_ref, client_number, f"conversation_sysprompt_{con_agent_system_prompt_version}", conversation_data)

    return f"conversation_sysprompt_{con_agent_system_prompt_version}"


# Streamlit UI
def main():
    if not check_password():
        st.stop()

    st.title("Client-Simulation")

    # Initialize Firebase at the start of the main function
    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error(
            "Firebase initialization failed. Please check your configuration and try again.")
        st.stop()

    st.sidebar.header("Settings")
    new_client_number = st.sidebar.number_input(
        "Client Number", min_value=1, value=1)

    if st.session_state.client_number != new_client_number:
        st.session_state.client_number = new_client_number
        st.session_state.agent_and_memory = None

    action = st.sidebar.radio(
        "Choose action", ["Load existing data", "Create new data"])

    if action == "Load existing data":
        profile_version = st.sidebar.number_input(
            "Profile Version", min_value=1.0, value=2.0, step=0.1, format="%.1f")
        con_agent_version = st.sidebar.number_input(
            "Con-agent System Prompt Version", min_value=1.0, value=2.0, step=0.1, format="%.1f")

        if st.sidebar.button("Load Data", key="load_data_button"):
            success, con_agent_system_prompt = load_existing_client_data(
                st.session_state.client_number, profile_version, con_agent_version)
            if success:
                st.sidebar.success(
                    f"Loaded existing data for Client {st.session_state.client_number}")
                st.session_state.agent_and_memory = create_conversational_agent(
                    format_version(profile_version), st.session_state.client_number, con_agent_system_prompt)

                # Display loaded versions
                st.success(
                    f"Profile version {format_version(profile_version)} successfully loaded")
                st.success(
                    f"Con-agent version {format_version(con_agent_version)} successfully loaded")
            else:
                st.sidebar.error("Failed to load existing data.")
    else:  # Create new data
        st.sidebar.subheader("Version Settings")
        profile_version = st.sidebar.number_input(
            "Profile Version", min_value=1.0, value=2.0, step=0.1, format="%.1f")
        con_agent_version = st.sidebar.number_input(
            "Con-agent Version", min_value=1.0, value=2.0, step=0.1, format="%.1f")
        beh_dir_version = st.sidebar.number_input(
            "Beh-dir-maker Version", min_value=1.0, value=1.0, step=0.1, format="%.1f")

        # Load prompts based on versions
        profile_system_prompt, actual_profile_version = load_prompt_and_get_version(
            "profile-maker", profile_version)
        history_system_prompt, actual_history_version = load_prompt_and_get_version(
            "history-maker", profile_version)
        con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
            "con-agent", con_agent_version)
        beh_dir_system_prompt, actual_beh_dir_version = load_prompt_and_get_version(
            "beh-dir-maker", beh_dir_version)

        st.sidebar.subheader("Patient Information")
        age = st.sidebar.number_input(
            "Age", min_value=0, max_value=120, value=40)
        gender = st.sidebar.selectbox("Gender", ["Female", "Male", "Other"])
        nationality = st.sidebar.text_input("Nationality", "South Korea")
        diagnosis = st.sidebar.text_input(
            "Diagnosis", "Major depressive disorder")

        given_information = f"""
        <Given information>
        Age : {age}
        Gender : {gender}
        Nationality: {nationality}
        Diagnosis : {diagnosis}
        </Given information>
        """

        if st.sidebar.button("Generate Profile, History, and Behavioral Direction", key="generate_all_button"):
            if all([profile_system_prompt, history_system_prompt, con_agent_system_prompt, beh_dir_system_prompt]):
                with st.spinner("Generating profile..."):
                    profile = profile_maker(format_version(
                        profile_version), given_information, st.session_state.client_number, profile_system_prompt)
                    if profile is not None:
                        st.session_state.profile = profile
                        st.success("Profile generated!")

                        with st.spinner("Generating history..."):
                            history = history_maker(format_version(
                                profile_version), st.session_state.client_number, history_system_prompt)
                            if history is not None:
                                st.session_state.history = history
                                st.success("History generated!")

                                with st.spinner("Generating behavioral direction..."):
                                    beh_dir = beh_dir_maker(format_version(
                                        profile_version), st.session_state.client_number, beh_dir_system_prompt)
                                    if beh_dir is not None:
                                        st.session_state.beh_dir = beh_dir
                                        st.success(
                                            "Behavioral direction generated!")

                                        st.session_state.agent_and_memory = create_conversational_agent(
                                            format_version(profile_version), st.session_state.client_number, con_agent_system_prompt)

                                        # Display loaded versions
                                        st.success(
                                            f"Profile version {actual_profile_version} successfully loaded")
                                        st.success(
                                            f"Con-agent version {actual_con_agent_version} successfully loaded")
                                        st.success(
                                            f"Beh-dir-maker version {actual_beh_dir_version} successfully loaded")
                                    else:
                                        st.error(
                                            "Failed to generate behavioral direction.")
                            else:
                                st.error("Failed to generate history.")
                    else:
                        st.error(
                            "Failed to generate profile. Please check the error messages above.")
            else:
                st.error(
                    "Failed to load one or more prompts. Please check the version settings.")

    # Main area for conversation
    st.header("Conversation with Simulated Client")

    if st.session_state.agent_and_memory:
        agent, memory = st.session_state.agent_and_memory
        for message in memory.chat_memory.messages:
            with st.chat_message("user" if isinstance(message, HumanMessage) else "assistant"):
                st.markdown(message.content)

        if prompt := st.chat_input("Interviewer:"):
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = agent(prompt)
                message_placeholder.markdown(full_response)
    else:
        st.warning(
            "Please load existing data or generate a new profile and history.")

    if st.button("End/Save Conversation", key="end_save_conversation_button"):
        if st.session_state.client_number is not None and st.session_state.agent_and_memory is not None:
            _, memory = st.session_state.agent_and_memory

            con_agent_system_prompt_version = load_from_firebase(
                firebase_ref, "prompts", f"con_agent_version{con_agent_version}")
            if con_agent_system_prompt_version:
                filename = save_conversation_to_firebase(
                    st.session_state.client_number,
                    memory.chat_memory.messages,
                    con_agent_system_prompt_version
                )
                st.success(
                    f"Conversation saved to Firebase for Client {st.session_state.client_number}!")
            else:
                st.error(
                    "Could not find the con-agent system prompt used for this client.")
        else:
            st.error(
                "Unable to save conversation. Client number is not set or no conversation has taken place.")


if __name__ == "__main__":
    main()
