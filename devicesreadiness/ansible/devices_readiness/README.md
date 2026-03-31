# Devices Readiness

Torque-ready Ansible grain that validates requested devices are present in Cisco Intersight and checks whether each device is ready based on category-specific discovery rules.

The grain supports two runtime modes:

- one-time readiness check
- wait for readiness by polling until devices are discovered or the attempt limit is reached

## Expected Host Groups

- Default runtime host group: `localhost`
- Overrideable host group variable: `group`
- The playbooks use `hosts: "{{ group | default('localhost') }}"` and `connection: local`

## Files

- `ansible/devices_readiness/playbook.yaml`
- `ansible/devices_readiness/teardown.yaml`
- `ansible/devices_readiness/requirements.yaml`
- `ansible/devices_readiness/tasks/evaluate_devices.yaml`
- `ansible/devices_readiness/tasks/check_readiness_pass.yaml`
- `ansible/devices_readiness/tasks/validate_fi_pair.yaml`

For Torque, the blueprint points to the bundle directory `ansible/devices_readiness`. The `kind: ansible` grain uses `playbook.yaml` in that directory as the default run entrypoint, and `teardown.yaml` is referenced explicitly for `on-destroy`.

## Required Variables

- `api_key_id`: Cisco Intersight API key ID
- `api_private_key`: Cisco Intersight private key content or a readable path
- `devices_yaml` or `devices_json`: one structured device payload is required

## Optional Variables

- `api_uri`: Intersight API base URI
  Default: `https://intersight.com/api/v1`
- `validate_certs`: boolean-like string
  Default: `true`
- `category_rules_json`: JSON object overriding category endpoints and readiness rules
- `api_request_timeout`: task timeout for API requests in seconds
  Default: `60`
- `wait_for_readiness`: boolean-like string
  Default: `false`
- `readiness_poll_interval`: seconds between readiness polls when waiting
  Default: `30`
- `readiness_max_attempts`: maximum poll attempts when waiting
  Default: `20`
- `group`: overrideable target host group

## Preferred Input Contract

Preferred input is YAML passed as a string through `devices_yaml`.

```yaml
devices:
  - category: Rack
    serial: WZP26430BCA

  - category: Blade
    serial: FCH270177BF

  - category: Chassis
    serial: FOX2917PR1U

  - category: FabricInterconnectPair
    serials:
      - FDO272406DE
      - FDO272406CK
```

The playbook normalizes the input into an internal device batch list so future CSV or alternate parsing only needs to change the normalization layer.

That normalization layer is the part we can revisit later if the source format changes to CSV or another ingestion format.

## Legacy Input Contract

Legacy JSON input is still supported through `devices_json`.

```json
[
  {
    "category": "Blade",
    "serial_numbers": ["FCH1234A1BC", "FCH1234A1BD"]
  },
  {
    "category": "Rack",
    "serial_numbers": ["ABC1234D5EF"]
  }
]
```

## Default Readiness Rules

If `category_rules_json` is not supplied, the grain uses these defaults:

- `Blade`
  Endpoint: `/compute/PhysicalSummaries`
  Readiness: `Lifecycle == Active`
- `Rack`
  Endpoint: `/compute/PhysicalSummaries`
  Readiness: `(ManagementMode == IMM and Lifecycle == Active) or ManagementMode == IntersightStandalone`
- `Chassis`
  Endpoint: `/equipment/Chasses`
  Readiness: present in `/equipment/Chasses`
- `FabricInterconnect`
  Endpoint: `/network/Elements`
  Readiness: `Operability == online`
  Pair validation: same `DeviceMoId`, one `SwitchId == A`, one `SwitchId == B`

## Example `category_rules_json`

```json
{
  "Blade": {
    "resource_path": "/compute/PhysicalSummaries",
    "serial_field": "Serial",
    "discovery_field": "Lifecycle",
    "allowed_discovery_states": ["Active"]
  },
  "Rack": {
    "resource_path": "/compute/PhysicalSummaries",
    "serial_field": "Serial",
    "discovery_field": "ManagementMode",
    "allowed_discovery_states": ["IMM", "IntersightStandalone"]
  },
  "Chassis": {
    "resource_path": "/equipment/Chasses",
    "serial_field": "Serial",
    "discovery_field": "Serial",
    "allowed_discovery_states": ["__present__"]
  },
  "FabricInterconnect": {
    "resource_path": "/network/Elements",
    "serial_field": "Serial",
    "discovery_field": "Operability",
    "allowed_discovery_states": ["online"],
    "pair_validation": true
  }
}
```

## Outputs

- `verification_summary_json`: summary payload for the full request
- `verification_success`: `true` or `false`
- `missing_devices_json`: missing device entries
- `invalid_lifecycle_devices_json`: devices that are present but not ready, plus invalid FI pair results

The summary also includes:

- `wait_for_readiness`
- `max_attempts`
- `attempts_executed`
- `last_attempt`

Today the playbook still uses `verification_*` output names for backward compatibility. We can rename those later if you want them to align more closely with `readiness_*`.

## Readiness Modes

Use the default behavior for a one-time check:

```yaml
wait_for_readiness: "false"
```

Use polling when downstream steps must not continue until devices are discovered:

```yaml
wait_for_readiness: "true"
readiness_poll_interval: "30"
readiness_max_attempts: "20"
```

When `wait_for_readiness` is `true`, the grain re-queries Intersight until:

- all requested devices are ready
- or `readiness_max_attempts` is reached

## Tags

- `always`
- `validate`
- `precheck`
- `configure`
- `verify`
- `outputs`

## Teardown Behavior

`teardown.yaml` is a no-op. This grain validates inventory state and does not create or modify remote resources that require cleanup.

## Blueprint Grain Snippet

```yaml
grains:
  devices_readiness:
    kind: ansible
    spec:
      source:
        store: local
        path: ansible/devices_readiness
      inventory-file:
        localhost:
          hosts:
            localhost:
              ansible_connection: local
          vars:
            api_key_id: '{{ .inputs.api_key_id }}'
            api_private_key: '{{ .inputs.api_private_key }}'
            api_uri: '{{ .inputs.api_uri }}'
            validate_certs: '{{ .inputs.validate_certs }}'
      inputs:
        - devices_yaml: '{{ .inputs.devices_yaml }}'
        - devices_json: '{{ .inputs.devices_json }}'
        - category_rules_json: '{{ .inputs.category_rules_json }}'
        - api_request_timeout: '{{ .inputs.api_request_timeout }}'
        - wait_for_readiness: '{{ .inputs.wait_for_readiness }}'
        - readiness_poll_interval: '{{ .inputs.readiness_poll_interval }}'
        - readiness_max_attempts: '{{ .inputs.readiness_max_attempts }}'
      outputs:
        - verification_summary_json
        - verification_success
        - missing_devices_json
        - invalid_lifecycle_devices_json
      on-destroy:
        - path: teardown.yaml
          inventory-file:
            localhost:
              hosts:
                localhost:
                  ansible_connection: local
```
