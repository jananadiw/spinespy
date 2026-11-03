"""Tests for macOS Keychain integration."""

from unittest.mock import patch, MagicMock
import subprocess

import pytest

from spinespy.keychain import (
    save_keychain_item,
    load_keychain_item,
    delete_keychain_item,
    KeychainError,
    SERVICE_NAME,
)


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for security command."""
    with patch("subprocess.run") as mock:
        yield mock


def test_save_keychain_item_success(mock_subprocess):
    """Saving to keychain should succeed with exit code 0."""
    mock_subprocess.return_value = MagicMock(
        returncode=0,
        stdout="",
        stderr="",
    )
    
    save_keychain_item("test_account", "test_password")
    
    # Should call delete first, then add
    assert mock_subprocess.call_count == 2
    
    # Check the add call
    add_call = mock_subprocess.call_args_list[1]
    assert "add-generic-password" in add_call[0][0]
    assert "-s" in add_call[0][0]
    assert SERVICE_NAME in add_call[0][0]
    assert "-a" in add_call[0][0]
    assert "test_account" in add_call[0][0]
    assert "-w" in add_call[0][0]
    assert "test_password" in add_call[0][0]


def test_save_keychain_item_failure(mock_subprocess):
    """Saving should raise KeychainError on failure."""
    mock_subprocess.return_value = MagicMock(
        returncode=1,
        stdout="",
        stderr="permission denied",
    )
    
    with pytest.raises(KeychainError) as exc_info:
        save_keychain_item("test_account", "test_password")
    
    assert "Failed to save" in str(exc_info.value)


def test_load_keychain_item_success(mock_subprocess):
    """Loading from keychain should return the password."""
    mock_subprocess.return_value = MagicMock(
        returncode=0,
        stdout="my_secret_password\n",
        stderr="",
    )
    
    result = load_keychain_item("test_account")
    
    assert result == "my_secret_password"
    
    # Check the find call
    assert mock_subprocess.call_count == 1
    call_args = mock_subprocess.call_args[0][0]
    assert "find-generic-password" in call_args
    assert "-s" in call_args
    assert SERVICE_NAME in call_args
    assert "-a" in call_args
    assert "test_account" in call_args
    assert "-w" in call_args


def test_load_keychain_item_not_found(mock_subprocess):
    """Loading non-existent item should return None."""
    mock_subprocess.return_value = MagicMock(
        returncode=44,
        stdout="",
        stderr="could not be found",
    )
    
    result = load_keychain_item("nonexistent")
    
    assert result is None


def test_load_keychain_item_error(mock_subprocess):
    """Loading should raise KeychainError on unexpected error."""
    mock_subprocess.return_value = MagicMock(
        returncode=1,
        stdout="",
        stderr="access denied",
    )
    
    with pytest.raises(KeychainError) as exc_info:
        load_keychain_item("test_account")
    
    assert "Failed to load" in str(exc_info.value)


def test_delete_keychain_item_success(mock_subprocess):
    """Deleting from keychain should succeed."""
    mock_subprocess.return_value = MagicMock(
        returncode=0,
        stdout="",
        stderr="",
    )
    
    delete_keychain_item("test_account")
    
    assert mock_subprocess.call_count == 1
    call_args = mock_subprocess.call_args[0][0]
    assert "delete-generic-password" in call_args
    assert "-s" in call_args
    assert SERVICE_NAME in call_args
    assert "-a" in call_args
    assert "test_account" in call_args


def test_delete_keychain_item_not_found_ok(mock_subprocess):
    """Deleting non-existent item should succeed silently."""
    mock_subprocess.return_value = MagicMock(
        returncode=44,
        stdout="",
        stderr="could not be found",
    )
    
    delete_keychain_item("nonexistent")


def test_delete_keychain_item_error(mock_subprocess):
    """Deleting should raise KeychainError on unexpected error."""
    mock_subprocess.return_value = MagicMock(
        returncode=1,
        stdout="",
        stderr="access denied",
    )
    
    with pytest.raises(KeychainError) as exc_info:
        delete_keychain_item("test_account")
    
    assert "Failed to delete" in str(exc_info.value)


def test_security_command_timeout(mock_subprocess):
    """Security command timeout should raise KeychainError."""
    mock_subprocess.side_effect = subprocess.TimeoutExpired("security", 5)
    
    with pytest.raises(KeychainError) as exc_info:
        save_keychain_item("test_account", "test_password")
    
    assert "Security command failed" in str(exc_info.value)


def test_security_command_not_found(mock_subprocess):
    """Missing security command should raise KeychainError."""
    mock_subprocess.side_effect = FileNotFoundError("security: command not found")
    
    with pytest.raises(KeychainError) as exc_info:
        save_keychain_item("test_account", "test_password")
    
    assert "Security command failed" in str(exc_info.value)
