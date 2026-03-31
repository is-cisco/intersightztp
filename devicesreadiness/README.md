# Discovery Readiness

This repository contains a Torque-compatible Ansible bundle for validating Cisco Intersight device readiness.

## Main Bundle

- `ansible/devices_readiness/playbook.yaml`
- `ansible/devices_readiness/teardown.yaml`
- `ansible/devices_readiness/requirements.yaml`
- `ansible/devices_readiness/tasks/evaluate_devices.yaml`
- `ansible/devices_readiness/tasks/check_readiness_pass.yaml`
- `ansible/devices_readiness/tasks/validate_fi_pair.yaml`
- `blueprints/devices_readiness.yaml`

## Main Documentation

- `ansible/devices_readiness/README.md`

The Torque blueprint points to the grain bundle directory at `ansible/devices_readiness`. In this layout, Torque uses `playbook.yaml` as the default run entrypoint and `teardown.yaml` for destroy behavior.

## Purpose

The bundle validates that requested devices are:

- present in Cisco Intersight
- ready according to category-specific readiness rules
- correctly paired for Fabric Interconnect A/B entities
- optionally polled until ready when discovery is still in progress

Current readiness defaults:

- `Rack`: present in `/compute/PhysicalSummaries` and matches the rack readiness rule
- `Blade`: present in `/compute/PhysicalSummaries` and `Lifecycle == Active`
- `Chassis`: present in `/equipment/Chasses`
- `FabricInterconnectPair`: both FI serials are present in `/network/Elements`, share the same `DeviceMoId`, and resolve to `SwitchId` `A` and `B`

## Supported Categories

- `Rack`
- `Blade`
- `Chassis`
- `FabricInterconnectPair`

## Preferred Input Format

The preferred runtime input is YAML passed through `devices_yaml`.

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

There are no Python source files in this bundle today. The maintained files are the Ansible playbooks, task includes, blueprint, and README documents. We can revisit structure and naming later if the logic grows.

## Readiness Modes

- `wait_for_readiness: "false"` runs a single readiness check
- `wait_for_readiness: "true"` keeps polling until all devices are ready or the max-attempt limit is reached

Key polling inputs:

- `readiness_poll_interval`
- `readiness_max_attempts`
