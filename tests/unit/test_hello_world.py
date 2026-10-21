"""
Hello World unit test.

This module contains a simple hello world test to demonstrate
basic test functionality.
"""

import pytest


def hello_world() -> str:
    """
    Return a hello world greeting.

    Returns:
        str: A hello world greeting message.
    """
    return "Hello, World!"


def test_hello_world():
    """Test that hello_world returns the expected greeting."""
    result = hello_world()
    assert result == "Hello, World!"
    assert isinstance(result, str)


def test_hello_world_not_empty():
    """Test that hello_world returns a non-empty string."""
    result = hello_world()
    assert len(result) > 0


@pytest.mark.parametrize("expected_substring", ["Hello", "World", "Hello, World!"])
def test_hello_world_contains_expected_words(expected_substring: str):
    """
    Test that hello_world contains expected substrings.

    Args:
        expected_substring: The substring to check for in the result.
    """
    result = hello_world()
    assert expected_substring in result
