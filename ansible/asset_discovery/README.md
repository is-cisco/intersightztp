# asset_discovery

Asset discovery grain for the modular onboarding flow.

This grain expands the incoming endpoint definitions, performs a lightweight
TCP 443 reachability probe, and exports a filtered generated inventory for the
downstream endpoint-touching grains.

Primary entrypoint:

- `ansible/asset_discovery/playbook.yaml`
- `infraonboarding/ansible/asset_discovery/playbook.yaml`

## Inputs

- `endpoints`
- `credentials`
- `default_credentials`
- `location`
- `organization`
- `debug_enabled`

## Outputs

- `generated_inventory_yaml`
- `generated_inventory_json`
- `generated_inventory_endpoints_json`
- `discovered_targets_json`
- `discovery_results_json`
- `total_targets`
- `discovered_targets`
- `non_intersight_managed_targets`
- `failed_targets`

## Notes

- This modular variant currently uses TCP 443 reachability as the discovery
  gate.
- Downstream grains only receive endpoints that passed the discovery probe.
