import streamlit as st
from PACA_claude2_utils import create_paca_agent, simulate_conversation, save_ai_conversation_to_firebase, save_conversation_to_csv
from SP_utils import create_conversational_agent, load_from_firebase, get_diag_from_given_information, load_prompt_and_get_version
from firebase_config import get_firebase_ref
# from langchain.schema import HumanMessage, AIMessage
import time
# from langchain.chat_models import ChatOpenAI, ChatAnthropic
# from langchain_openai import ChatOpenAI
# from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.chat_history import InMemoryChatMessageHistory
from SP_utils import create_conversational_agent, save_to_firebase
try:
    from sp_construct_generator import create_sp_construct
except Exception:
    create_sp_construct = None

try:
    from paca_construct_generator import create_paca_construct
except Exception:
    create_paca_construct = None

# PRESET
profile_version = 6.0
beh_dir_version = 6.0
con_agent_version = 6.0
paca_version = 3.0


def construct_generator_conversation_new(paca_agent):
    """
    Generate PACA construct using the new structured approach.
    This creates a construct with the same structure as SP construct.
    """
    if create_paca_construct is None:
        st.error("PACA construct generator not available (missing module 'paca_construct_generator').")
        return None
    
    try:
        with st.spinner("Generating PACA construct from conversation..."):
            paca_construct = create_paca_construct(paca_agent)
        return paca_construct
    except Exception as e:
        st.error(f"Failed to create PACA construct: {e}")
        return None


def experiment_page(client_number):
    st.set_page_config(
        page_title=f"AI-to-AI Experiment - Client {client_number}",
        page_icon="🤖",
    )

    firebase_ref = get_firebase_ref()
    if firebase_ref is None:
        st.error(
            "Firebase initialization failed. Please check your configuration and try again.")
        st.stop()

    st.title(f"AI-to-AI Conversation Experiment - Client {client_number}")

    # Load SP data
    profile = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version:.1f}".replace(".", "_"))
    history = load_from_firebase(
        firebase_ref, client_number, f"history_version{profile_version:.1f}".replace(".", "_"))
    beh_dir = load_from_firebase(
        firebase_ref, client_number, f"beh_dir_version{beh_dir_version:.1f}".replace(".", "_"))
    given_information = load_from_firebase(
        firebase_ref, client_number, "given_information")

    if all([profile, history, beh_dir, given_information]):
        diag = get_diag_from_given_information(given_information)

        # Create SP agent
        if diag == "BD":
            con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
                "con-agent", con_agent_version, diag)
            st.success("BD success")
        else:
            con_agent_system_prompt, actual_con_agent_version = load_prompt_and_get_version(
                "con-agent", con_agent_version)

        if con_agent_system_prompt:
            sp_agent, sp_memory = create_conversational_agent(
                f"{profile_version:.1f}".replace(".", "_"),
                f"{beh_dir_version:.1f}".replace(".", "_"),
                client_number,
                con_agent_system_prompt
            )
        else:
            st.error("Failed to load SP system prompt.")
            st.stop()

        # Create PACA agent
        if 'paca_agent' not in st.session_state or st.session_state.get('force_paca_update', False):
            st.session_state.paca_agent, st.session_state.paca_memory, actual_paca_version = create_paca_agent(
                paca_version)

        paca_agent = st.session_state.paca_agent
        paca_memory = st.session_state.paca_memory

        st.success("SP and PACA agents loaded successfully.")

        # Initialize session state
        if 'conversation' not in st.session_state:
            st.session_state.conversation = []
        if 'conversation_generator' not in st.session_state:
            st.session_state.conversation_generator = simulate_conversation(
                paca_agent, sp_agent)
        if 'constructs' not in st.session_state:
            st.session_state.constructs = None
        if 'sp_construct' not in st.session_state:
            st.session_state.sp_construct = None

        # Conversation area
        conversation_area = st.empty()

        # Button to generate conversation
        if st.sidebar.button("Generate Conversation"):
            while True:
                try:
                    next_turn = next(st.session_state.conversation_generator)
                    st.session_state.conversation.append(next_turn)

                    # Update conversation display
                    with conversation_area.container():
                        for speaker, message in st.session_state.conversation:
                            with st.chat_message(speaker):
                                st.write(message)

                except StopIteration:
                    break

                # Add a small delay to allow for visual updates
                time.sleep(0.1)

        # Button to stop conversation and generate constructs
        if st.sidebar.button("Stop and Generate Constructs"):
            if st.session_state.constructs is None:
                st.session_state.constructs = construct_generator_conversation(
                        paca_agent, paca_memory)
                st.success("Constructs generated!")
            st.rerun()

        # Display the conversation
        with conversation_area.container():
            for speaker, message in st.session_state.conversation:
                with st.chat_message(speaker):
                    st.write(message)

        # Display constructs if they have been generated
        if st.session_state.constructs:
            st.subheader("Construct Generator Output")
            for construct, value in st.session_state.constructs.items():
                st.write(f"{construct}: {value}")

        # Save conversation button
        if st.button("Save Conversation and Constructs"):
            conversation_id = save_ai_conversation_to_firebase(
                firebase_ref,
                client_number,
                st.session_state.conversation,
                actual_paca_version,
                actual_con_agent_version
            )

            if st.session_state.constructs:
                save_to_firebase(firebase_ref, client_number,
                                 f"constructs_{conversation_id}", st.session_state.constructs)

            # Also save PACA constructs under a versioned key so evaluator can load it
            if st.session_state.constructs:
                try:
                    save_to_firebase(firebase_ref, client_number,
                                     f"paca_construct_version{actual_paca_version}", st.session_state.constructs)
                except Exception as e:
                    st.error(f"Failed to save PACA construct under versioned key: {e}")

            st.success(
                f"Conversation and constructs saved with ID: {conversation_id}")

        if st.sidebar.button("Create SP Construct"):
            if create_sp_construct is None:
                st.error("SP construct generator not available (missing module 'sp_construct_generator').")
            else:
                given_form_path = f"data/prompts/paca_system_prompt/given_form_version{paca_version}.json"
                try:
                    sp_construct = create_sp_construct(
                        client_number,
                        f"{profile_version:.1f}",
                        f"{beh_dir_version:.1f}",
                        given_form_path,
                    )
                    if sp_construct:
                        st.session_state.sp_construct = sp_construct
                        st.success("SP Construct generated!")
                    else:
                        st.error("SP Construct generation returned no result.")
                except Exception as e:
                    st.error(f"Failed to create SP construct: {e}")
            st.rerun()

        # Display SP construct if it has been generated
        if st.session_state.sp_construct:
            st.subheader("SP Construct Output")
            st.json(st.session_state.sp_construct)
            
            # Save SP construct button
            if st.button("Save SP Construct"):
                try:
                    save_to_firebase(firebase_ref, client_number,
                                     f"sp_construct_version{paca_version}", st.session_state.sp_construct)
                    st.success("SP Construct saved successfully!")
                except Exception as e:
                    st.error(f"Failed to save SP construct: {e}")

        if st.session_state.conversation:
            csv_data = save_conversation_to_csv(st.session_state.conversation)
            st.download_button(
                label="Download Conversation as CSV",
                data=csv_data,
                file_name="conversation.csv",
                mime="text/csv"
            )

    else:
        st.error(
            "Failed to load client data. Please check if the data exists for the specified versions.")
