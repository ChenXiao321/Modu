import tempfile
from pathlib import Path

import pytest

from app.services.text_extractor import TextExtractor, TextExtractorError


class TestTextExtractor:
    def test_extract_txt(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello World\nSecond line")
            path = f.name
        try:
            result = TextExtractor.extract(path, "text/plain")
            assert "Hello World" in result
            assert "Second line" in result
        finally:
            Path(path).unlink()

    def test_unsupported_extension(self):
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            path = f.name
        try:
            with pytest.raises(TextExtractorError, match="不支持的文本提取格式"):
                TextExtractor.extract(path, "application/octet-stream")
        finally:
            Path(path).unlink()
