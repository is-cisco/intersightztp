# devicesreadiness

Modular product-folder layout for the device readiness workflow.

## Layout

- `ansible/devices_readiness/playbook.yaml`
- `ansible/devices_readiness/teardown.yaml`
- `ansible/devices_readiness/requirements.yaml`
- `ansible/devices_readiness/README.md`

## Goal

Keep the repo structure aligned with the modular onboarding pattern so Torque blueprints reference grains under a product folder such as `devicesreadiness/ansible/...` instead of placing the grain directly at the repository root.

## Blueprint entrypoint

The main blueprint uses:

- `devicesreadiness/ansible/devices_readiness/playbook.yaml`
- `devicesreadiness/ansible/devices_readiness/teardown.yaml`
