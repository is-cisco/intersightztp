#!/usr/bin/env python3
"""Per-host connector preparation helper for the inventory-first endpoint onboarding workflow."""

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


def request(session: requests.Session, method: str, url: str, *, verify_ssl: bool, timeout: int, **kwargs: Any) -> requests.Response:
    """Send an HTTP request using the provided session."""
    return session.request(method=method, url=url, verify=verify_ssl, timeout=timeout, **kwargs)


def first_item(payload: Any) -> dict[str, Any]:
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


def first_usable(credentials: list[dict[str, Any]]) -> dict[str, Any] | None:
    for credential in credentials:
        if not isinstance(credential, dict):
            continue
        username = str(credential.get("username", "")).strip()
        password = str(credential.get("password", "")).strip()
        if username and password:
            return credential
    return None


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


def login_with_xml_api(host: str, username: str, password: str, *, verify_ssl: bool, timeout: int) -> tuple[requests.Session, dict[str, str]]:
    """Open a UCS XML API session and return the session plus auth headers."""
    session = requests.Session()
    response = request(session, "POST", f"https://{host}/nuova", verify_ssl=verify_ssl, timeout=timeout, data=f'<aaaLogin inName="{username}" inPassword="{password}" />')
    response.raise_for_status()
    xml_tree = ElementTree.fromstring(response.content)
    xml_cookie = xml_tree.attrib.get("outCookie", "")
    if not xml_cookie:
        raise ValueError("XML login succeeded but no outCookie was returned")
    return session, {"ucsmcookie": f"ucsm-cookie={xml_cookie}"}


def logout_with_xml_api(session: requests.Session, host: str, headers: dict[str, str], *, verify_ssl: bool, timeout: int) -> None:
    """Best-effort logout for UCS XML API sessions."""
    cookie_header = str(headers.get("ucsmcookie", "")).strip()
    cookie_value = cookie_header.replace("ucsm-cookie=", "", 1).strip()
    if not cookie_value:
        return
    try:
        request(session, "POST", f"https://{host}/nuova", verify_ssl=verify_ssl, timeout=timeout, data=f'<aaaLogout inCookie="{cookie_value}" />')
    except Exception:
        pass


def login_with_imm_session(host: str, username: str, password: str, *, verify_ssl: bool, timeout: int) -> tuple[requests.Session, dict[str, str]]:
    """Open an IMM REST session and return the session plus auth headers."""
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


def logout_with_imm_session(session: requests.Session, host: str, headers: dict[str, str], *, verify_ssl: bool, timeout: int) -> None:
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


def get_json(session: requests.Session, host: str, path: str, *, verify_ssl: bool, timeout: int, headers: dict[str, str]) -> Any:
    """Fetch and decode a JSON endpoint using the active authenticated session."""
    response = request(session, "GET", f"https://{host}{path}", verify_ssl=verify_ssl, timeout=timeout, headers=headers)
    response.raise_for_status()
    if not response.content:
        return {}
    return response.json()


def build_prepared_target(base: dict[str, Any], device_type: str) -> dict[str, Any]:
    """Build the stable prepared-endpoint contract used by later grains."""
    return {
        "endpoint": base["endpoint"],
        "location": base.get("location", ""),
        "source_entry_type": base.get("source_entry_type", "single"),
        "device_type": device_type,
        "connector_status": "ready",
        "ntp_requested": False,
        "dns_requested": False,
        "proxy_requested": False,
        "certificate_upload_requested": False,
    }


def try_prepare_with_credential(
    endpoint: str,
    base_target: dict[str, Any],
    username: str,
    password: str,
    *,
    verify_ssl: bool,
    timeout: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    """Attempt connector preparation with one credential across IMC then IMM paths."""
    errors: list[str] = []

    try:
        session, headers = login_with_xml_api(endpoint, username, password, verify_ssl=verify_ssl, timeout=timeout)
        try:
            systems = get_json(session, endpoint, "/connector/Systems", verify_ssl=verify_ssl, timeout=timeout, headers=headers)
            item = first_item(systems)
            result = {
                "endpoint": endpoint,
                "device_type": "imc",
                "credential_username": username,
                "connector_status": "ready",
                "status": "ready_for_claim",
                "changed": False,
                "reason": "imc_connector_status_retrieved",
                "messages": ["Device Connector state retrieved successfully"],
                "connection_state": extract_value(item, "ConnectionState", "ConnectionStatus"),
                "account_ownership_state": extract_value(item, "AccountOwnershipState", "AccountOwnershipStatus"),
                "connector_enabled": normalize_bool(extract_value(item, "AdminState", "Adminstate", "Enabled")),
            }
            prepared_target = build_prepared_target(base_target, "imc")
            prepared_target["username"] = username
            prepared_target["password"] = password
            return prepared_target, result, errors
        finally:
            logout_with_xml_api(session, endpoint, headers, verify_ssl=verify_ssl, timeout=timeout)
            session.close()
    except Exception as imc_exc:
        errors.append(str(imc_exc))

    try:
        session, headers = login_with_imm_session(endpoint, username, password, verify_ssl=verify_ssl, timeout=timeout)
        try:
            systems = get_json(session, endpoint, "/connector/Systems", verify_ssl=verify_ssl, timeout=timeout, headers=headers)
            item = first_item(systems)
            result = {
                "endpoint": endpoint,
                "device_type": "imm",
                "credential_username": username,
                "connector_status": "ready",
                "status": "ready_for_claim",
                "changed": False,
                "reason": "imm_connector_status_retrieved",
                "messages": ["IMM session login succeeded", "Connector status retrieved"],
                "connection_state": extract_value(item, "ConnectionState", "ConnectionStatus"),
                "account_ownership_state": extract_value(item, "AccountOwnershipState", "AccountOwnershipStatus"),
                "connector_enabled": normalize_bool(extract_value(item, "AdminState", "Adminstate", "Enabled")),
            }
            prepared_target = build_prepared_target(base_target, "imm")
            prepared_target["username"] = username
            prepared_target["password"] = password
            return prepared_target, result, errors
        finally:
            logout_with_imm_session(session, endpoint, headers, verify_ssl=verify_ssl, timeout=timeout)
            session.close()
    except Exception as imm_exc:
        errors.append(str(imm_exc))

    return None, None, errors


def main() -> None:
    endpoint = str(os.environ.get("ENDPOINT", "")).strip()
    base_target = {
        "endpoint": endpoint,
        "source_entry_type": str(os.environ.get("SOURCE_ENTRY_TYPE", "single")).strip() or "single",
        "location": str(os.environ.get("LOCATION", "")).strip(),
    }
    desired_candidates = usable_credentials(load_json_env("DESIRED_CREDENTIALS_JSON", []))
    verify_ssl = parse_bool(os.environ.get("VALIDATE_CERTS"), default=False)
    timeout = int(os.environ.get("TIMEOUT", "20"))

    if not desired_candidates:
        print(json.dumps({
            "prepared_target": {},
            "result": {
                "endpoint": endpoint,
                "status": "failed",
                "changed": False,
                "reason": "desired_credential_missing",
                "messages": ["No usable desired credential was provided for this host"],
            },
        }))
        return

    errors: list[str] = []
    for desired in desired_candidates:
        username = str(desired.get("username", "")).strip()
        password = str(desired.get("password", "")).strip()
        prepared_target, result, attempt_errors = try_prepare_with_credential(
            endpoint,
            base_target,
            username,
            password,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )
        if prepared_target is not None and result is not None:
            print(json.dumps({"prepared_target": prepared_target, "result": result}))
            return
        errors.extend(attempt_errors)

    print(json.dumps({
        "prepared_target": {},
        "result": {
            "endpoint": endpoint,
            "status": "failed",
            "changed": False,
            "reason": "connector_prepare_failed",
            "messages": errors,
        },
    }))


if __name__ == "__main__":
    main()
