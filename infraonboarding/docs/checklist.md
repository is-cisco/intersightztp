# Checklist

Use this checklist before committing changes to `endpoint_onboarding`.

## Grain checklist

- grain path is under `ansible/<grain-name>/`
- main entrypoint is named `<grain-name>.yaml`
- `teardown.yaml` exists
- `requirements.yaml` exists when collections are used
- `README.md` is updated
- YAML is valid and starts with `---`
- `any_errors_fatal: true` is present
- `pre_tasks` input validation exists
- output validation exists before export for critical contracts
- secrets are protected with `no_log` where needed
- read-only tasks use `changed_when: false`
- tags are present and useful
- no static inventory assumptions are introduced

## Torque checklist

- blueprint uses `spec_version: 2`
- blueprint input names stay in `snake_case`
- launch-form inputs are user-facing and minimal
- grain outputs match the exported keys exactly
- `on-destroy` uses original blueprint inputs where possible
- output contracts are stable for downstream grains

## Validation checklist

- syntax-check updated playbooks
- syntax-check updated teardowns
- run targeted smoke tests when behavior changes
- verify destroy behavior separately when teardown changes
- confirm docs match actual observed behavior
