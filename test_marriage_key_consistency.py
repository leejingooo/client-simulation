"""Test for Marriage/Relationship History key consistency"""

import os
os.environ['OPENAI_API_KEY'] = 'dummy-key-for-testing'

# Check SP construct generator
print("=" * 80)
print("SP CONSTRUCT GENERATOR - Marriage/Relationship History key")
print("=" * 80)

with open('/workspaces/client-simulation/sp_construct_generator.py', 'r') as f:
    content = f.read()
    
# Find Marriage/Relationship History keys
import re
marriage_keys = re.findall(r'"Marriage[^"]*"', content)
print("\nFound keys:")
for key in set(marriage_keys):
    print(f"  {key}")

# Check PACA construct generator
print("\n" + "=" * 80)
print("PACA CONSTRUCT GENERATOR - Marriage/Relationship History key")
print("=" * 80)

with open('/workspaces/client-simulation/paca_construct_generator.py', 'r') as f:
    content = f.read()
    
marriage_keys = re.findall(r'"Marriage[^"]*"', content)
print("\nFound keys:")
for key in set(marriage_keys):
    print(f"  {key}")

# Check expert validation utils
print("\n" + "=" * 80)
print("EXPERT VALIDATION UTILS - Marriage/Relationship History key")
print("=" * 80)

with open('/workspaces/client-simulation/expert_validation_utils.py', 'r') as f:
    content = f.read()
    
marriage_keys = re.findall(r'"Marriage[^"]*"', content)
print("\nFound keys:")
for key in set(marriage_keys):
    print(f"  {key}")

print("\n" + "=" * 80)
print("ISSUE CHECK:")
print("=" * 80)
print("SP uses:    'Marriage/Relationship History'")
print("PACA uses:  'Marriage/Relationship History'")
print("Expert uses: ???")
print("\nIf expert validation uses a different key, it won't find the data!")
print("=" * 80)
