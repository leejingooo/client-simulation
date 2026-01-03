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


def create_sp_construct(client_number: str, profile_version: str, instruction_version: str, given_form_path: str, profile_override: Any = None) -> Dict[str, Any]:
    """
    Create an SP construct with PSYCHE RUBRIC structure.
    Ensures all PSYCHE RUBRIC fields are present.
    
    Args:
        client_number: Client number
        profile_version: Profile version string
        instruction_version: Instruction version string
        given_form_path: Path to given form
        profile_override: If provided, use this profile instead of loading from Firebase
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

    # Use profile_override if provided, otherwise load from Firebase
    if profile_override is not None:
        profile = profile_override
    else:
        profile = load_from_firebase(firebase_ref, client_number, firebase_profile_key)
    
    instruction = load_from_firebase(firebase_ref, client_number, firebase_beh_key)

    if profile is None and instruction is None:
        raise ValueError("Failed to load profile and behavioral instruction from Firebase")

    # Initialize construct with PSYCHE RUBRIC structure
    sp_construct = {
        "Chief complaint": {},
        "Present illness": {},
        "Family history": {},
        "Marriage/Relationship History": {},
        "Impulsivity": {},
        "Mental Status Examination": {}
    }

    # === Chief Complaint ===
    cc = get_nested_value(profile, "Chief complaint.description")
    sp_construct["Chief complaint"]["description"] = cc or ""

    # === Present Illness ===
    # Handle symptoms - collect all symptom_1, symptom_2, symptom_3, etc.
    present_illness = get_nested_value(profile, "Present illness")
    
    if present_illness and isinstance(present_illness, dict):
        # Collect all symptom_n keys (symptom_1, symptom_2, etc.) and add them directly
        for key in sorted(present_illness.keys()):
            if key.startswith("symptom_"):
                symptom_data = present_illness[key]
                if isinstance(symptom_data, dict):
                    sp_construct["Present illness"][key] = symptom_data

    # Triggering factor
    tf = get_nested_value(profile, "Present illness.triggering factor")
    sp_construct["Present illness"]["triggering_factor"] = tf or ""

    # Stressor
    stressor = get_nested_value(profile, "Present illness.stressor")
    sp_construct["Present illness"]["stressor"] = stressor or ""

    # === Family History ===
    # Collect all diagnosis_1, diagnosis_2, etc.
    family_history = get_nested_value(profile, "Family history")
    if family_history and isinstance(family_history, dict):
        # Collect diagnosis_n entries
        diagnosis_values = []
        for key in sorted(family_history.keys()):
            if key.startswith("diagnosis_"):
                val = family_history[key]
                if val and str(val).strip() and str(val).lower() not in ['none', 'n/a', 'null']:
                    diagnosis_values.append(str(val))
        
        if diagnosis_values:
            sp_construct["Family history"]["diagnosis"] = " ".join(diagnosis_values)
        else:
            sp_construct["Family history"]["diagnosis"] = ""
        
        # Collect substance_use_n entries
        substance_values = []
        for key in sorted(family_history.keys()):
            if key.startswith("substance_use_") or key.startswith("substance use_"):
                val = family_history[key]
                if val and str(val).strip() and str(val).lower() not in ['none', 'n/a', 'null']:
                    substance_values.append(str(val))
        
        if substance_values:
            sp_construct["Family history"]["substance use"] = " ".join(substance_values)
        else:
            sp_construct["Family history"]["substance use"] = ""
    else:
        sp_construct["Family history"]["diagnosis"] = ""
        sp_construct["Family history"]["substance use"] = ""

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
    
    # Define candidates for MSE fields (from given_form_version3.0.json)
    mse_candidates = {
        "Mood": ["euphoric", "elated", "euthymic", "dysphoric", "depressed", "irritable"],
        "Affect": ["broad", "restricted", "blunt", "flat", "labile", "anxious", "tense", "shallow", "inadequate", "inappropriate"],
        "Verbal productivity": ["increased", "moderate", "decreased"],
        "Spontaneity": ["(+)", "(-)"],
        "Insight": ["Complete denial of illness", "Slight awareness of being sick and needing help, but denying it at the same time", 
                    "Awareness of being sick but blaming it on others, external events", "Intellectual insight", "True emotional insight"],
        "Perception": ["Normal", "Illusion", "Auditory hallucination", "Visual hallucination", "Olfactory hallucination", 
                       "Gustatory hallucination", "Depersonalization", "Derealization", "Déjà vu", "Jamais vu"],
        "Thought process": ["Normal", "Loosening of association", "flight of idea", "circumstantiality", "tangentiality", 
                            "Word salad or incoherence", "Neologism", "Illogical", "Irrelevant"],
        "Thought content": ["Normal", "preoccupation", "overvalued idea", "idea of reference", "grandiosity, obsession/compulsion", 
                            "rumination", "delusion", "phobia"],
        "Social judgement": ["Normal", "Impaired"],
        "Reliability": ["Yes", "No"],
    }
    
    def normalize_mse_value(field: str, raw_value: str) -> str:
        """Normalize MSE value to match candidates from given_form"""
        if not raw_value:
            return ""
        
        if field not in mse_candidates:
            return raw_value
        
        raw_lower = raw_value.lower()
        candidates = mse_candidates[field]
        
        # Exact match (case-insensitive)
        for candidate in candidates:
            if raw_lower == candidate.lower():
                return candidate
        
        # For Affect: allow multiple selections (comma-separated)
        if field == "Affect":
            # Split by comma or parentheses and find all matching candidates
            parts = raw_value.replace('(', ',').replace(')', ',').split(',')
            matched = []
            for part in parts:
                word = part.strip().lower()
                if word:
                    for candidate in candidates:
                        if word == candidate.lower():
                            matched.append(candidate)
                            break
            if matched:
                # Return comma-separated list of matched affects
                return ", ".join(matched)
        
        # For Thought content: look for matching keywords
        if field == "Thought content":
            keywords = raw_value.lower().split()
            for keyword in keywords:
                for candidate in candidates:
                    if keyword in candidate.lower():
                        return candidate
        
        # Substring match - find best match
        for candidate in candidates:
            if candidate.lower() in raw_lower or raw_lower in candidate.lower():
                return candidate
        
        # Default: return first candidate if no match found
        return candidates[0] if candidates else raw_value
    
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
        
        # Normalize to match candidates
        normalized_value = normalize_mse_value(field, value)
        sp_construct["Mental Status Examination"][field] = normalized_value or ""

    return sp_construct
