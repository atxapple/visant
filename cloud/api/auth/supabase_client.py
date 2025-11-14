"""Supabase client integration for authentication."""

import os
from typing import Optional, Dict, Any

try:
    from supabase import create_client, Client, AuthApiError
    SUPABASE_AVAILABLE = True
except ImportError:
    print("WARNING: Supabase package not fully installed. Auth features will be limited.")
    print("   Run: pip install --upgrade supabase")
    SUPABASE_AVAILABLE = False
    Client = None
    AuthApiError = Exception  # Fallback

# Get Supabase credentials from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("WARNING: SUPABASE_URL or SUPABASE_KEY not set. Auth will not work.")


def get_supabase_client(use_service_key: bool = False) -> Optional[Client]:
    """
    Get Supabase client instance.

    Args:
        use_service_key: If True, use service role key (admin operations)
                        If False, use anon public key (user operations)

    Returns:
        Supabase client or None if credentials not set
    """
    if not SUPABASE_AVAILABLE:
        return None

    if not SUPABASE_URL:
        return None

    key = SUPABASE_SERVICE_KEY if use_service_key else SUPABASE_KEY
    if not key:
        return None

    try:
        return create_client(SUPABASE_URL, key)
    except Exception as e:
        print(f"ERROR: Failed to create Supabase client: {e}")
        return None


def create_supabase_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Create a new user in Supabase Auth.

    Args:
        email: User's email address
        password: User's password (min 6 characters)

    Returns:
        User data dict or None if failed
    """
    supabase = get_supabase_client(use_service_key=True)
    if not supabase:
        raise RuntimeError("Supabase client not configured")

    try:
        # Create user with email/password
        response = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,  # Auto-confirm email for development
        })

        return {
            "id": response.user.id,
            "email": response.user.email,
        }

    except AuthApiError as e:
        print(f"ERROR: Supabase auth error: {e}")
        raise ValueError(f"Failed to create user: {e.message}")
    except Exception as e:
        print(f"ERROR: Unexpected error creating user: {e}")
        raise


def sign_in_with_password(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Sign in a user with email and password.

    Args:
        email: User's email
        password: User's password

    Returns:
        Dict with access_token, refresh_token, and user info
    """
    supabase = get_supabase_client()
    if not supabase:
        raise RuntimeError("Supabase client not configured")

    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })

        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
            },
        }

    except AuthApiError as e:
        print(f"ERROR: Login failed: {e}")
        raise ValueError("Invalid email or password")
    except Exception as e:
        print(f"ERROR: Unexpected error during login: {e}")
        raise


def get_user_from_token(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Get user info from JWT access token.

    Args:
        access_token: JWT token from login

    Returns:
        User info dict or None if invalid
    """
    supabase = get_supabase_client()
    if not supabase:
        return None

    try:
        response = supabase.auth.get_user(access_token)
        return {
            "id": response.user.id,
            "email": response.user.email,
        }
    except Exception as e:
        print(f"ERROR: Failed to get user from token: {e}")
        return None


def send_password_reset(email: str) -> None:
    """
    Trigger Supabase password reset email for the given address.

    Args:
        email: Account email to reset
    """
    if os.getenv("SUPABASE_DISABLE_EMAIL", "").lower() in {"1", "true", "yes"}:
        print(f"[dev] Skipping Supabase reset email for {email} (disabled)")
        return

    supabase = get_supabase_client()
    if not supabase:
        raise RuntimeError("Supabase client not configured")

    try:
        redirect_to = os.getenv("PASSWORD_RESET_REDIRECT_URL")
        options = {"redirect_to": redirect_to} if redirect_to else None
        supabase.auth.reset_password_for_email(email, options=options)
    except AuthApiError as e:
        print(f"ERROR: Password reset error: {e}")
        raise ValueError(e.message or "Failed to send password reset email")
    except Exception as e:
        print(f"ERROR: Unexpected password reset error: {e}")
        raise RuntimeError("Failed to send password reset email") from e


def verify_user_password(email: str, password: str) -> bool:
    """
    Verify a user's current password.

    Args:
        email: User's email address
        password: Password to verify

    Returns:
        True if password is correct, False otherwise
    """
    try:
        # Try to sign in with the provided credentials
        result = sign_in_with_password(email, password)
        return result is not None
    except ValueError:
        # Invalid credentials
        return False
    except Exception as e:
        print(f"ERROR: Failed to verify password: {e}")
        return False


def update_user_password(supabase_user_id: str, new_password: str) -> bool:
    """
    Update a user's password in Supabase Auth.

    Args:
        supabase_user_id: The Supabase user ID
        new_password: New password (min 6 characters)

    Returns:
        True if successful, False otherwise
    """
    supabase = get_supabase_client(use_service_key=True)
    if not supabase:
        raise RuntimeError("Supabase client not configured")

    try:
        # Update user password using admin API
        supabase.auth.admin.update_user_by_id(
            supabase_user_id,
            {"password": new_password}
        )
        return True

    except AuthApiError as e:
        print(f"ERROR: Failed to update password: {e}")
        raise ValueError(f"Failed to update password: {e.message}")
    except Exception as e:
        print(f"ERROR: Unexpected error updating password: {e}")
        raise
