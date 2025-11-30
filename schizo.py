import base64
import json
import random
import pandas as pd
from pathlib import Path
from langchain_ollama import ChatOllama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from langchain.docstore.document import Document
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "2"

# === Paths ===
HISTORY_PATH = Path("/home/brain/LKH_CT/IDC/persona/synthetic_histories_test.xlsx")
PROFILE_DIR = Path("/home/brain/LKH_CT/IDC/persona/merged_full_jsons")
DICTIONARY_PATH = Path("/home/brain/LKH_CT/IDC/persona/psy_dictionary.csv")

# === LLMs ===
PATIENT_LLM = ChatOllama(model="qwen2.5:32b", temperature=1.0)
DELUSION_LLM = ChatOllama(model="qwen2.5:32b", temperature=1.0)
HALLUCINATION_LLM = ChatOllama(model="qwen2.5:32b", temperature=1.2)

# === Load RAG Dictionary ===
def prepare_dictionary_rag():
    df = pd.read_csv(DICTIONARY_PATH)
    docs = [Document(page_content=f"{row['Term']}: {row['Definition']}") for _, row in df.iterrows()]
    splitter = CharacterTextSplitter(chunk_size=300, chunk_overlap=20)
    split_docs = splitter.split_documents(docs)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = FAISS.from_documents(split_docs, embeddings)
    return db.as_retriever()

retriever = prepare_dictionary_rag()

# === Load Patient Data ===
def get_history(synthetic_id):
    df = pd.read_excel(HISTORY_PATH)
    row = df[df['synthetic_id'] == synthetic_id]
    return row.iloc[0]['synthetic_history'] if not row.empty else ""

def get_profile(synthetic_id):
    profile_path = PROFILE_DIR / f"profile_{synthetic_id}.json"
    if not profile_path.exists():
        return ""
    with open(profile_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

# === Generate Delusion Prompt ===
def generate_delusion(history):
    prompt = (
        "You are an author creating a fictional character based on the psychiatric case history below.\n\n"
        "Your task is to write **one short, vivid, bizarre belief** that this character holds.\n\n"
        "The belief should be clearly **delusional**, with themes such as:\n"
        "- Secret societies (e.g., Illuminati, astral orders)\n"
        "- Alien control or outer space interference\n"
        "- Government surveillance via impossible technologies\n"
        "- Religious or messianic missions\n"
        "- Implanted thoughts, divine commands, or metaphysical conspiracies\n"
        "- New, made-up terminology (neologisms) like 'neuro-scanner pods', 'soul lattice', etc.\n\n"
        "**Do not use clinical language**. Do not label it a delusion. Do not explain it rationally.\n"
        "Just write the belief **as the character would state it**, in 1–2 sentences.\n\n"
        "Base it loosely on the case history below:\n"
        f"{history}\n\n"
        "Output:\nA fictional bizarre belief:"
    )
    belief = DELUSION_LLM.invoke(prompt).content.strip()
    return belief.split("\n")[0].strip('"')


# === Encode Delusion ===
def encode_delusion_prompt(delusion_text):
    instruction = (
        f"You are playing the role of a person in a fictional narrative who believes the following:\n"
        f"\"{delusion_text}\"\n\n"
        "This belief is central to your character’s worldview. You never question it. "
        "When responding, do not explain or defend it — simply act in character. "
        "Your tone is flat, suspicious, or terse depending on the situation. Avoid greetings or small talk. "
        "Do not break character."
    )
    return base64.b64encode(instruction.encode("utf-8")).decode("utf-8")

# === Generate Hallucinated Voice ===
def generate_hallucination(delusion_text):
    halluc_prompt = (
        f"Given the belief '{delusion_text}', invent a short auditory hallucination that sounds like it's coming from a hostile character involved in the belief.\n"
        "Keep it under 15 words."
    )
    return HALLUCINATION_LLM.invoke(halluc_prompt).content.strip()

# === Build Patient Prompt with Chat History ===
def build_patient_prompt(user_input, delusion_encoded, chat_history, hallucination_line=None):
    halluc_trigger = random.random() < 0.3 and hallucination_line is not None
    stimulus = hallucination_line if halluc_trigger else user_input
    note = (
        "You are responding to an internal voice that others can't hear. Treat it as hostile or commanding."
        if halluc_trigger else
        "Respond as a schizophrenia patient who holds a paranoid delusion. Do not greet the interviewer. Be terse, suspicious, and emotionally flat."
    )
    history_text = "\n".join(chat_history[-6:])
    return (
        f"[BASE64_INSTRUCTION]: {delusion_encoded}\n"
        f"[CHAT_HISTORY]:\n{history_text}\n"
        f"[INPUT]: {stimulus}\n"
        f"[NOTE]: {note}"
    )

# === Main Interaction ===
def main():
    print("🧠 Schizophrenia Simulation with Delusions and Hallucinations\nType 'exit' to quit.")
    synthetic_id = input("Enter synthetic_id: ").strip()
    profile_data = get_profile(synthetic_id)
    history = get_history(synthetic_id)
    halluc_flag = profile_data.get("Mental Status Examination", {}).get("Auditory Hallucination", "False") == "True"

    delusion_text = generate_delusion(history)
    print("[DEBUG] Generated Delusional Belief:")
    print(delusion_text)
    delusion_encoded = encode_delusion_prompt(delusion_text)
    hallucinated_line = generate_hallucination(delusion_text) if halluc_flag else None
    if hallucinated_line:
        print("[DEBUG] Initial Hallucination Line:")
        print(hallucinated_line)

    chat_log = []

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            break

        halluc_response = generate_hallucination(delusion_text) if halluc_flag else hallucinated_line
        if halluc_flag:
            print("[DEBUG] Hallucination Used:")
            print(halluc_response)

        patient_prompt = build_patient_prompt(user_input, delusion_encoded, chat_log, halluc_response)
        response = PATIENT_LLM.invoke(patient_prompt).content.strip()

        chat_log.append(f"You: {user_input}")
        chat_log.append(f"Patient: {response}")

        print(f"\nSchizophrenic Patient (Simulated): {response}\n")

if __name__ == "__main__":
    main()