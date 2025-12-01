import pandas as pd
import json
from typing import Dict, Any, List, Tuple
# from langchain.chat_models import ChatOpenAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from SP_utils import load_from_firebase, get_firebase_ref, sanitize_key
import streamlit as st

llm = ChatOpenAI(temperature=0, model="gpt-5.1")


def load_given_form(form_path: str) -> Dict[str, Any]:
    with open(form_path, 'r') as f:
        return json.load(f)


def is_multiple_choice(field: Dict[str, Any]) -> bool:
    return 'candidate' in field


def parse_candidate_from_guide(guide: str) -> str:
    """If the guide string contains 'candidate:...', return the candidate substring after the colon."""
    if not guide or not isinstance(guide, str):
        return None
    lower = guide.lower()
    if 'candidate:' in lower:
        # find the part after 'candidate:' in original guide to preserve casing
        parts = guide.split('candidate:')
        if len(parts) >= 2:
            return parts[1].strip()
    return None


def get_nested_value(container: Any, key_parts: List[str]):
    """Try to retrieve a value from nested dicts using key_parts.
    Fallbacks:
    - direct lookup by last key (case-insensitive)
    - search for any key containing the last key substring (case-insensitive)
    Returns '' if not found.
    """
    if container is None:
        return ''

    # Try nested traversal
    current = container
    for i, k in enumerate(key_parts):
        if isinstance(current, dict) and k in current:
            current = current.get(k)
        else:
            # try keys case-insensitive
            if isinstance(current, dict):
                found = False
                for key in current.keys():
                    if key.lower() == k.lower():
                        current = current.get(key)
                        found = True
                        break
                if found:
                    continue
            current = None
            break

    # If nested traversal succeeded and current is not None, return it
    if current is not None:
        return current

    # Fallback: try direct lookup by last key in top-level container
    last = key_parts[-1]
    if isinstance(container, dict):
        # exact case-insensitive match
        for key, val in container.items():
            if key.lower() == last.lower():
                return val

        # substring match
        for key, val in container.items():
            if last.lower() in key.lower():
                return val

    return ''


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
    response = chain.invoke({
        "field_name": field_name,
        "original_text": sp_text,
        "generated_text": paca_text,
    })
    if hasattr(response, 'content'):
        result = response.content
    else:
        result = response

    try:
        # First try to parse lines like 'Score: 0.85'
        lines = [line.strip() for line in str(result).split('\n') if line.strip()]
        rating = None
        for line in lines:
            if line.lower().startswith('score:'):
                try:
                    rating = float(line.split(':', 1)[1].strip())
                    break
                except Exception:
                    continue

        # Fallback: try to parse any float present in the output (e.g., '1.0' or '0.75')
        if rating is None:
            import re
            text = '\n'.join(lines)
            m = re.search(r'([-+]?[0-9]*\.?[0-9]+)', text)
            if m:
                try:
                    rating = float(m.group(1))
                except Exception:
                    rating = None

        if rating is None:
            st.error(f"Error parsing G-eval result: {result}")
            return 0.0

        return max(0, min(1, float(rating)))  # Ensure the rating is between 0 and 1
    except Exception as e:
        st.error(f"Error in g_eval: {str(e)}")
        return 0.0


def evaluate_field(field_name: str, sp_value: Any, paca_value: Any, field_info: Dict[str, Any]) -> Tuple[float, str]:
    st.write(
        f"Evaluating field {field_name}: SP: {sp_value}, PACA: {paca_value}, Field info: {field_info}")

    # Detect candidate info either directly or embedded in guide string
    candidate_spec = None
    if 'candidate' in field_info:
        candidate_spec = field_info['candidate']
    elif 'guide' in field_info:
        candidate_spec = parse_candidate_from_guide(field_info['guide'])

    if candidate_spec:
        score = compare_multiple_choice(
            str(sp_value), str(paca_value), candidate_spec)
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
                    sp_value = get_nested_value(sp_dict, [key]) if isinstance(sp_dict, (dict, list)) else sp_dict
                    paca_value = get_nested_value(paca_dict, [key]) if isinstance(paca_dict, (dict, list)) else paca_dict
                    # If still empty, try nested lookup using the full path
                    if sp_value == '' and prefix:
                        sp_value = get_nested_value(sp_dict, prefix.split('.') + [key])
                    if paca_value == '' and prefix:
                        paca_value = get_nested_value(paca_dict, prefix.split('.') + [key])
                    # If form_value is dict but candidate info embedded in strings, parse it
                    if isinstance(form_value, dict) and 'candidate' not in form_value and 'guide' in form_value:
                        parsed = parse_candidate_from_guide(form_value.get('guide', ''))
                        if parsed:
                            form_value = {**form_value, 'candidate': parsed}
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
                # Try robust lookups for SP and PACA constructs
                sp_value = get_nested_value(sp_dict, prefix.split('.') + [key]) if prefix else get_nested_value(sp_dict, [key])
                paca_value = get_nested_value(paca_dict, prefix.split('.') + [key]) if prefix else get_nested_value(paca_dict, [key])

                # If guide string contains candidate specification, pass it through
                parsed_candidate = parse_candidate_from_guide(form_value)
                field_info = {'guide': form_value}
                if parsed_candidate:
                    field_info['candidate'] = parsed_candidate

                score, method = evaluate_field(
                    full_key, sp_value, paca_value, field_info)
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
        key_parts = key.split('.')
        sp_value = get_nested_value(sp_construct, key_parts)
        paca_value = get_nested_value(paca_construct, key_parts)

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

    # Fallback: if either construct isn't found via the expected versioned key,
    # try scanning the client's stored keys for alternate saves (e.g., constructs_{conversation_id}).
    if sp_construct is None or paca_construct is None:
        try:
            client_path = sanitize_key(f"clients/{client_number}")
            client_data = firebase_ref.child(client_path).get()
        except Exception as e:
            client_data = None

        if isinstance(client_data, dict):
            # Try to find SP construct if missing
            if sp_construct is None:
                for k, v in client_data.items():
                    if k.startswith('sp_construct_version') or k.startswith('sp_construct'):
                        sp_construct = v
                        break

            # Try to find PACA construct if missing
            if paca_construct is None:
                for k, v in client_data.items():
                    # common keys: 'paca_construct_versionX_X' or 'constructs_{conversation_id}'
                    if k.startswith('paca_construct_version') or k.startswith('constructs_'):
                        # if value looks like a dict (expected construct), accept it
                        if isinstance(v, dict):
                            paca_construct = v
                            break

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
