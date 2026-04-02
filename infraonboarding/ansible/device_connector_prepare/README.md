# device_connector_prepare

Production-ready connector preparation grain for the inventory-first endpoint onboarding workflow.

## Expected host groups

- `localhost`

## Required vars

- grain inputs:
  - `generated_inventory_json`
  - `password_reset_ready_endpoints_json`
- generated inventory host data:
  - `endpoint`
- shared run-scoped data:
  - `desired_credentials`

## Optional vars

- `operation_timeout_seconds`
- `debug_enabled`
- `group`

## Notes

- the helper currently tries the XML `/nuova` path first and then the Device Connector
  session path at `/Login`
- for IMM-style Device Connector sessions, the helper now carries:
  - `sessionId`
  - `DeviceConsolecookie`
  - `X-CSRF-Token` when returned by the endpoint
- the helper now performs an explicit `POST /Logout` before closing IMM sessions
- intermittent `/Login` failures such as `401 Invalid Character` have been observed on
  some endpoints even when credentials are valid; in practice this has behaved like a
  Device Connector service health issue rather than a deterministic credential failure
- execution is split into three plays:
  - a localhost inventory-shaping pass that builds a dynamic connector-preparation group
  - a per-host execution pass that runs the role using a concrete endpoint plus
    run-scoped desired credentials
  - a localhost aggregation pass that exports stable Torque outputs

## Outputs

- `connector_prep_results_json`
- `prepared_endpoints_json`

## Tags

- `always`
- `validate`
- `precheck`
- `prepare`
- `verify`
- `aggregate`
- `outputs`

## Teardown behavior

- `teardown.yaml` is a no-op
- exports `destroy_status` and `destroy_results_json`

## Blueprint grain snippet

```yaml
device_connector_prepare:
  kind: ansible
  depends-on: check_and_reset_default_password
  spec:
    source:
      store: intersightztp
      path: infraonboarding/ansible/device_connector_prepare/playbook.yaml
    inventory-file:
      localhost:
        hosts:
          localhost:
    inputs:
      - generated_inventory_json: '{{ .grains.asset_discovery.outputs.generated_inventory_json }}'
      - password_reset_ready_endpoints_json: '{{ .grains.check_and_reset_default_password.outputs.password_reset_ready_endpoints_json }}'
      - debug_enabled: '{{ .inputs.debug_enabled }}'
    outputs:
      - connector_prep_results_json
      - prepared_endpoints_json
```
