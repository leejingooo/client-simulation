import streamlit as st
from Home import check_participant
from firebase_config import get_firebase_ref
from SP_utils import *
import uuid

instructions = """
    환자 시뮬레이션 페이지에 오신 것을 환영합니다.
    당신은 정신과 환자와 면담하는 의사입니다.
    "안녕하세요, 저는 정신과 의사 OOO 입니다." 으로 대화를 시작하세요.
    
    Welcome to the Patient Simulation Page.
    You are a doctor interviewing a psychiatric patient.
    Begin the conversation with "Hello, I am Dr. OOO, a psychiatrist."
    """


def get_session_id():
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    return st.session_state.session_id


def validation_page(client_number, profile_version=5.0, beh_dir_version=5.0, con_agent_version=5.0):
    st.set_page_config(
        page_title="정신과 환자의 다면적 시뮬레이션",
        page_icon="🔬",
    )

    # Get unique session ID for this user
    session_id = get_session_id()

    # Initialize Firebase
    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error(
            "Firebase initialization failed. Please check your configuration and try again.")
        st.stop()

    if not check_participant():
        st.stop()

    st.title("정신과 환자의 다면적 시뮬레이션")

    st.write(instructions, unsafe_allow_html=True)

    # Store chat memory in session state with unique key for this user
    if f'chat_memory_{session_id}' not in st.session_state:
        st.session_state[f'chat_memory_{session_id}'] = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history"
        )

    # Load data only if not already in session state for this user
    if f'profile_{session_id}' not in st.session_state:
        profile = load_from_firebase(
            firebase_ref,
            client_number,
            f"profile_version{profile_version:.1f}".replace(".", "_")
        )
        if profile:
            st.session_state[f'profile_{session_id}'] = profile

    if f'history_{session_id}' not in st.session_state:
        history = load_from_firebase(
            firebase_ref,
            client_number,
            f"history_version{profile_version:.1f}".replace(".", "_")
        )
        if history:
            st.session_state[f'history_{session_id}'] = history

    if f'beh_dir_{session_id}' not in st.session_state:
        beh_dir = load_from_firebase(
            firebase_ref,
            client_number,
            f"beh_dir_version{beh_dir_version:.1f}".replace(".", "_")
        )
        if beh_dir:
            st.session_state[f'beh_dir_{session_id}'] = beh_dir

    # Check if all required data is loaded for this user
    if all([
        f'profile_{session_id}' in st.session_state,
        f'history_{session_id}' in st.session_state,
        f'beh_dir_{session_id}' in st.session_state
    ]):
        given_information = load_from_firebase(
            firebase_ref, client_number, "given_information")
        diag = get_diag_from_given_information(given_information)

        if diag == "BD":
            con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
                "con-agent", con_agent_version, diag)
        else:
            con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
                "con-agent", con_agent_version)

        if con_agent_system_prompt:
            # Create or get agent for this session
            if f'agent_{session_id}' not in st.session_state:
                chat_prompt = ChatPromptTemplate.from_messages([
                    ("system", con_agent_system_prompt),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{human_input}")
                ])

                def create_agent_for_session():
                    def agent(human_input):
                        response = chat_llm(chat_prompt.format_messages(
                            given_information=given_information,
                            current_date=FIXED_DATE,
                            profile_json=json.dumps(
                                st.session_state[f'profile_{session_id}'], indent=2),
                            history=st.session_state[f'history_{session_id}'],
                            behavioral_instruction=st.session_state[f'beh_dir_{session_id}'],
                            chat_history=st.session_state[f'chat_memory_{session_id}'].chat_memory.messages,
                            human_input=human_input
                        ))
                        st.session_state[f'chat_memory_{session_id}'].chat_memory.add_user_message(
                            human_input)
                        st.session_state[f'chat_memory_{session_id}'].chat_memory.add_ai_message(
                            response.content)
                        return response.content

                    return agent

                st.session_state[f'agent_{session_id}'] = create_agent_for_session(
                )

    # Display chat interface
    st.header("Simulated Session")

    if f'agent_{session_id}' in st.session_state:
        # Display chat history for this session
        for message in st.session_state[f'chat_memory_{session_id}'].chat_memory.messages:
            with st.chat_message("user" if isinstance(message, HumanMessage) else "assistant"):
                st.markdown(message.content)

        # Chat input
        if prompt := st.chat_input("Interviewer:"):
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = st.session_state[f'agent_{session_id}'](prompt)
                message_placeholder.markdown(full_response)

    # Buttons for conversation management
    if st.button("Start New Conversation"):
        if f'chat_memory_{session_id}' in st.session_state:
            st.session_state[f'chat_memory_{session_id}'].chat_memory.clear()
            st.success("New conversation started with the same client data.")
            st.rerun()

    if st.button("End/Save Conversation"):
        if f'chat_memory_{session_id}' in st.session_state:
            if 'name' in st.session_state and st.session_state['name_correct']:
                participant_name = st.session_state['name']
                filename = save_conversation_to_firebase(
                    firebase_ref,
                    client_number,
                    st.session_state[f'chat_memory_{session_id}'].chat_memory.messages,
                    con_agent_version,
                    participant_name
                )
                if filename:
                    st.success(
                        f"Conversation saved to Firebase for Client {client_number} by {participant_name}!")
