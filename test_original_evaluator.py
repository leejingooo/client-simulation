"""Test ORIGINAL evaluator behavior (before our fix)"""

import sys
import os
os.environ['OPENAI_API_KEY'] = 'dummy-key-for-testing'

# Define original get_value_from_construct (before our fix)
def flatten_construct(construct, parent_key=''):
    """Flatten nested construct into key-value pairs."""
    items = {}
    if isinstance(construct, dict):
        for k, v in construct.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, list):
                items[new_key] = v
            elif isinstance(v, dict) and not isinstance(v, str):
                items.update(flatten_construct(v, new_key))
            else:
                items[new_key] = str(v) if v is not None else ""
    return items


def get_value_from_construct_ORIGINAL(construct, field_name):
    """ORIGINAL version before our fix"""
    if construct is None:
        return None
    
    # First, try direct access to top-level fields
    field_lower = field_name.lower()
    for key, val in construct.items():
        if key.lower() == field_lower:
            return val
    
    # Then flatten and search
    flat = flatten_construct(construct)
    
    # Direct exact match
    for key, val in flat.items():
        if key.lower() == field_lower:
            return val
    
    # Match on last part of key path (ORIGINAL - no space/underscore handling)
    for key, val in flat.items():
        last_part = key.split('.')[-1].lower()
        if last_part == field_lower:  # THIS WAS THE PROBLEM
            return val
    
    return None


# Test
test_sp_construct = {
    "Present illness": {
        "triggering_factor": "Brought to ED by husband",
        "stressor": "home/work/interpersonal difficulty"
    }
}

print("=" * 80)
print("Testing ORIGINAL get_value_from_construct (before fix)")
print("=" * 80)

print("\nFlattened keys:")
flat = flatten_construct(test_sp_construct)
for key in flat.keys():
    print(f"  {key}")

print("\n1. Trying to get 'Triggering factor' (with space - PSYCHE RUBRIC name):")
result = get_value_from_construct_ORIGINAL(test_sp_construct, "Triggering factor")
print(f"   field_lower = 'triggering factor'")
print(f"   last_part from 'Present illness.triggering_factor' = 'triggering_factor'")
print(f"   Match? 'triggering_factor' == 'triggering factor' -> {result is not None}")
if result:
    print(f"   ✅ FOUND: {result}")
else:
    print(f"   ❌ NOT FOUND")

print("\n2. Trying to get 'Stressor':")
result = get_value_from_construct_ORIGINAL(test_sp_construct, "Stressor")
print(f"   field_lower = 'stressor'")
print(f"   last_part from 'Present illness.stressor' = 'stressor'")
print(f"   Match? 'stressor' == 'stressor' -> {result is not None}")
if result:
    print(f"   ✅ FOUND: {result}")
else:
    print(f"   ❌ NOT FOUND")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)
print("'triggering_factor' != 'triggering factor' (underscore vs space)")
print("So Triggering factor should have been ❌ NOT FOUND in original code!")
print("But Stressor should work fine (no underscore issue)")
print("=" * 80)
