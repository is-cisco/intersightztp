# Contracts

## Blueprint inputs

### `agent`

- type: `string`
- required: yes
- meaning: Torque agent used to run all grains

### `endpoints`

- type: `string`
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

### `credentials`

- type: `string`
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
- required: no
- default: `""`
- meaning: optional default location for the endpoint group in this run; individual endpoints may override it later if needed

### `default_credentials`

- type: `string`
- required: no
- default: `"[]"`
- meaning: optional factory/default credentials for first-boot password normalization in this endpoint group

### `api_key_id`

- type: `string`
- required: yes for claim stage

### `api_private_key`

- type: `string`
- required: yes for claim stage

### `api_uri`

- type: `string`
- default: `"https://intersight.com/api/v1"`

### `organization`

- type: `string`
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
- default: `"noop"`
- allowed values:
  - `noop`
  - `unclaim_input_targets`

### `debug_enabled`

- type: `string`
- default: `"false"`

## Grain outputs

### `asset_discovery_inventory`

- `generated_inventory_yaml`
- `generated_inventory_json`
- `generated_inventory_endpoints_json`

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
