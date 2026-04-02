# check_and_reset_default_password

Production-ready IMC password normalization grain for the inventory-first endpoint onboarding workflow.

## Expected host groups

- `localhost`

## Required vars

- grain inputs:
  - `generated_inventory_json`
- generated inventory host data:
  - `endpoint`
  - shared run-scoped `desired_credentials`
  - shared run-scoped `default_credentials`

## Optional vars

- `operation_timeout_seconds`
- `debug_enabled`
- `group`

## Outputs

- `password_reset_results_json`
- `password_reset_ready_endpoints_json`
- `password_reset_failed_endpoints_json`
- `password_reset_ready_count`
- `password_reset_failed_count`

## Tags

- `always`
- `validate`
- `precheck`
- `reset`
- `verify`
- `aggregate`
- `outputs`

## Teardown behavior

- `teardown.yaml` is a no-op
- exports `destroy_status` and `destroy_results_json`

## Blueprint grain snippet

```yaml
check_and_reset_default_password:
  kind: ansible
  depends-on: asset_discovery
  spec:
    source:
      store: intersightztp
      path: infraonboarding/ansible/check_and_reset_default_password/playbook.yaml
    inventory-file:
      localhost:
        hosts:
          localhost:
    inputs:
      - generated_inventory_json: '{{ .grains.asset_discovery.outputs.generated_inventory_json }}'
      - debug_enabled: '{{ .inputs.debug_enabled }}'
    outputs:
      - password_reset_results_json
      - password_reset_ready_endpoints_json
      - password_reset_failed_endpoints_json
      - password_reset_ready_count
      - password_reset_failed_count
  on-destroy:
    - source:
        store: intersightztp
        path: infraonboarding/ansible/check_and_reset_default_password/teardown.yaml
      inventory-file:
        localhost:
          hosts:
            localhost:
```
