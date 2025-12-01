import re
import json
from typing import Dict, Any, List
from SP_utils import load_from_firebase


def load_form(form_path: str) -> Dict[str, Any]:
    with open(form_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def extract_mse_from_instruction(instruction: str) -> Dict[str, str]:
    """Extract Mental Status Examination from instruction."""
    if not instruction:
        return {}
    
    mse = {}
    
    # Pattern to match "- Key : Value" where Value can be multiline until next "- Key"
    pattern = r'- ([\w\s/]+?) *: *(.+?)(?=\n- |\Z)'
    matches = re.findall(pattern, instruction, re.DOTALL)
    
    for key, value in matches:
        key = key.strip()
        # Clean up the value: remove quotes and extra whitespace
        value = value.strip()
        # Remove quoted examples
        value = re.sub(r'"[^"]*"', '', value)
        # Clean up whitespace
        value = re.sub(r'\s+', ' ', value).strip()
        
        if value:
            mse[key] = value
    
    return mse


# ============================================================================
# PSYCHE RUBRIC MAPPING - defines which fields go to which sections
# ============================================================================

PSYCHE_RUBRIC_STRUCTURE = {
    "Chief complaint": {
        "section": "Chief complaint",
        "profile_key": "Chief complaint.description"
    },
    
    "Present illness": {
        "Symptom name": {"profile_key": "Present illness.symptom_n", "subfield": "name"},
        "Alleviating factor": {"profile_key": "Present illness.symptom_n", "subfield": "alleviating factor"},
        "Exacerbating factor": {"profile_key": "Present illness.symptom_n", "subfield": "exacerbating factor"},
        "length": {"profile_key": "Present illness.symptom_n", "subfield": "length"},
        "Triggering factor": {"profile_key": "Present illness.triggering factor"},
        "Stressor": {"profile_key": "Present illness.stressor"},
    },
    
    "Family history": {
        "Diagnosis": {"profile_key": "Family history.diagnosis_n"},
        "Substance use": {"profile_key": "Family history.substance_use_n"},
    },
    
    "Marriage/Relationship History": {
        "Current family structure": {"profile_key": "Marriage_relationship history.current family structure"},
    },
    
    "Impulsivity": {
        "Suicidal ideation": {"profile_key": "Impulsivity.suicidal ideation"},
        "Self mutilating behavior risk": {"profile_key": "Impulsivity.self mutilating behavior risk"},
        "Homicide risk": {"profile_key": "Impulsivity.homicide risk"},
        "Suicidal plan": {"profile_key": "Impulsivity.suicidal plan"},
        "Suicidal attempt": {"profile_key": "Impulsivity.suicidal attempt"},
    },
    
    "Mental Status Examination": {
        "Mood": {"profile_key": "Mental Status Examination.Mood"},
        "Affect": {"profile_key": "Mental Status Examination.Affect"},
        "Verbal productivity": {"profile_key": "Mental Status Examination.Verbal productivity"},
        "Insight": {"profile_key": "Mental Status Examination.Insight"},
        "Perception": {"profile_key": "Mental Status Examination.Perception"},
        "Thought process": {"profile_key": "Mental Status Examination.Thought process"},
        "Thought content": {"profile_key": "Mental Status Examination.Thought content"},
        "Spontaneity": {"profile_key": "Mental Status Examination.Spontaneity"},
        "Social judgement": {"profile_key": "Mental Status Examination.Social judgement"},
        "Reliability": {"profile_key": "Mental Status Examination.Reliability"},
    }
}


def get_nested_value(obj: Any, path: str) -> Any:
    """Get value from nested object using dot notation."""
    if obj is None:
        return None
    
    parts = path.split('.')
    current = obj
    
    for part in parts:
        if isinstance(current, dict):
            # Try exact match first
            if part in current:
                current = current[part]
            else:
                # Try case-insensitive match
                for key in current.keys():
                    if key.lower() == part.lower():
                        current = current[key]
                        break
                else:
                    return None
        else:
            return None
    
    return current


def create_sp_construct(client_number: str, profile_version: str, instruction_version: str, given_form_path: str) -> Dict[str, Any]:
    """
    Create an SP construct with PSYCHE RUBRIC structure.
    Ensures all PSYCHE RUBRIC fields are present.
    """
    
    # Normalize versions
    try:
        if isinstance(profile_version, (int, float)):
            profile_version_str = f"{float(profile_version):.1f}"
        else:
            profile_version_str = str(profile_version)
    except Exception:
        profile_version_str = str(profile_version)

    try:
        if isinstance(instruction_version, (int, float)):
            instruction_version_str = f"{float(instruction_version):.1f}"
        else:
            instruction_version_str = str(instruction_version)
    except Exception:
        instruction_version_str = str(instruction_version)

    # Load data
    firebase_profile_key = f"profile_version{profile_version_str.replace('.', '_')}"
    firebase_beh_key = f"beh_dir_version{instruction_version_str.replace('.', '_')}"

    try:
        from firebase_config import get_firebase_ref
        firebase_ref = get_firebase_ref()
    except Exception:
        firebase_ref = None

    if firebase_ref is None:
        raise RuntimeError("Firebase reference not available. Ensure the app provides Firebase configuration.")

    profile = load_from_firebase(firebase_ref, client_number, firebase_profile_key)
    instruction = load_from_firebase(firebase_ref, client_number, firebase_beh_key)

    if profile is None and instruction is None:
        raise ValueError("Failed to load profile and behavioral instruction from Firebase")

    # Initialize construct with PSYCHE RUBRIC structure
    sp_construct = {
        "Chief complaint": {},
        "Present illness": {"symptom_n": []},
        "Family history": {},
        "Marriage/Relationship History": {},
        "Impulsivity": {},
        "Mental Status Examination": {}
    }

    # === Chief Complaint ===
    cc = get_nested_value(profile, "Chief complaint.description")
    sp_construct["Chief complaint"]["description"] = cc or ""

    # === Present Illness ===
    # Handle symptoms - can be dict (single) or list (multiple)
    symptom_list = get_nested_value(profile, "Present illness.symptom_n")
    
    if isinstance(symptom_list, dict):
        # Single symptom as dict
        sp_construct["Present illness"]["symptom_n"] = [symptom_list]
    elif isinstance(symptom_list, list):
        # Already a list
        sp_construct["Present illness"]["symptom_n"] = symptom_list
    else:
        sp_construct["Present illness"]["symptom_n"] = []

    # Triggering factor
    tf = get_nested_value(profile, "Present illness.triggering factor")
    sp_construct["Present illness"]["triggering_factor"] = tf or ""

    # Stressor
    stressor = get_nested_value(profile, "Present illness.stressor")
    sp_construct["Present illness"]["stressor"] = stressor or ""

    # === Family History ===
    # diagnosis_n can be string or list
    diagnosis = get_nested_value(profile, "Family history.diagnosis_n")
    if isinstance(diagnosis, list):
        sp_construct["Family history"]["diagnosis"] = " ".join(str(d) for d in diagnosis) if diagnosis else ""
    else:
        sp_construct["Family history"]["diagnosis"] = str(diagnosis) if diagnosis else ""

    # substance_use_n can be string or list
    substance = get_nested_value(profile, "Family history.substance_use_n")
    if isinstance(substance, list):
        sp_construct["Family history"]["substance use"] = " ".join(str(s) for s in substance) if substance else ""
    else:
        sp_construct["Family history"]["substance use"] = str(substance) if substance else ""

    # === Marriage/Relationship History ===
    family_struct = get_nested_value(profile, "Marriage_relationship history.current family structure")
    sp_construct["Marriage/Relationship History"]["current family structure"] = family_struct or ""

    # === Impulsivity ===
    impulsivity_fields = [
        ("suicidal ideation", "Suicidal ideation"),
        ("self mutilating behavior risk", "Self mutilating behavior risk"),
        ("homicide risk", "Homicide risk"),
        ("suicidal plan", "Suicidal plan"),
        ("suicidal attempt", "Suicidal attempt"),
    ]
    
    for profile_key, rubric_key in impulsivity_fields:
        val = get_nested_value(profile, f"Impulsivity.{profile_key}")
        sp_construct["Impulsivity"][rubric_key] = val or ""

    # === Mental Status Examination ===
    # Try to extract from instruction first, then profile
    mse_from_instruction = extract_mse_from_instruction(instruction) if instruction else {}
    
    mse_fields = [
        "Mood",
        "Affect", 
        "Verbal productivity",
        "Insight",
        "Perception",
        "Thought process",
        "Thought content",
        "Spontaneity",
        "Social judgement",
        "Reliability",
    ]
    
    for field in mse_fields:
        # Try instruction first (exact match or case-insensitive)
        value = None
        
        if field in mse_from_instruction:
            value = mse_from_instruction[field]
        else:
            # Try case-insensitive match in instruction
            for key in mse_from_instruction.keys():
                if key.lower() == field.lower():
                    value = mse_from_instruction[key]
                    break
        
        # If not found in instruction, try profile
        if not value:
            value = get_nested_value(profile, f"Mental Status Examination.{field}")
        
        sp_construct["Mental Status Examination"][field] = value or ""

    return sp_construct
