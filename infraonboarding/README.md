# endpoint_onboarding

Inventory-first endpoint onboarding workflow for claiming Cisco endpoints into Intersight.
This modular variant keeps the stable workflow shape but refactors the claim path
toward a narrower custom-module design.

## Goal

This repo replaces the older JSON batch handoff model with an inventory-driven Ansible flow.
The blueprint still accepts JSON launch inputs, but it converts them into generated inventory and
then runs the rest of the workflow per host.

## Blueprint entrypoints

Preferred Torque entrypoints:

- [blueprints/onboard_endpoints_intersight_saas.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_intersight_saas.yaml)
- [blueprints/onboard_endpoints_intersight_appliance.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_intersight_appliance.yaml)

Use the split onboarding blueprints for Torque launches:

- [blueprints/onboard_endpoints_intersight_saas.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_intersight_saas.yaml)
- [blueprints/onboard_endpoints_intersight_appliance.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_intersight_appliance.yaml)

The mechanism-split blueprints remain in the repo for later work:

- [blueprints/onboard_endpoints_device_connector.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_device_connector.yaml)
- [blueprints/onboard_endpoints_credential_targets.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_credential_targets.yaml)

## Validated flow

For SaaS runs:

1. `validate_target_org`
2. `asset_discovery`
3. `check_and_reset_default_password`
4. `device_connector_prepare`
5. `claim_to_intersight`

For appliance runs:

1. `validate_target_org`
2. `asset_discovery`
3. `check_and_reset_default_password`
4. `device_connector_prepare`
5. `platform_type_resolve`
6. `claim_to_appliance`

## Recommended launch pattern

For SaaS:

- use the SaaS blueprint
- use the `.intersight.com` API URI
- let the workflow retrieve device identifiers and security tokens from the endpoints

For appliance:

- use the appliance blueprint
- use the appliance API URI
- use the appliance credential claim path
- leave the appliance Device Connector token path for later work

Mode detail for the credential-target path:

1. `validate_target_org`
2. `asset_discovery`
3. `check_and_reset_default_password`
4. `platform_type_resolve`
5. `claim_to_appliance`
## Most users only need these inputs

- `agent` (`Torque Agent`)
- `endpoints_json` (`Endpoints JSON`)
- `desired_credentials_json` (`Desired Endpoint Credentials JSON`)
- `location`
- `api_key_id` (`Intersight API Key ID`)
- `api_private_key` (`Intersight Private Key`)

Advanced inputs:

- `factory_credentials_json` (`Factory Credentials JSON`)
- `api_uri` (`Intersight API URI`)
- `organization` (`Intersight Organization`)
- `destroy_behavior` (`Destroy Behavior`)
- `debug_enabled` (`Enable Debug Mode`)

## Copy-paste examples

### Single target `endpoints_json`

```json
[
  {
    "type": "single",
    "endpoint": "10.29.135.107"
  }
]
```

### Range `endpoints_json`

```json
[
  {
    "type": "range",
    "start_ip": "10.29.135.107",
    "end_ip": "10.29.135.109"
  }
]
```

### Optional global `location`

```text
SJC-DC1 / Row-A
```

Endpoints may override `location` individually when finer-grained placement is needed later.

### Desired `desired_credentials_json` (`Desired Endpoint Credentials JSON`)

```json
[
  {
    "username": "admin",
    "password": "Nbv!2345",
    "priority": 1
  }
]
```

### Optional `factory_credentials_json` (`Factory Credentials JSON`)

```json
[
  {
    "username": "admin",
    "password": "password",
    "priority": 1
  }
]
```

## Current behavior

- builds a generated inventory from `endpoints_json`
- stores desired and factory/default credentials as run-scoped generated inventory vars
- applies an optional run-level `location` to all endpoints unless an endpoint overrides it
- checks whether the desired password already works before attempting a reset
- for SaaS runs, prepares connector state per host
- for SaaS runs, retrieves claim serials and tokens inside the claim grain only for hosts that need claim submission
- for SaaS runs, submits claims and verifies `asset.DeviceRegistrations`
- for appliance runs, resolves `platform_type`, submits direct appliance claim requests, and records the newest matching `Device registration request` workflow in the result contract
- for appliance runs, omits `RequestId` from the claim payload so the appliance generates a unique value per request
- carries `organization` as the user-facing scope input for claim
- uses narrow local custom Ansible code only where the official collection does not cover the required claim behavior
- supports optional destroy-time unclaim for the tested IMC path

## Validated scenarios

- single IMC host already claimed
- single IMC host ready for claim and successfully claimed
- mixed batch where some hosts are already claimed and others are submitted in the same run
- appliance claim submission with workflow lookup and workflow-aware result enrichment
- appliance batch submission validated with five fresh `DeviceClaim` records in one run after removing the caller-supplied `RequestId`
- tested IMC unclaim path using the regional Intersight API endpoint and asynchronous verification

## Runtime dependencies

Python packages for the endpoint-side helper scripts, custom claim module support, and Intersight PEM handling:

```bash
python3 -m pip install -r infraonboarding/ansible/requirements.txt
```

Ansible collections:

```bash
ansible-galaxy collection install -r infraonboarding/ansible/claim_to_intersight/requirements.yaml
```

## Additional design documentation

- [Architecture](./docs/architecture.md)
- [Contracts](./docs/contracts.md)
- [Migration](./docs/migration.md)
- [Unclaim Status](./docs/unclaim-status.md)
- [Repo Standards](./docs/repo-standards.md)
- [Python Standards](./docs/python-standards.md)
- [Checklist](./docs/checklist.md)

## Design direction

- generated inventory for discovered endpoints
- run-scoped desired and default credentials for the endpoint group
- endpoint loop orchestration stays in Ansible
- custom Python is kept narrow and focused on missing Intersight API behaviors
- more idiomatic Ansible execution per host
