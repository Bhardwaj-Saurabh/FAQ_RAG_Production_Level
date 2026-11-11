"""Proves the toolchain works before any real code exists."""

import chromadb
import fastapi
import openai


def test_core_dependencies_import():
    assert fastapi.__version__
    assert openai.__version__
    assert chromadb.__version__
