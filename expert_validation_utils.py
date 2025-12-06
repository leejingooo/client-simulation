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
    """
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
    """
    # Normalize values
    expert_val = expert_value.lower() if expert_value else ''
    paca_val = paca_value.lower() if paca_value else ''
    
    # Map to numeric values
    expert_num = value_mapping.get(expert_val, 0)
    paca_num = value_mapping.get(paca_val, 0)
    
    delta = paca_num - expert_num
    
    return calculate_ordinal_score(delta)
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
# Scoring Options Generator
# ================================

def get_scoring_options(construct_data):
    """
    Generate scoring options based on construct data
    Returns a dictionary with categories and their scoring elements
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
            'element': 'Chief Complaint - Description',
            'paca_value': construct_data['Chief complaint']['description'],
            'options': ['Correct', 'Partially correct', 'Incorrect'],
            'category': 'Subjective',
            'score_function': calculate_subjective_score
        })
    
    # Present Illness - Symptoms
    if 'Present illness' in construct_data:
        present_illness = construct_data['Present illness']
        
        # Symptoms (name, alleviating factor, exacerbating factor)
        for i in range(1, 6):
            symptom_key = f'symptom_{i}'
            if symptom_key in present_illness:
                symptom = present_illness[symptom_key]
                
                # Symptom Name
                if 'name' in symptom:
                    scoring_options['Subjective Information'].append({
                        'element': f'Present Illness - Symptom {i} - Name',
                        'paca_value': symptom['name'],
                        'options': ['Correct', 'Partially correct', 'Incorrect'],
                        'category': 'Subjective',
                        'score_function': calculate_subjective_score
                    })
                
                # Alleviating Factor
                if 'alleviating factor' in symptom:
                    scoring_options['Subjective Information'].append({
                        'element': f'Present Illness - Symptom {i} - Alleviating Factor',
                        'paca_value': symptom['alleviating factor'],
                        'options': ['Correct', 'Partially correct', 'Incorrect'],
                        'category': 'Subjective',
                        'score_function': calculate_subjective_score
                    })
                
                # Exacerbating Factor
                if 'exacerbating factor' in symptom:
                    scoring_options['Subjective Information'].append({
                        'element': f'Present Illness - Symptom {i} - Exacerbating Factor',
                        'paca_value': symptom['exacerbating factor'],
                        'options': ['Correct', 'Partially correct', 'Incorrect'],
                        'category': 'Subjective',
                        'score_function': calculate_subjective_score
                    })
                
                # Length
                if 'length' in symptom:
                    scoring_options['Subjective Information'].append({
                        'element': f'Present Illness - Symptom {i} - Length',
                        'paca_value': symptom['length'],
                        'options': ['Correct', 'Incorrect'],
                        'category': 'Subjective',
                        'score_function': calculate_length_score
                    })
        
        # Triggering factor
        if 'triggering_factor' in present_illness:
            scoring_options['Subjective Information'].append({
                'element': 'Present Illness - Triggering Factor',
                'paca_value': present_illness['triggering_factor'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Subjective',
                'score_function': calculate_subjective_score
            })
        
        # Stressor
        if 'stressor' in present_illness:
            scoring_options['Subjective Information'].append({
                'element': 'Present Illness - Stressor',
                'paca_value': present_illness['stressor'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Subjective',
                'score_function': calculate_subjective_score
            })
    
    # Family History
    if 'Family history' in construct_data:
        family_history = construct_data['Family history']
        
        if 'diagnosis' in family_history:
            scoring_options['Subjective Information'].append({
                'element': 'Family History - Diagnosis',
                'paca_value': family_history['diagnosis'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Subjective',
                'score_function': calculate_subjective_score
            })
        
        if 'substance use' in family_history:
            scoring_options['Subjective Information'].append({
                'element': 'Family History - Substance Use',
                'paca_value': family_history['substance use'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Subjective',
                'score_function': calculate_subjective_score
            })
    
    # Marriage/Relationship History
    if 'Marriage_Relationship History' in construct_data:
        marriage = construct_data['Marriage_Relationship History']
        
        if 'current family structure' in marriage:
            scoring_options['Subjective Information'].append({
                'element': 'Marriage/Relationship History - Current Family Structure',
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
        if 'Suicidal ideation' in impulsivity:
            scoring_options['Impulsivity'].append({
                'element': 'Suicidal Ideation',
                'paca_value': impulsivity['Suicidal ideation'],
                'options': ['High', 'Moderate', 'Low'],
                'category': 'Impulsivity',
                'score_function': 'risk'
            })
        
        # Self mutilating behavior risk
        if 'Self mutilating behavior risk' in impulsivity:
            scoring_options['Impulsivity'].append({
                'element': 'Self Mutilating Behavior Risk',
                'paca_value': impulsivity['Self mutilating behavior risk'],
                'options': ['High', 'Moderate', 'Low'],
                'category': 'Impulsivity',
                'score_function': 'risk'
            })
        
        # Homicide risk
        if 'Homicide risk' in impulsivity:
            scoring_options['Impulsivity'].append({
                'element': 'Homicide Risk',
                'paca_value': impulsivity['Homicide risk'],
                'options': ['High', 'Moderate', 'Low'],
                'category': 'Impulsivity',
                'score_function': 'risk'
            })
        
        # Suicidal plan
        if 'Suicidal plan' in impulsivity:
            scoring_options['Impulsivity'].append({
                'element': 'Suicidal Plan',
                'paca_value': impulsivity['Suicidal plan'],
                'options': ['Correct AND Evaluated properly', 'Incorrect OR NOT evaluated'],
                'category': 'Impulsivity',
                'score_function': calculate_plan_attempt_score
            })
        
        # Suicidal attempt
        if 'Suicidal attempt' in impulsivity:
            scoring_options['Impulsivity'].append({
                'element': 'Suicidal Attempt',
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
        if 'Mood' in mse:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'MSE - Mood',
                'paca_value': mse['Mood'],
                'options': ['Irritable', 'Euphoric', 'Elated', 'Euthymic', 'Dysphoric', 'Depressed'],
                'category': 'Behavior',
                'score_function': 'mood'
            })
        
        # Verbal productivity
        if 'Verbal productivity' in mse:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'MSE - Verbal Productivity',
                'paca_value': mse['Verbal productivity'],
                'options': ['Increased', 'Moderate', 'Decreased'],
                'category': 'Behavior',
                'score_function': 'verbal_productivity'
            })
        
        # Insight
        if 'Insight' in mse:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'MSE - Insight',
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
        
        # Affect
        if 'Affect' in mse:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'MSE - Affect',
                'paca_value': mse['Affect'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Behavior',
                'score_function': calculate_categorical_score
            })
        
        # Perception
        if 'Perception' in mse:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'MSE - Perception',
                'paca_value': mse['Perception'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Behavior',
                'score_function': calculate_categorical_score
            })
        
        # Thought process
        if 'Thought process' in mse:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'MSE - Thought Process',
                'paca_value': mse['Thought process'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Behavior',
                'score_function': calculate_categorical_score
            })
        
        # Thought content
        if 'Thought content' in mse:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'MSE - Thought Content',
                'paca_value': mse['Thought content'],
                'options': ['Correct', 'Partially correct', 'Incorrect'],
                'category': 'Behavior',
                'score_function': calculate_categorical_score
            })
        
        # Spontaneity
        if 'Spontaneity' in mse:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'MSE - Spontaneity',
                'paca_value': mse['Spontaneity'],
                'options': ['Correct', 'Incorrect'],
                'category': 'Behavior',
                'score_function': calculate_binary_score
            })
        
        # Social judgement
        if 'Social judgement' in mse:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'MSE - Social Judgement',
                'paca_value': mse['Social judgement'],
                'options': ['Correct', 'Incorrect'],
                'category': 'Behavior',
                'score_function': calculate_binary_score
            })
        
        # Reliability
        if 'Reliability' in mse:
            scoring_options['Behavior (Mental Status Examination)'].append({
                'element': 'MSE - Reliability',
                'paca_value': mse['Reliability'],
                'options': ['Correct', 'Incorrect'],
                'category': 'Behavior',
                'score_function': calculate_binary_score
            })
    
    return scoring_options


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


def create_validation_result(construct_data, expert_responses, exp_item):
    """
    Create validation result JSON structure
    Returns a dictionary with element-level scores and total expert score
    
    Args:
        construct_data: PACA construct data
        expert_responses: Expert's responses for each element
        exp_item: Tuple of (client_number, exp_number)
    """
    client_number, exp_number = exp_item
    
    result = {
        'client_number': client_number,
        'experiment_number': exp_number,
        'timestamp': int(datetime.now().timestamp()),
        'elements': {}
    }
    
    scoring_options = get_scoring_options(construct_data)
    
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
            
            # Store element result
            result['elements'][element_name] = {
                'expert_choice': expert_choice,
                'paca_content': str(paca_content),
                'score': score,
                'weight': weight,
                'weighted_score': weighted_score
            }
    
    # Add total expert score
    result['expert_score'] = total_weighted_score
    
    return result


# ================================
# Firebase Operations
# ================================

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
        key = f"expert_{expert_name}_{client_number}_{exp_number}"
        firebase_ref.child(key).set(validation_result)
        return True
    except Exception as e:
        st.error(f"Firebase 저장 실패: {e}")
        return False


def load_validation_progress(firebase_ref, expert_name):
    """Load validation progress from Firebase"""
    try:
        progress_key = f"expert_progress_{expert_name}"
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
