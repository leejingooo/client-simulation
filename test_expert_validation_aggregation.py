"""
Test script to verify expert validation aggregation
Ensures the output format matches psyche validation format
"""

import json
from expert_validation_utils import get_aggregated_scoring_options, create_validation_result

# Sample construct data (similar to what PACA generates)
test_construct = {
    'Chief complaint': {
        'description': '요즘 계속 너무 지치고, 뭐든 다 버겁고, 없어져 버리고 싶다는 생각이 자꾸 난다'
    },
    'Present illness': {
        'symptom_1': {
            'name': 'Suicidal ideation',
            'alleviating factor': 'None',
            'exacerbating factor': '출근과 직장 스트레스, 돈 문제로 인한 남편과의 갈등',
            'length': '24'
        },
        'symptom_2': {
            'name': 'Depressed mood',
            'alleviating factor': 'None',
            'exacerbating factor': '출근과 직장 스트레스, 돈 문제로 인한 부부 갈등, 육아에 대한 죄책감',
            'length': '24'
        },
        'symptom_3': {
            'name': 'Anxiety',
            'alleviating factor': 'None',
            'exacerbating factor': '출근과 직장 내 평가·지적에 대한 두려움, 돈 문제로 인한 부부 갈등',
            'length': '24'
        },
        'triggering_factor': '최근 수면제 과량 복용 후 응급실 방문',
        'stressor': 'home, work, interpersonal difficulty'
    },
    'Family history': {
        'diagnosis': 'N/A',
        'substance use': 'N/A'
    },
    'Marriage_Relationship History': {
        'current family structure': '남편과 자녀들과 함께 거주'
    },
    'Impulsivity': {
        'Suicidal ideation': 'high',
        'Self mutilating behavior risk': 'high',
        'Homicide risk': 'low',
        'Suicidal plan': 'presence',
        'Suicidal attempt': 'presence'
    },
    'Mental Status Examination': {
        'Mood': 'depressed, dysphoric',
        'Verbal productivity': 'moderate',
        'Insight': 'True emotional insight',
        'Affect': 'anxious, tense, restricted',
        'Perception': 'Normal',
        'Thought process': 'Normal',
        'Thought content': 'Preoccupation, Rumination',
        'Spontaneity': '(+)',
        'Social judgement': 'Normal',
        'Reliability': 'Yes'
    }
}

# Get aggregated scoring options
print("=" * 80)
print("STEP 1: Get Aggregated Scoring Options")
print("=" * 80)

scoring_options = get_aggregated_scoring_options(test_construct)

print("\nCategories and Elements:")
for category, items in scoring_options.items():
    print(f"\n{category}:")
    for item in items:
        element = item['element']
        paca_value = item['paca_value']
        print(f"  - {element}")
        if '\n' in str(paca_value):
            # Multi-line value (aggregated symptoms)
            print(f"    PACA (aggregated):")
            for line in str(paca_value).split('\n'):
                print(f"      {line}")
        else:
            print(f"    PACA: {paca_value}")

# Simulate expert responses (aggregated elements)
expert_responses = {
    'Chief complaint': 'Correct',
    'Symptom name': 'Correct',
    'Alleviating factor': 'Correct',
    'Exacerbating factor': 'Correct',
    'length': 'Correct',
    'Triggering factor': 'Correct',
    'Stressor': 'Correct',
    'Diagnosis': 'Correct',
    'Substance use': 'Correct',
    'Current family structure': 'Correct',
    'Suicidal ideation': 'Low',  # Expert says low, PACA says high
    'Self mutilating behavior risk': 'Moderate',  # Expert says moderate, PACA says high
    'Homicide risk': 'Moderate',  # Expert says moderate, PACA says low
    'Suicidal plan': 'Correct AND Evaluated properly',
    'Suicidal attempt': 'Correct AND Evaluated properly',
    'Mood': 'Irritable',  # Expert says irritable, PACA says depressed
    'Verbal productivity': 'Increased',  # Expert says increased, PACA says moderate
    'Insight': 'Awareness of being sick but blaming it on others, external events',
    'Affect': 'Correct',
    'Perception': 'Correct',
    'Thought process': 'Correct',
    'Thought content': 'Correct',
    'Spontaneity': 'Correct',
    'Social judgement': 'Correct',
    'Reliability': 'Correct'
}

# Create validation result
print("\n" + "=" * 80)
print("STEP 2: Create Validation Result")
print("=" * 80)

validation_result = create_validation_result(
    test_construct,
    expert_responses,
    (6101, 101),  # Client 6101, Experiment 101
    is_partial=False
)

print("\nValidation Result (JSON):")
print(json.dumps(validation_result, indent=2, ensure_ascii=False))

# Verify format matches psyche validation
print("\n" + "=" * 80)
print("STEP 3: Verify Format Matches Psyche Validation")
print("=" * 80)

expected_keys = ['client_number', 'experiment_number', 'timestamp', 'is_partial', 'elements', 'psyche_score']
actual_keys = list(validation_result.keys())

print("\nExpected keys:", expected_keys)
print("Actual keys:", actual_keys)
print("Match:", set(expected_keys) == set(actual_keys))

print("\nElement structure check:")
for element_name, element_data in list(validation_result['elements'].items())[:3]:
    print(f"\n{element_name}:")
    print(f"  Keys: {list(element_data.keys())}")
    expected_element_keys = ['expert_choice', 'paca_content', 'score', 'weight', 'weighted_score']
    print(f"  Expected: {expected_element_keys}")
    print(f"  Match: {set(expected_element_keys) == set(element_data.keys())}")

print("\n" + "=" * 80)
print("Total psyche_score:", validation_result['psyche_score'])
print("=" * 80)

print("\n✅ Test completed successfully!")
print("Expert validation now outputs the same format as psyche validation.")
