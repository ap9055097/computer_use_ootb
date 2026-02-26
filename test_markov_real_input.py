#!/usr/bin/env python3
"""Test with the EXACT input format from the user's JSON."""

import sys
import re
import ast
import json

# Same functions as before
def replace_placeholders(text, data):
    if not isinstance(text, str):
        return text
    pattern = re.compile(r'\{\{(\w+)\}\}')
    return pattern.sub(lambda match: str(data.get(match.group(1), match.group(0))), text)

def _clean_text_for_parsing(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r'^```\w*\n?|```$', '', text, flags=re.MULTILINE).strip()
    while len(text) >= 2:
        if (text.startswith("'") and text.endswith("'")) or \
           (text.startswith('"') and text.endswith('"')):
            inner = text[1:-1]
            if inner.strip().startswith(('[', '{')):
                text = inner
            else:
                break
        else:
            break
    return text.strip()

def _try_extract_dict_from_text(text: str) -> dict | None:
    print(f"[DEBUG] _try_extract_dict_from_text input: {repr(text)}")
    cleaned = _clean_text_for_parsing(text)
    print(f"[DEBUG] After cleaning: {repr(cleaned)}")

    if not cleaned:
        print("[DEBUG] Cleaned text is empty!")
        return None

    try:
        parsed = ast.literal_eval(cleaned)
        print(f"[DEBUG] Parsed successfully: {parsed}")

        if isinstance(parsed, list) and len(parsed) > 0:
            parsed = parsed[0]
            print(f"[DEBUG] Took first item from list: {parsed}")

        if not isinstance(parsed, dict):
            print(f"[DEBUG] Not a dict! Type: {type(parsed)}")
            return None

        return parsed
    except (ValueError, SyntaxError, TypeError) as e:
        print(f"[DEBUG] Error parsing: {e}")
        return None

# Simulate what happens when the user pastes JSON into the Gradio textbox
user_json_str = '''{
  "execute_type": "Markov",
  "global_input": "[{\\"text\\": \\"QEWQDQWDQW\\", \\"unit\\": \\"20\\"}, {\\"text\\": \\"RPOOPOWRWR2\\", \\"unit\\": \\"30\\"}]",
  "input_type": "text",
  "initial_state_name": "FillingItem",
  "states": [
    {
      "name": "FillingItem",
      "is_terminal": false,
      "tools": [
        {
          "name": "FillingData",
          "description": "This tool handles the data entry",
          "input_type": "text",
          "input_schema": {},
          "actions": [
            { "action": "type", "text": "{{text}}" },
            { "action": "type", "text": "จำนวน " },
            { "action": "type", "text": "{{unit}}" }
          ],
          "target_state": "End"
        }
      ]
    },
    { "name": "End", "is_terminal": true }
  ]
}'''

print("=" * 60)
print("Test with EXACT user input format")
print("=" * 60)

# Parse the JSON
config = json.loads(user_json_str)
global_input = config['global_input']

print(f"Type of global_input: {type(global_input)}")
print(f"global_input value: {repr(global_input)}")
print()

# Try to extract
extracted = _try_extract_dict_from_text(global_input)
print()
print(f"Extracted result: {extracted}")
print()

# If successful, test replacement
if extracted:
    actions = config['states'][0]['tools'][0]['actions']
    print("Original actions:")
    for action in actions:
        print(f"  {action}")
    print()

    replaced_actions = [
        {k: replace_placeholders(v, extracted) for k, v in action.items()}
        for action in actions
    ]
    print("Replaced actions:")
    for action in replaced_actions:
        print(f"  {action}")
    print()
    print("✓ SUCCESS: Template substitution worked!")
else:
    print("✗ FAILED: Could not extract data from global_input")
