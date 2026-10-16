"""Load versioned prompts independently of the current working directory (SF-6)."""

from pathlib import Path

from config import StudyForgeError

PROMPT_DIRECTORY = Path(__file__).resolve().parent.parent / "prompts"


class PromptError(StudyForgeError):
    """A versioned prompt is unavailable or empty."""


def load_prompt(filename: str) -> str:
    """Read a Markdown prompt from prompts/ as UTF-8, including its version header.

    Args:
        filename: a plain .md filename, such as question_generation_v1.md.
    Returns:
        The complete non-empty prompt text, loaded fresh on every call.
    Raises:
        PromptError: the name is unsafe, or the file is missing/unreadable/empty.
    """
    if (not isinstance(filename, str) or not filename.endswith(".md")
            or "/" in filename or "\\" in filename or filename.startswith(".")):
        raise PromptError("Use a plain Markdown filename from prompts/.")
    try:
        text = (PROMPT_DIRECTORY / filename).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise PromptError(f"Could not load prompt '{filename}' from prompts/.") from exc
    if not text:
        raise PromptError(f"Prompt '{filename}' is empty.")
    return text
