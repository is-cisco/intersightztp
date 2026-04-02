# Contracts

## Blueprint inputs

Preferred Torque entrypoints:

- [blueprints/onboard_endpoints_intersight_saas.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_intersight_saas.yaml)
- [blueprints/onboard_endpoints_intersight_appliance.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_intersight_appliance.yaml)

Use the split onboarding blueprints instead:
[blueprints/onboard_endpoints_intersight_saas.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_intersight_saas.yaml)
and
[blueprints/onboard_endpoints_intersight_appliance.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_intersight_appliance.yaml)

The mechanism-split blueprints also remain available for later work:

- [blueprints/onboard_endpoints_device_connector.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_device_connector.yaml)
- [blueprints/onboard_endpoints_credential_targets.yaml](/Users/rkrishn2/intersightztp/blueprints/onboard_endpoints_credential_targets.yaml)

### `agent`

- type: `agent`
- title: `Torque Agent`
- required: yes
- meaning: Torque agent used to run all grains

### `endpoints_json`

- type: `string`
- title: `Endpoints JSON`
- required: yes
- default: `"[]"`
- meaning: JSON array of target definitions

Example:

```json
[
  {
    "type": "single",
    "endpoint": "10.29.135.107"
  },
  {
    "type": "range",
    "start_ip": "10.29.135.108",
    "end_ip": "10.29.135.109"
  }
]
```

### `desired_credentials_json`

- type: `string`
- title: `Desired Endpoint Credentials JSON`
- required: yes
- default: `"[]"`
- meaning: desired steady-state credentials for the endpoint group in this run

Example:

```json
[
  {
    "username": "admin",
    "password": "Nbv!2345",
    "priority": 1
  }
]
```

### `location`

- type: `string`
- title: `Location`
- required: no
- default: `""`
- meaning: optional default location for the endpoint group in this run; individual endpoints may override it later if needed

### `factory_credentials_json`

- type: `string`
- title: `Factory Credentials JSON`
- required: no
- default: `"[]"`
- meaning: optional factory/default credentials for first-boot password normalization in this endpoint group

### `api_key_id`

- type: `string`
- title: `Intersight API Key ID`
- sensitive: `true`
- required: yes for claim stage

### `api_private_key`

- type: `string`
- title: `Intersight Private Key`
- sensitive: `true`
- required: yes for claim stage

### `api_uri`

- type: `string`
- title: `Intersight API URI`
- meaning: API base URI used for validation and claim operations
- guidance: hosts ending in `.intersight.com` should use the SaaS blueprint; other hosts or raw IPs should use the appliance blueprint

### `organization`

- type: `string`
- title: `Intersight Organization`
- required: no
- default: `""`
- meaning: optional user-facing Intersight organization scope for the claim flow
- note: in the modular claim design this remains the user input even if the implementation
  uses hidden Resource Group and reservation plumbing behind the scenes

### `validate_certs`

- internal-only toggle
- not exposed as a launch input
- defaults to `false` in the current blueprint and Intersight-facing playbooks

### `destroy_behavior`

- type: `string`
- title: `Destroy Behavior`
- default: `"noop"`
- allowed values:
  - `noop`
  - `unclaim_input_targets`

### `debug_enabled`

- type: `string`
- title: `Enable Debug Mode`
- default: `"false"`
- allowed values:
  - `true`
  - `false`

## Grain outputs

### `asset_discovery`

- `generated_inventory_yaml`
- `generated_inventory_json`
- `generated_inventory_endpoints_json`
- `discovery_results_json`

### `check_and_reset_default_password`

- `password_reset_results_json`
- `password_reset_ready_endpoints_json`
- `password_reset_failed_endpoints_json`
- `password_reset_ready_count`
- `password_reset_failed_count`

### `device_connector_prepare`

- `connector_prep_results_json`
- `prepared_endpoints_json`

### `claim_to_intersight`

- `batch_status`
- `successful_endpoints`
- `failed_endpoints`
- `conflict_endpoints`
- `non_intersight_managed_targets`
- `skipped_endpoints`
- `changed_endpoints`
- `results_json`

Implementation note:

- in the modular variant, `claim_to_intersight` uses a local custom Ansible module for claim
  submission instead of relying on `cisco.intersight.intersight_target_claim`

### `platform_type_resolve`

- `platform_resolution_results_json`
- `appliance_claim_candidates_json`

Implementation notes:

- this grain derives appliance `PlatformType` values from discovery results
- it also passes through reservation information when present
- it performs logical-target dedup before appliance claim submission

### `claim_to_appliance`

- `batch_status`
- `successful_endpoints`
- `failed_endpoints`
- `conflict_endpoints`
- `non_intersight_managed_targets`
- `skipped_endpoints`
- `changed_endpoints`
- `results_json`
- `workflow_results_json`

Implementation notes:

- appliance claim uses direct `POST /appliance/DeviceClaims`
- appliance claim intentionally omits `RequestId` so the appliance generates a unique request identifier per claim
- `results_json` keeps the same top-level status contract as SaaS
- `workflow_results_json` exposes the matching `Device registration request` workflow records
- the newest matching workflow is merged back into each appliance result as supplemental fields such as `latest_workflow_status` and `latest_workflow_progress`
- this grain does not yet wait for workflow completion before returning

## Destroy outputs

### No-op teardowns

For non-owning grains:

- `destroy_status`
- `destroy_results_json`

### `claim_to_intersight` teardown

- `destroy_status`
- `destroy_results_json`

Current observed destroy reasons include:

- `noop_destroy_behavior`
- `device_identity_lookup_failed`
- `registration_lookup_failed`
- `device_claim_not_present`
- `unclaim_unauthorized`
- `device_claim_delete_no_change`
- `device_claim_deleted`
- `device_claim_delete_pending`
