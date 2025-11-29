import pandas as pd
import json
from typing import Dict, Any, List, Tuple
from langchain.chat_models import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from SP_utils import load_from_firebase, get_firebase_ref
import streamlit as st

llm = ChatOpenAI(temperature=0, model="gpt-4o")


def load_given_form(form_path: str) -> Dict[str, Any]:
    with open(form_path, 'r') as f:
        return json.load(f)


def is_multiple_choice(field: Dict[str, Any]) -> bool:
    return 'candidate' in field


def compare_multiple_choice(sp_value: str, paca_value: str, candidates: str) -> float:
    st.write(f"Comparing multiple choice: SP: {sp_value}, PACA: {paca_value}")
    if paca_value.lower() == sp_value.lower():
        return 1.0
    return 0.0


def g_eval(field_name: str, sp_text: str, paca_text: str) -> float:
    st.write(f"G-eval for {field_name}: SP: {sp_text}, PACA: {paca_text}")
    prompt_template = """
    Task description:
    Your task is to compare two pieces of text: the Original Text and the Generated Text. The generated text is the AI agent's assessment of a psychiatric patient after interviewing him/her. The original text is the actual information about this patient and is the correct answer.
    
    Evaluation steps:
    1. Understand the Context:
    - Read the Original Text carefully to understand the context, details, and overall sentiment of the psychiatric patient's case.
    - Read the Generated Text to grasp the AI agent's interpretation and summary of the patient's information.

    2. Compare Key Information:
    - Compare essential elements present in both texts.
    - Check for Omissions: Note if any important details from the original text are missing or inaccurately represented in the generated text.

    3. Assess Accuracy and Completeness:
    - Accuracy: Determine if the information in the generated text correctly reflects the facts and observations from the original text.
    - Completeness: Evaluate whether the generated text covers all the significant aspects mentioned in the original text without adding irrelevant information.

    4. Check for Paraphrasing and Interpretation:
    - Determine if the generated text is a paraphrased version of the original text or if it introduces any new interpretations that deviate from the original meaning.
    - Evaluate whether the paraphrasing maintains the integrity of the original information.

    5. Determine Overall Similarity:
    - Based on the comparisons, assess how similar the generated text is to the original text in terms of meaning and detail.
    - Consider any discrepancies in information or completeness when determining the similarity.

    6. Assign a Score:
    - Provide a score between 0 and 1 that reflects the degree of similarity between the original text and the generated text.
    - A score of 1 indicates that the texts are identical in meaning, while a score of 0 indicates they are completely different.
    
    Original text:
    {field_name}: {original_text}
    
    Generated text:
    {field_name}: {generated_text}
    
    Provide your Score as a float between 0 and 1.
    
    Score:
    """

    prompt = PromptTemplate(
        input_variables=["field_name", "original_text", "generated_text"],
        template=prompt_template
    )
    # New LangChain v1.x style: compose prompt + llm using the runnable (prompt | llm)
    chain = prompt | llm

    # invoke() returns a response object for chat LLMs; adjust to accept either string or response
    response = chain.invoke(field_name=field_name, original_text=sp_text,
                            generated_text=paca_text)
    if hasattr(response, 'content'):
        result = response.content
    else:
        result = response

    try:
        rating_line = [line for line in result.split(
            '\n') if line.startswith('Score:')][0]
        rating = float(rating_line.split(':')[1].strip())
        return max(0, min(1, rating))  # Ensure the rating is between 0 and 1
    except (IndexError, ValueError):
        st.error(f"Error parsing G-eval result: {result}")
        return 0.0


def evaluate_field(field_name: str, sp_value: Any, paca_value: Any, field_info: Dict[str, Any]) -> Tuple[float, str]:
    st.write(
        f"Evaluating field {field_name}: SP: {sp_value}, PACA: {paca_value}, Field info: {field_info}")

    if 'candidate' in field_info:
        score = compare_multiple_choice(
            str(sp_value), str(paca_value), field_info['candidate'])
        method = "Simple Accuracy"
    elif sp_value == "blank (data_type:string, guide:null)" and paca_value == "Not provided":
        score = 1.0
        method = "Simple Accuracy"
    elif sp_value == "blank (data_type:string, guide:null)" or paca_value == "Not provided":
        score = 0.0
        method = "Simple Accuracy"
    else:
        score = g_eval(field_name, str(sp_value), str(paca_value))
        method = "G-Eval"

    return score, method


def evaluate_constructs(sp_construct: Dict[str, Any], paca_construct: Dict[str, Any], given_form: Dict[str, Any]) -> Tuple[Dict[str, float], Dict[str, str]]:
    scores = {}
    methods = {}

    def recursive_evaluate(sp_dict, paca_dict, form_dict, prefix=''):
        for key, form_value in form_dict.items():
            full_key = f"{prefix}.{key}" if prefix else key
            st.write(f"Evaluating key: {full_key}")

            if isinstance(form_value, dict):
                if 'guide' in form_value or 'candidate' in form_value:
                    sp_value = sp_dict.get(key, '') if isinstance(
                        sp_dict, dict) else sp_dict
                    paca_value = paca_dict.get(key, '') if isinstance(
                        paca_dict, dict) else paca_dict
                    score, method = evaluate_field(
                        full_key, sp_value, paca_value, form_value)
                    scores[full_key] = score
                    methods[full_key] = method
                    st.write(
                        f"Evaluated {full_key}: SP: {sp_value}, PACA: {paca_value}, Score: {score}, Method: {method}")
                else:
                    recursive_evaluate(sp_dict.get(key, {}), paca_dict.get(
                        key, {}), form_value, full_key)
            else:
                st.write(f"Form value for {full_key}: {form_value}")
                sp_value = sp_dict.get(key, '') if isinstance(
                    sp_dict, dict) else sp_dict
                paca_value = paca_dict.get(key, '') if isinstance(
                    paca_dict, dict) else paca_dict
                score, method = evaluate_field(
                    full_key, sp_value, paca_value, {'guide': form_value})
                scores[full_key] = score
                methods[full_key] = method
                st.write(
                    f"Evaluated {full_key}: SP: {sp_value}, PACA: {paca_value}, Score: {score}, Method: {method}")

    recursive_evaluate(sp_construct, paca_construct, given_form)
    return scores, methods


def calculate_overall_score(scores: Dict[str, float]) -> float:
    return sum(scores.values()) / len(scores) if scores else 0


def create_evaluation_table(sp_construct: Dict[str, Any], paca_construct: Dict[str, Any], scores: Dict[str, float], methods: Dict[str, str]) -> pd.DataFrame:
    data = []
    for key in scores.keys():
        sp_value = sp_construct
        paca_value = paca_construct
        key_parts = key.split('.')
        for i, k in enumerate(key_parts):
            if isinstance(sp_value, dict):
                sp_value = sp_value.get(k, '')
            elif i < len(key_parts) - 1:
                sp_value = ''
                break

            if isinstance(paca_value, dict):
                paca_value = paca_value.get(k, '')
            elif i < len(key_parts) - 1:
                paca_value = ''
                break

        data.append({
            'Field': key,
            'SP-Construct': str(sp_value),
            'PACA-Construct': str(paca_value),
            'Method': methods[key],
            'Score': f"{scores[key]:.2f}"
        })

    return pd.DataFrame(data)


def evaluate_paca_performance(client_number: str, sp_construct_version: str, paca_construct_version: str, given_form_path: str) -> Tuple[Dict[str, float], float, pd.DataFrame]:
    firebase_ref = get_firebase_ref()

    sp_construct = load_from_firebase(
        firebase_ref, client_number, f"sp_construct_version{sp_construct_version}")
    paca_construct = load_from_firebase(
        firebase_ref, client_number, f"paca_construct_version{paca_construct_version}")
    given_form = load_given_form(given_form_path)

    if sp_construct is None or paca_construct is None:
        raise ValueError("Failed to load constructs from Firebase")

    st.write("SP Construct:", sp_construct)
    st.write("PACA Construct:", paca_construct)
    st.write("Given Form:", given_form)

    scores, methods = evaluate_constructs(
        sp_construct, paca_construct, given_form)
    overall_score = calculate_overall_score(scores)

    st.write("Final Scores:", scores)
    st.write("Evaluation Methods:", methods)
    st.write("Overall Score:", overall_score)

    evaluation_table = create_evaluation_table(
        sp_construct, paca_construct, scores, methods)

    return scores, overall_score, evaluation_table
