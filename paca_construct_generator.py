"""
PACA Construct Generator

Creates a PACA construct by querying the PACA agent for field values.
The output structure matches the SP construct structure for easy comparison.
"""

import json
from typing import Dict, Any, List, Tuple
import re


def generate_symptoms_from_paca(paca_agent) -> List[Dict[str, Any]]:
    """
    Query PACA for multiple symptoms.
    
    Returns a list of symptom dicts with keys: name, length, alleviating_factor, exacerbating_factor
    """
    
    # Step 1: Ask how many main symptoms
    prompt_symptoms_count = """Based on the patient interview, how many main psychiatric symptoms did the patient present? 
    Please provide ONLY a number (e.g., 1, 2, 3, 4, etc.). If uncertain, provide your best estimate."""
    
    response = paca_agent(prompt_symptoms_count)
    try:
        num_symptoms = int(re.search(r'\d+', response).group())
        num_symptoms = max(1, min(num_symptoms, 5))  # Limit to 1-5 symptoms
    except:
        num_symptoms = 1
    
    symptoms = []
    
    # Step 2: For each symptom, gather details
    for i in range(num_symptoms):
        symptom_num = i + 1
        symptom = {}
        
        # Get symptom name
        prompt_name = f"""Based on the patient interview, what is symptom #{symptom_num}? 
        Please provide ONLY the symptom name in SHORT form (e.g., "Depressed mood", "Insomnia", etc.).
        If uncertain or if there are fewer than {symptom_num} symptoms, state "N/A"."""
        
        response = paca_agent(prompt_name)
        symptom['name'] = response.strip()
        
        if "n/a" in response.lower():
            continue
        
        # Get symptom duration
        prompt_duration = f"""For the patient's symptom "{symptom['name']}", how long has it been present? 
        Please provide ONLY a number in weeks (e.g., 4, 12, 24). If over 24 weeks, answer 24.
        If uncertain, provide your best estimate."""
        
        response = paca_agent(prompt_duration)
        try:
            duration = int(re.search(r'\d+', response).group())
            duration = max(0, min(duration, 24))  # Limit to 0-24
        except:
            duration = 0
        symptom['length'] = duration
        
        # Get alleviating factors
        prompt_alleviating = f"""For the patient's symptom "{symptom['name']}", what makes it better or improves it?
        Please provide a concise answer. If none, state "None"."""
        
        response = paca_agent(prompt_alleviating)
        symptom['alleviating_factor'] = response.strip()
        
        # Get exacerbating factors
        prompt_exacerbating = f"""For the patient's symptom "{symptom['name']}", what makes it worse or triggers it?
        Please provide a concise answer. If none, state "None"."""
        
        response = paca_agent(prompt_exacerbating)
        symptom['exacerbating_factor'] = response.strip()
        
        symptoms.append(symptom)
    
    return symptoms if symptoms else [{"name": "N/A", "length": 0, "alleviating_factor": "", "exacerbating_factor": ""}]


def generate_field(paca_agent, field_name: str, guide: str = "") -> str:
    """
    Query PACA for a single field value.
    """
    question = f"""Based on your psychiatric interview and the entire conversation history, what is the patient's {field_name}?
    Please provide a concise answer{f', referencing the following guideline: {guide}' if guide else ''}.
    For example, if the mood is depressed, DO NOT say "The patient's mood is depressed", but just answer "depressed" as if it were a given candidate.
    Except for unavoidable cases like "Chief complaint", DO NOT answer in sentence form, but in SHORT-ANSWER form.
    If you're uncertain, simply state "N/A"."""
    
    response = paca_agent(question)
    
    if "i don't know" in response.lower() or "uncertain" in response.lower():
        return "N/A"
    
    return response.strip()


def create_paca_construct(paca_agent) -> Dict[str, Any]:
    """
    Create a PACA construct with the same structure as SP construct.
    
    Structure:
    {
        "Chief complaint": {"description": "..."},
        "Present illness": {
            "symptom_n": [{...}, {...}],
            "triggering_factor": "...",
            "stressor": "..."
        },
        "Family history": {
            "diagnosis": "...",
            "substance use": "..."
        },
        "Marriage/Relationship History": {
            "current family structure": "..."
        },
        "Impulsivity": {
            "Suicidal ideation": "...",
            "Self mutilating behavior risk": "...",
            "Homicide risk": "...",
            "Suicidal plan": "...",
            "Suicidal attempt": "..."
        },
        "Mental Status Examination": {
            "Mood": "...",
            "Affect": "...",
            ...
        }
    }
    """
    
    paca_construct = {}
    
    # === Chief Complaint ===
    paca_construct["Chief complaint"] = {
        "description": generate_field(paca_agent, "Chief complaint", "Describe in the patient's words")
    }
    
    # === Present Illness ===
    paca_construct["Present illness"] = {}
    
    # Generate multiple symptoms
    symptoms = generate_symptoms_from_paca(paca_agent)
    paca_construct["Present illness"]["symptom_n"] = symptoms
    
    # Get triggering factor
    paca_construct["Present illness"]["triggering_factor"] = generate_field(
        paca_agent, "triggering factor",
        "The reason patient came to the hospital at this time"
    )
    
    # Get stressor
    paca_construct["Present illness"]["stressor"] = generate_field(
        paca_agent, "stressor",
        "(multiple answers available) home/work/school/legal issue/medical comorbidity/interpersonal difficulty/null"
    )
    
    # === Family History ===
    paca_construct["Family history"] = {
        "diagnosis": generate_field(
            paca_agent, "Family history diagnosis",
            "Describe a psychiatric family history"
        ),
        "substance use": generate_field(
            paca_agent, "Family history substance use",
            "Describe a family history of substance use (alcohol, opioid, cannabinoid, etc.)"
        )
    }
    
    # === Marriage/Relationship History ===
    paca_construct["Marriage/Relationship History"] = {
        "current family structure": generate_field(
            paca_agent, "Current family structure"
        )
    }
    
    # === Impulsivity ===
    paca_construct["Impulsivity"] = {
        "Suicidal ideation": generate_field(
            paca_agent, "Suicidal ideation",
            "candidate: high/moderate/low"
        ),
        "Self mutilating behavior risk": generate_field(
            paca_agent, "Self mutilating behavior risk",
            "candidate: high/moderate/low"
        ),
        "Homicide risk": generate_field(
            paca_agent, "Homicide risk",
            "candidate: high/moderate/low"
        ),
        "Suicidal plan": generate_field(
            paca_agent, "Suicidal plan",
            "candidate: presence/absence"
        ),
        "Suicidal attempt": generate_field(
            paca_agent, "Suicidal attempt",
            "candidate: presence/absence"
        )
    }
    
    # === Mental Status Examination ===
    paca_construct["Mental Status Examination"] = {
        "Mood": generate_field(
            paca_agent, "Mood",
            "candidate: euphoric/elated/euthymic/dysphoric/depressed/irritable"
        ),
        "Affect": generate_field(
            paca_agent, "Affect",
            "candidate: broad/restricted/blunt/flat/labile/anxious/tense/shallow/inadequate/inappropriate"
        ),
        "Verbal productivity": generate_field(
            paca_agent, "Verbal productivity",
            "candidate: increased/moderate/decreased"
        ),
        "Insight": generate_field(
            paca_agent, "Insight",
            "candidate: Complete denial of illness/Slight awareness.../Awareness.../Intellectual insight/True emotional insight"
        ),
        "Perception": generate_field(
            paca_agent, "Perception",
            "candidate: Normal/Illusion/Auditory hallucination/Visual hallucination/etc."
        ),
        "Thought process": generate_field(
            paca_agent, "Thought process",
            "candidate: Normal/Loosening of association/flight of idea/etc."
        ),
        "Thought content": generate_field(
            paca_agent, "Thought content",
            "candidate: Normal/preoccupation/overvalued idea/etc."
        ),
        "Spontaneity": generate_field(
            paca_agent, "Spontaneity",
            "candidate: (+)/(-)"
        ),
        "Social judgement": generate_field(
            paca_agent, "Social judgement",
            "candidate: Normal/Impaired"
        ),
        "Reliability": generate_field(
            paca_agent, "Reliability",
            "candidate: Yes/No"
        )
    }
    
    return paca_construct
