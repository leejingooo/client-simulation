import json
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

llm = ChatOpenAI(temperature=0, model="gpt-4")


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
    3. Fill in the <Given form> using information extracted from the transcript, following the specific data types and guidelines for each field.
    4. Use English for all entries in the form.
    
    - If specific information is not available in the transcript, enter "Not provided" for that field.
    - Ensure all entered information is accurate and directly supported by the transcript.
    - If there are inconsistencies or ambiguities in the transcript, note them in [square brackets] after the relevant field.
    - Adhere to the data types and range/candidate/guides specified for each field.

    <Given transcript>
    {given_transcript}
    </Given transcript>

    <Given form>
    {given_form}
    </Given form>
    
    Present the completed form in a structured JSON format, maintaining the hierarchy and field names of the original form:
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
