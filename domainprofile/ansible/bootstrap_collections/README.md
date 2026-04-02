# Bootstrap Collections Grain

This helper grain installs the Ansible collections required by the domain
profile workflows on the executing Torque worker before the main grains run.

It uses the shared repository file:

- `ansible/requirements.yaml`

Current collections:
- `cisco.intersight`
- `torque.collections`

The playbook uses only built-in Ansible modules so it can run before those
collections are present.
