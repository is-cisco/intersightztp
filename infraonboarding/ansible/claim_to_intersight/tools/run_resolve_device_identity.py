#!/usr/bin/env python3
"""Resolve device identity from an endpoint for inventory-first teardown."""

from __future__ import annotations

import ast
import json
import os
from typing import Any
from xml.etree import ElementTree

import requests


def parse_bool(value: str | None, default: bool = False) -> bool:
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
    value = os.environ.get(name, "")
    if not value:
        return default
    try:
        return normalize_jsonish(json.loads(value))
    except ValueError:
        return normalize_jsonish(ast.literal_eval(value))


def request(session: requests.Session, method: str, url: str, *, verify_ssl: bool, timeout: int, **kwargs: Any) -> requests.Response:
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


def first_usable(credentials: list[dict[str, Any]]) -> dict[str, Any] | None:
    for credential in credentials:
        if not isinstance(credential, dict):
            continue
        username = str(credential.get("username", "")).strip()
        password = str(credential.get("password", "")).strip()
        if username and password:
            return credential
    return None


def login_with_xml_api(host: str, username: str, password: str, *, verify_ssl: bool, timeout: int) -> tuple[requests.Session, dict[str, str]]:
    session = requests.Session()
    response = request(session, "POST", f"https://{host}/nuova", verify_ssl=verify_ssl, timeout=timeout, data=f'<aaaLogin inName="{username}" inPassword="{password}" />')
    response.raise_for_status()
    xml_tree = ElementTree.fromstring(response.content)
    xml_cookie = xml_tree.attrib.get("outCookie", "")
    if not xml_cookie:
        error_code = xml_tree.attrib.get("errorCode", "")
        error_descr = xml_tree.attrib.get("errorDescr", "")
        detail = ", ".join(
            part for part in [
                f"errorCode={error_code}" if error_code else "",
                f"errorDescr={error_descr}" if error_descr else "",
            ] if part
        )
        raise ValueError("XML login succeeded but no outCookie was returned" + (f" ({detail})" if detail else ""))
    return session, {"ucsmcookie": f"ucsm-cookie={xml_cookie}"}


def logout_with_xml_api(session: requests.Session, host: str, headers: dict[str, str], *, verify_ssl: bool, timeout: int) -> None:
    cookie_header = str(headers.get("ucsmcookie", "")).strip()
    cookie_value = cookie_header.replace("ucsm-cookie=", "", 1).strip()
    if not cookie_value:
        return
    try:
        request(session, "POST", f"https://{host}/nuova", verify_ssl=verify_ssl, timeout=timeout, data=f'<aaaLogout inCookie="{cookie_value}" />')
    except Exception:
        pass


def login_with_imm_session(host: str, username: str, password: str, *, verify_ssl: bool, timeout: int) -> tuple[requests.Session, dict[str, str]]:
    session = requests.Session()
    response = request(session, "POST", f"https://{host}/Login", verify_ssl=verify_ssl, timeout=timeout, json={"User": username, "Password": password})
    response.raise_for_status()
    payload = response.json()
    session_id = payload.get("SessionId", "")
    if not session_id:
        raise ValueError("IMM login succeeded but no SessionId was returned")
    return session, {"Cookie": f"sessionId={session_id}"}


def get_json(session: requests.Session, host: str, path: str, *, verify_ssl: bool, timeout: int, headers: dict[str, str]) -> Any:
    response = request(session, "GET", f"https://{host}{path}", verify_ssl=verify_ssl, timeout=timeout, headers=headers)
    response.raise_for_status()
    if not response.content:
        return {}
    return response.json()


def resolve_identity(endpoint: str, credentials: list[dict[str, Any]], *, verify_ssl: bool, timeout: int) -> dict[str, Any]:
    desired = first_usable(credentials)
    if desired is None:
        return {
            "endpoint": endpoint,
            "status": "failed",
            "reason": "desired_credential_missing",
            "messages": ["No usable desired credential was provided for this host"],
        }

    username = str(desired.get("username", "")).strip()
    password = str(desired.get("password", "")).strip()

    try:
        session, headers = login_with_xml_api(endpoint, username, password, verify_ssl=verify_ssl, timeout=timeout)
        device_type = "imc"
        try:
            identifiers = get_json(session, endpoint, "/connector/DeviceIdentifiers", verify_ssl=verify_ssl, timeout=timeout, headers=headers)
            serial = extract_value(identifiers, "Id", "SerialNumber", "Identifier", "serial_number")
            return {
                "endpoint": endpoint,
                "device_type": device_type,
                "status": "resolved",
                "serial_number": serial or "",
                "messages": ["Device identifier retrieved successfully"],
            }
        finally:
            logout_with_xml_api(session, endpoint, headers, verify_ssl=verify_ssl, timeout=timeout)
            session.close()
    except Exception as imc_exc:
        imc_error = str(imc_exc)

    try:
        session, headers = login_with_imm_session(endpoint, username, password, verify_ssl=verify_ssl, timeout=timeout)
        device_type = "imm"
        try:
            identifiers = get_json(session, endpoint, "/connector/DeviceIdentifiers", verify_ssl=verify_ssl, timeout=timeout, headers=headers)
            serial = extract_value(identifiers, "Id", "SerialNumber", "Identifier", "serial_number")
            return {
                "endpoint": endpoint,
                "device_type": device_type,
                "status": "resolved",
                "serial_number": serial or "",
                "messages": ["Device identifier retrieved successfully"],
            }
        finally:
            session.close()
    except Exception as imm_exc:
        return {
            "endpoint": endpoint,
            "status": "failed",
            "reason": "device_identity_lookup_failed",
            "messages": [imc_error, str(imm_exc)],
        }


def main() -> None:
    endpoint = str(os.environ.get("ENDPOINT", "")).strip()
    credentials = load_json_env("DESIRED_CREDENTIALS_JSON", [])
    verify_ssl = parse_bool(os.environ.get("VALIDATE_CERTS"), default=False)
    timeout = int(os.environ.get("TIMEOUT", "20"))
    print(json.dumps(resolve_identity(endpoint, credentials, verify_ssl=verify_ssl, timeout=timeout)))


if __name__ == "__main__":
    main()
