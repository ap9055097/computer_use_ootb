import asyncio
import os
from typing import ClassVar, Literal

from anthropic.types.beta import BetaToolUseBlockParam, BetaToolUseBlock

from .base import BaseAnthropicTool, CLIResult, ToolError, ToolResult
from .computer import ComputerTool
from .bash_no_session import BashToolNoSession
import re


def replace_placeholders(text, data):
    if not isinstance(text, str):
        return text
    # This pattern matches any placeholder of the form {{key}}
    pattern = re.compile(r'\{\{(\w+)\}\}')
    return pattern.sub(lambda match: str(data.get(match.group(1), match.group(0))), text)

class FixActionTool(BaseAnthropicTool):
    """
    A tool that allows the agent to run fixed (by user) computer use actions.
    """
    name: ClassVar[Literal["FixAction"]] = "FixAction"
    description: str
    input_schema: dict
    actions: list[dict] = []
    computer: ComputerTool = ComputerTool(selected_screen=0)
    bash: BashTool = BashTool()

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
        replaced_actions = [{k: replace_placeholders(v, kwargs) for k, v in action.items()} for action in self.actions ]
        outputs = []
        outputs = []
        base64_image = None
        for action in replaced_actions:
            if "command" in action:
                result = await self.bash(**action)
                if result.output:
                    outputs.append(result.output)
                if result.error:
                    outputs.append(f"bash error: {result.error}")
            else:
                result = await self.computer(**action)
                await asyncio.sleep(1)
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