"""
Live smoke test for the Google AI connection (SF-7).

Every other test in this suite stubs the provider, so the whole suite runs on a
clean clone with no key and no network. That is deliberate — but it means
nothing in CI would notice if the real endpoint stopped answering. This module
is the one test that talks to Google for real.

It is skipped automatically when no usable GOOGLE_API_KEY is configured, so
"all tests pass on a clean clone" still holds. To run it, put a key in .env and
run the suite normally; pytest reports it as passed rather than skipped.

Run just this file:

    python -m pytest tests/test_live_api.py -v
"""

import pytest

from config import ConfigurationError, classify_api_error, get_api_key, get_client, get_model


def _key_is_configured() -> bool:
    """True when .env holds a real key rather than the placeholder.

    Reuses SF-9's own validation instead of re-reading the environment, so the
    placeholder value counts as "not configured" here exactly as it does there.
    """
    try:
        get_api_key()
        return True
    except ConfigurationError:
        return False


pytestmark = pytest.mark.skipif(
    not _key_is_configured(),
    reason="no usable GOOGLE_API_KEY configured — live smoke test skipped",
)


def test_configured_model_returns_a_non_empty_response():
    """The configured model answers a trivial prompt over the real network.

    Deliberately minimal: one short prompt, no schema, no retry. This checks
    that the key, the model identifier in GEMINI_MODEL and the network path all
    work together. Anything about question quality belongs to SF-4's tests, and
    anything about stage wiring belongs to SF-8's.
    """
    client = get_client()
    try:
        response = client.models.generate_content(
            model=get_model(),
            contents="Reply with the single word: ready",
        )
    except Exception as exc:  # noqa: BLE001 - provider raises untyped errors
        # Translated through SF-9 so a failing run names the real cause —
        # a rejected key, an exhausted quota or an overloaded model — rather
        # than dumping a raw provider traceback into the test report.
        raise classify_api_error(exc) from exc
    finally:
        client.close()

    assert response.text is not None, "the model returned no text at all"
    assert response.text.strip(), "the model returned an empty response"
