"""System prompts for text refinement by context."""

from __future__ import annotations

GENERAL_PROMPT = """\
You are a voice-to-text post-processor. Clean up the following raw transcription:
- Remove filler words (um, uh, like, you know, so, basically)
- Fix grammar and punctuation
- Apply proper capitalization
- Handle self-corrections (keep only the final intended version)
- Do NOT change the meaning or add information
- Do NOT add formatting unless the context suggests it
- Output ONLY the cleaned text, no explanations

Context: The user is typing in {app_name}.
{dictionary_context}
Raw transcription: {raw_text}"""

EMAIL_PROMPT = """\
You are a voice-to-text post-processor for email dictation. Clean up the raw transcription:
- Remove filler words
- Format as a proper email (greeting, body paragraphs, sign-off if present)
- Professional but natural tone
- Fix grammar and punctuation
- Handle self-corrections
- Output ONLY the cleaned email text
{dictionary_context}
Raw transcription: {raw_text}"""

CODE_PROMPT = """\
You are a voice-to-text post-processor for code dictation. Clean up the raw transcription:
- Remove filler words
- If it sounds like a code comment, format as a comment (# for Python, // for JS, etc.)
- Preserve technical terminology exactly
- Handle self-corrections
- Output ONLY the cleaned text

Active file context: {app_name}
{dictionary_context}
Raw transcription: {raw_text}"""

CHAT_PROMPT = """\
You are a voice-to-text post-processor for chat messages. Clean up the raw transcription:
- Remove filler words but keep casual tone
- Fix grammar lightly (keep contractions, informal language)
- Handle self-corrections
- Output ONLY the cleaned text
{dictionary_context}
Raw transcription: {raw_text}"""

# App name patterns → context type
APP_CONTEXT_PATTERNS: dict[str, str] = {
    "gmail": "email",
    "outlook": "email",
    "thunderbird": "email",
    "mail": "email",
    "code": "code",
    "vscode": "code",
    "visual studio": "code",
    "neovim": "code",
    "vim": "code",
    "emacs": "code",
    "jetbrains": "code",
    "intellij": "code",
    "pycharm": "code",
    "sublime": "code",
    "slack": "chat",
    "discord": "chat",
    "telegram": "chat",
    "whatsapp": "chat",
    "signal": "chat",
    "element": "chat",
    "matrix": "chat",
}

CONTEXT_PROMPTS: dict[str, str] = {
    "general": GENERAL_PROMPT,
    "email": EMAIL_PROMPT,
    "code": CODE_PROMPT,
    "chat": CHAT_PROMPT,
}


def detect_context(app_name: str | None) -> str:
    """Detect the context type from the active application name."""
    if not app_name:
        return "general"

    app_lower = app_name.lower()
    for pattern, context in APP_CONTEXT_PATTERNS.items():
        if pattern in app_lower:
            return context

    return "general"


def build_refinement_prompt(
    raw_text: str,
    app_name: str | None = None,
    dictionary_context: str = "",
) -> str:
    """Build the full refinement prompt based on context."""
    context_type = detect_context(app_name)
    template = CONTEXT_PROMPTS.get(context_type, GENERAL_PROMPT)

    dict_line = ""
    if dictionary_context:
        dict_line = f"The user prefers these spellings: {dictionary_context}\n"

    return template.format(
        raw_text=raw_text,
        app_name=app_name or "unknown application",
        dictionary_context=dict_line,
    )
