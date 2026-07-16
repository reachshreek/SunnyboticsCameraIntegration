from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def png_factory():
    def make(path: Path, size: tuple[int, int] = (64, 48)) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", size, (20, 80, 140)).save(path, format="PNG")
        return path

    return make
