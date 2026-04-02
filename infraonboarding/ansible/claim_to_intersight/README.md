# claim_to_intersight

Production-ready Intersight claim grain for the inventory-first endpoint onboarding workflow.

This grain now retrieves claim readiness just-in-time from prepared endpoints and submits
the claim in the same runtime flow. The modular variant replaces the helper
script claim path with a narrow local Ansible module that reuses the official
Cisco Intersight module utilities for signing and REST calls while adding the
missing organization-aware reservation-backed claim behavior.

Execution is split into three plays:

- a localhost inventory-shaping pass that builds a dynamic SaaS claim target group
- a per-host claim execution pass
- a localhost aggregation pass that exports stable Torque outputs

The per-host claim play currently runs with `serial: 1` so the grain can preserve
logical-target dedup behavior across endpoints before claim submission.

Primary entrypoint:

- `infraonboarding/ansible/claim_to_intersight/playbook.yaml`

Compatibility entrypoint:

- `infraonboarding/ansible/claim_to_intersight/claim_to_intersight.yaml`

## Expected host groups

- `localhost` for inventory shaping and aggregation
- dynamic per-endpoint execution group created at runtime for claim processing

## Required vars

- grain inputs:
  - `generated_inventory_json`
  - `prepared_endpoints_json`
  - `api_key_id`
  - `api_private_key`
- generated inventory host data:
  - `endpoint`

## Optional vars

- `api_uri`
- `organization`
- `validate_certs`
- `endpoint_validate_certs`
- `destroy_behavior`
- `debug_enabled`
- `group`
- `helper_timeout_seconds`
- `unclaim_poll_retries`
- `unclaim_poll_delay_seconds`

## Outputs

- `batch_status`
- `successful_endpoints`
- `failed_endpoints`
- `conflict_endpoints`
- `non_intersight_managed_targets`
- `skipped_endpoints`
- `changed_endpoints`
- `results_json`

## Tags

- `always`
- `validate`
- `precheck`
- `configure`
- `claim`
- `verify`
- `aggregate`
- `outputs`
- `teardown`

## Teardown behavior

- `destroy_behavior: noop`
  - reports a skipped no-op result
- `destroy_behavior: unclaim_input_targets`
  - rebuilds inventory from original launch inputs
  - resolves endpoint serial numbers
  - looks up `asset.DeviceRegistrations`
  - follows the linked `DeviceClaim.Moid`
  - attempts `DELETE` against `asset.DeviceClaims/<moid>`
  - polls registration state until the claim link disappears or timeout expires
  - exports `destroy_status` and `destroy_results_json`

## Blueprint grain snippet

```yaml
claim_to_intersight:
  kind: ansible
  depends-on: device_connector_prepare
  spec:
    source:
      store: intersightztp
      path: infraonboarding/ansible/claim_to_intersight/playbook.yaml
    inventory-file:
      localhost:
        hosts:
          localhost:
    inputs:
      - generated_inventory_json: '{{ .grains.asset_discovery.outputs.generated_inventory_json }}'
      - prepared_endpoints_json: '{{ .grains.device_connector_prepare.outputs.prepared_endpoints_json }}'
      - api_key_id: '{{ .inputs.api_key_id }}'
      - api_private_key: '{{ .inputs.api_private_key }}'
      - api_uri: '{{ .inputs.api_uri }}'
      - organization: '{{ .inputs.organization }}'
      - validate_certs: 'false'
      - debug_enabled: '{{ .inputs.debug_enabled }}'
    outputs:
      - batch_status
      - successful_endpoints
      - failed_endpoints
      - conflict_endpoints
      - non_intersight_managed_targets
      - skipped_endpoints
      - changed_endpoints
      - results_json
```
