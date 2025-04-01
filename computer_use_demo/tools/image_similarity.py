import asyncio
import os
from typing import ClassVar, Literal

from anthropic.types.beta import BetaToolUseBlockParam, BetaToolUseBlock

from .base import BaseAnthropicTool, CLIResult, ToolError, ToolResult
import re

class ImageSimilarityTool(BaseAnthropicTool):
    """
    A tool that allows the agent to find image similarity.
    """
    name: ClassVar[Literal["ImageSimilarity"]] = "ImageSimilarity"
    description: str
    input_schema: dict
    actions: list[dict] = []
    image_pool: dict[str, list[str]] = {}


    def __init__(self, name: str, description: str, input_schema: dict, actions: list[dict], **kwargs):
        super().__init__()
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.actions = actions
        
        ### to get target_dimension
        params = self.computer.to_params()

    async def __call__(
        self, **kwargs
    ):
        image_pool = kwargs.get("image_pool", {})
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
                    
            if "recommendation" in action and base64_image is None:
                result = await self.computer(**action)
                if result.output:
                    outputs.append(result.output)
                if result.base64_image:
                    base64_image=result.base64_image
        output = " and ".join(outputs)
        if not output:
            output = None
        return ToolResult(output=output, base64_image=base64_image)


    def to_params(self) -> BetaToolUseBlockParam:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }