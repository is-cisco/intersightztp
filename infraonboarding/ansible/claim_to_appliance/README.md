# claim_to_appliance

Production-ready direct appliance claim grain for the inventory-first endpoint onboarding workflow.

## Expected host groups

- `localhost`

## Required vars

- grain inputs:
  - `appliance_claim_candidates_json`
  - `api_key_id`
  - `api_private_key`
  - `api_uri`

## Optional vars

- `organization`
- `validate_certs`
- `debug_enabled`
- `group`

## Notes

- this grain performs direct claim against an Intersight appliance using `/appliance/DeviceClaims`
- it normalizes appliance responses into the same aggregate status shape used by the SaaS claim grain
- after claim submission, it performs a second-pass lookup against `/workflow/WorkflowInfos` to log matching appliance workflow records for each submitted endpoint
- this implementation does not yet wait for workflow completion; it keeps SaaS-style `submitted` claim status and exposes workflow progress as supplemental fields in `results_json`
- execution is split into three plays:
  - a localhost inventory-shaping pass that builds a dynamic claim target group
  - a per-host claim submission pass that uses inventory vars for endpoint-specific data
  - a localhost aggregation pass that enriches results with workflow data and exports stable Torque outputs

## Outputs

- `batch_status`
- `successful_endpoints`
- `failed_endpoints`
- `conflict_endpoints`
- `non_intersight_managed_targets`
- `skipped_endpoints`
- `changed_endpoints`
- `results_json`
- `workflow_results_json`

## Tags

- `always`
- `validate`
- `precheck`
- `claim`
- `verify`
- `aggregate`
- `outputs`

## Teardown behavior

- `teardown.yaml` is a no-op
- exports `destroy_status` and `destroy_results_json`

## Blueprint grain snippet

```yaml
claim_to_appliance:
  kind: ansible
  depends-on: platform_type_resolve
  spec:
    source:
      store: intersightztp
      path: infraonboarding/ansible/claim_to_appliance/playbook.yaml
    inventory-file:
      localhost:
        hosts:
          localhost:
    inputs:
      - appliance_claim_candidates_json: '{{ .grains.platform_type_resolve.outputs.appliance_claim_candidates_json }}'
      - api_key_id: '{{ .inputs.api_key_id }}'
      - api_private_key: '{{ .inputs.api_private_key }}'
      - api_uri: '{{ .inputs.api_uri }}'
      - organization: '{{ .grains.validate_target_org.outputs.org_name }}'
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
      - workflow_results_json
```
