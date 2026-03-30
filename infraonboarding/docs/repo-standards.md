# Repo Standards

## Purpose

This repo uses inventory-first Ansible grains and a Torque blueprint for Cisco IMC to Intersight Phase 1 workflows.

These standards capture the conventions we want contributors to follow in this repo.

## Grain layout

Within the project folder, each grain lives under:

- `ansible/<grain-name>/`

Each grain should include:

- `playbook.yaml` as the primary entrypoint
- optional `<grain-name>.yaml` compatibility wrapper when needed during migration
- `teardown.yaml`
- `requirements.yaml` when collections are required
- `README.md`
- `roles/` and `tools/` as needed

## Blueprint conventions

- use `spec_version: 2`
- keep one grain per meaningful automation unit
- use `depends-on` only when order truly matters
- keep launch-form inputs minimal and user-facing
- prefer stable output names once downstream grains depend on them
- wire destroy behavior through `on-destroy` using original blueprint inputs where possible

## Input contract rules

- use `snake_case` for all input and output names
- prefer string-safe contracts at the Torque boundary
- pass arrays and objects as JSON strings
- normalize boolean-like strings inside playbooks
- avoid exposing scratch paths or internal-only values in the blueprint

## Ansible rules

- start YAML files with `---`
- use valid YAML indentation and list formatting
- use `ansible.builtin.*` fully qualified names where applicable
- use `gather_facts: false` for controller-side API workflows unless facts are needed
- use `connection: local` for API-driven grains
- use `any_errors_fatal: true`
- add `pre_tasks` validation with `ansible.builtin.assert`
- add explicit output validation before exporting critical outputs
- mark read-only tasks with `changed_when: false`
- protect secrets with `no_log: true` or conditional `no_log`
- parameterize configurable values with variables and sensible defaults
- keep playbooks runnable both locally and in Torque

## Hosts and inventory

- do not ship static inventory files in the repo
- use generated inventory for runtime host context
- use the host group pattern:
  - `hosts: "{{ group | default('<expected_group>') }}"`
- use `localhost` only when the grain is intentionally controller-only

## Output rules

- export outputs with `torque.collections.export_torque_outputs`
- export from `localhost`
- use `delegate_to: localhost`
- use `run_once: true`
- use `ignore_errors: true` for graceful standalone execution
- keep exported outputs stable and meaningful
- prefer aggregate JSON/string outputs for Torque chaining

## Destroy behavior

- include `teardown.yaml` when the grain creates, claims, or mutates managed state
- keep destroy behavior conservative by default
- prefer original blueprint inputs during destroy instead of fragile runtime-only grain outputs
- document destroy assumptions and limitations in the grain README

## Cisco and Intersight guidance

- keep CIMC or endpoint-side login/query/mutate logic separate from Intersight-side claim logic
- use explicit API paths and predictable verification steps
- document regional API endpoint requirements when observed in practice
- prefer asynchronous verification when the platform behavior is eventually consistent

## Python guidance

- keep Python narrow and focused
- prefer custom Ansible modules over standalone scripts for Intersight-side gaps
- keep loops, orchestration, and aggregation in Ansible whenever practical
- reuse official Cisco Intersight module utilities for signing and REST calls when building custom modules
- follow the detailed guidance in [Python Standards](./python-standards.md)

## Documentation expectations

Each grain README should document:

- expected host groups
- required vars
- optional vars
- outputs
- tags
- teardown behavior
- a blueprint snippet

Top-level docs should cover:

- architecture
- contracts
- migration notes
- lifecycle caveats such as unclaim behavior
- Python standards when custom helpers or modules are part of the design
