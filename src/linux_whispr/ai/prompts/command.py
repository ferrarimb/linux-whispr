"""System prompts for Command Mode processing."""

from __future__ import annotations

COMMAND_SYSTEM_PROMPT = """\
You are an AI text assistant. The user has spoken a command about text they have selected.

Execute the command on the selected text. Output ONLY the resulting text, no explanations."""

COMMAND_USER_PROMPT = """\
User's command: {command_text}
Selected text: {selected_text}"""

GENERATE_SYSTEM_PROMPT = """\
You are an AI text assistant. The user has spoken a request to generate text.

Generate the requested text. Output ONLY the resulting text, no explanations."""

GENERATE_USER_PROMPT = """\
User's request: {command_text}"""


def build_command_prompt(
    command_text: str,
    selected_text: str | None = None,
) -> tuple[str, str]:
    """Build the system + user prompt pair for Command Mode.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    if selected_text:
        return (
            COMMAND_SYSTEM_PROMPT,
            COMMAND_USER_PROMPT.format(
                command_text=command_text,
                selected_text=selected_text,
            ),
        )
    else:
        return (
            GENERATE_SYSTEM_PROMPT,
            GENERATE_USER_PROMPT.format(command_text=command_text),
        )
