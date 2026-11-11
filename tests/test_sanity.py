"""Proves the package installs and imports before any real code exists."""

import faq_service


def test_package_imports_with_version() -> None:
    assert faq_service.__version__ == "0.1.0"
