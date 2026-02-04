"""
Agentic sampling loop that calls the Google Gemini API for OCR tasks.
"""
import asyncio
import platform
import re
import json
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from typing import Any, cast, Dict, Literal

import google.generativeai as genai
from google.generativeai.types import GenerationConfig, ContentDict, PartDict
from google.generativeai.types import GenerateContentResponse # For type hinting the callback

from PIL import Image # Retained for potential future use, not strictly needed for base64
from io import BytesIO # Retained for potential future use
# Removed: ComputerTool, EditTool, ToolCollection, ToolResult, FixActionTool as they are not used in the provided snippet
# If they are needed for other parts of your application, you'll need to integrate them separately.

# Note: The original script's tools (BashTool, etc.) were not used in the AnthropicExtractor
# or its call. If you need tool use with Gemini, that's a separate, more complex topic.

# Simplified for direct Google usage; APIProvider enum can be removed or adapted if you plan to switch again.
# PROVIDER_TO_DEFAULT_MODEL_NAME is no longer directly used in this Gemini-specific version.

# SYSTEM_PROMPT remains the same as it's a good instruction for the LLM.
SYSTEM_PROMPT = (
    "You are an OCR specialist. Given an image, extract **only** the following three fields "
    "and output them as a single JSON object exactly conforming to this JSON Schema:\n\n"
    "{\n"
    '  "type": "object",\n'
    '  "properties": {\n'
    '    "item_barcode": {"type": "string"},\n'
    '    "item_qty":     {"type": "string"},\n'
    '    "item_unit":    {"type": "string"}\n'
    "  },\n"
    '  "required": ["item_barcode","item_qty","item_unit"]\n'
    "}\n\n"
    "Respond **only** with the JSON object—no extra text.\n"
)


class GeminiExtractor:
    def __init__(
        self,
        # provider: APIProvider, # Removed, specific to Google Gemini now
        google_api_key: str,
        # model_name: str = "gemini-1.5-pro-latest", # User requested 2.5 Pro, use appropriate identifier
        model_name: str = "gemini-2.5-pro",
        system_prompt_suffix: str = "",
        api_response_callback: Callable[[GenerateContentResponse], None] | None = None, # Adjusted type hint
        max_tokens: int = 4096,
        # only_n_most_recent_images: int | None = None, # Not used in the core __call__ logic
        # selected_screen: int = 0, # Not used in the core __call__ logic
        print_usage: bool = True,
    ):
        self.model_name = model_name
        self.system_prompt_suffix = system_prompt_suffix
        self.google_api_key = google_api_key
        self.api_response_callback = api_response_callback
        self.max_tokens = max_tokens
        # self.only_n_most_recent_images = only_n_most_recent_images
        # self.selected_screen = selected_screen
        self.print_usage = print_usage

        genai.configure(api_key=self.google_api_key)

        # The system prompt for Gemini is often passed as part of the 'contents'
        # or as a 'system_instruction' if the model/SDK version supports it distinctly.
        # For this version, we'll prepend it to the user's message content.
        # The structure of the SYSTEM_PROMPT itself (requesting JSON) is good.

        # For more complex system instructions with `gemini-1.5-pro` and newer,
        # you can use the `system_instruction` parameter in `GenerativeModel`.
        self.system_instruction_text = (
            f"{SYSTEM_PROMPT}{' ' + system_prompt_suffix if system_prompt_suffix else ''}"
        )

        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            # system_instruction can be used here for models that support it well.
            # For maximum compatibility with the prompt structure, we'll include it
            # in the `__call__` method's contents for now.
            # If you are sure your model version handles system_instruction well for this,
            # you can move self.system_instruction_text here.
            # Example: system_instruction=self.system_instruction_text
        )

        self.total_token_usage = 0
        self.total_cost = 0 # TODO: Implement Gemini-specific cost calculation

    def __call__(
        self,
        *,
        image_base64: str | None = None,
        text: str | None = None,
        input_schema: dict | None = None,
        input_type: Literal["text", "screenshot"] = "screenshot",
        input_instruction: str | None = None,
    ):
        if input_schema:
            schema_str = json.dumps(input_schema, indent=2)
            current_system_prompt = (
                "You are a data-extraction specialist. Given the following input—which may be "
                "either an image or a plain-text message—extract **only** the fields defined "
                "in this JSON Schema and output a single JSON object that exactly conforms:\n\n"
                f"{schema_str}\n\n"
                "Respond **only** with the JSON object, no extra text, no markdown."
            )
        else:
            # Fallback to the generic OCR system prompt if no specific schema is given in the call
            current_system_prompt = self.system_instruction_text # From __init__ (original SYSTEM_PROMPT)


        # `prompt_parts_for_user_turn` will hold the actual user inputs (image, text, specific instructions)
        # for this particular call. This list is passed as the `contents` to the model.
        prompt_parts_for_user_turn: list[PartDict | str] = []

        if input_type == "screenshot":
            if not image_base64:
                raise ValueError("image_base64 must be provided for input_type 'screenshot'")
            # Add a contextual text part before the image, if desired
            prompt_parts_for_user_turn.append({"text": "Please process the following image based on the provided schema and instructions:"})
            prompt_parts_for_user_turn.append({
                "inline_data": {
                    "mime_type": "image/png", # Or image/jpeg, ensure this matches your data
                    "data": image_base64
                }
            })
        else: # input_type == "text"
            if not text:
                raise ValueError("text must be provided for input_type 'text'")
            prompt_parts_for_user_turn.append({"text": "Please process the following text based on the provided schema and instructions:"})
            prompt_parts_for_user_turn.append({"text": text})

        if input_instruction:
            prompt_parts_for_user_turn.append({"text": f"Additional specific instructions for this request: {input_instruction}"})

        # The `current_system_prompt` (which contains the schema and overall task)
        # is best passed via the `system_instruction` parameter of the GenerativeModel.
        # This separates the system-level guidance from the user's immediate input parts.
        model_for_this_call = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=current_system_prompt
        )

        generation_config = GenerationConfig(
            max_output_tokens=self.max_tokens,
            temperature=0.0, # For precise JSON extraction
        )

        # safety_settings = { ... } # Optional

        print(f"--- Sending to Gemini ---")
        # print(f"System Instruction (via model config):\n{current_system_prompt[:500]}...")
        # To see the exact parts being sent as 'contents':
        # print(f"User Content Parts for 'generate_content': {prompt_parts_for_user_turn}")
        print(f"Image provided in parts: {image_base64 is not None}")
        print(f"Text provided in parts: {text is not None}")
        print(f"Input instruction in parts: {input_instruction is not None}")
        print(f"---")

        response = model_for_this_call.generate_content(
            contents=prompt_parts_for_user_turn, # This IS using prompt_parts_for_user_turn
            generation_config=generation_config,
            # safety_settings=safety_settings
        )

        # ... (rest of the response processing remains the same)
        if self.api_response_callback:
            self.api_response_callback(response)

        # ... (token counting, JSON extraction) ...
        # (Code from previous response for this part is fine)

        if not response.candidates or not response.candidates[0].content.parts:
            print("Error: No content or parts found in Gemini response.")
            # print(f"Prompt Feedback: {response.prompt_feedback}") # Useful for debugging if available
            # print(f"Response Candidates: {response.candidates}")
            # It's good to check response.prompt_feedback if available and finish_reason
            if response.prompt_feedback and hasattr(response.prompt_feedback, 'block_reason'):
                 print(f"Prompt Feedback Block Reason: {response.prompt_feedback.block_reason}")
            if response.candidates and hasattr(response.candidates[0], 'finish_reason') and response.candidates[0].finish_reason != "STOP":
                 print(f"Warning: Finish reason was {response.candidates[0].finish_reason}")
            raise ValueError("Gemini response is empty, malformed, or content was blocked.")

        extracted_text_content = ""
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'text'):
                extracted_text_content += part.text
        
        if not extracted_text_content.strip():
            print("Error: Extracted text from Gemini response is empty.")
            # print(f"Full response candidate: {response.candidates[0]}")
            raise ValueError("No text content found in Gemini response parts.")

        print(f"GeminiExtractor model output text: {extracted_text_content}")
        
        data = self._extract_json_from_text(extracted_text_content)
        return data

    def _extract_json_from_text(self, text_content: str):
        # Find the first TextBlock in content (adapted from original)
        # For Gemini, we directly get the text, so this is simpler.
        text = text_content.strip()
        # Sometimes LLMs may wrap JSON in ```json ... ``` or just ```...``` – strip those:
        # Remove ```json prefix if present
        if text.startswith("```json"):
            text = text[len("```json"):]
        # Remove surrounding triple backticks or single quotes if present
        text = re.sub(r"^```+|```+$", "", text, flags=re.DOTALL).strip()
        text = re.sub(r"^['\"]|['\"]$", "", text).strip() # Remove surrounding single/double quotes
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON: {e}")
            print(f"Problematic text content for JSON parsing: '{text}'")
            raise ValueError(f"No valid JSON found in model output. Content: {text}")


# Example Usage (main guard for testing):
if __name__ == "__main__":
    # --- Configuration ---
    # IMPORTANT: Set your GOOGLE_API_KEY environment variable, or pass it directly.
    # from dotenv import load_dotenv
    # import os
    # load_dotenv()
    # GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # For direct assignment:
    GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY" # REPLACE WITH YOUR ACTUAL KEY

    if GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY":
        print("Please replace 'YOUR_GOOGLE_API_KEY' with your actual Google API key.")
        exit()

    # Example base64 encoded image string (replace with your actual image data)
    # This is a tiny 1x1 transparent PNG image as a placeholder
    EXAMPLE_IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    
    # Define a simple schema for testing
    test_schema = {
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "A brief description of the image content."},
            "main_color": {"type": "string"}
        },
        "required": ["description"]
    }

    # Callback function to see the raw API response (optional)
    def my_api_callback(response: GenerateContentResponse):
        print("\n--- Raw API Response Received (Callback) ---")
        # print(response) # This can be very verbose
        if response.usage_metadata:
             print(f"Tokens (from callback): {response.usage_metadata.total_token_count}")
        print("--- End Raw API Response ---")


    # --- Initialize Extractor ---
    try:
        # You can use "gemini-1.5-flash-latest" for faster, cheaper, but potentially less capable responses
        # For "Gemini 2.5 Pro", ensure you have access and use the correct model identifier string.
        # Common public models are "gemini-1.5-pro-latest", "gemini-1.0-pro-vision-latest", "gemini-experimental"
        extractor = GeminiExtractor(
            google_api_key=GOOGLE_API_KEY,
            model_name="gemini-1.5-pro-latest", # Or "gemini-1.5-flash-latest"
            system_prompt_suffix="Focus on visual details for the description.", # Optional suffix
            api_response_callback=my_api_callback,
            print_usage=True
        )
    except Exception as e:
        print(f"Error initializing GeminiExtractor: {e}")
        exit()

    # --- Test Case 1: Text Extraction ---
    print("\n--- Test Case 1: Text Input ---")
    try:
        text_data_to_extract = "The image shows a red apple and a green pear. The main color is red."
        extracted_json_from_text = extractor(
            text=text_data_to_extract,
            input_schema=test_schema,
            input_type="text",
            input_instruction="Extract the description and main color. Prefer 'apple' for main color context."
        )
        print("\nSuccessfully extracted JSON from text:")
        print(json.dumps(extracted_json_from_text, indent=2))
    except Exception as e:
        print(f"Error during text extraction test: {e}")

    # --- Test Case 2: Image Extraction (using placeholder image) ---
    # For a real test, replace EXAMPLE_IMAGE_BASE64 with a base64 string of an actual image.
    # You can use an online converter or a small Python script to get base64 from an image file.
    print("\n--- Test Case 2: Image Input (with placeholder image) ---")
    # This test uses the generic SYSTEM_PROMPT from __init__ because input_schema is not passed.
    # If you pass input_schema here, it will use that schema instead.
    # For the original item_barcode, item_qty, item_unit schema, that is the default.
    item_schema = {
      "type": "object",
      "properties": {
        "item_barcode": {"type": "string"},
        "item_qty":     {"type": "string"},
        "item_unit":    {"type": "string"}
      },
      "required": ["item_barcode","item_qty","item_unit"]
    }
    try:
        # To test with a real image:
        # with open("path_to_your_image.png", "rb") as image_file:
        #     import base64
        #     image_b64_real = base64.b64encode(image_file.read()).decode('utf-8')
        # Then use image_b64_real below instead of EXAMPLE_IMAGE_BASE64

        extracted_json_from_image = extractor(
            image_base64=EXAMPLE_IMAGE_BASE64, # Replace with your actual base64 image
            input_schema=item_schema, # Using the original OCR schema
            input_type="screenshot",
            input_instruction="This is a product label. Extract barcode, quantity, and unit."
        )
        print("\nSuccessfully extracted JSON from image (using placeholder):")
        print(json.dumps(extracted_json_from_image, indent=2))
    except ValueError as ve:
        print(f"ValueError during image extraction test (likely due to placeholder image or API issue): {ve}")
    except Exception as e:
        print(f"Error during image extraction test: {e}")

    print(f"\nTotal accumulated tokens (example): {extractor.total_token_usage}")
    # print(f"Total estimated cost (example): ${extractor.total_cost:.6f}") # Uncomment when cost logic is added