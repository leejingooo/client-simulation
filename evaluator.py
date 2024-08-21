import pandas as pd
import json
from typing import Dict, Any, List, Tuple
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from SP_utils import load_from_firebase, get_firebase_ref
import streamlit as st

llm = ChatOpenAI(temperature=0, model="gpt-4")


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


def g_eval(sp_text: str, paca_text: str) -> float:
    st.write(f"G-eval: SP: {sp_text}, PACA: {paca_text}")
    prompt_template = """
    You are an expert evaluator. Your task is to compare two pieces of text: the original text and the generated text.
    Evaluate how well the generated text captures the key information and sentiment of the original text.
    
    Original text: {original_text}
    Generated text: {generated_text}
    
    Please rate the similarity on a scale from 0 to 1, where 0 means completely different and 1 means identical in meaning and sentiment.
    Provide your rating as a float between 0 and 1, and a brief explanation.
    
    Rating:
    Explanation:
    """

    prompt = PromptTemplate(
        input_variables=["original_text", "generated_text"],
        template=prompt_template
    )

    chain = LLMChain(llm=llm, prompt=prompt)

    result = chain.run(original_text=sp_text, generated_text=paca_text)

    try:
        rating_line = [line for line in result.split(
            '\n') if line.startswith('Rating:')][0]
        rating = float(rating_line.split(':')[1].strip())
        return max(0, min(1, rating))  # Ensure the rating is between 0 and 1
    except (IndexError, ValueError):
        st.error(f"Error parsing G-eval result: {result}")
        return 0.0


def evaluate_field(sp_value: Any, paca_value: Any, field_info: Dict[str, Any]) -> float:
    st.write(
        f"Evaluating field: SP: {sp_value}, PACA: {paca_value}, Field info: {field_info}")
    if is_multiple_choice(field_info):
        return compare_multiple_choice(str(sp_value), str(paca_value), field_info.get('candidate', ''))
    else:
        if sp_value == "blank (data_type:string, guide:null)" and paca_value == "Not provided":
            return 1.0
        elif sp_value == "blank (data_type:string, guide:null)" or paca_value == "Not provided":
            return 0.0
        else:
            return g_eval(str(sp_value), str(paca_value))


def evaluate_constructs(sp_construct: Dict[str, Any], paca_construct: Dict[str, Any], given_form: Dict[str, Any]) -> Tuple[Dict[str, float], Dict[str, str]]:
    scores = {}
    methods = {}

    def recursive_evaluate(sp_dict, paca_dict, form_dict, prefix=''):
        for key, form_value in form_dict.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(form_value, dict):
                if 'guide' in form_value or 'candidate' in form_value:
                    sp_value = sp_dict.get(key, '')
                    paca_value = paca_dict.get(key, '')
                    score, method = evaluate_field(
                        sp_value, paca_value, form_value)
                    scores[full_key] = score
                    methods[full_key] = method
                else:
                    recursive_evaluate(sp_dict.get(key, {}), paca_dict.get(
                        key, {}), form_value, full_key)
            else:
                sp_value = sp_dict.get(key, '')
                paca_value = paca_dict.get(key, '')
                score, method = evaluate_field(
                    sp_value, paca_value, {'guide': form_value})
                scores[full_key] = score
                methods[full_key] = method

    recursive_evaluate(sp_construct, paca_construct, given_form)
    return scores, methods


def calculate_overall_score(scores: Dict[str, float]) -> float:
    return sum(scores.values()) / len(scores) if scores else 0


def create_evaluation_table(sp_construct: Dict[str, Any], paca_construct: Dict[str, Any], scores: Dict[str, float], methods: Dict[str, str]) -> pd.DataFrame:
    data = []
    for key in scores.keys():
        sp_value = sp_construct
        paca_value = paca_construct
        for k in key.split('.'):
            sp_value = sp_value.get(k, '')
            paca_value = paca_value.get(k, '')

        data.append({
            'Field': key,
            'SP-Construct': str(sp_value),
            'PACA-Construct': str(paca_value),
            'Method': methods.get(key, ''),
            'Score': f"{scores[key]:.2f}"
        })

    return pd.DataFrame(data)


def evaluate_paca_performance(client_number: str, sp_construct_version: str, paca_construct_version: str, given_form_path: str) -> Tuple[Dict[str, float], float]:
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

    evaluation_table = create_evaluation_table(
        sp_construct, paca_construct, scores, methods)

    st.write("Final Scores:", scores)
    st.write("Overall Score:", overall_score)

    return scores, overall_score, evaluation_table
