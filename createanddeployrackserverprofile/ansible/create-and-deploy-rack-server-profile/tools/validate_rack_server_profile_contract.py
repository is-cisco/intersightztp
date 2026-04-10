#!/usr/bin/env python3

import json
import sys
from pathlib import Path

import yaml


def load_structured_file(path_str):
    path = Path(path_str)
    data = yaml.safe_load(path.read_text())
    return data if data is not None else {}


def unwrap_root(data, key):
    if isinstance(data, dict) and key in data:
        return data[key]
    return data


def main():
    if len(sys.argv) != 4:
      print(
          "usage: validate_rack_server_profile_contract.py <rack_server> <server_profile> <policy_definitions>",
          file=sys.stderr,
      )
      return 2

    rack_server = unwrap_root(load_structured_file(sys.argv[1]), "rack_server")
    server_profile = unwrap_root(load_structured_file(sys.argv[2]), "server_profile")
    policy_definitions = unwrap_root(load_structured_file(sys.argv[3]), "policies")

    errors = []

    if not isinstance(rack_server, dict):
        errors.append("rack_server input must be a mapping")
    else:
        if not any(str(rack_server.get(key, "")).strip() for key in ("moid", "serial", "name")):
            errors.append("rack_server requires one of: moid, serial, or name")

    if not isinstance(server_profile, dict):
        errors.append("server_profile input must be a mapping")
    else:
        if not str(server_profile.get("name", "")).strip():
            errors.append("server_profile.name is required")

    if not isinstance(policy_definitions, list):
        errors.append("policy_definitions input must be a list or a {policies: [...]} wrapper")
    else:
        for index, item in enumerate(policy_definitions):
            if not isinstance(item, dict):
                errors.append(f"policy[{index}] must be a mapping")
                continue
            for field in ("name", "resource_path", "object_type"):
                if not str(item.get(field, "")).strip():
                    errors.append(f"policy[{index}].{field} is required")

    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        return 1

    print(
        json.dumps(
            {
                "valid": True,
                "rack_server_selector": {
                    "moid": rack_server.get("moid", ""),
                    "serial": rack_server.get("serial", ""),
                    "name": rack_server.get("name", ""),
                },
                "server_profile_name": server_profile.get("name", ""),
                "policy_count": len(policy_definitions),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
