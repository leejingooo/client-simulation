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
    1. View the <Given transcript>
    2. The <Given form> is for information about the patient, which is all blank.
    3. Fill in the <Given form> based on the transcript.

    <Given transcript>
    {given_transcript}
    </Given transcript>

    <Given form>
    {given_form}
    </Given form>
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
