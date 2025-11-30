import re
import json
from typing import Dict, Any
from SP_utils import load_from_firebase


def load_form(form_path: str) -> Dict[str, Any]:
    with open(form_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def extract_mse_from_instruction(instruction: str) -> Dict[str, str]:
    # Safely extract the MSE <Form> ... </Form> section
    try:
        mse_section = instruction.split("<Form>")[1].split("</Form>")[0].strip()
    except Exception:
        return {}

    mse = {}
    # Use regex to split items like '- Item : value'
    pattern = r'- *([\w /]+) *: *(.+?)(?=- *[\w /]+ *:|$)'
    matches = re.findall(pattern, mse_section, re.DOTALL)

    for key, value in matches:
        cleaned_value = re.sub(r'"[^\"]*"', '', value).strip()
        cleaned_value = re.sub(r'\s+', ' ', cleaned_value)
        mse[key.strip()] = cleaned_value

    return mse


def create_sp_construct(client_number: str, profile_version: str, instruction_version: str, given_form_path: str) -> Dict[str, Any]:
    """
    Create an SP construct by combining the stored profile and behavioral instruction
    according to the structure of the given form.

    Parameters:
    - client_number: client id (string or numeric)
    - profile_version: version string or number (e.g. '6.0' or '6_0' or 6.0)
    - instruction_version: version string or number (similar format)
    - given_form_path: path to the given_form json file

    Returns a dict representing the SP construct or raises on failure.
    """

    # Normalize versions to string with dot if needed
    try:
        # If numeric, convert to x.y format
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

    # Load profile and instruction from Firebase
    firebase_profile_key = f"profile_version{profile_version_str.replace('.', '_')}"
    firebase_beh_key = f"beh_dir_version{instruction_version_str.replace('.', '_')}"

    # Note: load_from_firebase requires firebase_ref and client_number; callers typically
    # call create_sp_construct from the web app where firebase_ref is available via SP_utils.
    # We'll obtain firebase_ref below and then call load_from_firebase with proper args.

    # Instead of calling load_from_firebase without firebase_ref, we'll attempt to import
    # get_firebase_ref here if available to obtain the firebase ref dynamically.
    try:
        from firebase_config import get_firebase_ref
        firebase_ref = get_firebase_ref()
    except Exception:
        firebase_ref = None

    if firebase_ref is None:
        # Try calling load_from_firebase with None will fail; instead, raise informative error
        raise RuntimeError("Firebase reference not available. Ensure the app provides Firebase configuration.")

    profile = load_from_firebase(firebase_ref, client_number, firebase_profile_key)
    instruction = load_from_firebase(firebase_ref, client_number, firebase_beh_key)

    if profile is None and instruction is None:
        raise ValueError("Failed to load profile and behavioral instruction from Firebase")

    # Load the given form file
    try:
        given_form = load_form(given_form_path)
    except Exception as e:
        raise ValueError(f"Failed to load given form: {e}")

    # Helper to clean values like in deprecated generator
    def clean_value(value):
        if isinstance(value, str):
            cleaned = re.sub(r'"[^\"]*"', '', value).strip()
            cleaned = re.sub(r'\s+', ' ', cleaned)
            return cleaned
        elif isinstance(value, dict):
            return {k: clean_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [clean_value(item) for item in value]
        else:
            return value

    sp_construct: Dict[str, Any] = {}

    for key, value in given_form.items():
        if isinstance(profile, dict) and key in profile:
            sp_construct[key] = clean_value(profile[key])
        elif key == "Mental Status Examination" and instruction:
            sp_construct[key] = extract_mse_from_instruction(instruction)
        else:
            sp_construct[key] = clean_value(value)

    return sp_construct
