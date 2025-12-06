"""
Test with ACTUAL Firebase structure (sanitized keys)
"""

import os
os.environ['OPENAI_API_KEY'] = 'dummy-key-for-testing'

import sys
sys.path.insert(0, '/workspaces/client-simulation')

from evaluator import get_value_from_construct, PSYCHE_RUBRIC
from expert_validation_utils import get_aggregated_scoring_options

# This is what constructs look like AFTER being saved and loaded from Firebase
# (sanitize_dict converts / to _)
test_construct_from_firebase = {
    "Chief complaint": {
        "description": "I feel empty and exhausted"
    },
    "Present illness": {
        "symptom_1": {
            "name": "Low mood",
            "alleviating factor": "Rest",
            "exacerbating factor": "Work stress",
            "length": 12
        },
        "triggering_factor": "Brought to ED by husband after overdose",
        "stressor": "home_work_interpersonal difficulty"  # Sanitized!
    },
    "Family history": {
        "diagnosis": "Depression in mother",
        "substance use": "None"
    },
    "Marriage_Relationship History": {  # Sanitized: / → _
        "current family structure": "Married with 2 children"
    },
    "Impulsivity": {
        "Suicidal ideation": "high",
        "Self mutilating behavior risk": "low",
        "Homicide risk": "low",
        "Suicidal plan": "presence",
        "Suicidal attempt": "presence"
    },
    "Mental Status Examination": {
        "Mood": "depressed",
        "Affect": "restricted, blunt",
        "Verbal productivity": "decreased",
        "Spontaneity": "(-)",
        "Insight": "slight awareness of being sick and needing help, but denying it at the same time",
        "Perception": "Normal",
        "Thought process": "Normal",
        "Thought content": "preoccupation, rumination",
        "Social judgement": "Normal",
        "Reliability": "Yes"
    }
}

print("=" * 100)
print("TEST WITH ACTUAL FIREBASE STRUCTURE (after sanitize_dict)")
print("=" * 100)

# Test critical fields
print("\n[TEST] Critical Fields from Firebase-loaded construct")
print("-" * 100)

critical_tests = {
    "Triggering factor": test_construct_from_firebase["Present illness"].get("triggering_factor"),
    "Stressor": test_construct_from_firebase["Present illness"].get("stressor"),
    "Current family structure": test_construct_from_firebase["Marriage_Relationship History"].get("current family structure")
}

all_pass = True
for field_name, expected_value in critical_tests.items():
    result = get_value_from_construct(test_construct_from_firebase, field_name)
    status = "✅" if result else "❌"
    if not result:
        all_pass = False
    print(f"{status} {field_name:30s} → {str(result)[:60] if result else 'NOT FOUND'}")
    if expected_value and result != expected_value:
        print(f"   ⚠️  Expected: {expected_value}")
        print(f"   ⚠️  Got: {result}")

# Test expert validation
print("\n[TEST] Expert Validation Utils")
print("-" * 100)

scoring_options = get_aggregated_scoring_options(test_construct_from_firebase)

found_elements = []
for category, items in scoring_options.items():
    for item in items:
        found_elements.append(item['element'])

for field in ["Triggering factor", "Stressor", "Current family structure"]:
    if field in found_elements:
        print(f"✅ {field:30s} found in scoring options")
    else:
        print(f"❌ {field:30s} NOT FOUND in scoring options")
        all_pass = False

print("\n" + "=" * 100)
if all_pass:
    print("🎉 ALL TESTS PASSED - Firebase sanitization handled correctly")
else:
    print("⚠️  TESTS FAILED - Need to handle Firebase sanitization")
print("=" * 100)
