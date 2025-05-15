import time
import asyncio
import base64
from PIL import Image
from io import BytesIO
from .fix_action import (
    find_tool_image_similarity, 
    compute_hash, 
    FixActionTool,
)
from .computer import ComputerTool
from .base import BaseAnthropicTool, CLIResult, ToolError, ToolResult
from .extractor import AnthropicExtractor
import json
from typing import Callable, ClassVar, Literal
from anthropic.types.beta import BetaMessage, BetaTextBlock, BetaToolUseBlock, BetaThinkingBlock


def capture_screenshot_dhash() -> str:
    # Capture the screenshot. This returns a PIL Image.
    def base64_to_pil(base64_string: str) -> Image.Image:
        # Sometimes the base64 string may include metadata like "data:image/png;base64,"
        # We remove this header if it's present.
        if base64_string.startswith("data:"):
            base64_string = base64_string.split(",")[1]
        
        # Decode the base64 string into bytes
        image_data = base64.b64decode(base64_string)
        
        # Create a BytesIO stream from the bytes data
        image_bytes = BytesIO(image_data)
        
        # Open the image with PIL
        image = Image.open(image_bytes)
        return image
    computer = ComputerTool(selected_screen=0)
    computer.to_params()
    toolresult = asyncio.run(computer.screenshot())
    return toolresult.base64_image
    # pil_image = base64_to_pil(toolresult.base64_image)
    # return pil_image, compute_hash(pil_image)


class MarkovTool:
    def __init__(
        self, 
        name: str, 
        description: str = None,
        input_type: Literal["text", "screenshot"] = "screenshot",
        input_instruction: str = None,
        input_schema: dict = None,
        embedded_images: list[dict[str, str]] = None, 
        actions: list[str] | None = None, 
        target_state: str=None,
        extractor: AnthropicExtractor | None = None,
        output_callback: Callable[[str], None] = None,
        
    ):
        self.name = name
        self.description = description
        self.input_type = input_type
        self.input_instruction = input_instruction
        self.input_schema = input_schema or {}
        self.embedded_images = embedded_images
        self.actions = actions
        self.target_state = target_state
        self.extractor = extractor
        self.output_callback = output_callback or (lambda x: None)
        
    
    def execute_actions(
        self, 
        image_base64: str = None,
        text: str = None,
    ) -> ToolResult:
        # print(f"[Tool] Executing actions for tool '{self.name}'... text: {text}")
        if self.input_schema and self.input_schema.get("properties"):
            input_value = self.extractor(
                image_base64=image_base64, 
                text=text, 
                input_schema=self.input_schema,
                input_type=self.input_type,
                input_instruction=self.input_instruction,
            )
        else:
            input_value = {}
        print(f"[Tool] Extracted input value: {input_value}")
        # message = f"[Tool] Extracted input value: {input_value}"
        tooluse_message = BetaToolUseBlock(
            id=self.name,
            name=self.name,
            input=input_value,
            type="tool_use",
        )
        
        self.output_callback(tooluse_message, sender="bot")
        
        
        result: ToolResult = asyncio.run(
            FixActionTool(
                name=self.name,
                description=self.description,
                input_schema=self.input_schema,
                actions=self.actions,
                tooluse_log=False,
            )(**input_value)
        )
        return result

        

class MarkovState:
    def __init__(
            self, 
            name: str, 
            tools: list[MarkovTool] = [], 
            is_terminal: bool = False,
            image_pool: dict[str, list[str]] = None,
            output_callback: callable = None,
    ):
        """
        Represents a state in the RPA Markov chain.
        :param name: Name/identifier of the state.
        :param tools: List of Tool objects associated with this state.
        :param is_terminal: Whether this state is an end (terminal) state.
        """
        self.name = name
        self.tools = tools or []  # Tools available in this state
        self.is_terminal = is_terminal
        self.image_pool = image_pool or {}  # Image pool for this state
        self.output_callback = output_callback or (lambda x: None)
        
        self._set_image_pool()
        print('[State] Initialized state:', self.name)
        print('[State] Image pool:', self.image_pool)

    def add_tool(self, tool):
        """Add a Tool to this state."""
        self.tools.append(tool)
    
    def get_tool(self, tool_name: str):
        """Get a Tool by its name."""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None
    
    def _set_image_pool(self):
        if not self.tools:
            return
        
        image_pool = {}
        for tool in self.tools:
            image_pool[tool.name] = tool.embedded_images or []
        
        self.image_pool = image_pool
    
    def find_tool_image_similarity(
        self,
        base64_image: str,
    ) -> str:
        """
        Find the most similar tool based on the provided image.
        :param base64_image: Base64 encoded image to compare against.
        :return: The name of the recommended tool.
        """
        if len(self.tools) == 1:
            return self.tools[0].name
        
        recommended_tool = find_tool_image_similarity(
            base64_image=base64_image, 
            embedded_image_algo="dhash",
            image_pool=self.image_pool,
        )
        return recommended_tool


class MarkovRPA:
    def __init__(
            self, 
            initial_state_name: str, 
            output_callback: callable = None,
            states: list[MarkovState] | dict[str, MarkovState] = None,
            global_input: str = None,
        ):
        """
        The Robot orchestrates the RPA process through various states.
        :param initial_state: The State object to start from.
        :param states: A dictionary or list of State objects that the robot can navigate through.
        """
        # Store states in a name-to-state dict for easy lookup
        if isinstance(states, dict):
            self.states = states
        else:
            self.states = {state.name: state for state in states}
        self.current_state = self.states[initial_state_name]
        self.output_callback = output_callback or (lambda x: None)
        self.global_input = global_input
        
        
    def run(self, max_iterations=10, timeout_seconds=None):
        """
        Run the RPA loop until an end state or iteration/timeout limit is reached.
        """
        start_time = time.time()
        iterations = 0
        # print(f"[Robot] Starting automation in state: '{self.current_state.name}'")
        message = f"[Robot] Starting automation in state: '{self.current_state.name}'"
        self.output_callback(message, sender="bot")
        yield message
        # Main loop
        while True:
            # Check termination conditions
            if self.current_state.is_terminal:
                # print(f"[Robot] Reached terminal state: '{self.current_state.name}'. Stopping.")
                message = f"[Robot] Reached terminal state: '{self.current_state.name}'. Stopping."
                self.output_callback(message, sender="bot")
                yield message
                break
            if iterations >= max_iterations:
                # print(f"[Robot] Max iterations ({max_iterations}) reached. Stopping.")
                message = f"[Robot] Max iterations ({max_iterations}) reached. Stopping."
                self.output_callback(message, sender="bot")
                yield message
                break
            if timeout_seconds is not None and (time.time() - start_time) > timeout_seconds:
                # print(f"[Robot] Timeout of {timeout_seconds} seconds reached. Stopping.")
                message = f"[Robot] Timeout of {timeout_seconds} seconds reached. Stopping."
                self.output_callback(message, sender="bot")
                yield message
                break

            iterations += 1
            # Take a screenshot of the current screen
            screenshot_base64 = capture_screenshot_dhash()  # Returns a PIL Image of the screen:contentReference[oaicite:9]{index=9}
            self.output_callback(ToolResult(base64_image=screenshot_base64), sender="bot")
            # Determine the best matching tool in the current state
            best_tool_name = self.current_state.find_tool_image_similarity(screenshot_base64)
            # print(f"[Robot] Current state: '{self.current_state.name}'. Best match tool: '{best_tool_name}'.")
            best_tool = self.current_state.get_tool(best_tool_name)
            # print('[Robot] Best tool:', best_tool)
            if best_tool is None:
                # print("[Robot] No suitable tool found for the current state. Stopping.")
                message = "[Robot] No suitable tool found for the current state. Stopping."
                self.output_callback(message, sender="bot")
                yield message
                break

            # Log the chosen tool and similarity score
            # print(f"[Robot] Current state: '{self.current_state.name}'. Best match tool: '{best_tool.name}'.")
            message = f"[Robot] Current state: '{self.current_state.name}'. Best match tool: '{best_tool.name}'."
            self.output_callback(message, sender="bot")
            yield message
            # Execute the tool's actions
            # print(f"[Robot] Executing actions for tool '{best_tool.name}'...")
            message = f"[Robot] Executing actions for tool '{best_tool.name}'..."
            self.output_callback(message, sender="bot")
            yield message
            result: ToolResult = best_tool.execute_actions(
                image_base64=screenshot_base64,
                text=self.global_input,
                )
            # print(f"[Robot] Tool '{best_tool.name}' executed. Output: {result.output}")
            message = f"[Robot] Tool '{best_tool.name}' executed. Output: {result.output}"
            self.output_callback(message, sender="bot")
            yield message
            # Transition to the next state if defined
            if best_tool.target_state:
                next_state_name = best_tool.target_state
                if next_state_name in self.states:
                    prev_state = self.current_state.name
                    self.current_state = self.states[next_state_name]
                    # print(f"[Robot] Transitioned from state '{prev_state}' to state '{self.current_state.name}'.")
                    message = f"[Robot] Transitioned from state '{prev_state}' to state '{self.current_state.name}'."
                    self.output_callback(message, sender="bot")
                    yield message
                else:
                    # If target state is not recognized, we can either stop or stay in current state.
                    # print(f"[Robot] Warning: target state '{next_state_name}' not found. Staying in current state.")
                    message = f"[Robot] Warning: target state '{next_state_name}' not found. Staying in current state."
                    self.output_callback(message, sender="bot")
                    yield message
            else:
                # No target state means remain in the same state (or end if we decide that means a terminal action).
                # print(f"[Robot] Tool '{best_tool.name}' has no target state; remaining in '{self.current_state.name}'.")
                message = f"[Robot] Tool '{best_tool.name}' has no target state; remaining in '{self.current_state.name}'."
                self.output_callback(message, sender="bot")
                yield message
        # End of run
        # print("[Robot] Automation run complete.")
        message = "[Robot] Automation run complete."
        self.output_callback(message, sender="bot")
        return message
        

