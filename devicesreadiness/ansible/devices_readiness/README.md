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

- `devicesreadiness/ansible/devices_readiness/playbook.yaml`
- `devicesreadiness/ansible/devices_readiness/teardown.yaml`
- `devicesreadiness/ansible/devices_readiness/requirements.yaml`
- `devicesreadiness/ansible/devices_readiness/tasks/evaluate_devices.yaml`
- `devicesreadiness/ansible/devices_readiness/tasks/check_readiness_pass.yaml`
- `devicesreadiness/ansible/devices_readiness/tasks/validate_fi_pair.yaml`

For Torque, the blueprint should point directly to `devicesreadiness/ansible/devices_readiness/playbook.yaml`. Use `devicesreadiness/ansible/devices_readiness/teardown.yaml` explicitly for `on-destroy` so the runner always receives a concrete playbook file path.

## Required Variables

- `agent`: Torque agent name used by the blueprint to select the runner
- `api_key_id`: Cisco Intersight API key ID
- `api_private_key`: Cisco Intersight private key content or a readable path
- `devices_yaml`: structured device payload is required

## Optional Variables

- `api_uri`: Intersight API base URI
  Default: `https://intersight.com/api/v1`
- `validate_certs`: boolean-like string
  Default: `true`
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

The grain also accepts the same payload when launch tooling sends it as a single string with escaped newline sequences such as `\n`.

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

## Default Readiness Rules

The grain uses these internal defaults:

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

## Outputs

- `readiness_summary_json`: summary payload for the full request
- `readiness_success`: `true` or `false`
- `missing_devices_json`: missing device entries
- `not_ready_devices_json`: devices that are present but not ready, plus invalid FI pair results

The summary also includes:

- `wait_for_readiness`
- `max_attempts`
- `attempts_executed`
- `last_attempt`

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
        store: intersightztp
        path: devicesreadiness/ansible/devices_readiness/playbook.yaml
      agent:
        name: '{{ .inputs.agent }}'
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
        - api_request_timeout: '{{ .inputs.api_request_timeout }}'
        - wait_for_readiness: '{{ .inputs.wait_for_readiness }}'
        - readiness_poll_interval: '{{ .inputs.readiness_poll_interval }}'
        - readiness_max_attempts: '{{ .inputs.readiness_max_attempts }}'
      outputs:
        - readiness_summary_json
        - readiness_success
        - missing_devices_json
        - not_ready_devices_json
    on-destroy:
      - source:
          store: intersightztp
          path: devicesreadiness/ansible/devices_readiness/teardown.yaml
        inventory-file:
          localhost:
            hosts:
              localhost:
                ansible_connection: local
```
