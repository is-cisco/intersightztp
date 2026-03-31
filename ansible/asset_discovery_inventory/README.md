# asset_discovery_inventory

Production-ready inventory builder grain for the inventory-first Phase 1 workflow.

## Expected host groups

- `localhost`

## Required vars

- `endpoints`
- `credentials`

`endpoints` must be a JSON array where every item includes:
- `type: "single"` with `endpoint`
- or `type: "range"` with `start_ip` and `end_ip`

## Optional vars

- `default_credentials`
- `debug_enabled`
- `group`

## Outputs

- `generated_inventory_yaml`
- `generated_inventory_json`
- `generated_inventory_endpoints_json`

## Tags

- `always`
- `validate`
- `precheck`
- `inventory`
- `outputs`
- `verify`

## Teardown behavior

- `teardown.yaml` is a no-op
- exports `destroy_status` and `destroy_results_json`

## Blueprint grain snippet

```yaml
asset_discovery_inventory:
  kind: ansible
  spec:
    source:
      store: intersightztp
      path: infraonboarding/ansible/asset_discovery_inventory/playbook.yaml
    inventory-file:
      localhost:
        hosts:
          localhost:
    inputs:
      - endpoints: '{{ .inputs.endpoints }}'
      - credentials: '{{ .inputs.credentials }}'
      - location: '{{ .inputs.location }}'
      - default_credentials: '{{ .inputs.default_credentials }}'
      - debug_enabled: '{{ .inputs.debug_enabled }}'
    outputs:
      - generated_inventory_yaml
      - generated_inventory_json
      - generated_inventory_endpoints_json
  on-destroy:
    - source:
        store: intersightztp
        path: infraonboarding/ansible/asset_discovery_inventory/teardown.yaml
      inventory-file:
        localhost:
          hosts:
            localhost:
```
