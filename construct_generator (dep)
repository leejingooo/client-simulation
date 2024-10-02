import re
import json
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from typing import Dict, Any
from SP_utils import *

llm = ChatOpenAI(temperature=0, model="gpt-4o")


def load_form(form_path):
    with open(form_path, 'r') as file:
        return json.load(file)


def format_transcript(transcript):
    formatted_transcript = ""
    for turn in transcript:
        formatted_transcript += f"Doctor: {turn['Doctor']}\n"
        formatted_transcript += f"Patient: {turn['Patient']}\n"
    return formatted_transcript.strip()


def create_construct_generator():

    prompt_template = """
    Complete the given patient information form based on the provided transcript of a psychiatric assessment, adhering strictly to the structure and guidelines provided in the form.
    
    1. Carefully review the content within the <Given transcript> tags.
    2. Examine the structured <Given form> which contains fields for patient information.
    3. Fill in the <Given form> using information extracted from the transcript, following the specific data type, guide or candidate for each field.
    
    - You're a psychiatric expert. Even when information is not directly stated, try to take clues from the <Given transcript> and fill in all the blanks with appropriate medical and psychiatric inferences.
    - In <Given form>, there are items labeled “_n”. Fill in the “n” of these items with the appropriate number.
    - Ensure all entered information is accurate and directly supported by the transcript.
    - Adhere to the data type, guide or candidate specified for each field.

    <Given transcript>
    {given_transcript}
    </Given transcript>

    <Given form>
    {given_form}
    </Given form>
    
    Present the completed form in a structured JSON format, maintaining the hierarchy and field names of the original form. Use English for all entries in the form:
    """

    prompt = PromptTemplate(
        input_variables=["given_transcript", "given_form"],
        template=prompt_template
    )

    chain = LLMChain(llm=llm, prompt=prompt)
    return chain


def generate_construct(generator, transcript, form):
    formatted_transcript = format_transcript(transcript)
    result = generator.run(given_transcript=formatted_transcript,
                           given_form=json.dumps(form, indent=2))
    return result


def create_sp_construct(client_number: str, profile_version: str, instruction_version: str, given_form_path: str) -> Dict[str, Any]:
    firebase_ref = get_firebase_ref()

    # Load profile and instruction from Firebase
    profile = load_from_firebase(
        firebase_ref, client_number, f"profile_version{profile_version}")
    instruction = load_from_firebase(
        firebase_ref, client_number, f"beh_dir_version{instruction_version}")

    if not profile or not instruction:
        raise ValueError("Failed to load profile or instruction from Firebase")

    # Load the given form
    with open(given_form_path, 'r') as f:
        given_form = json.load(f)

    # Create the SP construct
    sp_construct = {}

    def clean_value(value):
        if isinstance(value, str):
            # 쌍따옴표로 둘러싸인 부분 제거
            cleaned = re.sub(r'"[^"]*"', '', value).strip()
            # 연속된 공백을 하나의 공백으로 대체
            cleaned = re.sub(r'\s+', ' ', cleaned)
            return cleaned
        elif isinstance(value, dict):
            return {k: clean_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [clean_value(item) for item in value]
        else:
            return value

    for key, value in given_form.items():
        if key in profile:
            sp_construct[key] = clean_value(profile[key])
        elif key == "Mental Status Examination":
            sp_construct[key] = extract_mse_from_instruction(instruction)
        else:
            sp_construct[key] = clean_value(value)

    return sp_construct


def extract_mse_from_instruction(instruction: str) -> Dict[str, str]:
    mse = {}
    mse_section = instruction.split("<Form>")[1].split("</Form>")[0].strip()

    # 정규 표현식을 사용하여 각 항목을 분리
    pattern = r'- *([\w /]+) *: *(.+?)(?=- *[\w /]+ *:|$)'
    matches = re.findall(pattern, mse_section, re.DOTALL)

    for key, value in matches:
        # 쌍따옴표로 둘러싸인 부분 제거
        cleaned_value = re.sub(r'"[^"]*"', '', value).strip()
        # 연속된 공백을 하나의 공백으로 대체
        cleaned_value = re.sub(r'\s+', ' ', cleaned_value)
        mse[key.strip()] = cleaned_value

    return mse
