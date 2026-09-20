"""
StudyForge — Google AI Platform connection test.

Verifies that the Gemini API is reachable and correctly configured.
Run this before any agent development work:

    python src/api_test.py

Evidence of a successful run is a P-1 deliverable for EC-360.
"""

import os
import sys

from dotenv import load_dotenv
from google import genai


MODEL = "gemini-2.0-flash"

TEST_PROMPT = (
    "Generate one short multiple-choice question about binary search trees, "
    "with four options and the correct answer marked."
)


def load_api_key() -> str:
    """Read GOOGLE_API_KEY from the .env file, exiting with guidance if absent."""
    load_dotenv()
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        sys.exit(
            "ERROR: GOOGLE_API_KEY not found.\n"
            "  1. Copy .env.example to .env\n"
            "  2. Add your key from https://aistudio.google.com/apikey\n"
            "  3. Re-run this script."
        )
    return key


def run_connection_test(api_key: str) -> None:
    """Send a single prompt to Gemini and print the response."""
    client = genai.Client(api_key=api_key)

    print(f"Model:  {MODEL}")
    print(f"Prompt: {TEST_PROMPT}\n")
    print("Sending request to Google AI Platform...\n")

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=TEST_PROMPT,
        )
    except Exception as exc:
        sys.exit(
            f"ERROR: request failed — {type(exc).__name__}: {exc}\n"
            "Common causes: invalid API key, exhausted free-tier quota, "
            "or no network route to the Google AI endpoint."
        )

    if not response.text or not response.text.strip():
        sys.exit("ERROR: the API returned an empty response.")

    print("-" * 60)
    print(response.text.strip())
    print("-" * 60)
    print("\nSUCCESS — Google AI Platform connection verified.")


if __name__ == "__main__":
    run_connection_test(load_api_key())