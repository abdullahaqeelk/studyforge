"""
StudyForge — Google AI Platform connection test.

Verifies that the Gemini API is reachable and correctly configured. Run this
before any agent development work, and after changing anything in .env:

    python src/api_test.py

Model identifier and credentials come from src/config.py, which reads them
from .env. Nothing is hardcoded here.

Evidence of a successful run is a P-1 deliverable for EC-360.
"""

import sys

from config import (
    StudyForgeError,
    classify_api_error,
    get_client,
    get_model,
)

TEST_PROMPT = (
    "Generate one short multiple-choice question about binary search trees, "
    "with four options and the correct answer marked."
)


def run_connection_test() -> None:
    """Send a single prompt to Gemini and print the response."""
    model = get_model()

    print(f"Model:  {model}")
    print(f"Prompt: {TEST_PROMPT}\n")
    print("Sending request to Google AI Platform...\n")

    client = get_client()

    try:
        response = client.models.generate_content(
            model=model,
            contents=TEST_PROMPT,
        )
    except Exception as exc:  # noqa: BLE001 - translated immediately below
        raise classify_api_error(exc) from exc

    if not response.text or not response.text.strip():
        raise StudyForgeError("The API returned an empty response.")

    print("-" * 60)
    print(response.text.strip())
    print("-" * 60)
    print("\nSUCCESS - Google AI Platform connection verified.")


if __name__ == "__main__":
    try:
        run_connection_test()
    except StudyForgeError as exc:
        sys.exit(f"ERROR: {exc}")
