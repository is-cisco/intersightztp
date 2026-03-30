# Architecture

## Overview

`endpoint_onboarding` is an inventory-first endpoint onboarding workflow for claiming Cisco standalone endpoints
into Cisco Intersight.

The design keeps the Torque launch contract simple while shifting execution toward more
idiomatic Ansible:

- launch-time inputs remain JSON strings
- the first grain converts those JSON strings into generated inventory
- downstream grains run per host against that generated inventory
- each grain still exports stable aggregate outputs for Torque chaining
- the modular claim path keeps batch looping in Ansible and moves only the missing
  organization-aware claim behavior into a narrow custom module

## Grain sequence

1. `asset_discovery_inventory`
2. `check_and_reset_default_password`
3. `device_connector_prepare`
4. `claim_to_intersight`

## Why inventory-first

The older repo used JSON list handoffs between every grain.

The new design keeps JSON only at the launch boundary and uses generated inventory to carry:

- endpoint identity
- run-scoped desired credentials
- run-scoped default credentials
- optional run-scoped location context
- per-host execution context

This makes the implementation closer to standard Ansible while still fitting Torque grain
contracts.

## Execution model

### Launch boundary

Torque passes:

- `endpoints`
- `credentials`
- `location`
- `default_credentials`
- `organization`
- Intersight authentication inputs

### Inventory shaping

`asset_discovery_inventory` expands:

- `single` endpoints using `endpoint`
- `range` endpoints using `start_ip` and `end_ip`

It generates:

- `generated_inventory_yaml`
- `generated_inventory_json`
- `generated_inventory_endpoints_json`

### Per-host execution

The remaining grains run against `endpoints` in generated inventory and use host vars such as:

- `endpoint`
- `location`

Shared per-run data is carried in generated inventory `all.vars` as:

- `desired_credentials`
- `default_credentials`
- `location` when provided

### Torque-safe aggregation

Each execution grain has:

- a host execution play
- a localhost aggregation play

The aggregation play exports stable JSON/string outputs for the next grain and for the
Torque UI.

`claim_to_intersight` also performs the endpoint-side claim-readiness lookup immediately
before claim submission so the main onboarding path does not need a separate claim-info grain.
In the modular variant, the actual claim submission is handled by a local custom module that
reuses Cisco's official Intersight module utilities for HTTP signing and REST calls.

## Security model

- endpoint credentials remain scoped to the run and are shared only across the selected endpoint group
- Intersight credentials are passed at the blueprint level
- helpers and API tasks use `no_log: true` or conditional no-log behavior where secrets may
  appear
- normal runs keep `debug_enabled: "false"`
- Device Connector session-based helpers now perform explicit logout for IMM-style
  sessions to reduce stale session buildup on the endpoint
- the modular claim path keeps the user-facing scope as `organization`; if organization-aware
  claim enforcement is used, the implementation may reuse or create a same-name Resource Group
  internally and create a reservation without exposing Resource Group as a launch input

## Destroy model

The claim grain owns destroy behavior.

Current options:

- `destroy_behavior: noop`
- `destroy_behavior: unclaim_input_targets`

`unclaim_input_targets` is implemented and has been validated for the tested IMC path when the regional Intersight API endpoint is used together with asynchronous post-delete verification.

## Known design boundaries

- IMC-focused validation is strongest today
- IMM-style Device Connector claim flows are supported, but some endpoints have shown
  intermittent `POST /Login` instability even with valid credentials; treat that as an
  endpoint-side service health concern before treating it as an automation-side credential bug
- forward claim path is validated for both single-host and small-batch runs
- destroy is now validated for the tested IMC path, though broader endpoint and org-scope coverage is still worth extending.
- the modular variant intentionally favors official `cisco.intersight` collection usage where
  it works and adds custom code only for the claim gap
