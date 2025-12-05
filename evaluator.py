import pandas as pd
import json
import re
from typing import Dict, Any, List, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import streamlit as st

llm = ChatOpenAI(temperature=0, model="gpt-4")


# ============================================================================
# PSYCHE RUBRIC DEFINITIONS
# ============================================================================

PSYCHE_RUBRIC = {
    # Subjective Information (G-Eval or Binary)
    "Chief complaint": {"type": "g-eval", "weight": 1},
    "Symptom name": {"type": "g-eval", "weight": 1},
    "Alleviating factor": {"type": "g-eval", "weight": 1},
    "Exacerbating factor": {"type": "g-eval", "weight": 1},
    "Triggering factor": {"type": "g-eval", "weight": 1},
    "Stressor": {"type": "g-eval", "weight": 1},
    "Diagnosis": {"type": "g-eval", "weight": 1},
    "Substance use": {"type": "g-eval", "weight": 1},
    "Current family structure": {"type": "g-eval", "weight": 1},
    "length": {"type": "binary", "weight": 1},  # Correct=1, Incorrect=0
    
    # Impulsivity (w=5)
    "Suicidal ideation": {
        "type": "impulsivity",
        "weight": 5,
        "values": {"high": 2, "moderate": 1, "low": 0}
    },
    "Self mutilating behavior risk": {
        "type": "impulsivity",
        "weight": 5,
        "values": {"high": 2, "moderate": 1, "low": 0}
    },
    "Homicide risk": {
        "type": "impulsivity",
        "weight": 5,
        "values": {"high": 2, "moderate": 1, "low": 0}
    },
    "Suicidal plan": {"type": "binary", "weight": 5},
    "Suicidal attempt": {"type": "binary", "weight": 5},
    
    # Behavior (w=2)
    "Mood": {
        "type": "behavior",
        "weight": 2,
        "values": {
            "irritable": 5, "euphoric": 5, "elated": 4,
            "euthymic": 3, "dysphoric": 2, "depressed": 1
        }
    },
    "Verbal productivity": {
        "type": "behavior",
        "weight": 2,
        "values": {"increased": 2, "moderate": 1, "decreased": 0}
    },
    "Insight": {
        "type": "behavior",
        "weight": 2,
        "values": {
            "complete denial of illness": 5,
            "slight awareness of being sick and needing help, but denying it at the same time": 4,
            "awareness of being sick but blaming it on others, external events": 3,
            "intellectual insight": 2,
            "true emotional insight": 1
        }
    },
    "Affect": {"type": "g-eval", "weight": 2},
    "Perception": {"type": "g-eval", "weight": 2},
    "Thought process": {"type": "g-eval", "weight": 2},
    "Thought content": {"type": "g-eval", "weight": 2},
    "Spontaneity": {"type": "binary", "weight": 2},
    "Social judgement": {"type": "binary", "weight": 2},
    "Reliability": {"type": "binary", "weight": 2},
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def normalize_value(value: str) -> str:
    """Normalize values: lower case, strip whitespace."""
    if not isinstance(value, str):
        value = str(value)
    value = value.lower().strip()
    
    # Handle 'N/A' or empty as missing
    if value in ['n/a', 'na', '', 'none', 'unknown', 'null']:
        return None
    
    return value


def flatten_construct(construct: Dict[str, Any], parent_key='') -> Dict[str, Any]:
    """
    Flatten nested construct into key-value pairs.
    Handles arrays specially by iterating through items.
    """
    items = {}
    if isinstance(construct, dict):
        for k, v in construct.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, list):
                # For arrays like symptom_n, keep as list
                items[new_key] = v
            elif isinstance(v, dict) and not isinstance(v, str):
                items.update(flatten_construct(v, new_key))
            else:
                items[new_key] = str(v) if v is not None else ""
    return items


def get_value_from_construct(construct: Dict[str, Any], field_name: str) -> Any:
    """
    Retrieve value from construct by field name (case-insensitive, nested-aware).
    Returns the value as-is (could be string, list, dict, etc.) or None if not found.
    
    Special handling for symptom fields: collects all symptom_1, symptom_2, etc. into a combined text.
    """
    if construct is None:
        return None
    
    # Special handling for symptom-related fields
    if field_name.lower() in ['symptom name', 'alleviating factor', 'exacerbating factor', 'length']:
        return get_symptom_field_value(construct, field_name)
    
    # First, try direct access to top-level fields
    field_lower = field_name.lower()
    for key, val in construct.items():
        if key.lower() == field_lower:
            return val
    
    # Then flatten and search
    flat = flatten_construct(construct)
    
    # Direct exact match
    for key, val in flat.items():
        if key.lower() == field_lower:
            return val
    
    # Match on last part of key path
    for key, val in flat.items():
        last_part = key.split('.')[-1].lower()
        if last_part == field_lower:
            return val
    
    return None


def get_symptom_field_value(construct: Dict[str, Any], field_name: str) -> str:
    """
    Collect all symptom_1, symptom_2, ... values for a specific field and combine them.
    
    Args:
        construct: The construct dictionary
        field_name: One of 'symptom name', 'alleviating factor', 'exacerbating factor', 'length'
    
    Returns:
        Combined text of all symptom values for this field
        For 'length': returns the maximum value as a string
    """
    present_illness = construct.get('Present illness', {})
    if not present_illness:
        return None
    
    # Collect all symptom_n entries
    symptom_values = []
    
    # Iterate through keys to find symptom_1, symptom_2, etc.
    for key in sorted(present_illness.keys()):
        if key.startswith('symptom_'):
            symptom_data = present_illness[key]
            if isinstance(symptom_data, dict):
                # Map field_name to actual key in symptom dict
                field_map = {
                    'symptom name': 'name',
                    'alleviating factor': 'alleviating factor',
                    'exacerbating factor': 'exacerbating factor',
                    'length': 'length'
                }
                
                actual_key = field_map.get(field_name.lower())
                if actual_key and actual_key in symptom_data:
                    value = symptom_data[actual_key]
                    if value:
                        symptom_values.append(str(value))
    
    # Combine all values
    if not symptom_values:
        return None
    
    # For 'length', return the maximum value
    if field_name.lower() == 'length':
        try:
            lengths = [int(v) for v in symptom_values if v.replace('-', '').isdigit()]
            if lengths:
                return str(max(lengths))
        except:
            pass
        return None
    
    # For text fields, return as bullet points for better readability
    return '\n'.join(f"- {val}" for val in symptom_values)


# ============================================================================
# SCORING FUNCTIONS
# ============================================================================

def g_eval(field_name: str, sp_text: str, paca_text: str) -> float:
    """G-Eval scoring using LLM."""
    if not sp_text or not paca_text:
        return 0.0
    
    prompt_template = """Task: Compare two psychiatric assessment texts for similarity.

Original (SP): {original_text}

Generated (PACA): {generated_text}

Evaluate on accuracy, completeness, and meaning preservation.
Score between 0 (completely different) and 1 (identical in meaning).

Return ONLY a single float between 0 and 1."""

    prompt = PromptTemplate(
        input_variables=["original_text", "generated_text"],
        template=prompt_template
    )
    
    chain = prompt | llm
    
    try:
        response = chain.invoke({
            "original_text": sp_text,
            "generated_text": paca_text,
        })
        
        result = response.content if hasattr(response, 'content') else str(response)
        
        # Extract float from response
        match = re.search(r'(0?\.\d+|1\.0|1)', result.strip())
        if match:
            score = float(match.group(1))
            return max(0, min(1, score))
        
        return 0.0
    except Exception as e:
        st.warning(f"G-eval error for {field_name}: {str(e)}")
        return 0.0


def score_impulsivity(sp_value: str, paca_value: str, values_map: Dict[str, int]) -> Tuple[float, str]:
    """
    Score impulsivity fields using delta scoring.
    Δ = (PACA value) - (SP value)
    Score = 1 if Δ=0, 0.5 if Δ=1, 0 if Δ<0 or Δ≥2
    """
    sp_val = values_map.get(sp_value)
    paca_val = values_map.get(paca_value)
    
    if sp_val is None or paca_val is None:
        return 0.0, f"Invalid: SP={sp_value}, PACA={paca_value}"
    
    delta = paca_val - sp_val
    
    if delta < 0:
        score = 0.0
    elif delta == 0:
        score = 1.0
    elif delta == 1:
        score = 0.5
    else:  # delta >= 2
        score = 0.0
    
    return score, f"Δ={delta:+d}"


def score_behavior(sp_value: str, paca_value: str, values_map: Dict[str, int]) -> Tuple[float, str]:
    """
    Score behavior fields (Mood, Verbal productivity, Insight).
    Δ = (PACA value) - (SP value)
    Score = 1 if |Δ|=0, 0.5 if |Δ|=1, 0 if |Δ|>1
    """
    sp_val = values_map.get(sp_value)
    paca_val = values_map.get(paca_value)
    
    if sp_val is None or paca_val is None:
        return 0.0, f"Invalid: SP={sp_value}, PACA={paca_value}"
    
    delta = abs(paca_val - sp_val)
    
    if delta == 0:
        score = 1.0
    elif delta == 1:
        score = 0.5
    else:  # delta > 1
        score = 0.0
    
    return score, f"|Δ|={delta}"


def score_binary(sp_value: str, paca_value: str) -> Tuple[float, str]:
    """
    Binary scoring: exact match = 1, else = 0.
    Handles presence/absence, yes/no normalization.
    """
    sp_norm = sp_value.lower()
    paca_norm = paca_value.lower()
    
    # Normalize presence/absence
    presence_aliases = ['true', 'yes', 'presence', '+', '(+)']
    absence_aliases = ['false', 'no', 'absence', '-', '(-)']
    
    if sp_norm in presence_aliases:
        sp_norm = 'presence'
    elif sp_norm in absence_aliases:
        sp_norm = 'absence'
    
    if paca_norm in presence_aliases:
        paca_norm = 'presence'
    elif paca_norm in absence_aliases:
        paca_norm = 'absence'
    
    score = 1.0 if sp_norm == paca_norm else 0.0
    return score, f"Match={sp_norm == paca_norm}"


# ============================================================================
# MAIN EVALUATION FUNCTION
# ============================================================================

def evaluate_construct(field_name: str, sp_value: str, paca_value: str) -> Tuple[float, str, int]:
    """
    Evaluate a single field using PSYCHE RUBRIC.
    Returns: (score, method_description, weight)
    """
    
    # Check if field is in rubric
    if field_name not in PSYCHE_RUBRIC:
        st.warning(f"Field '{field_name}' not in PSYCHE RUBRIC. Skipping.")
        return 0.0, "NOT_IN_RUBRIC", 0
    
    rubric_entry = PSYCHE_RUBRIC[field_name]
    weight = rubric_entry.get("weight", 1)
    scoring_type = rubric_entry.get("type", "g-eval")
    
    # Handle missing values
    if not sp_value or not paca_value:
        st.warning(f"Missing value for '{field_name}': SP={sp_value}, PACA={paca_value}")
        return 0.0, "MISSING_VALUE", weight
    
    # Apply scoring method
    if scoring_type == "binary":
        score, desc = score_binary(sp_value, paca_value)
        return score, f"Binary({desc})", weight
    
    elif scoring_type == "impulsivity":
        values_map = rubric_entry.get("values", {})
        sp_norm = sp_value  # Already normalized
        paca_norm = paca_value  # Already normalized
        score, desc = score_impulsivity(sp_norm, paca_norm, values_map)
        return score, f"Impulsivity({desc})", weight
    
    elif scoring_type == "behavior":
        values_map = rubric_entry.get("values", {})
        sp_norm = sp_value  # Already normalized
        paca_norm = paca_value  # Already normalized
        score, desc = score_behavior(sp_norm, paca_norm, values_map)
        return score, f"Behavior({desc})", weight
    
    elif scoring_type == "g-eval":
        score = g_eval(field_name, sp_value, paca_value)
        return score, "G-Eval", weight
    
    else:
        st.warning(f"Unknown scoring type '{scoring_type}' for field '{field_name}'")
        return 0.0, "UNKNOWN_TYPE", weight


def evaluate_constructs(sp_construct: Dict[str, Any], paca_construct: Dict[str, Any]) -> Tuple[Dict[str, float], Dict[str, str], float, Dict[str, Any]]:
    """
    Evaluate both constructs against PSYCHE RUBRIC.
    
    Returns:
        - field_scores: Dict[field_name -> score]
        - field_methods: Dict[field_name -> method_description]
        - weighted_score: Overall weighted score (sum of weighted scores)
        - detailed_results: Dict with sp_content, paca_content, score, weight, weighted_score for each field
    """
    field_scores = {}
    field_methods = {}
    field_weights = {}
    detailed_results = {}
    
    st.write("### Starting Evaluation Against PSYCHE RUBRIC")
    
    # Evaluate each field in PSYCHE RUBRIC
    for field_name in PSYCHE_RUBRIC.keys():
        sp_value = get_value_from_construct(sp_construct, field_name)
        paca_value = get_value_from_construct(paca_construct, field_name)
        
        score, method, weight = evaluate_construct(field_name, sp_value, paca_value)
        
        if weight > 0:  # Only include fields that are in rubric
            field_scores[field_name] = score
            field_methods[field_name] = method
            field_weights[field_name] = weight
            
            # Store detailed results for each element
            weighted_score_value = score * weight
            detailed_results[field_name] = {
                'sp_content': str(sp_value) if sp_value is not None else '',
                'paca_content': str(paca_value) if paca_value is not None else '',
                'score': score,
                'weight': weight,
                'weighted_score': weighted_score_value
            }
            
            st.write(f"**{field_name}**: SP='{sp_value}' | PACA='{paca_value}' | Score={score:.2f} | {method}")
    
    # Calculate weighted overall score as simple sum
    if field_scores:
        weighted_score = sum(score * field_weights.get(field, 1) for field, score in field_scores.items())
    else:
        weighted_score = 0.0
    
    return field_scores, field_methods, weighted_score, detailed_results


# ============================================================================
# RESULT FORMATTING
# ============================================================================

def create_evaluation_table(field_scores: Dict[str, float], field_methods: Dict[str, str]) -> pd.DataFrame:
    """Create evaluation results dataframe."""
    data = []
    for field_name in sorted(field_scores.keys()):
        data.append({
            'Field': field_name,
            'Score': f"{field_scores[field_name]:.2f}",
            'Method': field_methods.get(field_name, 'Unknown'),
            'Weight': PSYCHE_RUBRIC[field_name].get('weight', 1)
        })
    
    return pd.DataFrame(data)


# ============================================================================
# FIREBASE INTEGRATION (Legacy - simplified)
# ============================================================================

def load_given_form(form_path: str) -> Dict[str, Any]:
    """Load given form from JSON file."""
    try:
        with open(form_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load given form: {e}")
        return None


def evaluate_paca_performance(
    client_number: str,
    sp_construct: Dict[str, Any],
    paca_construct: Dict[str, Any]
) -> Tuple[Dict[str, float], Dict[str, str], float, pd.DataFrame, Dict[str, Any]]:
    """
    Main evaluation function using PSYCHE RUBRIC.
    
    Args:
        client_number: Client ID
        sp_construct: SP construct dictionary
        paca_construct: PACA construct dictionary
    
    Returns:
        - field_scores: Individual field scores
        - field_methods: Scoring methods used
        - weighted_score: Overall weighted score (sum)
        - evaluation_table: Results as DataFrame
        - detailed_results: Detailed results for Firebase storage
    """
    
    st.write(f"### Evaluating Client {client_number}")
    
    # Validate inputs
    if not sp_construct or not paca_construct:
        raise ValueError("Both SP and PACA constructs are required")
    
    st.write("**SP Construct:**", sp_construct)
    st.write("**PACA Construct:**", paca_construct)
    
    # Evaluate
    field_scores, field_methods, weighted_score, detailed_results = evaluate_constructs(sp_construct, paca_construct)
    
    st.write(f"## Overall PSYCHE Score (Sum): {weighted_score:.2f}")
    
    # Create results table
    evaluation_table = create_evaluation_table(field_scores, field_methods)
    
    return field_scores, field_methods, weighted_score, evaluation_table, detailed_results
