# validate_target_org

Run-level grain that ensures a requested Intersight organization exists before claim.

## Expected host groups

- `localhost`

## Required vars

- `api_key_id`
- `api_private_key`

## Optional vars

- `organization`
- `api_uri`
- `validate_certs`
- `debug_enabled`
- `group`

## Outputs

- `org_status`
- `org_name`
- `org_action`
- `org_result_json`

## Tags

- `always`
- `validate`
- `precheck`
- `configure`
- `verify`
- `outputs`

## Teardown behavior

This grain does not delete organizations. `teardown.yaml` is a no-op.

## Blueprint grain snippet

```yaml
validate_target_org:
  kind: ansible
  spec:
    source:
      store: automation-repo
      path: infraonboarding/ansible/validate_target_org/playbook.yaml
    inventory-file:
      localhost:
        hosts:
          localhost:
    inputs:
      - organization: '{{ .inputs.organization }}'
      - api_key_id: '{{ .inputs.api_key_id }}'
      - api_private_key: '{{ .inputs.api_private_key }}'
      - api_uri: '{{ .inputs.api_uri }}'
      - validate_certs: 'false'
      - debug_enabled: '{{ .inputs.debug_enabled }}'
    outputs:
      - org_status
      - org_name
      - org_action
      - org_result_json
```
