import asyncio
import os
from typing import ClassVar, Literal

from anthropic.types.beta import BetaToolBash20241022Param

from .base import BaseAnthropicTool, CLIResult, ToolError, ToolResult


class _BashSession:
    """A session to run a bash command non-interactively."""

    # Path to Git Bash executable.
    bash_executable = r"C:\Program Files\Git\bin\bash.exe"
    _timeout: float = 120.0  # seconds

    async def run(self, command: str):
        """Execute a command in bash non-interactively using the -c flag."""
        process = await asyncio.create_subprocess_exec(
            self.bash_executable,
            '--noprofile',
            '--norc',
            '-c',
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            output, error = await asyncio.wait_for(process.communicate(), timeout=self._timeout)
        except asyncio.TimeoutError:
            process.terminate()
            raise ToolError(
                f"timed out: bash did not complete in {self._timeout} seconds and was terminated"
            )

        return CLIResult(output=output.decode().strip(), error=error.decode().strip())


class BashToolNoSession(BaseAnthropicTool):
    """
    A tool that allows the agent to run bash commands.
    The tool parameters are defined by Anthropic and are not editable.
    """

    _session: _BashSession | None
    name: ClassVar[Literal["bash"]] = "bash"
    api_type: ClassVar[Literal["bash_20241022", "bash_20250124"]] = "bash_20250124"

    def __init__(self):
        self._session = _BashSession()
        super().__init__()

    async def __call__(self, command: str | None = None, restart: bool = False, **kwargs):
        if command is None:
            raise ToolError("no command provided.")
        # Run the command using our non-interactive session.
        return await self._session.run(command)

    def to_params(self) -> BetaToolBash20241022Param:
        return {
            "type": self.api_type,
            "name": self.name,
        }


# Example usage:
async def main():
    command = (
        'DOWNLOAD_DIR="/c/Users/Administrator/Downloads"; '
        'API_URL="http://example.com/upload"; '
        'LATEST_FILE=$(ls -t "$DOWNLOAD_DIR" | head -n 1); '
        '[ -z "$LATEST_FILE" ] && { echo "No files found in $DOWNLOAD_DIR"; exit 1; }; '
        'FILE_PATH="$DOWNLOAD_DIR/$LATEST_FILE"; '
        'echo "Uploading file: $FILE_PATH"; '
    )

    bash_tool = BashTool()
    result = await bash_tool(command=command)
    print("Output:", result.output)
    print("Error:", result.error)

# To run the example:
if __name__ == "__main__":
    asyncio.run(main())
