# Migration

## Source repos

Active implementation:

- `/Users/rkrishn2/Documents/endpoint_onboarding`

Reference-only source:

- `/Users/rkrishn2/Documents/JustPlanning`

## What changed

### Before

The older Phase 1 flow relied heavily on JSON list handoffs between grains.

Characteristics:

- target lists passed as JSON between grains
- credentials passed as JSON between grains
- more helper-driven batch behavior
- less natural Ansible host scoping

### Now

The new flow uses generated inventory after the launch boundary.

Characteristics:

- launch inputs are still JSON strings
- only the first grain parses and expands them
- downstream grains run per host using generated inventory
- aggregation still happens for Torque outputs

## Grain mapping

### Old direction

- `asset_discovery`
- `device_connector_prepare`
- `claim_to_intersight`

### New direction

- `asset_discovery_inventory`
- `check_and_reset_default_password`
- `device_connector_prepare`
- `claim_to_intersight`

## New major behavior

### Password normalization grain

`check_and_reset_default_password` is now an explicit phase in the workflow.

It separates:

- desired credentials
- default/factory credentials

This keeps the claim flow cleaner and makes first-boot behavior easier to reason about.

### Generated inventory contract

Instead of handing a discovered target list to every grain, the first grain builds:

- `endpoints`
- host vars for credentials and metadata

### Aggregation pattern

Each execution grain now has:

- per-host execution
- localhost aggregation

This gives Torque stable outputs without keeping the whole implementation in “batch helper”
mode.

## What was intentionally preserved

- JSON string inputs at the Torque boundary
- aggregate outputs for Torque chaining
- helper-based protocol handling where IMC/IMM behavior is awkward in pure Ansible
- conservative destroy semantics

## What was intentionally not backported

Per user direction:

- `JustPlanning` remains reference only
- active changes go only into `endpoint_onboarding`
