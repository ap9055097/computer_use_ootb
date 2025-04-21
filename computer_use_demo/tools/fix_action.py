import asyncio
import os
from typing import ClassVar, Literal

from anthropic.types.beta import BetaToolUseBlockParam, BetaToolUseBlock

from .base import BaseAnthropicTool, CLIResult, ToolError, ToolResult
from .computer import ComputerTool
from .bash_no_session import BashToolNoSession
import re

import base64
from io import BytesIO
from PIL import Image
import imagehash


def replace_placeholders(text, data):
    if not isinstance(text, str):
        return text
    # This pattern matches any placeholder of the form {{key}}
    pattern = re.compile(r'\{\{(\w+)\}\}')
    return pattern.sub(lambda match: str(data.get(match.group(1), match.group(0))), text)

class FixActionTool(BaseAnthropicTool):
    """
    A tool that allows the agent to run fixed (by user) actions.
    """
    name: ClassVar[Literal["FixAction"]] = "FixAction"
    description: str
    input_schema: dict
    actions: list[dict] = []
    embedded_image_algo: Literal["dhash"] = "dhash"
    image_pool: dict[str, list[str]] = {} ## key -> name: str,  values -> embedded_images: list[str]}
    computer: ComputerTool = ComputerTool(selected_screen=0)
    bash: BashToolNoSession = BashToolNoSession()
    tooluse_log: bool = False

    def __init__(self, name: str, description: str, input_schema: dict, actions: list[dict], embedded_image_algo: Literal["dhash"] = "dhash", image_pool: dict[str, list[str]] = {}, tooluse_log=False, **kwargs):
        super().__init__()
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.actions = actions
        self.embedded_image_algo = embedded_image_algo
        self.image_pool = image_pool
        self.tooluse_log = tooluse_log
        
        
        ### to get target_dimension
        params = self.computer.to_params()

    async def __call__(
        self, **kwargs
    ):
        replaced_actions = [{k: replace_placeholders(v, kwargs) for k, v in action.items()} for action in self.actions ]
        outputs = []
        base64_image = None
        for action in replaced_actions:
            if "command" in action:
                result = await self.bash(**action)
                if result.output:
                    outputs.append(result.output)
                if result.error:
                    outputs.append(f"bash error: {result.error}")
                    
            if "action" in action:
                result = await self.computer(**action)
                await asyncio.sleep(1)
                if result.output:
                    outputs.append(result.output)
                if result.base64_image:
                    base64_image=result.base64_image
                    
            if "tool_recommendation" in action and base64_image is not None:
                recommended_tool = find_tool_image_similarity(
                    base64_image=base64_image, 
                    embedded_image_algo=self.embedded_image_algo,
                    image_pool=self.image_pool,
                )
                recommended_tool_message = f"Recommended tool: {recommended_tool}"
                outputs.append(recommended_tool_message)
        output = " and ".join(outputs)
        if not output:
            output = None
        return ToolResult(output=output, base64_image=base64_image, tooluse_log=self.tooluse_log)


    def to_params(self) -> BetaToolUseBlockParam:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
        

def find_tool_image_similarity(
    base64_image: str,
    embedded_image_algo: str,
    image_pool: dict[str, list[str]],
    aggregate_methed: Literal["min", "max", "avg"] = "min",
) -> ToolResult:
    """
    Find the most similar image in the pool to the given image.
    """
    recommended_tool = None
    if embedded_image_algo == "dhash":
        config = {"algo": "dhash"}
    else:
        return recommended_tool
    
    screenshot_image = load_image_from_base64(base64_image)
    screenshot_hash = compute_hash(screenshot_image, config)
    min_agg_distance = float("inf")
    for tool_name, embedded_images in image_pool.items():
        tool_distances = []
        for embedded_image in embedded_images:
            if embedded_image["type"] != embedded_image_algo:
                continue
            image_hash = imagehash.hex_to_hash(embedded_image["value"])
            distance = compare_hashes(screenshot_hash, image_hash)
            tool_distances.append(distance)
        if not tool_distances:
            continue
        if aggregate_methed == "avg":
            agg_distance = sum(tool_distances) / len(tool_distances)
        elif aggregate_methed == "min":
            agg_distance = min(tool_distances)
        elif aggregate_methed == "max":
            agg_distance = max(tool_distances)
        else:
            raise ValueError(f"Unsupported aggregate method: {aggregate_methed}")
        if agg_distance < min_agg_distance:
            min_agg_distance = agg_distance
            recommended_tool = tool_name
        print(f"recommended_tool: {tool_name}: {agg_distance}")
    return recommended_tool

def load_image_from_file(image_path):
    """Load an image from a file path."""
    return Image.open(image_path)

def load_image_from_base64(b64_string):
    """Load an image from a base64-encoded string."""
    image_data = base64.b64decode(b64_string)
    image_bytes = BytesIO(image_data)
    return Image.open(image_bytes)

def compute_hash(image, algo_config = {"algo": "dhash"}):
    """
    Compute image hash based on a configuration dictionary.

    algo_config: dict with keys:
        - "algo": one of "average", "phash", "dhash", "whash", "color"
        - "kwargs": (optional) a dictionary of additional keyword arguments
          to pass to the hash function (like hash_size or highfreq_factor for whash)
    """
    algo = algo_config.get("algo", "phash")
    kwargs = algo_config.get("kwargs", {})
    
    if algo == "average":
        return imagehash.average_hash(image, **kwargs)
    elif algo == "phash":
        return imagehash.phash(image, **kwargs)
    elif algo == "dhash":
        return imagehash.dhash(image, **kwargs)
    elif algo == "whash":
        return imagehash.whash(image, **kwargs)
    elif algo == "color":
        return imagehash.colorhash(image, **kwargs)
    else:
        raise ValueError(f"Unsupported algorithm: {algo}")

def compare_hashes(hash1, hash2):
    """
    Compare two imagehash objects using the Hamming distance.
    A smaller distance indicates higher similarity.
    """
    return hash1 - hash2