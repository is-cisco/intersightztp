# Architecture

## Overview

`endpoint_onboarding` is an inventory-first endpoint onboarding workflow for claiming Cisco endpoints
into Cisco Intersight.

The design keeps the Torque launch contract simple while shifting execution toward more
idiomatic Ansible:

- launch-time inputs remain JSON strings
- the first grain converts those JSON strings into generated inventory
- downstream grains run per host against that generated inventory
- each grain still exports stable aggregate outputs for Torque chaining
- the modular claim path keeps batch looping in Ansible and moves only the missing
  organization-aware claim behavior into a narrow custom module

## Blueprint entrypoints

Preferred Torque entrypoints:

- [blueprints/onboard_endpoints_intersight_saas.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_intersight_saas.yaml)
- [blueprints/onboard_endpoints_intersight_appliance.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_intersight_appliance.yaml)

The older combined blueprint remains in the repo as an experimental reference. The mechanism-split blueprints also remain available for later work:

- [blueprints/onboard_endpoints_device_connector.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_device_connector.yaml)
- [blueprints/onboard_endpoints_credential_targets.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_credential_targets.yaml)

## Grain sequence

SaaS path:

1. `asset_discovery`
2. `check_and_reset_default_password`
3. `device_connector_prepare`
4. `claim_to_intersight`

Appliance path:

1. `asset_discovery`
2. `check_and_reset_default_password`
3. `device_connector_prepare`
4. `platform_type_resolve`
5. `claim_to_appliance`

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

- `endpoints_json` (`Endpoints JSON`)
- `desired_credentials_json` (`Desired Endpoint Credentials JSON`)
- `location` (`Location`)
- `factory_credentials_json` (`Factory Credentials JSON`)
- `organization` (`Intersight Organization`)
- Intersight authentication inputs (`Intersight API Key ID`, `Intersight Private Key`, and `Intersight API URI`)

Current entrypoint heuristic:

- use the SaaS blueprint for `.intersight.com` claim flows
- use the appliance blueprint for appliance API claim flows
- keep the mechanism-split blueprints for later work

### Inventory shaping

`asset_discovery` expands:

- `single` endpoints using `endpoint`
- `range` endpoints using `start_ip` and `end_ip`

It generates:

- `generated_inventory_yaml`
- `generated_inventory_json`
- `generated_inventory_endpoints_json`

### Per-host execution

The remaining grains run against `endpoints` in generated inventory and keep the
per-host contract intentionally small. Downstream execution grains should consume
plain literal host data rather than wrapper expressions.

Typical per-host data:

- `endpoint`
- `location` when that grain actually needs it
- `reservation` for the appliance claim path

Shared per-run data is carried in generated inventory `all.vars` as:

- `desired_credentials`
- `default_credentials`
- `organization`

Implementation note:

- the endpoint task path now avoids re-reading per-host variables back from
  themselves with `default(...)` chains, which prevents recursive templating
  failures in Torque runtime workspaces

### Torque-safe aggregation

Each execution grain has:

- a host execution play
- a localhost aggregation play

The aggregation play exports stable JSON/string outputs for the next grain and for the
Torque UI.

`claim_to_intersight` performs the endpoint-side claim-readiness lookup immediately
before claim submission so the SaaS path does not need a separate claim-info grain.

`claim_to_appliance` keeps the appliance path inside the same onboarding phase:

- `platform_type_resolve` prepares appliance claim candidates and deduplicates logical targets
- `claim_to_appliance` submits direct appliance claim requests
- `claim_to_appliance` omits `RequestId` so the appliance generates a unique request identifier for each submission
- the grain then does a second workflow lookup pass against `/workflow/WorkflowInfos`
- workflow state is exposed as supplemental result detail without changing the top-level SaaS-style claim status semantics

In the modular variant, the actual claim submission is handled by narrow local custom code only
for behaviors that are not covered cleanly by the official collection.

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
- appliance claim candidates may also carry reservation information so appliance claim scoping stays symmetric with the SaaS model

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
- appliance credential claim is the current recommended CVA or PVA path; appliance Device Connector token claim remains later work
- appliance claim currently reports submission plus newest workflow state; it does not wait for terminal workflow completion inside the onboarding grain
- destroy is now validated for the tested IMC path, though broader endpoint and org-scope coverage is still worth extending.
- the modular variant intentionally favors official `cisco.intersight` collection usage where
  it works and adds custom code only for the claim gap
