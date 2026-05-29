import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def force_mock_llm_provider():
    """Ensure all tests use the mock LLM provider to avoid external API dependencies."""
    original = settings.llm_provider
    settings.llm_provider = "mock"
    yield
    settings.llm_provider = original
