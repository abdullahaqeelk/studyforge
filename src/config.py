"""
StudyForge — centralised configuration and Google AI client construction.

Every module that talks to the Google AI Platform obtains its client from this
module rather than constructing one itself. Two reasons:

1. The model identifier lives in configuration, not in code. During Sprint 0 the
   model originally targeted (gemini-2.0-flash) was retired by the provider
   mid-development. Because the identifier was hardcoded, that became a code
   change. It is now a one-line edit in .env. See docs/ai-decisions.md.

2. Provider failures are translated into typed, readable errors here, so that
   callers handle a StudyForgeError rather than parsing provider exception text.

Usage:

    from config import get_client, get_model, StudyForgeError

    client = get_client()
    response = client.models.generate_content(model=get_model(), contents="...")
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

# Loaded once at import. Values already present in the real environment win,
# which is what allows CI or a container to override the local .env file.
load_dotenv()

DEFAULT_MODEL = "gemini-3.6-flash"


# --------------------------------------------------------------------------
# Error types
# --------------------------------------------------------------------------

class StudyForgeError(Exception):
    """Base class for every error this project raises deliberately."""


class ConfigurationError(StudyForgeError):
    """Required configuration is missing or malformed."""


class APIKeyError(StudyForgeError):
    """The API key was rejected by the provider."""


class QuotaExceededError(StudyForgeError):
    """The free-tier request quota has been exhausted."""


class ModelUnavailableError(StudyForgeError):
    """The configured model no longer exists or was renamed by the provider."""


class ServiceUnavailableError(StudyForgeError):
    """The provider is temporarily overloaded. The request may succeed if retried."""


class NetworkError(StudyForgeError):
    """The Google AI endpoint could not be reached."""


# --------------------------------------------------------------------------
# Configuration accessors
# --------------------------------------------------------------------------

def get_api_key() -> str:
    """Return the Google AI Studio API key, or raise ConfigurationError."""
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not key or key == "your_api_key_here":
        raise ConfigurationError(
            "GOOGLE_API_KEY is not set.\n"
            "  1. Copy .env.example to .env\n"
            "  2. Paste your key from https://aistudio.google.com/apikey\n"
            "  3. Run the command again."
        )
    return key


def get_model() -> str:
    """Return the configured Gemini model identifier."""
    return os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL


def get_client():
    """Build a Google GenAI client from the configured key.

    Returns:
        google.genai.Client, authenticated with GOOGLE_API_KEY.

    Raises:
        ConfigurationError: the key is absent or still the placeholder value.
        StudyForgeError: the client could not be constructed.
    """
    from google import genai  # imported lazily so config stays cheap to import

    try:
        return genai.Client(api_key=get_api_key())
    except ConfigurationError:
        raise
    except Exception as exc:  # noqa: BLE001 - provider raises untyped errors
        raise StudyForgeError(f"Could not create the Google AI client: {exc}") from exc


# --------------------------------------------------------------------------
# Error translation
# --------------------------------------------------------------------------

def classify_api_error(exc: Exception) -> StudyForgeError:
    """Translate a provider exception into a typed StudyForge error.

    The Google GenAI SDK raises a small number of exception classes carrying
    an HTTP status and a message. Rather than let that detail leak into every
    caller, this function maps it onto the four failure modes the project
    actually distinguishes.

    Args:
        exc: the exception raised by the provider SDK.

    Returns:
        A StudyForgeError subclass with a message safe to show a user.
    """
    text = str(exc).lower()

    if "api key" in text or "unauthenticated" in text or "401" in text or "403" in text:
        return APIKeyError(
            "The Google AI API key was rejected. Check GOOGLE_API_KEY in your "
            ".env file, and that the key is still active in Google AI Studio."
        )

    # Checked before quota: an overloaded model and an exhausted quota are both
    # "try later", but only one of them is the team's problem to fix.
    if "503" in text or "unavailable" in text or "overloaded" in text or "high demand" in text:
        return ServiceUnavailableError(
            f"The model '{get_model()}' is temporarily overloaded on the provider's "
            "side. This is not a problem with your key, quota or network. Wait a "
            "few minutes and run the command again."
        )

    if "quota" in text or "resource_exhausted" in text or "429" in text:
        return QuotaExceededError(
            "The Google AI free-tier quota is exhausted. Wait for the quota to "
            "reset, or use a different API key."
        )

    if "not_found" in text or "404" in text or "no longer available" in text:
        return ModelUnavailableError(
            f"The configured model '{get_model()}' is not available. The provider "
            "may have retired it. Update GEMINI_MODEL in your .env file; the "
            "provider's error below usually names the replacement.\n"
            f"  Provider said: {exc}"
        )

    if "connection" in text or "timeout" in text or "network" in text or "unreachable" in text:
        return NetworkError(
            "Could not reach the Google AI endpoint. Check your internet "
            "connection and try again."
        )

    return StudyForgeError(f"Unexpected Google AI error: {type(exc).__name__}: {exc}")
