"""
Final comprehensive test - verify all fixes work correctly
"""

import os
os.environ['OPENAI_API_KEY'] = 'dummy-key-for-testing'

import sys
sys.path.insert(0, '/workspaces/client-simulation')

from evaluator import get_value_from_construct, PSYCHE_RUBRIC
from expert_validation_utils import get_aggregated_scoring_options

# Create test construct matching actual SP/PACA structure
test_construct = {
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
        "symptom_2": {
            "name": "Insomnia",
            "alleviating factor": "Music",
            "exacerbating factor": "Phone use",
            "length": 10
        },
        "triggering_factor": "Brought to ED by husband after overdose",
        "stressor": "home/work/interpersonal difficulty"
    },
    "Family history": {
        "diagnosis": "Depression in mother",
        "substance use": "None"
    },
    "Marriage/Relationship History": {
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
print("FINAL COMPREHENSIVE VERIFICATION TEST")
print("=" * 100)

# Test 1: evaluator.py - get_value_from_construct
print("\n[TEST 1] evaluator.py - get_value_from_construct()")
print("-" * 100)

critical_fields = {
    "Triggering factor": "triggering_factor in Present illness",
    "Stressor": "stressor in Present illness",
    "Current family structure": "current family structure in Marriage/Relationship History"
}

test1_pass = True
for field_name, expected_location in critical_fields.items():
    result = get_value_from_construct(test_construct, field_name)
    status = "✅ PASS" if result else "❌ FAIL"
    if not result:
        test1_pass = False
    print(f"{status} - {field_name:30s} → {str(result)[:60] if result else 'NOT FOUND'}")
    if not result:
        print(f"       Expected location: {expected_location}")

# Test 2: expert_validation_utils.py - get_aggregated_scoring_options
print("\n[TEST 2] expert_validation_utils.py - get_aggregated_scoring_options()")
print("-" * 100)

scoring_options = get_aggregated_scoring_options(test_construct)

test2_pass = True
critical_elements = ["Triggering factor", "Stressor", "Current family structure"]

found_elements = []
for category, items in scoring_options.items():
    for item in items:
        found_elements.append(item['element'])

for element in critical_elements:
    if element in found_elements:
        print(f"✅ PASS - {element:30s} found in scoring options")
    else:
        print(f"❌ FAIL - {element:30s} NOT FOUND in scoring options")
        test2_pass = False

# Test 3: All PSYCHE RUBRIC fields
print("\n[TEST 3] All PSYCHE RUBRIC fields accessible")
print("-" * 100)

test3_pass = True
missing_fields = []

for rubric_field in PSYCHE_RUBRIC.keys():
    result = get_value_from_construct(test_construct, rubric_field)
    if result is None or (isinstance(result, str) and result.strip() == ""):
        missing_fields.append(rubric_field)
        test3_pass = False

if missing_fields:
    print(f"❌ FAIL - {len(missing_fields)} fields not found:")
    for field in missing_fields:
        print(f"       - {field}")
else:
    print(f"✅ PASS - All {len(PSYCHE_RUBRIC)} PSYCHE RUBRIC fields found")

# Final Summary
print("\n" + "=" * 100)
print("FINAL SUMMARY")
print("=" * 100)

all_pass = test1_pass and test2_pass and test3_pass

if all_pass:
    print("🎉 ALL TESTS PASSED!")
    print("\nKey fixes verified:")
    print("  ✅ Triggering factor: space/underscore normalization working")
    print("  ✅ Marriage/Relationship History: slash key fixed in expert_validation_utils")
    print("  ✅ All PSYCHE RUBRIC fields accessible via get_value_from_construct")
else:
    print("⚠️  SOME TESTS FAILED - Review output above")
    if not test1_pass:
        print("  ❌ Test 1 failed: evaluator.py cannot find critical fields")
    if not test2_pass:
        print("  ❌ Test 2 failed: expert_validation_utils missing critical fields")
    if not test3_pass:
        print("  ❌ Test 3 failed: some PSYCHE RUBRIC fields not accessible")

print("=" * 100)
