"""Test to verify if triggering factor and stressor were being found in evaluation page"""

import sys
import os

# Set dummy API key to avoid initialization errors
os.environ['OPENAI_API_KEY'] = 'dummy-key-for-testing'

from evaluator import get_value_from_construct, flatten_construct

# Simulate SP construct structure (as created by create_sp_construct)
test_sp_construct = {
    "Chief complaint": {
        "description": "Test complaint"
    },
    "Present illness": {
        "symptom_1": {
            "name": "Low mood",
            "alleviating factor": "Rest",
            "exacerbating factor": "Work stress",
            "length": 12
        },
        "triggering_factor": "Brought to the emergency department by her husband after she ingested an excessive amount of over-the-counter sleeping pills two weeks ago and recently disclosed persistent suicidal thoughts to her sister.",
        "stressor": "home/work/interpersonal difficulty"
    },
    "Mental Status Examination": {
        "Mood": "depressed",
        "Affect": "restricted"
    }
}

print("=" * 80)
print("Testing get_value_from_construct BEFORE fix")
print("=" * 80)

# Test flattening
print("\n1. Flattened construct:")
flat = flatten_construct(test_sp_construct)
for key, val in flat.items():
    if 'trigger' in key.lower() or 'stress' in key.lower():
        print(f"  {key}: {val[:50]}..." if len(str(val)) > 50 else f"  {key}: {val}")

# Test getting values with PSYCHE RUBRIC field names (with spaces)
print("\n2. Trying to get 'Triggering factor' (PSYCHE RUBRIC name with space):")
result = get_value_from_construct(test_sp_construct, "Triggering factor")
if result:
    print(f"  ✅ FOUND: {result[:80]}...")
else:
    print(f"  ❌ NOT FOUND (returned None)")

print("\n3. Trying to get 'Stressor' (PSYCHE RUBRIC name):")
result = get_value_from_construct(test_sp_construct, "Stressor")
if result:
    print(f"  ✅ FOUND: {result}")
else:
    print(f"  ❌ NOT FOUND (returned None)")

# Test with exact key names (with underscores)
print("\n4. Trying to get 'triggering_factor' (exact key in construct):")
result = get_value_from_construct(test_sp_construct, "triggering_factor")
if result:
    print(f"  ✅ FOUND: {result[:80]}...")
else:
    print(f"  ❌ NOT FOUND (returned None)")

print("\n5. Trying to get 'stressor' (exact key in construct):")
result = get_value_from_construct(test_sp_construct, "stressor")
if result:
    print(f"  ✅ FOUND: {result}")
else:
    print(f"  ❌ NOT FOUND (returned None)")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)
print("If items 2 and 3 show ❌ NOT FOUND, then the evaluation page")
print("was NOT working correctly for Triggering factor and Stressor!")
print("=" * 80)
