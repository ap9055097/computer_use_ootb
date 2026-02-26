#!/usr/bin/env python3
"""Test script to replicate Markov template substitution bug."""

import sys
import re
import ast

# Test the replace_placeholders function
def replace_placeholders(text, data):
    if not isinstance(text, str):
        return text
    pattern = re.compile(r'\{\{(\w+)\}\}')
    return pattern.sub(lambda match: str(data.get(match.group(1), match.group(0))), text)

# Test the _clean_text_for_parsing function
def _clean_text_for_parsing(text: str) -> str:
    """Clean text string before attempting to parse as Python literal."""
    if not text:
        return ""

    text = text.strip()

    # Remove markdown code block markers if present
    text = re.sub(r'^```\w*\n?|```$', '', text, flags=re.MULTILINE).strip()

    # Remove outer string quotes if the whole thing is wrapped
    while len(text) >= 2:
        if (text.startswith("'") and text.endswith("'")) or \
           (text.startswith('"') and text.endswith('"')):
            inner = text[1:-1]
            # Only unwrap if inner looks like a dict/list
            if inner.strip().startswith(('[', '{')):
                text = inner
            else:
                break
        else:
            break

    return text.strip()

# Test the _try_extract_dict_from_text function
def _try_extract_dict_from_text(text: str) -> dict | None:
    """Attempt to extract a dict from text."""
    cleaned = _clean_text_for_parsing(text)
    if not cleaned:
        return None

    try:
        parsed = ast.literal_eval(cleaned)

        # Normalize to single dict (take first item if list)
        if isinstance(parsed, list) and len(parsed) > 0:
            parsed = parsed[0]

        if not isinstance(parsed, dict):
            return None

        return parsed
    except (ValueError, SyntaxError, TypeError) as e:
        print(f"Error parsing: {e}")
        return None

# Test case 1: Direct replace_placeholders test
print("=" * 60)
print("Test 1: replace_placeholders function")
print("=" * 60)

data = {"text": "QEWQDQWDQW", "unit": "20"}
template = "{{text}}"
result = replace_placeholders(template, data)
print(f"Input: {template}")
print(f"Data: {data}")
print(f"Result: {result}")
print(f"Expected: QEWQDQWDQW")
print(f"Success: {result == 'QEWQDQWDQW'}")
print()

# Test case 2: _try_extract_dict_from_text
print("=" * 60)
print("Test 2: _try_extract_dict_from_text function")
print("=" * 60)

global_input = '[{"text": "QEWQDQWDQW", "unit": "20"}, {"text": "RPOOPOWRWR2", "unit": "30"}]'
print(f"Input: {global_input}")
extracted = _try_extract_dict_from_text(global_input)
print(f"Extracted: {extracted}")
print(f"Expected: {{'text': 'QEWQDQWDQW', 'unit': '20'}}")
print(f"Success: {extracted == {'text': 'QEWQDQWDQW', 'unit': '20'}}")
print()

# Test case 3: Full flow simulation
print("=" * 60)
print("Test 3: Full flow - extract then replace")
print("=" * 60)

global_input = '[{"text": "QEWQDQWDQW", "unit": "20"}]'
actions = [
    {"action": "type", "text": "{{text}}"},
    {"action": "type", "text": "จำนวน "},
    {"action": "type", "text": "{{unit}}"},
]

# Extract data
input_value = _try_extract_dict_from_text(global_input)
print(f"Global input: {global_input}")
print(f"Extracted data: {input_value}")
print()

# Replace placeholders in actions
if input_value:
    replaced_actions = [
        {k: replace_placeholders(v, input_value) for k, v in action.items()}
        for action in actions
    ]
    print("Replaced actions:")
    for action in replaced_actions:
        print(f"  {action}")
else:
    print("ERROR: Failed to extract data from global_input!")

print()
print("=" * 60)
print("Summary")
print("=" * 60)
if input_value and replaced_actions[0]['text'] == 'QEWQDQWDQW':
    print("✓ Template substitution works correctly!")
else:
    print("✗ Template substitution FAILED!")
    print(f"  Expected text: 'QEWQDQWDQW'")
    print(f"  Actual text: '{replaced_actions[0]['text'] if input_value else 'N/A'}'")
