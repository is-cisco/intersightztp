#!/usr/bin/env python3
"""Per-host default password check and reset helper for inventory-first Phase 1."""

from __future__ import annotations

import ast
import json
import os
from typing import Any

import requests


def parse_bool(value: str | None, default: bool = False) -> bool:
    """Normalize string-like booleans from environment variables."""
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def normalize_jsonish(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return normalize_jsonish(json.loads(stripped))
            except ValueError:
                return value
        return value
    if isinstance(value, list):
        return [normalize_jsonish(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_jsonish(item) for key, item in value.items()}
    return value


def load_json_env(name: str, default: Any) -> Any:
    """Load a JSON-like environment variable into Python objects."""
    value = os.environ.get(name, "")
    if not value:
        return default
    try:
        return normalize_jsonish(json.loads(value))
    except ValueError:
        return normalize_jsonish(ast.literal_eval(value))


def request(
    session: requests.Session,
    method: str,
    url: str,
    *,
    verify_ssl: bool,
    timeout: int,
    **kwargs: Any,
) -> requests.Response | None:
    """Perform a best-effort HTTP request and return None on transport failures."""
    try:
        return session.request(
            method=method,
            url=url,
            verify=verify_ssl,
            timeout=timeout,
            **kwargs,
        )
    except requests.exceptions.RequestException:
        return None


def redfish_account_uri(account_id: str = "1") -> str:
    return f"/redfish/v1/AccountService/Accounts/{account_id}"


def query_redfish_root(
    host: str,
    *,
    verify_ssl: bool,
    timeout: int,
) -> tuple[int | None, dict[str, Any], str]:
    """Query the Redfish service root to detect IMC-style Redfish behavior."""
    session = requests.Session()
    response = request(
        session,
        "GET",
        f"https://{host}/redfish/v1",
        verify_ssl=verify_ssl,
        timeout=timeout,
    )
    if response is None:
        return None, {}, "request_error"
    payload: dict[str, Any] = {}
    if response.content:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
    return response.status_code, payload, ""


def is_cisco_imc_redfish_root(payload: dict[str, Any]) -> bool:
    vendor = str(payload.get("Vendor", "")).strip().lower()
    product = str(payload.get("Product", "")).strip().upper()
    return vendor.startswith("cisco systems inc") and product.startswith("UCSC-")


def query_account(
    host: str,
    username: str,
    password: str,
    *,
    verify_ssl: bool,
    timeout: int,
) -> tuple[int | None, dict[str, Any], str]:
    """Read the default account object using Redfish basic auth."""
    session = requests.Session()
    response = request(
        session,
        "GET",
        f"https://{host}{redfish_account_uri()}",
        verify_ssl=verify_ssl,
        timeout=timeout,
        auth=(username, password),
    )
    if response is None:
        return None, {}, "request_error"
    payload: dict[str, Any] = {}
    if response.content:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
    return response.status_code, payload, ""


def patch_password(
    host: str,
    username: str,
    password: str,
    new_password: str,
    *,
    verify_ssl: bool,
    timeout: int,
) -> tuple[int | None, str]:
    """Patch the Redfish account password when a default password is still active."""
    session = requests.Session()
    response = request(
        session,
        "PATCH",
        f"https://{host}{redfish_account_uri()}",
        verify_ssl=verify_ssl,
        timeout=timeout,
        auth=(username, password),
        headers={"Content-Type": "application/json"},
        json={"Password": new_password},
    )
    if response is None:
        return None, "request_error"
    return response.status_code, ""


def imm_login_works(
    host: str,
    username: str,
    password: str,
    *,
    verify_ssl: bool,
    timeout: int,
) -> bool:
    """Check whether IMM session login succeeds with the supplied credentials."""
    session = requests.Session()
    try:
        response = request(
            session,
            "POST",
            f"https://{host}/Login",
            verify_ssl=verify_ssl,
            timeout=timeout,
            json={"User": username, "Password": password},
        )
        if response is None:
            return False
        response.raise_for_status()
        payload = response.json() if response.content else {}
        return bool(payload.get("SessionId"))
    except (requests.exceptions.RequestException, ValueError):
        return False
    finally:
        session.close()


def usable_credentials(credentials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter the credential list down to entries with both username and password."""
    usable: list[dict[str, Any]] = []
    for credential in credentials:
        if not isinstance(credential, dict):
            continue
        username = str(credential.get("username", "")).strip()
        password = str(credential.get("password", "")).strip()
        if username and password:
            usable.append({"username": username, "password": password})
    return usable


def main() -> None:
    """Evaluate password state for one endpoint and emit a JSON-safe result."""
    endpoint = str(os.environ.get("ENDPOINT", "")).strip()
    desired_credentials = load_json_env("DESIRED_CREDENTIALS_JSON", [])
    default_credentials = load_json_env("DEFAULT_CREDENTIALS_JSON", [])
    verify_ssl = parse_bool(os.environ.get("VALIDATE_CERTS"), default=False)
    timeout = int(os.environ.get("TIMEOUT", "20"))

    desired_candidates = usable_credentials(desired_credentials)
    if not desired_candidates:
        print(json.dumps({
            "endpoint": endpoint,
            "status": "failed",
            "changed": False,
            "reason": "desired_credential_missing",
            "messages": ["No usable desired credential was provided for this host"],
        }))
        return

    desired = desired_candidates[0]
    desired_status: int | None = None
    desired_payload: dict[str, Any] = {}
    desired_error = ""
    attempted_desired_usernames: list[str] = []
    redfish_root_status, redfish_root_payload, redfish_root_error = query_redfish_root(
        endpoint,
        verify_ssl=verify_ssl,
        timeout=timeout,
    )
    redfish_root_vendor = str(redfish_root_payload.get("Vendor", "")).strip()
    redfish_root_product = str(redfish_root_payload.get("Product", "")).strip()
    cisco_imc_redfish = (
        redfish_root_status == 200
        and is_cisco_imc_redfish_root(redfish_root_payload)
    )

    if not cisco_imc_redfish:
        for candidate in desired_candidates:
            attempted_desired_usernames.append(candidate["username"])
            if imm_login_works(
                endpoint,
                candidate["username"],
                candidate["password"],
                verify_ssl=verify_ssl,
                timeout=timeout,
            ):
                print(json.dumps({
                    "endpoint": endpoint,
                    "status": "ready",
                    "changed": False,
                    "reason": "imm_password_reset_not_applicable",
                    "messages": ["IMM target detected; password reset is not applicable and the host will continue to connector preparation"],
                    "password_change_required": False,
                    "password_reset_applicable": False,
                    "device_type": "imm",
                    "redfish_root_status": redfish_root_status,
                    "redfish_root_vendor": redfish_root_vendor,
                    "redfish_root_product": redfish_root_product,
                }))
                return

        print(json.dumps({
            "endpoint": endpoint,
            "status": "failed",
            "changed": False,
            "reason": "non_imc_redfish_or_imm_login_failed",
            "messages": ["The endpoint did not match the Cisco IMC Redfish fingerprint and no desired credential succeeded via the non-IMC login path"],
            "attempted_desired_usernames": attempted_desired_usernames,
            "redfish_root_status": redfish_root_status,
            "redfish_root_error": redfish_root_error,
            "redfish_root_vendor": redfish_root_vendor,
            "redfish_root_product": redfish_root_product,
        }))
        return

    for candidate in desired_candidates:
        attempted_desired_usernames.append(candidate["username"])
        candidate_status, candidate_payload, candidate_error = query_account(
            endpoint,
            candidate["username"],
            candidate["password"],
            verify_ssl=verify_ssl,
            timeout=timeout,
        )
        if candidate_status == 200:
            print(json.dumps({
                "endpoint": endpoint,
                "status": "ready",
                "changed": False,
                "reason": "desired_password_already_active",
                "messages": ["Desired credential already works for the Redfish account"],
                "password_change_required": bool(candidate_payload.get("PasswordChangeRequired", False)),
                "password_reset_applicable": True,
                "device_type": "imc",
                "redfish_root_vendor": redfish_root_vendor,
                "redfish_root_product": redfish_root_product,
            }))
            return

        if imm_login_works(
            endpoint,
            candidate["username"],
            candidate["password"],
            verify_ssl=verify_ssl,
            timeout=timeout,
        ):
            print(json.dumps({
                "endpoint": endpoint,
                "status": "ready",
                "changed": False,
                "reason": "imm_password_reset_not_applicable",
                "messages": ["IMM target detected; password reset is not applicable and the host will continue to connector preparation"],
                "password_change_required": False,
                "password_reset_applicable": False,
                "device_type": "imm",
                "redfish_root_vendor": redfish_root_vendor,
                "redfish_root_product": redfish_root_product,
            }))
            return

        if desired_status is None:
            desired = candidate
            desired_status = candidate_status
            desired_payload = candidate_payload
            desired_error = candidate_error

    attempted_default_usernames: list[str] = []
    for credential in default_credentials:
        if not isinstance(credential, dict):
            continue
        username = str(credential.get("username", "")).strip()
        password = str(credential.get("password", "")).strip()
        if not username or not password:
            continue
        attempted_default_usernames.append(username)
        default_status, default_payload, default_error = query_account(
            endpoint,
            username,
            password,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )
        if default_status != 200:
            continue

        if not bool(default_payload.get("PasswordChangeRequired", False)):
            print(json.dumps({
                "endpoint": endpoint,
                "status": "failed",
                "changed": False,
                "reason": "default_password_active_without_forced_change",
                "messages": ["A default credential worked, but Redfish did not report PasswordChangeRequired"],
                "attempted_default_usernames": attempted_default_usernames,
                "attempted_desired_usernames": attempted_desired_usernames,
                "redfish_root_vendor": redfish_root_vendor,
                "redfish_root_product": redfish_root_product,
            }))
            return

        patch_status, patch_error = patch_password(
            endpoint,
            username,
            password,
            str(desired.get("password", "")).strip(),
            verify_ssl=verify_ssl,
            timeout=timeout,
        )
        if patch_status not in {200, 204}:
            print(json.dumps({
                "endpoint": endpoint,
                "status": "failed",
                "changed": False,
                "reason": "password_reset_failed",
                "messages": [patch_error or f"Unexpected Redfish patch status {patch_status}"],
                "attempted_default_usernames": attempted_default_usernames,
                "attempted_desired_usernames": attempted_desired_usernames,
                "redfish_root_vendor": redfish_root_vendor,
                "redfish_root_product": redfish_root_product,
            }))
            return

        verify_status, _, verify_error = query_account(
            endpoint,
            str(desired.get("username", "")).strip(),
            str(desired.get("password", "")).strip(),
            verify_ssl=verify_ssl,
            timeout=timeout,
        )
        if verify_status == 200:
            print(json.dumps({
                "endpoint": endpoint,
                "status": "changed",
                "changed": True,
                "reason": "password_reset_completed",
                "messages": ["Password change requirement was detected and the desired password was applied"],
                "attempted_default_usernames": attempted_default_usernames,
                "attempted_desired_usernames": attempted_desired_usernames,
                "password_reset_applicable": True,
                "device_type": "imc",
                "redfish_root_vendor": redfish_root_vendor,
                "redfish_root_product": redfish_root_product,
            }))
            return

        print(json.dumps({
            "endpoint": endpoint,
            "status": "failed",
            "changed": True,
            "reason": "password_reset_verification_failed",
            "messages": [verify_error or f"Desired credential verification failed with status {verify_status}"],
            "attempted_default_usernames": attempted_default_usernames,
            "attempted_desired_usernames": attempted_desired_usernames,
            "redfish_root_vendor": redfish_root_vendor,
            "redfish_root_product": redfish_root_product,
        }))
        return

    print(json.dumps({
        "endpoint": endpoint,
        "status": "failed",
        "changed": False,
        "reason": "no_matching_default_credential",
        "messages": ["No supplied default credential could read the Redfish account resource"],
        "attempted_default_usernames": attempted_default_usernames,
        "attempted_desired_usernames": attempted_desired_usernames,
        "desired_precheck_status": desired_status,
        "desired_precheck_error": desired_error,
        "redfish_root_status": redfish_root_status,
        "redfish_root_error": redfish_root_error,
        "redfish_root_vendor": redfish_root_vendor,
        "redfish_root_product": redfish_root_product,
    }))


if __name__ == "__main__":
    main()
