"""Secure storage of SpineSpy Pro license data in macOS Keychain."""

from __future__ import annotations

import subprocess
from typing import Optional


SERVICE_NAME = "com.spinespy.license"


class KeychainError(Exception):
    """Raised when keychain operations fail."""
    pass


def _run_security_command(args: list[str]) -> tuple[int, str, str]:
    """Run macOS security command and return (exit_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["security"] + args,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode, result.stdout, result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError) as error:
        raise KeychainError(f"Security command failed: {error}")


def save_keychain_item(account: str, password: str) -> None:
    """
    Save a secret to the macOS Keychain.
    
    Args:
        account: The account name (e.g., 'license_key', 'instance_id', 'trial_start')
        password: The secret value to store
    
    Raises:
        KeychainError: If the save operation fails
    """
    # First try to delete existing item (ignore errors if it doesn't exist)
    _run_security_command([
        "delete-generic-password",
        "-s", SERVICE_NAME,
        "-a", account,
    ])
    
    # Add the new item
    exit_code, _, stderr = _run_security_command([
        "add-generic-password",
        "-s", SERVICE_NAME,
        "-a", account,
        "-w", password,
        "-U",  # Update if exists
    ])
    
    if exit_code != 0:
        raise KeychainError(f"Failed to save to keychain: {stderr}")


def load_keychain_item(account: str) -> Optional[str]:
    """
    Load a secret from the macOS Keychain.
    
    Args:
        account: The account name to retrieve
    
    Returns:
        The secret value, or None if not found
    
    Raises:
        KeychainError: If the operation fails (other than item not found)
    """
    exit_code, stdout, stderr = _run_security_command([
        "find-generic-password",
        "-s", SERVICE_NAME,
        "-a", account,
        "-w",  # Print password only
    ])
    
    if exit_code == 0:
        return stdout.strip()
    
    # Exit code 44 means item not found, which is expected
    if exit_code == 44 or "could not be found" in stderr:
        return None
    
    raise KeychainError(f"Failed to load from keychain: {stderr}")


def delete_keychain_item(account: str) -> None:
    """
    Delete a secret from the macOS Keychain.
    
    Args:
        account: The account name to delete
    
    Raises:
        KeychainError: If the delete operation fails (other than item not found)
    """
    exit_code, _, stderr = _run_security_command([
        "delete-generic-password",
        "-s", SERVICE_NAME,
        "-a", account,
    ])
    
    # Exit code 44 or "not found" is acceptable (already deleted)
    if exit_code == 0 or exit_code == 44 or "could not be found" in stderr:
        return
    
    raise KeychainError(f"Failed to delete from keychain: {stderr}")
