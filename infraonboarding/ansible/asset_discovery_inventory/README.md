# asset_discovery_inventory

Production-ready inventory builder grain for the inventory-first endpoint onboarding workflow.

## Expected host groups

- `localhost`

## Required vars

- `endpoints_json` (blueprint title: `Endpoints JSON`)
- `desired_credentials_json` (blueprint title: `Desired Endpoint Credentials JSON`)

`endpoints_json` must be a JSON array where every item includes:
- `type: "single"` with `endpoint`
- or `type: "range"` with `start_ip` and `end_ip`

## Optional vars

- `factory_credentials_json` (blueprint title: `Factory Credentials JSON`)
- `debug_enabled` (blueprint title: `Enable Debug Mode`)
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
      - endpoints_json: '{{ .inputs.endpoints_json }}'
      - desired_credentials_json: '{{ .inputs.desired_credentials_json }}'
      - location: '{{ .inputs.location }}'
      - factory_credentials_json: '{{ .inputs.factory_credentials_json }}'
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
