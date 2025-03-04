import asyncio
import os
from typing import ClassVar, Literal

from anthropic.types.beta import BetaToolUseBlockParam, BetaToolUseBlock

from .base import BaseAnthropicTool, CLIResult, ToolError, ToolResult
from .computer import ComputerTool



class FixActionTool(BaseAnthropicTool):
    """
    A tool that allows the agent to run fixed (by user) computer use actions.
    """
    name: ClassVar[Literal["bash"]] = "bash"
    description: str
    input_schema: dict
    actions: list[dict] = []
    computer: ComputerTool = ComputerTool(selected_screen=0)

    def __init__(self, name: str, description: str, input_schema: dict, actions: list[dict], **kwargs):
        print('computer params')
        super().__init__()
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.actions = actions
        
        ### to get target_dimension
        params = self.computer.to_params()
        print('computer params', params)

    async def __call__(
        self, **kwargs
    ):
        params = self.computer.to_params()
        print('computer params', params)
        print('FixActionTool kwargs', kwargs)
        action_outputs = []
        for action in self.actions:
            result = await self.computer(**action)
            action_outputs.append(result.output)
        print('action_outputs', action_outputs)
        # return ToolResult(output=f"Perform {' and '.join(action_outputs)}")
        return ToolResult(output=f"Perform tool: {self.name}")


    def to_params(self) -> BetaToolUseBlockParam:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }