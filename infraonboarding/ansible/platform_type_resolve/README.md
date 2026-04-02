# platform_type_resolve

Production-ready appliance platform resolution grain for the inventory-first endpoint onboarding workflow.

## Expected host groups

- `localhost`

## Required vars

- grain inputs:
  - `generated_inventory_json`
  - `password_reset_ready_endpoints_json`
  - `discovery_results_json`
- generated inventory host data:
  - `endpoint`
  - shared run-scoped `desired_credentials`

## Optional vars

- `debug_enabled`
- `group`

## Notes

- this first implementation resolves standalone endpoint types discovered as `imc` or `imm` to appliance `PlatformType` `IMCRack`
- endpoints whose platform cannot yet be resolved are marked failed with `platform_type_unresolved`
- logical-target dedup is applied at this stage so later appliance claim work can act on one canonical target per normalized key
- execution is split into three plays:
  - a localhost inventory-shaping pass that builds a dynamic endpoint group
  - a per-host resolution pass that evaluates one endpoint at a time using inventory vars
  - a localhost aggregation pass that deduplicates logical targets and exports stable Torque outputs

## Outputs

- `platform_resolution_results_json`
- `appliance_claim_candidates_json`

## Tags

- `always`
- `validate`
- `precheck`
- `resolve`
- `verify`
- `aggregate`
- `outputs`

## Teardown behavior

- `teardown.yaml` is a no-op
- exports `destroy_status` and `destroy_results_json`

## Blueprint grain snippet

```yaml
platform_type_resolve:
  kind: ansible
  depends-on: check_and_reset_default_password
  spec:
    source:
      store: intersightztp
      path: infraonboarding/ansible/platform_type_resolve/playbook.yaml
    inventory-file:
      localhost:
        hosts:
          localhost:
    inputs:
      - generated_inventory_json: '{{ .grains.asset_discovery.outputs.generated_inventory_json }}'
      - password_reset_ready_endpoints_json: '{{ .grains.check_and_reset_default_password.outputs.password_reset_ready_endpoints_json }}'
      - discovery_results_json: '{{ .grains.asset_discovery.outputs.discovery_results_json }}'
      - debug_enabled: '{{ .inputs.debug_enabled }}'
    outputs:
      - platform_resolution_results_json
      - appliance_claim_candidates_json
```
