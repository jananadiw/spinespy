"""Tests for SpineSpy Pro licensing and trial functionality."""

from datetime import datetime, timedelta
import json
from unittest.mock import MagicMock, patch, call
import urllib.error

import pytest

from spinespy.licensing import (
    activate_license,
    deactivate_license,
    format_license_status,
    get_license_info,
    is_pro,
    validate_license,
    LicenseActivationError,
    LicenseActivationLimitError,
    LicenseError,
    LicenseStatus,
    LicenseValidationError,
    TRIAL_DAYS,
    VALIDATION_INTERVAL_DAYS,
)


@pytest.fixture
def mock_keychain():
    """Mock keychain operations."""
    keychain_data = {}
    
    def save_item(account, password):
        keychain_data[account] = password
    
    def load_item(account):
        return keychain_data.get(account)
    
    def delete_item(account):
        keychain_data.pop(account, None)
    
    with patch("spinespy.licensing.save_keychain_item", side_effect=save_item), \
         patch("spinespy.licensing.load_keychain_item", side_effect=load_item), \
         patch("spinespy.licensing.delete_keychain_item", side_effect=delete_item):
        yield keychain_data


@pytest.fixture
def mock_urlopen():
    """Mock urllib.request.urlopen for API calls."""
    with patch("urllib.request.urlopen") as mock:
        yield mock


def test_trial_starts_on_first_launch(mock_keychain):
    """Trial should start on first launch and have full days remaining."""
    info = get_license_info()
    
    assert info.status == LicenseStatus.TRIAL_ACTIVE
    assert info.is_pro is True
    assert info.trial_days_remaining == TRIAL_DAYS
    assert "trial_start" in mock_keychain


def test_trial_days_decrement(mock_keychain):
    """Trial days should decrement as time passes."""
    # Set trial start to 3 days ago
    start_date = datetime.now() - timedelta(days=3)
    mock_keychain["trial_start"] = start_date.isoformat()
    
    info = get_license_info()
    
    assert info.status == LicenseStatus.TRIAL_ACTIVE
    assert info.is_pro is True
    assert info.trial_days_remaining == TRIAL_DAYS - 3


def test_trial_expires_after_7_days(mock_keychain):
    """Trial should expire after 7 days."""
    start_date = datetime.now() - timedelta(days=8)
    mock_keychain["trial_start"] = start_date.isoformat()
    
    info = get_license_info()
    
    assert info.status == LicenseStatus.TRIAL_EXPIRED
    assert info.is_pro is False
    assert info.trial_days_remaining == 0


def test_trial_persists_across_restarts(mock_keychain):
    """Trial start date should persist in keychain."""
    # First check
    info1 = get_license_info()
    assert info1.status == LicenseStatus.TRIAL_ACTIVE
    
    # Simulate restart by checking again
    info2 = get_license_info()
    assert info2.status == LicenseStatus.TRIAL_ACTIVE
    assert info2.trial_days_remaining == info1.trial_days_remaining


def test_activate_license_success(mock_keychain, mock_urlopen):
    """Successful license activation should save key and return active status."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "activated": True,
        "license_key": {
            "id": 123,
            "status": "active",
        },
        "meta": {
            "store_id": "test-store",
            "variant_id": "test-product",
        },
    }).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response
    
    info = activate_license("TEST-KEY-1234")
    
    assert info.status == LicenseStatus.ACTIVE
    assert info.is_pro is True
    assert info.license_key == "TEST-KEY-1234"
    assert mock_keychain["license_key"] == "TEST-KEY-1234"
    assert "last_validation" in mock_keychain


def test_activate_license_limit_reached(mock_keychain, mock_urlopen):
    """Activation should fail with specific error when limit is reached."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "activated": False,
        "error": "Activation limit reached for this license key",
    }).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response
    
    with pytest.raises(LicenseActivationLimitError) as exc_info:
        activate_license("TEST-KEY-FULL")
    
    assert "3 Macs" in str(exc_info.value)
    assert "license_key" not in mock_keychain


def test_activate_license_invalid_key(mock_keychain, mock_urlopen):
    """Activation should fail for invalid key."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "activated": False,
        "error": "Invalid license key",
    }).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response
    
    with pytest.raises(LicenseActivationError) as exc_info:
        activate_license("INVALID-KEY")
    
    assert "Invalid license key" in str(exc_info.value)
    assert "license_key" not in mock_keychain


def test_activate_license_network_error(mock_keychain, mock_urlopen):
    """Activation should fail gracefully on network error."""
    mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
    
    with pytest.raises(LicenseActivationError) as exc_info:
        activate_license("TEST-KEY")
    
    assert "Network" in str(exc_info.value)


def test_validate_license_online_success(mock_keychain, mock_urlopen):
    """Online validation should succeed for valid license."""
    mock_keychain["license_key"] = "VALID-KEY"
    mock_keychain["instance_id"] = "test-instance"
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "valid": True,
        "license_key": {
            "id": 123,
            "status": "active",
        },
    }).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response
    
    info = validate_license(force=True)
    
    assert info.status == LicenseStatus.ACTIVE
    assert info.is_pro is True
    assert "last_validation" in mock_keychain


def test_validate_license_disabled(mock_keychain, mock_urlopen):
    """Validation should return disabled status for disabled license."""
    mock_keychain["license_key"] = "DISABLED-KEY"
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "valid": False,
        "license_key": {
            "id": 123,
            "status": "disabled",
        },
    }).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response
    
    info = validate_license(force=True)
    
    assert info.status == LicenseStatus.DISABLED
    assert info.is_pro is False


def test_validate_license_offline_within_grace(mock_keychain, mock_urlopen):
    """License should remain valid offline within grace period."""
    mock_keychain["license_key"] = "VALID-KEY"
    mock_keychain["last_validation"] = (datetime.now() - timedelta(days=3)).isoformat()
    
    mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
    
    info = validate_license(force=True)
    
    assert info.status == LicenseStatus.ACTIVE
    assert info.is_pro is True
    assert "offline" in info.message


def test_validate_license_offline_past_grace(mock_keychain, mock_urlopen):
    """License should become inactive offline past grace period."""
    mock_keychain["license_key"] = "VALID-KEY"
    mock_keychain["last_validation"] = (
        datetime.now() - timedelta(days=VALIDATION_INTERVAL_DAYS + 1)
    ).isoformat()
    
    mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
    
    info = validate_license(force=True)
    
    assert info.status == LicenseStatus.INACTIVE
    assert info.is_pro is False
    assert "offline" in info.message.lower()


def test_validate_license_uses_cache_within_grace(mock_keychain, mock_urlopen):
    """Validation should use cache and not make API call within grace period."""
    mock_keychain["license_key"] = "VALID-KEY"
    mock_keychain["last_validation"] = (datetime.now() - timedelta(days=1)).isoformat()
    
    info = validate_license(force=False)
    
    assert info.status == LicenseStatus.ACTIVE
    assert info.is_pro is True
    assert "cached" in info.message
    assert not mock_urlopen.called


def test_validate_license_force_ignores_cache(mock_keychain, mock_urlopen):
    """Force validation should ignore cache and make API call."""
    mock_keychain["license_key"] = "VALID-KEY"
    mock_keychain["last_validation"] = (datetime.now() - timedelta(days=1)).isoformat()
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "valid": True,
        "license_key": {"id": 123, "status": "active"},
    }).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response
    
    info = validate_license(force=True)
    
    assert info.status == LicenseStatus.ACTIVE
    assert mock_urlopen.called


def test_deactivate_license_success(mock_keychain, mock_urlopen):
    """Deactivation should clear local license and call API."""
    mock_keychain["license_key"] = "VALID-KEY"
    mock_keychain["instance_id"] = "test-instance"
    mock_keychain["last_validation"] = datetime.now().isoformat()
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "deactivated": True,
    }).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response
    
    deactivate_license()
    
    assert "license_key" not in mock_keychain
    assert "last_validation" not in mock_keychain
    assert mock_urlopen.called


def test_deactivate_license_no_key(mock_keychain):
    """Deactivation should fail if no license key exists."""
    with pytest.raises(LicenseError) as exc_info:
        deactivate_license()
    
    assert "No license key" in str(exc_info.value)


def test_deactivate_license_clears_local_even_on_api_error(mock_keychain, mock_urlopen):
    """Deactivation should clear local license even if API call fails."""
    mock_keychain["license_key"] = "VALID-KEY"
    mock_keychain["instance_id"] = "test-instance"
    
    mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
    
    deactivate_license()
    
    assert "license_key" not in mock_keychain


def test_is_pro_returns_true_for_active_license(mock_keychain, mock_urlopen):
    """is_pro() should return True for active license."""
    mock_keychain["license_key"] = "VALID-KEY"
    mock_keychain["last_validation"] = datetime.now().isoformat()
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "valid": True,
        "license_key": {"status": "active"},
    }).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response
    
    assert is_pro() is True


def test_is_pro_returns_true_for_active_trial(mock_keychain):
    """is_pro() should return True for active trial."""
    assert is_pro() is True


def test_is_pro_returns_false_for_expired_trial(mock_keychain):
    """is_pro() should return False for expired trial."""
    start_date = datetime.now() - timedelta(days=8)
    mock_keychain["trial_start"] = start_date.isoformat()
    
    assert is_pro() is False


def test_is_pro_degrades_gracefully_on_error(mock_keychain, mock_urlopen):
    """is_pro() should fall back to trial check on validation errors."""
    mock_keychain["license_key"] = "VALID-KEY"
    mock_urlopen.side_effect = Exception("Unexpected error")
    
    # Should fall back to trial check, which starts a new trial
    assert is_pro() is True


def test_format_license_status_trial_active(mock_keychain):
    """Status formatting for active trial."""
    status = format_license_status()
    
    assert "Trial" in status
    assert f"{TRIAL_DAYS} days" in status


def test_format_license_status_trial_expired(mock_keychain):
    """Status formatting for expired trial."""
    start_date = datetime.now() - timedelta(days=8)
    mock_keychain["trial_start"] = start_date.isoformat()
    
    status = format_license_status()
    
    assert "Trial expired" in status


def test_format_license_status_active_license(mock_keychain, mock_urlopen):
    """Status formatting for active license."""
    mock_keychain["license_key"] = "VALID-KEY"
    mock_keychain["last_validation"] = datetime.now().isoformat()
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "valid": True,
        "license_key": {"status": "active"},
    }).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response
    
    status = format_license_status()
    
    assert "SpineSpy Pro" in status


def test_license_replaces_trial(mock_keychain, mock_urlopen):
    """Activating a license should take precedence over trial."""
    # Start with active trial
    info1 = get_license_info()
    assert info1.status == LicenseStatus.TRIAL_ACTIVE
    
    # Activate license
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "activated": True,
        "license_key": {"status": "active"},
        "meta": {"store_id": "test", "variant_id": "test"},
    }).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response
    
    activate_license("TEST-KEY")
    
    # License should take precedence
    info2 = get_license_info()
    assert info2.status == LicenseStatus.ACTIVE


def test_instance_id_persists(mock_keychain, mock_urlopen):
    """Instance ID should be generated once and persist."""
    # Instance ID is only created when activating/validating a license
    mock_keychain["license_key"] = "VALID-KEY"
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "valid": True,
        "license_key": {"status": "active"},
    }).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response
    
    info1 = get_license_info()
    instance_id1 = mock_keychain.get("instance_id")
    
    assert instance_id1 is not None
    
    # Check again
    info2 = get_license_info()
    instance_id2 = mock_keychain.get("instance_id")
    
    assert instance_id1 == instance_id2


def test_activate_license_strips_whitespace(mock_keychain, mock_urlopen):
    """License activation should strip whitespace from key."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "activated": True,
        "license_key": {"status": "active"},
        "meta": {},
    }).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response
    
    activate_license("  TEST-KEY-WITH-SPACES  \n")
    
    # Check the API was called with stripped key
    assert mock_urlopen.called
    request = mock_urlopen.call_args[0][0]
    request_data = json.loads(request.data.decode("utf-8"))
    assert request_data["license_key"] == "TEST-KEY-WITH-SPACES"
