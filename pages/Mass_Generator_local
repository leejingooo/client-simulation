from pages.all_in_one_local import (
    load_prompt,
    get_file_list,
    select_prompt,
    client_exists,
    profile_maker,
    history_maker
)
from langchain.chat_models import ChatOpenAI
import pandas as pd
import json
import sys
import os
import streamlit as st

# Set page config at the very beginning
st.set_page_config(
    page_title="Mass Generator",
    page_icon="🔄",
)


# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Now import from the All-in-one page

st.title("Mass Profile/History Generator")

# Initialize the language model
llm = ChatOpenAI(
    temperature=0.7,
    model="gpt-4",
)

# Fixed date
FIXED_DATE = "01/07/2024"


def generate_clients(start_num, end_num, form_version, profile_system_prompt, history_system_prompt, given_information):
    existing_clients = []
    generated_clients = []

    for client_num in range(start_num, end_num + 1):
        if client_exists(client_num):
            existing_clients.append(client_num)
        else:
            with st.spinner(f"Generating client {client_num}..."):
                profile = profile_maker(
                    form_version, given_information, client_num, profile_system_prompt)
                if profile is not None:
                    history = history_maker(
                        form_version, client_num, history_system_prompt)
                    generated_clients.append(client_num)
                else:
                    st.error(
                        f"Failed to generate profile for client {client_num}")

    return existing_clients, generated_clients


def main():
    st.sidebar.header("Settings")

    # Input for client number range
    start_num = st.sidebar.number_input(
        "Start Client Number", min_value=1, value=1)
    end_num = st.sidebar.number_input(
        "End Client Number", min_value=start_num, value=start_num)

    form_version = st.sidebar.number_input(
        "Form Version", min_value=1.0, value=1.0, step=0.1)

    st.sidebar.header("Select Prompts")
    profile_system_prompt = select_prompt("profile-maker", "new")
    history_system_prompt = select_prompt("history-maker", "new")

    st.sidebar.header("Patient Information")
    age = st.sidebar.number_input("Age", min_value=0, max_value=120, value=24)
    gender = st.sidebar.selectbox("Gender", ["Female", "Male", "Other"])
    nationality = st.sidebar.text_input("Nationality", "South Korea")
    diagnosis = st.sidebar.text_input("Diagnosis", "Major depressive disorder")

    given_information = f"""
    <Given information>
    Age : {age}
    Gender : {gender}
    Nationality: {nationality}
    Diagnosis : {diagnosis}
    </Given information>
    """

    if st.sidebar.button("Generate Clients"):
        existing_clients, generated_clients = generate_clients(
            start_num, end_num, form_version, profile_system_prompt, history_system_prompt, given_information
        )

        if existing_clients:
            st.warning(
                f"The following client numbers already exist: {', '.join(map(str, existing_clients))}")

        if generated_clients:
            st.success(
                f"Successfully generated data for clients: {', '.join(map(str, generated_clients))}")

        if not generated_clients and not existing_clients:
            st.info("No new clients were generated.")

    # Display generated clients
    st.header("Generated Clients")
    if os.path.exists("data/output"):
        clients = [d for d in os.listdir(
            "data/output") if d.startswith("client_")]
        if clients:
            client_data = []
            for client in clients:
                client_num = client.split("_")[1]
                profile_path = f"data/output/{client}/profile_{client}_version{form_version}.json"
                if os.path.exists(profile_path):
                    try:
                        with open(profile_path, 'r') as f:
                            profile = json.load(f)
                        client_data.append({
                            "Client Number": client_num,
                            "Name": profile.get("name", "N/A"),
                            "Age": profile.get("age", "N/A"),
                            "Gender": profile.get("gender", "N/A"),
                            "Diagnosis": profile.get("diagnosis", "N/A")
                        })
                    except json.JSONDecodeError:
                        st.error(
                            f"Error reading profile for client {client_num}. The file may be empty or not properly formatted.")

            if client_data:
                df = pd.DataFrame(client_data)
                st.dataframe(df)
            else:
                st.info("No valid client data found.")
        else:
            st.info("No clients have been generated yet.")
    else:
        st.info("No output directory found. Generate some clients to see data.")


if __name__ == "__main__":
    main()
