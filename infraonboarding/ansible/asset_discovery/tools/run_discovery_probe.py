#!/usr/bin/env python3
"""Probe reachable endpoints with candidate credentials and classify platform type."""

from __future__ import annotations

import ast
import json
import os
from typing import Any
from xml.etree import ElementTree

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


def load_json_env(name: str) -> Any:
    """Load a JSON-like environment variable into Python objects."""
    value = os.environ.get(name, "")
    if not value:
        return []
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
        return session.request(method=method, url=url, verify=verify_ssl, timeout=timeout, **kwargs)
    except requests.exceptions.RequestException:
        return None


def logout_with_imm_session(
    session: requests.Session,
    host: str,
    session_id: str,
    *,
    verify_ssl: bool,
    timeout: int,
) -> None:
    """Best-effort logout for IMM sessions opened during discovery probing."""
    if not str(session_id).strip():
        return
    request_headers = {"Cookie": f"sessionId={session_id}"}
    csrf_token = str(session.cookies.get("csrf", "")).strip()
    if csrf_token:
        request_headers["X-CSRF-Token"] = csrf_token
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


def probe_endpoint(
    host: str,
    username: str,
    password: str,
    *,
    verify_ssl: bool,
    timeout: int,
) -> dict[str, str]:
    """Probe platform fingerprints in the same order used by downstream endpoint logic."""
    session = requests.Session()

    redfish_response = request(
        session,
        "GET",
        f"https://{host}/redfish/v1/Managers/CIMC",
        verify_ssl=verify_ssl,
        timeout=timeout,
        auth=(username, password),
    )
    if redfish_response is not None and redfish_response.status_code == 200:
        return {
            "device_type": "imc",
            "detection_status": "live_detected",
            "detection_reason": "Redfish CIMC manager endpoint responded successfully",
            "detection_probe": "redfish_manager_cimc",
        }

    imm_response = request(
        session,
        "POST",
        f"https://{host}/Login",
        verify_ssl=verify_ssl,
        timeout=timeout,
        json={"User": username, "Password": password},
    )
    if imm_response is not None and imm_response.status_code == 200:
        try:
            imm_payload = imm_response.json()
        except ValueError:
            imm_payload = {}
        imm_session_id = str(imm_payload.get("SessionId", "")).strip()
        if imm_session_id:
            try:
                return {
                    "device_type": "imm",
                    "detection_status": "live_detected",
                    "detection_reason": "IMM login endpoint returned a session identifier",
                    "detection_probe": "imm_login",
                }
            finally:
                logout_with_imm_session(
                    session,
                    host,
                    imm_session_id,
                    verify_ssl=verify_ssl,
                    timeout=timeout,
                )

    xml_response = request(
        session,
        "POST",
        f"https://{host}/nuova",
        verify_ssl=verify_ssl,
        timeout=timeout,
        data=f'<aaaLogin inName="{username}" inPassword="{password}" />',
    )
    if xml_response is not None and xml_response.status_code == 200:
        try:
            xml_tree = ElementTree.fromstring(xml_response.content)
        except ElementTree.ParseError:
            xml_tree = None
        if xml_tree is not None:
            xml_cookie = xml_tree.attrib.get("outCookie", "")
            if xml_cookie:
                xml_redfish = request(
                    session,
                    "GET",
                    f"https://{host}/redfish/v1/Managers/CIMC",
                    verify_ssl=verify_ssl,
                    timeout=timeout,
                    headers={"ucsmcookie": f"ucsm-cookie={xml_cookie}"},
                )
                if xml_redfish is not None and xml_redfish.status_code == 200:
                    return {
                        "device_type": "imc",
                        "detection_status": "live_detected",
                        "detection_reason": "XML login succeeded and CIMC Redfish manager endpoint is reachable",
                        "detection_probe": "xml_login_plus_redfish",
                    }
                return {
                    "device_type": "imm",
                    "detection_status": "live_detected",
                    "detection_reason": "XML login succeeded but CIMC Redfish fingerprint was not present; target is normalized to imm for downstream processing",
                    "detection_probe": "xml_login",
                }

    return {
        "device_type": "undetermined",
        "detection_status": "no_platform_match",
        "detection_reason": "No platform-specific fingerprint matched the endpoint",
        "detection_probe": "none",
    }


def usable_credentials(credentials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return usable credentials sorted by priority for deterministic probing."""
    usable: list[dict[str, Any]] = []
    for credential in credentials:
        if not isinstance(credential, dict):
            continue
        username = str(credential.get("username", "")).strip()
        password = str(credential.get("password", "")).strip()
        if username and password:
            usable.append(
                {
                    "username": username,
                    "password": password,
                    "priority": int(credential.get("priority", 1000) or 1000),
                }
            )
    usable.sort(key=lambda item: (item["priority"], item["username"]))
    return usable


def main() -> None:
    """Probe every reachable endpoint and emit a JSON discovery result list."""
    targets = load_json_env("TARGETS_JSON")
    credentials = usable_credentials(load_json_env("CREDENTIALS_JSON"))
    verify_ssl = parse_bool(os.environ.get("VALIDATE_CERTS"), default=False)
    timeout = int(os.environ.get("TIMEOUT", "20"))

    results: list[dict[str, Any]] = []
    for target in targets:
        if not isinstance(target, dict):
            continue

        if not target.get("reachable", False):
            results.append(
                {
                    **target,
                    "device_type": "undetermined",
                    "detection_status": "skipped_unreachable",
                    "detection_reason": "Endpoint was not reachable on the management port",
                    "detection_probe": "none",
                    "credential_resolution_status": "skipped_unreachable",
                }
            )
            continue

        if not credentials:
            results.append(
                {
                    **target,
                    "device_type": "undetermined",
                    "detection_status": "no_credentials_available",
                    "detection_reason": "No usable credential material was supplied",
                    "detection_probe": "none",
                    "credential_resolution_status": "no_credentials_available",
                }
            )
            continue

        attempted_usernames: list[str] = []
        successful_result: dict[str, Any] | None = None
        for credential in credentials:
            attempted_usernames.append(credential["username"])
            probe_result = probe_endpoint(
                target["endpoint"],
                credential["username"],
                credential["password"],
                verify_ssl=verify_ssl,
                timeout=timeout,
            )
            candidate = {
                **target,
                **probe_result,
                "credential_username": credential["username"],
                "credential_resolution_status": "probe_attempted",
            }
            if probe_result["detection_status"] == "live_detected":
                successful_result = candidate
                break

        if successful_result is not None:
            results.append(successful_result)
            continue

        results.append(
            {
                **target,
                "device_type": "undetermined",
                "detection_status": "no_platform_match",
                "detection_reason": "No supplied credential returned a supported platform fingerprint",
                "detection_probe": "none",
                "credential_resolution_status": "no_successful_credential",
                "attempted_usernames": attempted_usernames,
            }
        )

    print(json.dumps(results))


if __name__ == "__main__":
    main()
