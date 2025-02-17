"""
Agentic sampling loop that calls the Anthropic API and local implementation of computer use tools.
"""
import time
import json
from collections.abc import Callable
from enum import StrEnum

from anthropic import APIResponse
from anthropic.types.beta import BetaContentBlock, BetaMessage, BetaMessageParam
from computer_use_demo.tools import ToolResult


import torch

from computer_use_demo.gui_agent.planner.anthropic_agent import AnthropicActor
from computer_use_demo.executor.anthropic_executor import AnthropicExecutor
from computer_use_demo.gui_agent.planner.api_vlm_planner import APIVLMPlanner
from computer_use_demo.gui_agent.planner.local_vlm_planner import LocalVLMPlanner
from computer_use_demo.gui_agent.actor.showui_agent import ShowUIActor
from computer_use_demo.executor.showui_executor import ShowUIExecutor
from computer_use_demo.gui_agent.actor.uitars_agent import UITARS_Actor
from computer_use_demo.tools.colorful_text import colorful_text_showui, colorful_text_vlm
from computer_use_demo.tools.screen_capture import get_screenshot
from computer_use_demo.gui_agent.llm_utils.oai import encode_image

from computer_use_demo.tools.logger import logger



class APIProvider(StrEnum):
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    VERTEX = "vertex"
    OPENAI = "openai"
    QWEN = "qwen"
    SSH = "ssh"


PROVIDER_TO_DEFAULT_MODEL_NAME: dict[APIProvider, str] = {
    APIProvider.ANTHROPIC: "claude-3-5-sonnet-20241022",
    APIProvider.BEDROCK: "anthropic.claude-3-5-sonnet-20241022-v2:0",
    APIProvider.VERTEX: "claude-3-5-sonnet-v2@20241022",
    APIProvider.OPENAI: "gpt-4o",
    APIProvider.QWEN: "qwen2vl",
    APIProvider.SSH: "qwen2-vl-2b",
}


def sampling_loop_sync(
    *,
    planner_model: str,
    planner_provider: APIProvider | None,
    actor_model: str,
    actor_provider: APIProvider | None,
    system_prompt_suffix: str,
    messages: list[BetaMessageParam],
    output_callback: Callable[[BetaContentBlock], None],
    tool_output_callback: Callable[[ToolResult, str], None],
    api_response_callback: Callable[[APIResponse[BetaMessage]], None],
    api_key: str,
    only_n_most_recent_images: int | None = None,
    max_tokens: int = 4096,
    selected_screen: int = 0,
    showui_max_pixels: int = 1344,
    showui_awq_4bit: bool = False,
    ui_tars_url: str = ""
):
    """
    Synchronous agentic sampling loop for the assistant/tool interaction of computer use.
    """

    # ---------------------------
    # Initialize Planner
    # ---------------------------
    if planner_model == "claude-3-5-sonnet-20241022":
        # Register Actor and Executor
        actor = AnthropicActor(
            model=planner_model, 
            provider=actor_provider, 
            system_prompt_suffix=system_prompt_suffix, 
            api_key=api_key, 
            api_response_callback=api_response_callback,
            max_tokens=max_tokens,
            only_n_most_recent_images=only_n_most_recent_images,
            selected_screen=selected_screen
        )

        executor = AnthropicExecutor(
            output_callback=output_callback,
            tool_output_callback=tool_output_callback,
            selected_screen=selected_screen
        )

        loop_mode = "unified"

    elif planner_model in ["gpt-4o", "gpt-4o-mini", "qwen2-vl-max"]:

        if torch.cuda.is_available(): device = torch.device("cuda")
        elif torch.backends.mps.is_available(): device = torch.device("mps")
        else: device = torch.device("cpu") # support: 'cpu', 'mps', 'cuda'
        logger.info(f"Model inited on device: {device}.")

        planner = APIVLMPlanner(
            model=planner_model,
            provider=planner_provider,
            system_prompt_suffix=system_prompt_suffix,
            api_key=api_key,
            api_response_callback=api_response_callback,
            selected_screen=selected_screen,
            output_callback=output_callback,
            device=device
        )
        loop_mode = "planner + actor"

    elif planner_model == "qwen2-vl-7b-instruct":
        planner = LocalVLMPlanner(
            model=planner_model,
            provider=planner_provider,
            system_prompt_suffix=system_prompt_suffix,
            api_key=api_key,
            api_response_callback=api_response_callback,
            selected_screen=selected_screen,
            output_callback=output_callback,
            device=device
        )
        loop_mode = "planner + actor"
    elif "ssh" in planner_model:
        if torch.cuda.is_available(): device = torch.device("cuda")
        elif torch.backends.mps.is_available(): device = torch.device("mps")
        else: device = torch.device("cpu") # support: 'cpu', 'mps', 'cuda'
        logger.info(f"Model inited on device: {device}.")
        planner = APIVLMPlanner(
            model=planner_model,
            provider=planner_provider,
            system_prompt_suffix=system_prompt_suffix,
            api_key=api_key,
            api_response_callback=api_response_callback,
            selected_screen=selected_screen,
            output_callback=output_callback,
            device=device
        )
        loop_mode = "planner + actor"
    else:
        logger.error(f"Planner Model {planner_model} not supported")
        raise ValueError(f"Planner Model {planner_model} not supported")
        

    # ---------------------------
    # Initialize Actor
    # ---------------------------
    if actor_model == "ShowUI":
        if showui_awq_4bit:
            showui_model_path = "./showui-2b-awq-4bit/"
        else:
            showui_model_path = "./showui-2b/"

        actor = ShowUIActor(
            model_path=showui_model_path,  
            device=device,  
            split='desktop',  # 'desktop' or 'phone'
            selected_screen=selected_screen,
            output_callback=output_callback,
            max_pixels=showui_max_pixels,
            awq_4bit=showui_awq_4bit
        )

        executor = ShowUIExecutor(
            output_callback=output_callback,
            tool_output_callback=tool_output_callback,
            selected_screen=selected_screen
        )
    elif actor_model == "UI-TARS":
        actor = UITARS_Actor(
            ui_tars_url=ui_tars_url,
            output_callback=output_callback,
            selected_screen=selected_screen
        )
        
    elif actor_model == "claude-3-5-sonnet-20241022":
        ...

    else:
        raise ValueError(f"Actor Model {actor_model} not supported")


    tool_result_content = None
    showui_loop_count = 0
    
    logger.info(f"Start the message loop. User messages: {messages}")

    if loop_mode == "unified":
        # ------------------------------
        # Unified loop: repeatedly call actor -> executor -> check tool_result -> maybe end
        # ------------------------------
        while True:
            # Call the actor with current messages
            response = actor(messages=messages)

            # Let the executor process that response, yielding any intermediate messages
            for message, tool_result_content in executor(response, messages):
                yield message

            # If executor didn't produce further content, we're done
            if not tool_result_content:
                return messages

            # If there is more tool content, treat that as user input
            messages.append({
                "content": tool_result_content,
                "role": "user"
            })

    elif loop_mode == "planner + actor":
        # ------------------------------------------------------
        # Planner + actor loop: 
        # 1) planner => get next_action
        # 2) If no next_action -> end 
        # 3) Otherwise actor => executor
        # 4) repeat
        # ------------------------------------------------------
        while True:
            # Step 1: Planner (VLM) response
            vlm_response = planner(messages=messages)

            # Step 2: Extract the "Next Action" from the planner output
            next_action = json.loads(vlm_response).get("Next Action")

            # Yield the next_action string, in case the UI or logs want to show it
            yield next_action

            # Step 3: Check if there are no further actions
            if not next_action or next_action in ("None", ""):
                final_sc, final_sc_path = get_screenshot(selected_screen=selected_screen)
                final_image_b64 = encode_image(str(final_sc_path))

                output_callback(
                    (
                        f"No more actions from {colorful_text_vlm}. End of task. Final State:\n"
                        f'<img src="data:image/png;base64,{final_image_b64}">'
                    ),
                    sender="bot"
                )
                yield None
                break

            # Step 4: Output an action message
            output_callback(
                f"{colorful_text_vlm} sending action to {colorful_text_showui}:\n{next_action}",
                sender="bot"
            )

            # Step 5: Actor response
            actor_response = actor(messages=next_action)
            yield actor_response

            # Step 6: Execute the actor response
            for message, tool_result_content in executor(actor_response, messages):
                time.sleep(0.5)  # optional small delay
                yield message

            # Step 7: Update conversation with embedding history of plan and actions
            messages.append({
                "role": "user",
                "content": [
                    "History plan:" + str(json.loads(vlm_response)),
                    "History actions:" + str(actor_response["content"])
                ]
            })

            logger.info(
                f"End of loop {showui_loop_count + 1}. "
                f"Messages: {str(messages)[:100000]}. "
                f"Total cost: $USD{planner.total_cost:.5f}"
            )


            # Increment loop counter
            showui_loop_count += 1
