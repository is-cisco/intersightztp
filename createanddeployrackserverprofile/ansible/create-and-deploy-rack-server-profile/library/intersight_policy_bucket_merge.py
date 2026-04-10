#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: intersight_policy_bucket_merge
short_description: Merge desired Intersight policy bucket references with an existing bucket
description:
- Normalizes policy references and returns a merged bucket plus the set of
  missing desired references.
options:
  existing_bucket:
    description:
    - Existing live policy bucket from an Intersight managed object.
    type: list
    elements: dict
    default: []
  desired_bucket:
    description:
    - Desired policy references to ensure on the target object.
    type: list
    elements: dict
    default: []
author:
- OpenAI
'''

RETURN = r'''
merged_bucket:
  description: Existing bucket with desired references added when missing.
  returned: always
  type: list
missing_bucket:
  description: Desired references that were not already present in the existing bucket.
  returned: always
  type: list
'''

from ansible.module_utils.basic import AnsibleModule


def _normalize_ref(item):
    if not isinstance(item, dict):
        return {}

    normalized = dict(item)
    moid = str(normalized.get("Moid", "")).strip()
    object_type = str(normalized.get("ObjectType", "")).strip()
    name = str(normalized.get("Name", "")).strip()

    if moid:
        normalized["Moid"] = moid
    if object_type:
        normalized["ObjectType"] = object_type
    if name:
        normalized["Name"] = name
    if "ClassId" not in normalized and object_type:
        normalized["ClassId"] = "mo.MoRef"
    return normalized


def _ref_key(item):
    normalized = _normalize_ref(item)
    moid = normalized.get("Moid", "")
    object_type = normalized.get("ObjectType", "")
    name = normalized.get("Name", "")
    if moid:
        return "moid::{0}::{1}".format(object_type, moid)
    return "name::{0}::{1}".format(object_type, name)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            existing_bucket=dict(type="list", elements="dict", default=[]),
            desired_bucket=dict(type="list", elements="dict", default=[]),
        ),
        supports_check_mode=True,
    )

    existing_bucket = module.params["existing_bucket"] or []
    desired_bucket = module.params["desired_bucket"] or []

    merged_bucket = []
    seen_keys = set()

    for item in existing_bucket:
        normalized = _normalize_ref(item)
        if not normalized:
            continue
        key = _ref_key(normalized)
        if key in seen_keys:
            continue
        merged_bucket.append(normalized)
        seen_keys.add(key)

    missing_bucket = []
    for item in desired_bucket:
        normalized = _normalize_ref(item)
        if not normalized:
            continue
        key = _ref_key(normalized)
        if key in seen_keys:
            continue
        merged_bucket.append(normalized)
        missing_bucket.append(normalized)
        seen_keys.add(key)

    module.exit_json(
        changed=len(missing_bucket) > 0,
        merged_bucket=merged_bucket,
        missing_bucket=missing_bucket,
    )


if __name__ == "__main__":
    main()
