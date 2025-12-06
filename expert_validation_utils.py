"""
Expert Validation Utility Functions
전문가 검증을 위한 유틸리티 함수들
"""

import streamlit as st
from datetime import datetime


# ================================
# Scoring Weights (from Expert Rubric)
# ================================
WEIGHTS = {
    'Subjective': 1,
    'Impulsivity': 5,
    'Behavior': 2
}

# ================================
# Value Mappings for Ordinal Scales
# ================================
MOOD_VALUES = {
    'irritable': 5,
    'euphoric': 5,
    'elated': 4,
    'euthymic': 3,
    'dysphoric': 2,
    'depressed': 1
}

VERBAL_PRODUCTIVITY_VALUES = {
    'increased': 2,
    'moderate': 1,
    'decreased': 0
}

INSIGHT_VALUES = {
    'complete denial of illness': 5,
    'slight awareness of being sick and needing help, but denying it at the same time': 4,
    'awareness of being sick but blaming it on others, external events': 3,
    'intellectual insight': 2,
    'true emotional insight': 1
}

RISK_LEVEL_VALUES = {
    'high': 2,
    'moderate': 1,
    'low': 0
}

# ================================
# Scoring Functions
# ================================

def calculate_subjective_score(selected_option):
    """Calculate score for subjective information elements"""
    if selected_option == "Correct":
        return 1
    elif selected_option == "Partially correct":
        return 0.5
    else:  # Incorrect
        return 0


def calculate_length_score(selected_option):
    """Calculate score for symptom length"""
    if selected_option == "Correct":
        return 1
    else:  # Incorrect
        return 0


def is_none_or_na(value):
    """
    Check if value is None, N/A, or similar
    Returns True if the value should be treated as missing/invalid
    """
    if value is None:
        return True
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in ['N/A', 'NA', 'NONE', '', 'NULL']:
            return True
    return False


def calculate_risk_score(delta):
    """
    Calculate score for risk assessment (Suicidal ideation, Self-mutilating behavior, Homicide risk)
    Delta = (PACA value) - (Expert value)
    """
    if delta < 0:
        return 0
    elif delta == 0:
        return 1
    elif delta == 1:
        return 0.5
    else:  # delta >= 2
        return 0


def calculate_risk_score_from_values(expert_value, paca_value):
    """
    Calculate score for risk assessment based on expert and PACA values
    expert_value, paca_value: 'high', 'moderate', or 'low' (case-insensitive)
    Delta = (PACA value) - (Expert value)
    
    Returns 0 if PACA value is None or N/A
    """
    # Check if PACA value is missing
    if is_none_or_na(paca_value):
        return 0
    
    # Normalize values
    expert_val = expert_value.lower() if expert_value else 'low'
    paca_val = paca_value.lower() if paca_value else 'low'
    
    # Map to numeric values
    value_map = RISK_LEVEL_VALUES
    expert_num = value_map.get(expert_val, 0)
    paca_num = value_map.get(paca_val, 0)
    
    delta = paca_num - expert_num
    
    return calculate_risk_score(delta)


def calculate_ordinal_score_from_values(expert_value, paca_value, value_mapping):
    """
    Calculate score for ordinal variables based on expert and PACA values
    Delta = abs((PACA value) - (Expert value))
    
    Returns 0 if PACA value is None or N/A
    """
    # Check if PACA value is missing
    if is_none_or_na(paca_value):
        return 0
    
    # Normalize values
    expert_val = expert_value.lower() if expert_value else ''
    paca_val = paca_value.lower() if paca_value else ''
    
    # Map to numeric values
    expert_num = value_mapping.get(expert_val, 0)
    paca_num = value_mapping.get(paca_val, 0)
    
    delta = paca_num - expert_num
    
    return calculate_ordinal_score(delta)


def calculate_plan_attempt_score(selected_option):
    """Calculate score for suicidal plan/attempt"""
    if selected_option == "Correct AND Evaluated properly":
        return 1
    else:  # Incorrect OR NOT evaluated
        return 0


def calculate_ordinal_score(delta):
    """
    Calculate score for ordinal variables (Mood, Verbal productivity, Insight)
    Delta = abs((PACA value) - (Expert value))
    """
    abs_delta = abs(delta)
    if abs_delta == 0:
        return 1
    elif abs_delta == 1:
        return 0.5
    else:  # abs_delta > 1
        return 0


def calculate_categorical_score(selected_option):
    """Calculate score for categorical variables (Affect, Perception, etc.)"""
    if selected_option == "Correct":
        return 1
    elif selected_option == "Partially correct":
        return 0.5
    else:  # Incorrect
        return 0


def calculate_binary_score(selected_option):
    """Calculate score for binary variables (Spontaneity, Social judgement, Reliability)"""
    if selected_option == "Correct":
        return 1
    else:  # Incorrect
        return 0


# ================================
# Aggregated Scoring Options Generator (Psyche Validation Style)
# ================================

def get_aggregated_scoring_options(construct_data):
    """
    Generate aggregated scoring options based on PSYCHE RUBRIC
    Similar to evaluator.py - combines symptom_1, symptom_2, etc. into single categories
    
    Returns a dictionary with categories and their scoring elements (aggregated)
    """
    scoring_options = {
        'Subjective Information': [],
        'Impulsivity': [],
        'Behavior (Mental Status Examination)': []
    }
    
    # ================================
    # Subjective Information
    # ================================
    
    # Chief Complaint - Description
    if 'Chief complaint' in construct_data and 'description' in construct_data['Chief complaint']:
        scoring_options['Subjective Information'].append({
            'element': 'Chief complaint',
            'paca_value': construct_data['Chief complaint']['description'],
            'options': ['Correct', 'Partially correct', 'Incorrect'],
            'category': 'Subjective',
            'score_function': calculate_subjective_score
        })
    
    # Present Illness - Aggregated symptoms
    if 'Present illness' in construct_data:
        present_illness = construct_data['Present illness']
        
        # Aggregate all symptoms into categories
        symptom_names = []
        alleviating_factors = []
        exacerbating_factors = []
        lengths = []
        
        for i in range(1, 10):  # Support up to 9 symptoms
            symptom_key = f'symptom_{i}'
            if symptom_key in present_illness:
                symptom = present_illness[symptom_key]
                
                if 'name' in symptom and symptom['name']:
                    symptom_names.append(symptom['name'])
                
                if 'alleviating factor' in symptom and symptom['alleviating factor']:
                    alleviating_factors.append(symptom['alleviating factor'])
                
                if 'exacerbating factor' in symptom and symptom['exacerbating factor']:
                    exacerbating_factors.append(symptom['exacerbating factor'])
                
                if 'length' in symptom and symptom['length']:
                    lengths.append(symptom['length'])
        
        # Symptom name (aggregated)
        if symptom_names:
            combined_names = '\n'.join(f"- {name}" for name in symptom_names)
            scoring_options['Subjective Information'].append({
                'element': 'Symptom name',
                'paca_value': combined_names,
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Subjective',
                'score_function': calculate_subjective_score
            })
        
        # Alleviating factor (aggregated)
        if alleviating_factors:
            combined_alleviating = '\n'.join(f"- {factor}" for factor in alleviating_factors)
            scoring_options['Subjective Information'].append({
                'element': 'Alleviating factor',
                'paca_value': combined_alleviating,
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Subjective',
                'score_function': calculate_subjective_score
            })
        
        # Exacerbating factor (aggregated)
        if exacerbating_factors:
            combined_exacerbating = '\n'.join(f"- {factor}" for factor in exacerbating_factors)
            scoring_options['Subjective Information'].append({
                'element': 'Exacerbating factor',
                'paca_value': combined_exacerbating,
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Subjective',
                'score_function': calculate_subjective_score
            })
        
        # Length (max value)
        if lengths:
            try:
                max_length = max(int(l) for l in lengths if str(l).replace('-', '').isdigit())
                scoring_options['Subjective Information'].append({
                    'element': 'length',
                    'paca_value': str(max_length),
                    'options': ['Correct', 'Incorrect'],
                    'category': 'Subjective',
                    'score_function': calculate_length_score
                })
            except:
                pass
        
        # Triggering factor
        if 'triggering_factor' in present_illness and present_illness['triggering_factor']:
            scoring_options['Subjective Information'].append({
                'element': 'Triggering factor',
                'paca_value': present_illness['triggering_factor'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Subjective',
                'score_function': calculate_subjective_score
            })
        
        # Stressor
        if 'stressor' in present_illness and present_illness['stressor']:
            scoring_options['Subjective Information'].append({
                'element': 'Stressor',
                'paca_value': present_illness['stressor'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Subjective',
                'score_function': calculate_subjective_score
            })
    
    # Family History
    if 'Family history' in construct_data:
        family_history = construct_data['Family history']
        
        if 'diagnosis' in family_history and family_history['diagnosis']:
            scoring_options['Subjective Information'].append({
                'element': 'Diagnosis',
                'paca_value': family_history['diagnosis'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Subjective',
                'score_function': calculate_subjective_score
            })
        
        if 'substance use' in family_history and family_history['substance use']:
            scoring_options['Subjective Information'].append({
                'element': 'Substance use',
                'paca_value': family_history['substance use'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Subjective',
                'score_function': calculate_subjective_score
            })
    
    # Marriage/Relationship History
    if 'Marriage_Relationship History' in construct_data:
        marriage = construct_data['Marriage_Relationship History']
        
        if 'current family structure' in marriage and marriage['current family structure']:
            scoring_options['Subjective Information'].append({
                'element': 'Current family structure',
                'paca_value': marriage['current family structure'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Subjective',
                'score_function': calculate_subjective_score
            })
    
    # ================================
    # Impulsivity
    # ================================
    
    if 'Impulsivity' in construct_data:
        impulsivity = construct_data['Impulsivity']
        
        # Suicidal ideation
        if 'Suicidal ideation' in impulsivity and impulsivity['Suicidal ideation']:
            scoring_options['Impulsivity'].append({
                'element': 'Suicidal ideation',
                'paca_value': impulsivity['Suicidal ideation'],
                'options': ['High', 'Moderate', 'Low'],
                'category': 'Impulsivity',
                'score_function': 'risk'
            })
        
        # Self mutilating behavior risk
        if 'Self mutilating behavior risk' in impulsivity and impulsivity['Self mutilating behavior risk']:
            scoring_options['Impulsivity'].append({
                'element': 'Self mutilating behavior risk',
                'paca_value': impulsivity['Self mutilating behavior risk'],
                'options': ['High', 'Moderate', 'Low'],
                'category': 'Impulsivity',
                'score_function': 'risk'
            })
        
        # Homicide risk
        if 'Homicide risk' in impulsivity and impulsivity['Homicide risk']:
            scoring_options['Impulsivity'].append({
                'element': 'Homicide risk',
                'paca_value': impulsivity['Homicide risk'],
                'options': ['High', 'Moderate', 'Low'],
                'category': 'Impulsivity',
                'score_function': 'risk'
            })
        
        # Suicidal plan
        if 'Suicidal plan' in impulsivity and impulsivity['Suicidal plan']:
            scoring_options['Impulsivity'].append({
                'element': 'Suicidal plan',
                'paca_value': impulsivity['Suicidal plan'],
                'options': ['Correct AND Evaluated properly', 'Incorrect OR NOT evaluated'],
                'category': 'Impulsivity',
                'score_function': calculate_plan_attempt_score
            })
        
        # Suicidal attempt
        if 'Suicidal attempt' in impulsivity and impulsivity['Suicidal attempt']:
            scoring_options['Impulsivity'].append({
                'element': 'Suicidal attempt',
                'paca_value': impulsivity['Suicidal attempt'],
                'options': ['Correct AND Evaluated properly', 'Incorrect OR NOT evaluated'],
                'category': 'Impulsivity',
                'score_function': calculate_plan_attempt_score
            })
    
    # ================================
    # Behavior (Mental Status Examination)
    # ================================
    
    if 'Mental Status Examination' in construct_data:
        mse = construct_data['Mental Status Examination']
        
        # Mood
        if 'Mood' in mse and mse['Mood']:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'Mood',
                'paca_value': mse['Mood'],
                'options': ['Irritable', 'Euphoric', 'Elated', 'Euthymic', 'Dysphoric', 'Depressed'],
                'category': 'Behavior',
                'score_function': 'mood'
            })
        
        # Verbal productivity
        if 'Verbal productivity' in mse and mse['Verbal productivity']:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'Verbal productivity',
                'paca_value': mse['Verbal productivity'],
                'options': ['Increased', 'Moderate', 'Decreased'],
                'category': 'Behavior',
                'score_function': 'verbal_productivity'
            })
        
        # Insight
        if 'Insight' in mse and mse['Insight']:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'Insight',
                'paca_value': mse['Insight'],
                'options': [
                    'Complete denial of illness',
                    'Slight awareness of being sick and needing help, but denying it at the same time',
                    'Awareness of being sick but blaming it on others, external events',
                    'Intellectual insight',
                    'True emotional insight'
                ],
                'category': 'Behavior',
                'score_function': 'insight'
            })
        
        # Affect (G-Eval style - categorical)
        if 'Affect' in mse and mse['Affect']:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'Affect',
                'paca_value': mse['Affect'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Behavior',
                'score_function': calculate_categorical_score
            })
        
        # Perception (G-Eval style - categorical)
        if 'Perception' in mse and mse['Perception']:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'Perception',
                'paca_value': mse['Perception'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Behavior',
                'score_function': calculate_categorical_score
            })
        
        # Thought process (G-Eval style - categorical)
        if 'Thought process' in mse and mse['Thought process']:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'Thought process',
                'paca_value': mse['Thought process'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Behavior',
                'score_function': calculate_categorical_score
            })
        
        # Thought content (G-Eval style - categorical)
        if 'Thought content' in mse and mse['Thought content']:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'Thought content',
                'paca_value': mse['Thought content'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Behavior',
                'score_function': calculate_categorical_score
            })
        
        # Spontaneity (Binary)
        if 'Spontaneity' in mse and mse['Spontaneity']:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'Spontaneity',
                'paca_value': mse['Spontaneity'],
                'options': ['Correct', 'Incorrect'],
                'category': 'Behavior',
                'score_function': calculate_binary_score
            })
        
        # Social judgement (Binary)
        if 'Social judgement' in mse and mse['Social judgement']:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'Social judgement',
                'paca_value': mse['Social judgement'],
                'options': ['Correct', 'Incorrect'],
                'category': 'Behavior',
                'score_function': calculate_binary_score
            })
        
        # Reliability (Binary)
        if 'Reliability' in mse and mse['Reliability']:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'Reliability',
                'paca_value': mse['Reliability'],
                'options': ['Correct', 'Incorrect'],
                'category': 'Behavior',
                'score_function': calculate_binary_score
            })
    
    return scoring_options


# ================================
# Scoring Options Generator (Legacy - for compatibility)
# ================================

def get_scoring_options(construct_data):
    """
    Legacy function - now redirects to get_aggregated_scoring_options
    Generate scoring options based on construct data
    Returns a dictionary with categories and their scoring elements
    """
    return get_aggregated_scoring_options(construct_data)

# ================================
# Result Creation
# ================================

def extract_score_from_option(option_text):
    """Extract score value from option text (e.g., 'Score=1' -> 1)"""
    import re
    match = re.search(r'Score=([\d.]+)', option_text)
    if match:
        return float(match.group(1))
    return 0


def create_validation_result(construct_data, expert_responses, exp_item, is_partial=False):
    """
    Create validation result JSON structure (Psyche validation style)
    Returns a dictionary with aggregated element-level scores and total psyche score
    
    Args:
        construct_data: PACA construct data
        expert_responses: Expert's responses for each element (already aggregated)
        exp_item: Tuple of (client_number, exp_number)
        is_partial: Boolean indicating if this is a partial save (default: False)
    """
    client_number, exp_number = exp_item
    
    result = {
        'client_number': client_number,
        'experiment_number': exp_number,
        'timestamp': int(datetime.now().timestamp()),
        'is_partial': is_partial,
        'elements': {}
    }
    
    # Get aggregated scoring options (already following PSYCHE RUBRIC structure)
    scoring_options = get_aggregated_scoring_options(construct_data)
    
    total_weighted_score = 0
    
    # Process each category
    for category, items in scoring_options.items():
        for item in items:
            element_name = item['element']
            
            if element_name not in expert_responses:
                continue
            
            expert_choice = expert_responses[element_name]
            paca_content = item['paca_value']
            score_func_type = item.get('score_function', None)
            
            # Check if PACA content is None or N/A - automatic 0 score
            if is_none_or_na(paca_content):
                score = 0
                weight = 0  # Set weight to 0 for missing data
            else:
                # Determine category weight
                if 'Subjective' in category:
                    weight = WEIGHTS['Subjective']
                elif 'Impulsivity' in category:
                    weight = WEIGHTS['Impulsivity']
                else:  # Behavior
                    weight = WEIGHTS['Behavior']
                
                # Calculate score based on function type
                score = 0
                
                if score_func_type == 'risk':
                    # Risk assessment (Impulsivity)
                    score = calculate_risk_score_from_values(expert_choice, paca_content)
                elif score_func_type == 'mood':
                    # Mood (ordinal)
                    score = calculate_ordinal_score_from_values(expert_choice, paca_content, MOOD_VALUES)
                elif score_func_type == 'verbal_productivity':
                    # Verbal productivity (ordinal)
                    score = calculate_ordinal_score_from_values(expert_choice, paca_content, VERBAL_PRODUCTIVITY_VALUES)
                elif score_func_type == 'insight':
                    # Insight (ordinal)
                    score = calculate_ordinal_score_from_values(expert_choice, paca_content, INSIGHT_VALUES)
                elif callable(score_func_type):
                    # Callable function
                    score = score_func_type(expert_choice)
                else:
                    # Default: extract from option text or use 0
                    score = extract_score_from_option(expert_choice)
                    if score == 0:
                        # Try to use default scoring based on text
                        if expert_choice == "Correct":
                            score = 1
                        elif expert_choice == "Partially correct":
                            score = 0.5
                        elif expert_choice == "Correct AND Evaluated properly":
                            score = 1
            
            weighted_score = score * weight
            total_weighted_score += weighted_score
            
            # Store element result directly (no need for aggregation since already aggregated)
            result['elements'][element_name] = {
                'expert_choice': expert_choice,  # Store expert's choice for reference
                'paca_content': str(paca_content),
                'score': score,
                'weight': weight,
                'weighted_score': weighted_score
            }
    
    # Add total psyche score (matching psyche validation format)
    result['psyche_score'] = total_weighted_score
    
    return result


# ================================
# Firebase Operations
# ================================

def sanitize_firebase_key(key):
    """
    Sanitize a string to be used as Firebase key or value
    Firebase doesn't allow: . $ # [ ] /
    """
    if key is None:
        return "None"
    
    key_str = str(key)
    # Replace forbidden characters with underscores
    replacements = {
        '.': '_',
        '$': '_',
        '#': '_',
        '[': '_',
        ']': '_',
        '/': '_'
    }
    
    for char, replacement in replacements.items():
        key_str = key_str.replace(char, replacement)
    
    return key_str


def save_validation_to_firebase(firebase_ref, expert_name, exp_item, validation_result):
    """
    Save validation result to Firebase
    
    Args:
        firebase_ref: Firebase reference
        expert_name: Name of the expert
        exp_item: Tuple of (client_number, exp_number)
        validation_result: Validation result dictionary
    """
    try:
        client_number, exp_number = exp_item
        # Sanitize expert name to avoid Firebase key errors
        sanitized_expert_name = sanitize_firebase_key(expert_name)
        key = f"expert_{sanitized_expert_name}_{client_number}_{exp_number}"
        firebase_ref.child(key).set(validation_result)
        return True
    except Exception as e:
        st.error(f"Firebase 저장 실패: {e}")
        return False


def load_validation_progress(firebase_ref, expert_name):
    """Load validation progress from Firebase"""
    try:
        # Sanitize expert name to match saved key
        sanitized_expert_name = sanitize_firebase_key(expert_name)
        progress_key = f"expert_progress_{sanitized_expert_name}"
        data = firebase_ref.child(progress_key).get()
        return data
    except Exception as e:
        st.error(f"진행도 로드 실패: {e}")
        return None


# ================================
# Helper Functions
# ================================

def calculate_score(element_type, selected_option, paca_value=None, expert_value=None):
    """
    Generic score calculation function
    Determines which scoring method to use based on element type
    """
    if element_type == 'subjective':
        return calculate_subjective_score(selected_option)
    elif element_type == 'length':
        return calculate_length_score(selected_option)
    elif element_type == 'risk':
        # Need to parse delta from option or calculate from values
        return extract_score_from_option(selected_option)
    elif element_type == 'plan_attempt':
        return calculate_plan_attempt_score(selected_option)
    elif element_type == 'ordinal':
        # Need delta value
        return extract_score_from_option(selected_option)
    elif element_type == 'categorical':
        return calculate_categorical_score(selected_option)
    elif element_type == 'binary':
        return calculate_binary_score(selected_option)
    else:
        return 0
