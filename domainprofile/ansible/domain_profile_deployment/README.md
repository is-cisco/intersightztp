# Domain Onboarding Grain

This grain is a Torque-ready foundation for Cisco Intersight domain onboarding.
It validates input contracts, discovers FI model details from Intersight by
serial number, reads FI model defaults from the repository, validates customer
port overrides against the discovered model, composes the onboarding payload,
and exports stable outputs for downstream grains or later network-intent
provisioning.

The downstream network intent provisioning companion lives in
`ansible/network_intent_provisioning/`.

The first iteration assumes Ethernet-only port configuration. Fibre Channel,
FCoE, and breakout-specific behavior are intentionally out of scope.
FI model defaults are hardware-only. VLANs, VLAN groups, and solution-specific
uplink intent are now treated as deferred network intent for a separate
provisioning workflow rather than being part of the onboarding deployment path.
Management-global settings such as NTP and DNS are handled in onboarding
through a default domain-policy catalog and can be overridden through
`global_settings`.

## Inputs

All user-facing complex contracts are string-safe for Torque.

- `api_key_id`: Intersight API key ID. Blueprint title: `Intersight API Key ID`
- `api_private_key`: PEM-formatted Intersight API private key content. Blueprint title: `Intersight Private Key`
- `api_uri`: Optional custom Intersight endpoint. Blueprint title: `Intersight API URI`
- `fi_devices_json`: JSON array of FI device objects. Blueprint title: `Fabric Interconnect Devices JSON`
- `deployment_name`: Required deployment prefix used to name all created Intersight policies and profiles. Blueprint title: `Deployment Name`
- `customer_overrides_json`: Optional JSON object for onboarding global settings or port-default overrides. Blueprint title: `Customer Overrides JSON`
- `port_catalog_key`: Optional catalog key under `catalog/domain_profile_ports/` used to load a named customer port layout. Blueprint title: `Port Catalog Key`
- `port_config_yaml`: Optional YAML string for onboarding port-level overrides,
  including `server_ports`, `uplinks`, and `uplink_port_channels`.
  If both `port_catalog_key` and `port_config_yaml` are omitted, the grain can
  fall back to a model-defined default uplink port-channel when the FI model
  provides one. Blueprint title: `Port Config YAML`
- `organization`: Initial deployment context input for Intersight
  organization. This is not sourced from solution intent files. The
  organization must already exist in Intersight; this workflow validates it
  but does not create it. Blueprint title: `Intersight Organization`

The onboarding blueprint is intended for zero-touch deployment, so it always
creates the baseline onboarding stack: switch control policy, System QoS
policy, port policy, switch cluster profile, and A/B switch profiles. Optional
NTP and DNS/network connectivity baseline policies are also created from the
default policy catalog unless overridden through `global_settings`.

The onboarding blueprint does not ask for solution intent selection. Deferred
intent metadata can be supplied later by the network intent provisioning workflow.

## Internal Defaults

- `validate_certs` is not exposed in the blueprint launch form.
  The blueprint passes `false` to the grain.

## Example Inputs

`fi_devices_json`

```json
[
  {
    "name": "fi-a",
    "serial_number": "FDO12345678"
  },
  {
    "name": "fi-b",
    "serial_number": "FDO12345679"
  }
]
```

`customer_overrides_json`

```json
{
  "global_settings": {
    "switch_control": {
      "ethernet_switching_mode": "end-host"
    },
    "ntp": {
      "servers": ["time.example.com"],
      "timezone": "America/Los_Angeles"
    },
    "dns": {
      "enable_ipv4_dns_from_dhcp": false,
      "preferred_ipv4_dns_server": "10.10.10.10",
      "alternate_ipv4_dns_server": "10.10.10.11"
    }
  }
}
```

`port_config_yaml`

```yaml
uplinks:
  - port_id: "1/49"
    role: ethernet-uplink
    speed: 100G
uplink_port_channels:
  - name: core-a
    pc_id: 101
    member_ports: ["1/49", "1/50"]
server_ports:
  - port_id: "1/1"
    role: server
    speed: 25G
```

`port_catalog_key`

```text
example_customer
```

## Outputs

- `validations_passed`
- `solution_intent_resolved`
- `fi_model_resolved`
- `fi_inventory_json`
- `domain_profile_payload_json`
- `uplink_profiles_json`
- `intersight_resource_plan_json`
- `intersight_trace_ids_json`
- `tac_handoff_json`
- `effective_ethernet_uplink_ports_json`
- `effective_ethernet_uplink_port_channels_json`
- `effective_server_ports_json`
- `vlans_json`
- `vlan_groups_json`
- `port_defaults_json`

## Destroy Behavior

`teardown.yaml` removes the onboarding stack in dependency order, including the
switch cluster profile, switch profiles, port policy, and baseline switch
policies including NTP and network connectivity. It also tolerates older runs
that may have created optional SNMP or flow-control policies.

## Repository Defaults

- Solution intents live under `catalog/solution_intents/`.
- Default domain onboarding policy data lives under `catalog/domain_profile_policies/`.
- Optional customer port catalogs live under `catalog/domain_profile_ports/`.
- FI model defaults live under `defaults/fi_models/`.
- FI model defaults currently describe Ethernet port ranges only.
- Domain-policy catalog defaults currently define baseline switch control,
  system QoS, NTP, and DNS/network connectivity behavior.
- VLANs and VLAN groups are intentionally kept out of FI model defaults.
- Solution intent files remain available as catalog metadata, but their VLAN
  and VLAN-group content is deferred to a separate network intent provisioning
  workflow.
- Domain onboarding focuses on hardware discovery, server ports, uplink
  ports, and uplink port-channels.
- Port merge precedence is:
  1. FI model defaults
  2. optional `port_catalog_key`
  3. `customer_overrides_json.port_defaults`
  4. explicit `port_config_yaml` for concrete port entries
- FI model discovery is always performed from Intersight via
  `/network/Elements`.
- The target `organization` is validated in preflight and must already exist
  in Intersight.
- Each discovered FI is also validated for assignability in the target
  `organization` before any policy or profile objects are created.
- If no explicit uplink input is provided, a model-defined default uplink
  port-channel may be used.
- `global_settings.ntp` overrides the default onboarding NTP policy values.
- `global_settings.dns` overrides the default onboarding network connectivity
  policy values.
- `global_settings.uplink_mode` currently defaults to `standard` for
  onboarding.
- NTP and network connectivity policies are part of the default domain onboarding
  baseline and can be overridden through `global_settings`.
- When created, they are not yet attached to the FI switch profile bucket
  until the exact domain-side attachment model is confirmed.
- `deployment_name` is the naming anchor for all created policies and profiles.
- The current naming style uses `deployment_name` plus readable suffixes such
  as `{{ deployment_name }}-Domain-Profile`, `{{ deployment_name }}-Port-Policy`,
  `{{ deployment_name }}-Switch-Control`, `{{ deployment_name }}-System-QoS`,
  `{{ deployment_name }}-NTP`, and `{{ deployment_name }}-Network-Connectivity`.
- Customer `port_config_yaml` overrides are validated against the discovered FI
  model before payload assembly.
- FI model filenames are normalized to lowercase with non-alphanumeric
  characters converted to underscores. Example: `UCS-FI-6536` becomes
  `ucs_fi_6536.yaml`.
- The grain exports an `intersight_resource_plan_json` output that captures the
  intended onboarding create order for baseline policies and the domain profile
  object graph.
