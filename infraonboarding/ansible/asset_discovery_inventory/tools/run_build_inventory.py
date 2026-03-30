#!/usr/bin/env python3
"""Build an inventory-first contract from endpoint and credential JSON."""

from __future__ import annotations

import ast
import ipaddress
import json
import os
import sys
from typing import Any

import yaml


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


def fail(message: str) -> None:
    """Exit with a clear inventory-contract error message."""
    print(json.dumps({"error": message}))
    sys.exit(1)


def expand_endpoints(endpoints: list[dict[str, Any]], default_location: str = "") -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for index, item in enumerate(endpoints, start=1):
        if not isinstance(item, dict):
            fail(f"endpoints[{index}] must be an object with type single or range")

        endpoint_type = str(item.get("type", "")).strip().lower()
        if endpoint_type not in {"single", "range"}:
            fail(f"endpoints[{index}].type must be 'single' or 'range'")

        if endpoint_type == "single":
            endpoint = str(item.get("endpoint", "")).strip()
            if not endpoint:
                fail(f"endpoints[{index}].endpoint is required when type is 'single'")
            expanded.append(
                {
                    "endpoint": endpoint,
                    "location": str(item.get("location", default_location)).strip(),
                    "source_entry_type": "single",
                }
            )
            continue

        if endpoint_type == "range":
            start_ip = str(item.get("start_ip", "")).strip()
            end_ip = str(item.get("end_ip", "")).strip()
            if not start_ip or not end_ip:
                fail(f"endpoints[{index}].start_ip and endpoints[{index}].end_ip are required when type is 'range'")
            try:
                start = ipaddress.IPv4Address(start_ip)
                end = ipaddress.IPv4Address(end_ip)
            except ipaddress.AddressValueError:
                fail(f"endpoints[{index}] contains an invalid IPv4 address")
            if int(end) < int(start):
                fail(f"endpoints[{index}].end_ip must be greater than or equal to start_ip")
            for current in range(int(start), int(end) + 1):
                endpoint = str(ipaddress.IPv4Address(current))
                expanded.append(
                    {
                        "endpoint": endpoint,
                        "location": str(item.get("location", default_location)).strip(),
                        "source_entry_type": "range",
                    }
                )
    seen: set[str] = set()
    unique_endpoints: list[dict[str, Any]] = []
    for endpoint_item in expanded:
        endpoint = endpoint_item["endpoint"]
        if endpoint in seen:
            continue
        seen.add(endpoint)
        unique_endpoints.append(endpoint_item)
    return unique_endpoints


def normalize_credentials(credentials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for credential in credentials:
        if not isinstance(credential, dict):
            continue
        normalized.append(
            {
                "username": str(credential.get("username", credential.get("username_param", ""))).strip(),
                "password": str(credential.get("password", credential.get("password_param", ""))).strip(),
                "priority": int(credential.get("priority", 1000) or 1000),
            }
        )
    return sorted(normalized, key=lambda item: (item["priority"], item["username"]))


def to_host_name(endpoint: str) -> str:
    return endpoint.replace(".", "_")


def build_inventory(
    endpoints: list[dict[str, Any]],
    desired_credentials: list[dict[str, Any]],
    default_credentials: list[dict[str, Any]],
    organization: str,
) -> dict[str, Any]:
    hosts: dict[str, Any] = {}
    normalized_endpoints: list[dict[str, Any]] = []
    for endpoint_item in endpoints:
        endpoint = endpoint_item["endpoint"]
        host_name = to_host_name(endpoint)
        host_payload = {
            "ansible_host": endpoint,
            "endpoint": endpoint,
            "location": endpoint_item.get("location", ""),
            "source_entry_type": endpoint_item.get("source_entry_type", "single"),
        }
        hosts[host_name] = host_payload
        normalized_endpoints.append(
            {
                "endpoint": endpoint,
                "location": endpoint_item.get("location", ""),
                "source_entry_type": endpoint_item.get("source_entry_type", "single"),
            }
        )

    inventory = {
        "all": {
            "vars": {
                "desired_credentials": desired_credentials,
                "default_credentials": default_credentials,
                "organization": organization,
            },
            "hosts": {
                "localhost": {
                    "ansible_connection": "local",
                }
            },
            "children": {
                "endpoints": {
                    "hosts": hosts,
                }
            },
        }
    }
    return {
        "generated_inventory_yaml": yaml.safe_dump(inventory, sort_keys=False),
        "generated_inventory_json": inventory,
        "generated_inventory_json_string": json.dumps(inventory),
        "generated_inventory_endpoints": normalized_endpoints,
    }


def main() -> None:
    default_location = str(os.environ.get("LOCATION", "")).strip()
    organization = str(os.environ.get("ORGANIZATION", "")).strip()
    raw_endpoints = load_json_env("ENDPOINTS_JSON", [])
    if not isinstance(raw_endpoints, list):
        fail("endpoints must be a JSON array")
    endpoints = expand_endpoints(raw_endpoints, default_location=default_location)
    desired_credentials = normalize_credentials(load_json_env("CREDENTIALS_JSON", []))
    default_credentials = normalize_credentials(load_json_env("DEFAULT_CREDENTIALS_JSON", []))
    payload = build_inventory(endpoints, desired_credentials, default_credentials, organization)
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
