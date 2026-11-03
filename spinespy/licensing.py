"""SpineSpy Pro licensing and trial management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json
from typing import Optional
import urllib.request
import urllib.error
import uuid

from spinespy.keychain import (
    save_keychain_item,
    load_keychain_item,
    delete_keychain_item,
    KeychainError,
)


# Lemon Squeezy License API configuration
LEMON_SQUEEZY_API_URL = "https://api.lemonsqueezy.com/v1/licenses"

# Configurable product IDs - set these to match your Lemon Squeezy setup
LEMON_SQUEEZY_STORE_ID = "your-store-id"
LEMON_SQUEEZY_PRODUCT_ID = "your-product-id"

# Checkout URL for purchasing - configurable
CHECKOUT_URL = "https://your-checkout-url.lemonsqueezy.com/checkout"

# Trial configuration
TRIAL_DAYS = 7
VALIDATION_INTERVAL_DAYS = 7

# Keychain account names
KEYCHAIN_LICENSE_KEY = "license_key"
KEYCHAIN_INSTANCE_ID = "instance_id"
KEYCHAIN_TRIAL_START = "trial_start"
KEYCHAIN_LAST_VALIDATION = "last_validation"


class LicenseStatus(Enum):
    """Possible license states."""
    TRIAL_ACTIVE = "trial_active"
    TRIAL_EXPIRED = "trial_expired"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISABLED = "disabled"


class LicenseError(Exception):
    """Base exception for licensing errors."""
    pass


class LicenseValidationError(LicenseError):
    """Raised when license validation fails."""
    pass


class LicenseActivationError(LicenseError):
    """Raised when license activation fails."""
    pass


class LicenseActivationLimitError(LicenseActivationError):
    """Raised when activation limit is reached."""
    pass


@dataclass
class LicenseInfo:
    """Information about the current license state."""
    status: LicenseStatus
    is_pro: bool
    message: str
    trial_days_remaining: Optional[int] = None
    license_key: Optional[str] = None
    instance_id: Optional[str] = None


def _make_license_request(
    endpoint: str,
    data: Optional[dict] = None,
    timeout: int = 10,
) -> dict:
    """
    Make a request to the Lemon Squeezy License API.
    
    Args:
        endpoint: The API endpoint (e.g., "activate", "validate")
        data: Optional JSON data to send
        timeout: Request timeout in seconds
    
    Returns:
        The JSON response as a dictionary
    
    Raises:
        LicenseValidationError: If the request fails
    """
    url = f"{LEMON_SQUEEZY_API_URL}/{endpoint}"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    
    request_data = json.dumps(data).encode("utf-8") if data else None
    
    try:
        request = urllib.request.Request(
            url,
            data=request_data,
            headers=headers,
            method="POST",
        )
        
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            return response_data
    except urllib.error.HTTPError as error:
        try:
            error_data = json.loads(error.read().decode("utf-8"))
            error_message = error_data.get("error", str(error))
        except (json.JSONDecodeError, UnicodeDecodeError):
            error_message = str(error)
        raise LicenseValidationError(f"License API request failed: {error_message}")
    except urllib.error.URLError as error:
        raise LicenseValidationError(f"Network error: {error.reason}")
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise LicenseValidationError(f"Invalid API response: {error}")
    except Exception as error:
        raise LicenseValidationError(f"Unexpected error: {error}")


def _get_or_create_instance_id() -> str:
    """Get the existing instance ID or create a new one."""
    instance_id = load_keychain_item(KEYCHAIN_INSTANCE_ID)
    if instance_id:
        return instance_id
    
    # Generate a new instance ID
    instance_id = str(uuid.uuid4())
    try:
        save_keychain_item(KEYCHAIN_INSTANCE_ID, instance_id)
    except KeychainError:
        pass  # Fail silently, ID will be regenerated on next run
    return instance_id


def _get_trial_start_date() -> Optional[datetime]:
    """Get the trial start date from keychain."""
    try:
        trial_start_str = load_keychain_item(KEYCHAIN_TRIAL_START)
        if trial_start_str:
            return datetime.fromisoformat(trial_start_str)
    except (KeychainError, ValueError):
        pass
    return None


def _set_trial_start_date(start_date: datetime) -> None:
    """Save the trial start date to keychain."""
    try:
        save_keychain_item(KEYCHAIN_TRIAL_START, start_date.isoformat())
    except KeychainError:
        pass  # Fail silently - trial won't persist, but app still works


def _get_last_validation_date() -> Optional[datetime]:
    """Get the last successful validation date from keychain."""
    try:
        validation_str = load_keychain_item(KEYCHAIN_LAST_VALIDATION)
        if validation_str:
            return datetime.fromisoformat(validation_str)
    except (KeychainError, ValueError):
        pass
    return None


def _set_last_validation_date(validation_date: datetime) -> None:
    """Save the last validation date to keychain."""
    try:
        save_keychain_item(KEYCHAIN_LAST_VALIDATION, validation_date.isoformat())
    except KeychainError:
        pass  # Fail silently


def _get_stored_license_key() -> Optional[str]:
    """Get the stored license key from keychain."""
    try:
        return load_keychain_item(KEYCHAIN_LICENSE_KEY)
    except KeychainError:
        return None


def _save_license_key(license_key: str) -> None:
    """Save the license key to keychain."""
    try:
        save_keychain_item(KEYCHAIN_LICENSE_KEY, license_key)
    except KeychainError as error:
        raise LicenseError(f"Failed to save license key: {error}")


def _delete_license_key() -> None:
    """Delete the license key from keychain."""
    try:
        delete_keychain_item(KEYCHAIN_LICENSE_KEY)
    except KeychainError:
        pass  # Already deleted or doesn't exist


def _check_trial_status() -> tuple[bool, int]:
    """
    Check if trial is active.
    
    Returns:
        (is_active, days_remaining)
    """
    trial_start = _get_trial_start_date()
    
    if trial_start is None:
        # First launch - start trial
        trial_start = datetime.now()
        _set_trial_start_date(trial_start)
        return True, TRIAL_DAYS
    
    elapsed = datetime.now() - trial_start
    days_remaining = max(0, TRIAL_DAYS - elapsed.days)
    is_active = days_remaining > 0
    
    return is_active, days_remaining


def activate_license(license_key: str) -> LicenseInfo:
    """
    Activate a license key with Lemon Squeezy.
    
    Args:
        license_key: The license key to activate
    
    Returns:
        LicenseInfo with activation details
    
    Raises:
        LicenseActivationError: If activation fails
        LicenseActivationLimitError: If activation limit is reached
    """
    instance_id = _get_or_create_instance_id()
    
    try:
        response = _make_license_request("activate", {
            "license_key": license_key.strip(),
            "instance_name": f"SpineSpy-{instance_id[:8]}",
        })
        
        # Check for activation limit
        if not response.get("activated", False):
            error_msg = response.get("error", "Activation failed")
            if "limit" in error_msg.lower():
                raise LicenseActivationLimitError(
                    "Activation limit reached. This license is already active on 3 Macs. "
                    "Deactivate SpineSpy Pro on another Mac to use it here."
                )
            raise LicenseActivationError(error_msg)
        
        # Check license status
        meta = response.get("meta", {})
        store_id = str(meta.get("store_id", ""))
        product_id = str(meta.get("variant_id", ""))
        
        # Verify it's for the correct product (optional, can be lenient)
        # if store_id != LEMON_SQUEEZY_STORE_ID or product_id != LEMON_SQUEEZY_PRODUCT_ID:
        #     raise LicenseActivationError("License key is not valid for SpineSpy Pro")
        
        # Save the validated license
        _save_license_key(license_key)
        _set_last_validation_date(datetime.now())
        
        return LicenseInfo(
            status=LicenseStatus.ACTIVE,
            is_pro=True,
            message="License activated successfully",
            license_key=license_key,
            instance_id=instance_id,
        )
        
    except LicenseActivationLimitError:
        raise  # Re-raise activation limit errors
    except LicenseValidationError as error:
        raise LicenseActivationError(f"Failed to activate license: {error}")


def validate_license(license_key: Optional[str] = None, force: bool = False) -> LicenseInfo:
    """
    Validate a license key with Lemon Squeezy.
    
    Args:
        license_key: The license key to validate (uses stored key if None)
        force: Force validation even if within grace period
    
    Returns:
        LicenseInfo with validation details
    """
    if license_key is None:
        license_key = _get_stored_license_key()
    
    if not license_key:
        return _check_trial_or_expired()
    
    instance_id = _get_or_create_instance_id()
    
    # Check if we need to revalidate
    if not force:
        last_validation = _get_last_validation_date()
        if last_validation:
            grace_period = timedelta(days=VALIDATION_INTERVAL_DAYS)
            if datetime.now() - last_validation < grace_period:
                # Still within grace period, consider valid
                return LicenseInfo(
                    status=LicenseStatus.ACTIVE,
                    is_pro=True,
                    message="License valid (cached)",
                    license_key=license_key,
                    instance_id=instance_id,
                )
    
    # Attempt to validate with API
    try:
        response = _make_license_request("validate", {
            "license_key": license_key.strip(),
            "instance_id": instance_id,
        })
        
        valid = response.get("valid", False)
        license_key_data = response.get("license_key", {})
        status_api = license_key_data.get("status", "")
        
        if valid and status_api == "active":
            _set_last_validation_date(datetime.now())
            return LicenseInfo(
                status=LicenseStatus.ACTIVE,
                is_pro=True,
                message="License valid",
                license_key=license_key,
                instance_id=instance_id,
            )
        
        # License is invalid or disabled
        if status_api == "disabled":
            status = LicenseStatus.DISABLED
            message = "License has been disabled"
        else:
            status = LicenseStatus.INACTIVE
            message = "License is not active"
        
        return LicenseInfo(
            status=status,
            is_pro=False,
            message=message,
            license_key=license_key,
            instance_id=instance_id,
        )
        
    except LicenseValidationError:
        # Network error or API unavailable
        last_validation = _get_last_validation_date()
        if last_validation:
            grace_period = timedelta(days=VALIDATION_INTERVAL_DAYS)
            if datetime.now() - last_validation < grace_period:
                # Within grace period, allow offline usage
                return LicenseInfo(
                    status=LicenseStatus.ACTIVE,
                    is_pro=True,
                    message="License valid (offline, within grace period)",
                    license_key=license_key,
                    instance_id=instance_id,
                )
        
        # Outside grace period or never validated
        return LicenseInfo(
            status=LicenseStatus.INACTIVE,
            is_pro=False,
            message="Unable to validate license (offline, past grace period)",
            license_key=license_key,
            instance_id=instance_id,
        )


def _check_trial_or_expired() -> LicenseInfo:
    """Check trial status when no license is present."""
    is_active, days_remaining = _check_trial_status()
    
    if is_active:
        return LicenseInfo(
            status=LicenseStatus.TRIAL_ACTIVE,
            is_pro=True,
            message=f"{days_remaining} day{'s' if days_remaining != 1 else ''} remaining in trial",
            trial_days_remaining=days_remaining,
        )
    
    return LicenseInfo(
        status=LicenseStatus.TRIAL_EXPIRED,
        is_pro=False,
        message="Trial expired",
        trial_days_remaining=0,
    )


def deactivate_license() -> None:
    """
    Deactivate the current license on this Mac.
    
    Raises:
        LicenseError: If deactivation fails
    """
    license_key = _get_stored_license_key()
    if not license_key:
        raise LicenseError("No license key found")
    
    instance_id = _get_or_create_instance_id()
    
    try:
        _make_license_request("deactivate", {
            "license_key": license_key.strip(),
            "instance_id": instance_id,
        })
    except LicenseValidationError as error:
        # Even if API call fails, clear local license
        pass
    finally:
        # Always clear local license data
        _delete_license_key()
        try:
            delete_keychain_item(KEYCHAIN_LAST_VALIDATION)
        except KeychainError:
            pass


def get_license_info() -> LicenseInfo:
    """
    Get the current license information.
    
    Returns:
        LicenseInfo with current status
    """
    return validate_license()


def is_pro() -> bool:
    """
    Check if the user has an active Pro license or trial.
    
    Returns:
        True if Pro features are available, False otherwise
    """
    try:
        info = get_license_info()
        if info.is_pro:
            return True
        
        # If license validation failed but returned inactive (not disabled),
        # fall back to trial check (graceful degradation for network errors)
        if info.status == LicenseStatus.INACTIVE and info.license_key:
            try:
                is_active, _ = _check_trial_status()
                return is_active
            except Exception:
                pass
        
        return info.is_pro
    except KeychainError:
        # On keychain errors, be permissive (graceful degradation)
        return True
    except Exception:
        # On other errors, check trial status as fallback
        try:
            is_active, _ = _check_trial_status()
            return is_active
        except Exception:
            # Ultimate fallback: deny Pro features
            return False


def format_license_status() -> str:
    """
    Get a human-readable license status string.
    
    Returns:
        A formatted status string for display
    """
    try:
        info = get_license_info()
        
        if info.status == LicenseStatus.TRIAL_ACTIVE:
            return f"Trial: {info.trial_days_remaining} days left"
        elif info.status == LicenseStatus.TRIAL_EXPIRED:
            return "Trial expired"
        elif info.status == LicenseStatus.ACTIVE:
            return "SpineSpy Pro"
        elif info.status == LicenseStatus.DISABLED:
            return "License disabled"
        else:
            return "Free version"
    except Exception:
        return "SpineSpy"
