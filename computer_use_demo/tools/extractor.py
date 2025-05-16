"""
Agentic sampling loop that calls the Anthropic API and local implementation of anthropic-defined computer use tools.
"""
import asyncio
import platform
import re
import json
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from typing import Any, cast

from anthropic import Anthropic, AnthropicBedrock, AnthropicVertex, APIResponse
from anthropic.types import (
    ToolResultBlockParam,
)
from anthropic.types.beta import (
    BetaContentBlock,
    BetaContentBlockParam,
    BetaImageBlockParam,
    BetaMessage,
    BetaMessageParam,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
)
from anthropic.types import TextBlock
from anthropic.types.beta import BetaMessage, BetaTextBlock, BetaToolUseBlock

from computer_use_demo.tools import BashTool, ComputerTool, EditTool, ToolCollection, ToolResult, FixActionTool

from PIL import Image
from io import BytesIO
import gradio as gr
from typing import Dict, Literal



class APIProvider(StrEnum):
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    VERTEX = "vertex"


PROVIDER_TO_DEFAULT_MODEL_NAME: dict[APIProvider, str] = {
    APIProvider.ANTHROPIC: "claude-3-5-sonnet-20241022",
    APIProvider.BEDROCK: "anthropic.claude-3-5-sonnet-20241022-v2:0",
    APIProvider.VERTEX: "claude-3-5-sonnet-v2@20241022",
}


# Check OS
# SYSTEM_PROMPT = f"""<SYSTEM_CAPABILITY>
# * You are utilizing a Windows system with internet access.
# * The current date is {datetime.today().strftime('%A, %B %d, %Y')}.
# </SYSTEM_CAPABILITY>
# """

# SYSTEM_PROMPT = (
#     "You are an OCR specialist. Given an image, extract **only** the following three fields "
#     "and output them as a single JSON object exactly conforming to this JSON Schema:\n\n"
#     "{\n"
#     '  "type": "object",\n'
#     '  "properties": {\n'
#     '    "item_barcode": {"type": "string"},\n'
#     '    "item_qty":     {"type": "string"},\n'
#     '    "item_unit":    {"type": "string"}\n'
#     "  },\n"
#     '  "required": ["item_barcode","item_qty","item_unit"]\n'
#     "}\n\n"
#     "Respond **only** with the JSON object—no extra text.\n"
# )

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


class AnthropicExtractor:
    def __init__(
        self, 
        provider: APIProvider, 
        system_prompt_suffix: str, 
        api_key: str,
        api_response_callback: Callable[[APIResponse[BetaMessage]], None],
        max_tokens: int = 4096,
        only_n_most_recent_images: int | None = None,
        selected_screen: int = 0,
        print_usage: bool = True,
    ):
        # self.model = "claude-3-7-sonnet-20250219"
        self.model = "claude-3-5-haiku-latest"
        self.provider = provider
        self.system_prompt_suffix = system_prompt_suffix
        self.api_key = api_key
        self.api_response_callback = api_response_callback
        self.max_tokens = max_tokens
        self.only_n_most_recent_images = only_n_most_recent_images
        self.selected_screen = selected_screen
            

        self.system = (
            f"{SYSTEM_PROMPT}{' ' + system_prompt_suffix if system_prompt_suffix else ''}"
        )
        
        self.total_token_usage = 0
        self.total_cost = 0
        self.print_usage = print_usage

        # Instantiate the appropriate API client based on the provider
        if provider == APIProvider.ANTHROPIC:
            self.client = Anthropic(api_key=api_key)
        elif provider == APIProvider.VERTEX:
            self.client = AnthropicVertex()
        elif provider == APIProvider.BEDROCK:
            self.client = AnthropicBedrock()
        else:
            self.client = Anthropic(api_key=api_key)

    def __call__(
        self, 
        *,
        image_base64: str = None,
        text: str = None,
        input_schema: dict = {},
        input_type: Literal["text", "screenshot"] = "screenshot",
        input_instruction: str =  None,
    ):
        schema_str = json.dumps(input_schema, indent=2)
        # system_prompt = (
        #     "You are an OCR specialist. Given an image, extract **only** the following fields "
        #     "and output them as a single JSON object exactly conforming to this JSON Schema:\n\n"
        #     f"{schema_str}\n\n"
        #     "Respond **only** with the JSON object—no extra text."
        # )
        system_prompt = (
            "You are a data-extraction specialist. Given the following input—which may be "
            "either an image or a plain-text message—extract **only** the fields defined "
            "in this JSON Schema and output a single JSON object that exactly conforms:\n\n"
            f"{schema_str}\n\n"
            "Respond **only** with the JSON object, no extra text, no markdown."
        )
        
        """
        Generate a response given history messages.
        """
        content_blocks = []
        if input_type == "screenshot":
            content_blocks.append({"type": "text", "text": "Here is the image to process:"})
            content_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",               # Required
                    "media_type": "image/png",      # Must match your file format
                    "data": image_base64                 # The actual base64 string
                }
            })
            
        else:
            content_blocks.append({"type": "text", "text": "Here is the text to process:"})
            content_blocks.append({"type": "text", "text": text})
        if input_instruction:
            content_blocks.append({"type": "text", "text": input_instruction})
        # print('content_blocks', content_blocks)
        messages = [{
            "role": "user",
            "content": content_blocks
        }]
        # image_block = {
        #     "type": "image",
        #     "source": {
        #         "type": "base64",               # Required
        #         "media_type": "image/png",      # Must match your file format
        #         "data": image_base64                 # The actual base64 string
        #     }
        # }
        # messages = [
        #     {
        #         "role": "user",
        #         "content": [
        #             {"type": "text", "text": "Here is the image to process:"},
        #             image_block,
        #         ]
        #     }
        # ]

        
        raw_response = self.client.messages.with_raw_response.create(
            max_tokens=self.max_tokens,
            model=self.model,
            system=system_prompt,
            messages=messages,
            temperature=0,
            # temperature=1,
            # thinking={"type": "enabled", "budget_tokens": 1024},
        )

        self.api_response_callback(cast(APIResponse[BetaMessage], raw_response))

        response = raw_response.parse()
        print(f"AnthropicActor response: {response}")

        self.total_token_usage += response.usage.input_tokens + response.usage.output_tokens
        self.total_cost += (response.usage.input_tokens * 3 / 1000000 + response.usage.output_tokens * 15 / 1000000)
        
        if self.print_usage:
            print(f"Claude total token usage so far: {self.total_token_usage}, total cost so far: $USD{self.total_cost}")
        data = extract_json_from_msg(response)
        # print(f"[Extractor] Extracted data: {data}")
        return data

# --- 2. Extract the JSON block ---
def extract_json_from_msg(message):
    # Find the first TextBlock in content
    for block in message.content:
        if isinstance(block, TextBlock) and block.type == "text":
            text = block.text.strip()
            # Sometimes Claude may wrap JSON in backticks or quotes – strip those:
            # Remove surrounding triple backticks or single quotes if present
            text = re.sub(r"^```+|```+$", "", text, flags=re.DOTALL).strip()
            text = re.sub(r"^['\"]|['\"]$", "", text).strip()
            return json.loads(text)
    raise ValueError("No JSON TextBlock found in message.content")