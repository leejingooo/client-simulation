import json
import os
import re
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import streamlit as st

# Make sure to set your OpenAI API key
os.environ["OPENAI_API_KEY"] = "your-api-key-here"

# Initialize the language model
llm = ChatOpenAI(temperature=0.7)

# Fixed date
FIXED_DATE = "07/01/2024"

# Load prompts from files


@st.cache_data
def load_prompt(uploaded_file):
    if uploaded_file is not None:
        return uploaded_file.getvalue().decode("utf-8")
    return ""

# Extract version number from filename


def extract_version(filename):
    match = re.search(r'version(\d+(?:\.\d+)?)\.json$', filename)
    return match.group(1) if match else "1.0"

# Check if client number already exists


def client_exists(client_number):
    return os.path.exists(f"profile_client{client_number}_version1.json") or \
        os.path.exists(f"history_client{client_number}_version1.txt")

# Module 1: Profile-maker


@st.cache_data
def profile_maker(form_version, given_information, client_number, system_prompt, human_prompt):
    with open(f"profile_form_version{form_version}.json", "r") as f:
        profile_form = json.load(f)

    chat_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ])

    chain = chat_prompt | llm

    result = chain.invoke({
        "current_date": FIXED_DATE,
        "profile_form": json.dumps(profile_form, indent=2),
        "given_information": given_information
    })

    # Save the result
    with open(f"profile_client{client_number}_version{form_version}.json", "w") as f:
        json.dump(json.loads(result.content), f, indent=2)

    return result.content

# Module 2: History-maker


@st.cache_data
def history_maker(profile_version, client_number, system_prompt, human_prompt):
    with open(f"profile_client{client_number}_version{profile_version}.json", "r") as f:
        profile_json = json.load(f)

    chat_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ])

    chain = chat_prompt | llm

    result = chain.invoke({
        "current_date": FIXED_DATE,
        "profile_json": json.dumps(profile_json, indent=2)
    })

    # Save the result
    with open(f"history_client{client_number}_version{profile_version}.txt", "w") as f:
        f.write(result.content)

    return result.content

# Module 3: Conversational agent


@st.cache_resource
def create_conversational_agent(profile_version, client_number, system_prompt, human_prompt):
    with open(f"profile_client{client_number}_version{profile_version}.json", "r") as f:
        profile_json = json.load(f)

    with open(f"history_client{client_number}_version{profile_version}.txt", "r") as f:
        history = f.read()

    chat_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ])

    chain = chat_prompt | llm

    return lambda human_input: chain.invoke({
        "current_date": FIXED_DATE,
        "profile_json": json.dumps(profile_json, indent=2),
        "history": history,
        "human_input": human_input
    }).content

# Streamlit UI


def main():
    st.title("Psychiatric Evaluation Framework")

    # Sidebar for input and file uploads
    st.sidebar.header("Settings")
    client_number = st.sidebar.number_input(
        "Client Number", min_value=1, value=1)

    if client_exists(client_number):
        st.sidebar.error("Cannot proceed due to duplicate client number")
        return

    form_version = extract_version(st.sidebar.file_uploader("Upload profile form JSON", type="json").name if st.sidebar.file_uploader(
        "Upload profile form JSON", type="json") else "profile_form_version1.0.json")

    st.sidebar.header("Upload Prompts")
    profile_system_prompt = load_prompt(st.sidebar.file_uploader(
        "Profile Maker System Prompt", type="txt"))
    profile_human_prompt = load_prompt(st.sidebar.file_uploader(
        "Profile Maker Human Prompt", type="txt"))
    history_system_prompt = load_prompt(st.sidebar.file_uploader(
        "History Maker System Prompt", type="txt"))
    history_human_prompt = load_prompt(st.sidebar.file_uploader(
        "History Maker Human Prompt", type="txt"))
    agent_system_prompt = load_prompt(st.sidebar.file_uploader(
        "Conversational Agent System Prompt", type="txt"))
    agent_human_prompt = load_prompt(st.sidebar.file_uploader(
        "Conversational Agent Human Prompt", type="txt"))

    st.sidebar.header("Patient Information")
    age = st.sidebar.number_input("Age", min_value=0, max_value=120, value=24)
    gender = st.sidebar.selectbox("Gender", ["Female", "Male", "Other"])
    nationality = st.sidebar.text_input("Nationality", "South Korea")
    diagnosis = st.sidebar.text_input("Diagnosis", "Major depressive disorder")

    given_information = f"""
    Age : {age}
    Gender : {gender}
    Nationality: {nationality}
    Diagnosis : {diagnosis}
    """

    if st.sidebar.button("Generate Profile and History"):
        with st.spinner("Generating profile..."):
            profile = profile_maker(form_version, given_information,
                                    client_number, profile_system_prompt, profile_human_prompt)
            st.session_state.profile = profile
            st.success("Profile generated!")

        with st.spinner("Generating history..."):
            history = history_maker(
                form_version, client_number, history_system_prompt, history_human_prompt)
            st.session_state.history = history
            st.success("History generated!")

        st.session_state.agent = create_conversational_agent(
            form_version, client_number, agent_system_prompt, agent_human_prompt)

    # Main area for conversation
    st.header("Conversation with Patient")

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Interviewer:"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if 'agent' in st.session_state:
            with st.chat_message("assistant"):
                with st.spinner("Patient is thinking..."):
                    response = st.session_state.agent(prompt)
                    st.markdown(response)
            st.session_state.messages.append(
                {"role": "assistant", "content": response})
        else:
            st.warning("Please generate profile and history first.")


if __name__ == "__main__":
    main()
