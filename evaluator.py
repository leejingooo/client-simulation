import json
from typing import Dict, Any, List, Tuple
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from SP_utils import load_from_firebase, get_firebase_ref

llm = ChatOpenAI(temperature=0, model="gpt-4")


def compare_multiple_choice(sp_construct: Dict[str, Any], paca_construct: Dict[str, Any]) -> Tuple[int, int]:
    correct = 0
    total = 0

    for key, sp_value in sp_construct.items():
        if isinstance(sp_value, dict):
            sub_correct, sub_total = compare_multiple_choice(
                sp_value, paca_construct.get(key, {}))
            correct += sub_correct
            total += sub_total
        elif isinstance(sp_value, str) and '/' in sp_value:
            total += 1
            if key in paca_construct and paca_construct[key] in sp_value.split('/'):
                correct += 1

    return correct, total


def g_eval(sp_text: str, paca_text: str) -> float:
    prompt_template = """
    You are an expert evaluator. Your task is to compare two pieces of text: the original text and the generated text.
    Evaluate how well the generated text captures the key information and sentiment of the original text.
    
    Original text: {original_text}
    Generated text: {generated_text}
    
    Please rate the similarity on a scale from 0 to 1, where 0 means completely different and 1 means identical in meaning and sentiment.
    Provide your rating and a brief explanation.
    
    Rating:
    Explanation:
    """

    prompt = PromptTemplate(
        input_variables=["original_text", "generated_text"],
        template=prompt_template
    )

    chain = LLMChain(llm=llm, prompt=prompt)

    result = chain.run(original_text=sp_text, generated_text=paca_text)

    rating_line = [line for line in result.split(
        '\n') if line.startswith('Rating:')][0]
    rating = float(rating_line.split(':')[1].strip())

    return rating


def evaluate_constructs(sp_construct: Dict[str, Any], paca_construct: Dict[str, Any]) -> Dict[str, float]:
    scores = {}

    for key, sp_value in sp_construct.items():
        if isinstance(sp_value, dict):
            sub_scores = evaluate_constructs(
                sp_value, paca_construct.get(key, {}))
            for sub_key, sub_score in sub_scores.items():
                scores[f"{key}.{sub_key}"] = sub_score
        elif isinstance(sp_value, str):
            if '/' in sp_value:  # Multiple choice
                correct, total = compare_multiple_choice(
                    {key: sp_value}, {key: paca_construct.get(key, '')})
                scores[key] = correct / total if total > 0 else 0
            else:  # Narrative
                paca_value = paca_construct.get(key, '')
                scores[key] = g_eval(sp_value, paca_value)

    return scores


def calculate_overall_score(scores: Dict[str, float]) -> float:
    return sum(scores.values()) / len(scores) if scores else 0


def evaluate_paca_performance(client_number: str, sp_construct_version: str, paca_construct_version: str) -> Tuple[Dict[str, float], float]:
    firebase_ref = get_firebase_ref()

    sp_construct = load_from_firebase(
        firebase_ref, client_number, f"sp_construct_version{sp_construct_version}")
    paca_construct = load_from_firebase(
        firebase_ref, client_number, f"paca_construct_version{paca_construct_version}")

    if sp_construct is None or paca_construct is None:
        raise ValueError("Failed to load constructs from Firebase")

    scores = evaluate_constructs(sp_construct, paca_construct)
    overall_score = calculate_overall_score(scores)

    return scores, overall_score
