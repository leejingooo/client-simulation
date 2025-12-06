"""Comprehensive test for PSYCHE RUBRIC field mapping issues"""

import os
os.environ['OPENAI_API_KEY'] = 'dummy-key-for-testing'

from evaluator import PSYCHE_RUBRIC, get_value_from_construct

# Simulate complete SP construct structure
test_sp_construct = {
    "Chief complaint": {
        "description": "Test chief complaint"
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
        "triggering_factor": "Brought to ED by husband",
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
print("COMPREHENSIVE PSYCHE RUBRIC FIELD MAPPING TEST")
print("=" * 100)

# Map PSYCHE RUBRIC names to expected SP construct keys
EXPECTED_MAPPINGS = {
    # Top level or nested fields
    "Chief complaint": "Chief complaint.description",
    "Symptom name": "Present illness.symptom_n.name (aggregated)",
    "Alleviating factor": "Present illness.symptom_n.alleviating factor (aggregated)",
    "Exacerbating factor": "Present illness.symptom_n.exacerbating factor (aggregated)",
    "Triggering factor": "Present illness.triggering_factor",  # UNDERSCORE!
    "Stressor": "Present illness.stressor",
    "Diagnosis": "Family history.diagnosis",
    "Substance use": "Family history.substance use",
    "Current family structure": "Marriage/Relationship History.current family structure",
    "length": "Present illness.symptom_n.length (max)",
    
    # Impulsivity
    "Suicidal ideation": "Impulsivity.Suicidal ideation",
    "Self mutilating behavior risk": "Impulsivity.Self mutilating behavior risk",
    "Homicide risk": "Impulsivity.Homicide risk",
    "Suicidal plan": "Impulsivity.Suicidal plan",
    "Suicidal attempt": "Impulsivity.Suicidal attempt",
    
    # MSE
    "Mood": "Mental Status Examination.Mood",
    "Verbal productivity": "Mental Status Examination.Verbal productivity",
    "Insight": "Mental Status Examination.Insight",
    "Affect": "Mental Status Examination.Affect",
    "Perception": "Mental Status Examination.Perception",
    "Thought process": "Mental Status Examination.Thought process",
    "Thought content": "Mental Status Examination.Thought content",
    "Spontaneity": "Mental Status Examination.Spontaneity",
    "Social judgement": "Mental Status Examination.Social judgement",
    "Reliability": "Mental Status Examination.Reliability"
}

issues = []
passed = []

for rubric_field in PSYCHE_RUBRIC.keys():
    result = get_value_from_construct(test_sp_construct, rubric_field)
    expected_path = EXPECTED_MAPPINGS.get(rubric_field, "UNKNOWN")
    
    if result is None or (isinstance(result, str) and result.strip() == ""):
        issues.append({
            'field': rubric_field,
            'expected_path': expected_path,
            'result': 'NOT FOUND'
        })
    else:
        passed.append({
            'field': rubric_field,
            'expected_path': expected_path,
            'result': str(result)[:60] + "..." if len(str(result)) > 60 else str(result)
        })

# Print results
print("\n✅ PASSED ({}/{}):".format(len(passed), len(PSYCHE_RUBRIC)))
print("-" * 100)
for p in passed:
    print(f"  ✓ {p['field']:30s} → {p['result']}")

if issues:
    print("\n❌ ISSUES FOUND ({}/{}):".format(len(issues), len(PSYCHE_RUBRIC)))
    print("-" * 100)
    for issue in issues:
        print(f"  ✗ {issue['field']:30s}")
        print(f"    Expected path: {issue['expected_path']}")
        print(f"    Result: {issue['result']}")
        print()

print("\n" + "=" * 100)
print("KEY NAMING ISSUES TO CHECK:")
print("=" * 100)
print("1. Space vs Underscore:")
print("   - PSYCHE: 'Triggering factor' vs SP Construct: 'triggering_factor'")
print("   - PSYCHE: 'Substance use' vs SP Construct: 'substance use'")
print("   - PSYCHE: 'Current family structure' vs SP Construct: 'current family structure'")
print()
print("2. Case sensitivity:")
print("   - PSYCHE: 'Suicidal ideation' vs SP Construct: 'Suicidal ideation'")
print("   - Should all be case-insensitive")
print()
print("3. Nested paths:")
print("   - All MSE fields are under 'Mental Status Examination'")
print("   - Impulsivity fields are under 'Impulsivity'")
print("=" * 100)

if not issues:
    print("\n🎉 ALL FIELDS MAPPED CORRECTLY!")
else:
    print(f"\n⚠️  {len(issues)} FIELD(S) NEED ATTENTION")
