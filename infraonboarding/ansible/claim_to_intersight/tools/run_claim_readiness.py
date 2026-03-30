#!/usr/bin/env python3
"""Per-host claim readiness helper for inventory-first Phase 1."""

from __future__ import annotations

import ast
import json
import os
from typing import Any
from xml.etree import ElementTree

import requests
import urllib3


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
) -> requests.Response:
    """Send an HTTP request using the supplied session."""
    return session.request(
        method=method,
        url=url,
        verify=verify_ssl,
        timeout=timeout,
        **kwargs,
    )


def first_item(payload: Any) -> dict[str, Any]:
    """Return the first useful object from common API response shapes."""
    if isinstance(payload, list):
        return payload[0] if payload else {}
    if isinstance(payload, dict):
        for key in ("Results", "results", "Items", "items"):
            value = payload.get(key)
            if isinstance(value, list) and value:
                return value[0]
        return payload
    return {}


def extract_value(payload: Any, *keys: str) -> Any:
    """Read the first populated key from a JSON payload."""
    item = first_item(payload)
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return None


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "enabled", "enable"}
    return bool(value)


def usable_credentials(credentials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usable: list[dict[str, Any]] = []
    for credential in credentials:
        if not isinstance(credential, dict):
            continue
        username = str(credential.get("username", "")).strip()
        password = str(credential.get("password", "")).strip()
        if username and password:
            usable.append(credential)
    usable.sort(key=lambda item: int(item.get("priority", 1000)))
    return usable


def login_with_xml_api(
    host: str,
    username: str,
    password: str,
    *,
    verify_ssl: bool,
    timeout: int,
) -> tuple[requests.Session, dict[str, str]]:
    """Open a UCS XML API session and return auth headers for connector calls."""
    session = requests.Session()
    response = request(
        session,
        "POST",
        f"https://{host}/nuova",
        verify_ssl=verify_ssl,
        timeout=timeout,
        data=f'<aaaLogin inName="{username}" inPassword="{password}" />',
    )
    response.raise_for_status()
    xml_tree = ElementTree.fromstring(response.content)
    xml_cookie = xml_tree.attrib.get("outCookie", "")
    if not xml_cookie:
        error_code = xml_tree.attrib.get("errorCode", "")
        error_descr = xml_tree.attrib.get("errorDescr", "")
        detail = ", ".join(
            part
            for part in [
                f"errorCode={error_code}" if error_code else "",
                f"errorDescr={error_descr}" if error_descr else "",
            ]
            if part
        )
        raise ValueError(
            "XML login succeeded but no outCookie was returned"
            + (f" ({detail})" if detail else "")
        )
    return session, {"ucsmcookie": f"ucsm-cookie={xml_cookie}"}


def logout_with_xml_api(
    session: requests.Session,
    host: str,
    headers: dict[str, str],
    *,
    verify_ssl: bool,
    timeout: int,
) -> None:
    """Best-effort logout for UCS XML API sessions."""
    cookie_header = str(headers.get("ucsmcookie", "")).strip()
    cookie_value = cookie_header.replace("ucsm-cookie=", "", 1).strip()
    if not cookie_value:
        return
    try:
        request(
            session,
            "POST",
            f"https://{host}/nuova",
            verify_ssl=verify_ssl,
            timeout=timeout,
            data=f'<aaaLogout inCookie="{cookie_value}" />',
        )
    except Exception:
        pass


def login_with_imm_session(
    host: str,
    username: str,
    password: str,
    *,
    verify_ssl: bool,
    timeout: int,
) -> tuple[requests.Session, dict[str, str]]:
    """Open an IMM REST session and return auth headers for connector calls."""
    response = requests.post(
        f"https://{host}/Login",
        verify=verify_ssl,
        timeout=timeout,
        json={"User": username, "Password": password},
    )
    if not response.ok:
        response_text = (response.text or "").strip()
        response_headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower() in {"content-type", "set-cookie", "server"}
        }
        raise requests.HTTPError(
            "IMM login failed: "
            f"status={response.status_code}, "
            f"body={response_text or '<empty>'}, "
            f"response_headers={response_headers}, "
            f"requests={requests.__version__}, "
            f"urllib3={urllib3.__version__}",
            response=response,
        )
    payload = response.json()
    session_id = payload.get("SessionId", "")
    if not session_id:
        raise ValueError("IMM login succeeded but no SessionId was returned")
    session = requests.Session()
    session.cookies.update(response.cookies)
    return session, {"Cookie": f"sessionId={session_id}"}


def logout_with_imm_session(
    session: requests.Session,
    host: str,
    headers: dict[str, str],
    *,
    verify_ssl: bool,
    timeout: int,
) -> None:
    """Best-effort logout for IMM sessions."""
    request_headers = {}
    cookie_header = str(headers.get("Cookie", "")).strip()
    if cookie_header:
        request_headers["Cookie"] = cookie_header
    csrf_token = str(session.cookies.get("csrf", "")).strip()
    if csrf_token:
        request_headers["X-CSRF-Token"] = csrf_token
    if not str(request_headers.get("Cookie", "")).strip():
        return
    try:
        request(
            session,
            "POST",
            f"https://{host}/Logout",
            verify_ssl=verify_ssl,
            timeout=timeout,
            headers=request_headers,
        )
    except Exception:
        pass


def get_json(
    session: requests.Session,
    host: str,
    path: str,
    *,
    verify_ssl: bool,
    timeout: int,
    headers: dict[str, str],
) -> Any:
    """Fetch and decode a JSON endpoint using the active authenticated session."""
    response = request(
        session,
        "GET",
        f"https://{host}{path}",
        verify_ssl=verify_ssl,
        timeout=timeout,
        headers=headers,
    )
    response.raise_for_status()
    if not response.content:
        return {}
    return response.json()


def fetch_claim_readiness(
    endpoint: str,
    prepared_target: dict[str, Any],
    desired_credentials: list[dict[str, Any]],
    *,
    verify_ssl: bool,
    timeout: int,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    device_type = str(prepared_target.get("device_type", "")).strip().lower()
    if not endpoint or not desired_credentials:
        return None, {
            "endpoint": endpoint,
            "device_type": device_type or "unknown",
            "status": "failed",
            "changed": False,
            "reason": "claim_readiness_credentials_missing",
            "messages": ["Endpoint credentials were not available for claim readiness retrieval"],
        }

    if device_type not in {"imc", "imm"}:
        return None, {
            "endpoint": endpoint,
            "device_type": device_type or "unknown",
            "status": "skipped",
            "changed": False,
            "reason": "claim_readiness_not_supported_for_device_type",
            "messages": [f"Claim readiness retrieval is not required for {device_type or 'unknown'}"],
        }

    attempt_errors: list[str] = []
    for desired_credential in desired_credentials:
        username = str(desired_credential.get("username", "")).strip()
        password = str(desired_credential.get("password", "")).strip()
        if not username or not password:
            continue

        session: requests.Session | None = None
        headers: dict[str, str] = {}

        try:
            if device_type == "imc":
                session, headers = login_with_xml_api(
                    endpoint,
                    username,
                    password,
                    verify_ssl=verify_ssl,
                    timeout=timeout,
                )
            else:
                session, headers = login_with_imm_session(
                    endpoint,
                    username,
                    password,
                    verify_ssl=verify_ssl,
                    timeout=timeout,
                )

            systems_payload = get_json(
                session,
                endpoint,
                "/connector/Systems",
                verify_ssl=verify_ssl,
                timeout=timeout,
                headers=headers,
            )
            system_item = first_item(systems_payload)
            connector_enabled = normalize_bool(
                extract_value(system_item, "AdminState", "Adminstate", "Enabled")
            )
            connection_state = extract_value(system_item, "ConnectionState", "ConnectionStatus")
            ownership_state = extract_value(
                system_item, "AccountOwnershipState", "AccountOwnershipStatus"
            )

            identifier_payload = get_json(
                session,
                endpoint,
                "/connector/DeviceIdentifiers",
                verify_ssl=verify_ssl,
                timeout=timeout,
                headers=headers,
            )
            claim_serial_number = extract_value(
                identifier_payload, "Id", "SerialNumber", "Identifier", "serial_number"
            )

            ownership_state_normalized = str(ownership_state or "").strip().lower()
            claimed_already = ownership_state_normalized not in {"", "not claimed"}
            claim_security_token = None
            if not claimed_already:
                token_payload = get_json(
                    session,
                    endpoint,
                    "/connector/SecurityTokens",
                    verify_ssl=verify_ssl,
                    timeout=timeout,
                    headers=headers,
                )
                claim_security_token = extract_value(
                    token_payload, "Token", "SecurityToken", "security_token"
                )
        except Exception as exc:
            attempt_errors.append(str(exc))
            continue
        finally:
            if session is not None:
                if device_type == "imc":
                    logout_with_xml_api(
                        session,
                        endpoint,
                        headers,
                        verify_ssl=verify_ssl,
                        timeout=timeout,
                    )
                else:
                    logout_with_imm_session(
                        session,
                        endpoint,
                        headers,
                        verify_ssl=verify_ssl,
                        timeout=timeout,
                    )
                session.close()

        result = {
            "endpoint": endpoint,
            "device_type": device_type or "unknown",
            "changed": False,
            "claim_serial_number_present": bool(claim_serial_number),
            "claim_security_token_present": bool(claim_security_token),
            "connection_state": connection_state,
            "account_ownership_state": ownership_state,
            "connector_enabled": connector_enabled,
        }

        if claimed_already and claim_serial_number:
            claim_ready_target = {
                **prepared_target,
                "claim_serial_number": claim_serial_number,
                "claim_security_token": "",
                "connection_state": connection_state,
                "account_ownership_state": ownership_state,
                "connector_enabled": connector_enabled,
                "claim_submission_required": False,
            }
            return claim_ready_target, {
                **result,
                "status": "already_claimed",
                "reason": "connector_reports_already_claimed",
                "messages": [
                    "Connector reports the device is already claimed; security token retrieval was skipped"
                ],
            }

        if not claim_serial_number or not claim_security_token:
            return None, {
                **result,
                "status": "failed",
                "reason": "claim_readiness_incomplete",
                "messages": [
                    "Claim readiness was retrieved but did not include both device identifier and security token"
                ],
            }

        claim_ready_target = {
            **prepared_target,
            "claim_serial_number": claim_serial_number,
            "claim_security_token": claim_security_token,
            "connection_state": connection_state,
            "account_ownership_state": ownership_state,
            "connector_enabled": connector_enabled,
            "claim_submission_required": True,
        }
        return claim_ready_target, {
            **result,
            "status": "ready_for_claim",
            "reason": "claim_readiness_retrieved",
            "messages": ["Claim readiness retrieved successfully"],
        }

    return None, {
        "endpoint": endpoint,
        "device_type": device_type or "unknown",
        "status": "failed",
        "changed": False,
        "reason": "claim_readiness_retrieval_failed",
        "messages": attempt_errors
        or ["Claim readiness retrieval failed for all supplied desired credentials"],
    }


def main() -> None:
    endpoint = str(os.environ.get("ENDPOINT", "")).strip()
    desired = usable_credentials(load_json_env("DESIRED_CREDENTIALS_JSON", []))
    prepared_targets = load_json_env("PREPARED_TARGETS_JSON", [])
    verify_ssl = parse_bool(os.environ.get("VALIDATE_CERTS"), default=False)
    timeout = int(os.environ.get("TIMEOUT", "20"))

    prepared_target = next(
        (
            item
            for item in prepared_targets
            if isinstance(item, dict) and str(item.get("endpoint", "")).strip() == endpoint
        ),
        None,
    )
    if prepared_target is None:
        print(
            json.dumps(
                {
                    "claim_ready_target": {},
                    "result": {
                        "endpoint": endpoint,
                        "status": "failed",
                        "changed": False,
                        "reason": "prepared_target_missing",
                        "messages": ["Prepared target metadata was not available for this host"],
                    },
                }
            )
        )
        return

    try:
        claim_ready_target, result = fetch_claim_readiness(
            endpoint,
            prepared_target,
            desired,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )
    except Exception as exc:
        claim_ready_target = None
        result = {
            "endpoint": endpoint,
            "device_type": prepared_target.get("device_type", "unknown"),
            "status": "failed",
            "changed": False,
            "reason": "claim_readiness_retrieval_failed",
            "messages": [str(exc)],
        }

    print(
        json.dumps(
            {
                "claim_ready_target": claim_ready_target or {},
                "result": result,
            }
        )
    )


if __name__ == "__main__":
    main()
