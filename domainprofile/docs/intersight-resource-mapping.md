# Intersight Resource Mapping

This document makes the first implementation path concrete for the current
domain-profile framework. It maps the repository contracts into Cisco
Intersight resources and the Ansible modules available in the installed
`cisco.intersight` collection.

## Assumptions

- Ethernet-only port configuration in the first iteration.
- FI hardware model is discovered from Intersight by serial number.
- `organization` is provided by the Torque blueprint input.
- VLANs and VLAN groups come from solution intent or customer overrides.
- The installed collection does not expose a dedicated domain-profile module,
  so final domain-profile creation is expected to use
  `cisco.intersight.intersight_rest_api`.

## Resource Order

1. `organization.Organization`
   Module: `cisco.intersight.intersight_rest_api`
   Resource path:
   - `/api/v1/organization/Organizations`
   Purpose:
   - resolve the organization Moid used by later create calls

2. `fabric.EthNetworkPolicy`
   Module: `cisco.intersight.intersight_vlan_policy`
   Source data:
   - `vlans`
   Purpose:
   - create the VLAN policy and all VLAN members needed by the domain

3. `fabric.EthNetworkGroupPolicy`
   Module: `cisco.intersight.intersight_ethernet_network_group_policy`
   Source data:
   - `vlan_groups`
   - `uplink_profiles[].native_vlan`
   Purpose:
   - create one policy per VLAN group so uplink definitions can reference
     allowed VLAN sets cleanly

4. `fabric.SwitchControlPolicy`
   Module: `cisco.intersight.intersight_switch_control_policy`
   Source data:
   - `global_settings.network_control`
   - future switch-mode specific settings
   Purpose:
   - define global FI switching behavior such as Ethernet mode, MAC aging,
     reserved VLAN block, and UDLD behavior

5. `fabric.FlowControlPolicy`
   Module: `cisco.intersight.intersight_flow_control_policy`
   Source data:
   - `global_settings.policy_attachments`
   - future flow-control defaults
   Purpose:
   - define the flow-control posture used by uplink and server-facing ports

6. `fabric.PortPolicy`
   Module: `cisco.intersight.intersight_port_policy`
   Source data:
   - discovered `fi_model`
   - `port_config_yaml`
   - `uplink_profiles`
   - `global_settings.port_policy_defaults`
   Purpose:
   - create server ports
   - create Ethernet uplink ports or port-channels
   - bind Ethernet network group policies and other port-level policies

7. `fabric.SwitchClusterProfile`
   Module: `cisco.intersight.intersight_rest_api`
   Resource path:
   - `/api/v1/fabric/SwitchClusterProfiles`
   Source data:
   - `organization`
   - naming defaults
   Purpose:
   - create the domain profile container object

8. `fabric.SwitchProfile`
   Module: `cisco.intersight.intersight_rest_api`
   Resource path:
   - `/api/v1/fabric/SwitchProfiles`
   Source data:
   - switch cluster profile Moid
   - naming defaults
   Purpose:
   - create the A and B switch profiles under the switch cluster profile

9. `fabric.SwitchProfile/PolicyBucket`
   Module: `cisco.intersight.intersight_rest_api`
   Resource path:
   - `/api/v1/fabric/SwitchProfiles/{Moid}/PolicyBucket`
   Source data:
   - Moids of the created policies
   Purpose:
   - attach the shared policies to each switch profile

## Concrete REST Sequence

The most concrete sequence I found is:

1. Create `fabric.SwitchClusterProfile`
2. Create `fabric.SwitchProfile` for fabric A and fabric B
3. Attach policies through each switch profile `PolicyBucket`

Example shape:

```json
POST /api/v1/fabric/SwitchClusterProfiles
{
  "Name": "demoX",
  "Organization": {
    "ObjectType": "organization.Organization",
    "Moid": "<organization_moid>"
  }
}
```

```json
POST /api/v1/fabric/SwitchProfiles
{
  "Name": "demoX-A",
  "SwitchClusterProfile": "<switch_cluster_profile_moid>"
}
```

```json
POST /api/v1/fabric/SwitchProfiles/<switch_profile_moid>/PolicyBucket
[
  {
    "ObjectType": "fabric.EthNetworkPolicy",
    "Moid": "<vlan_policy_moid>"
  },
  {
    "ObjectType": "fabric.PortPolicy",
    "Moid": "<port_policy_moid>"
  }
]
```

## Repository To Resource Mapping

- `vlans`
  Maps to `intersight_vlan_policy.vlans`

- `vlan_groups`
  Maps to one `intersight_ethernet_network_group_policy` per group

- `global_settings.port_policy_defaults`
  Maps to default values for `intersight_port_policy.server_ports` and
  `intersight_port_policy.ethernet_uplink_ports`

- `global_settings.network_control`
  Maps primarily to `intersight_switch_control_policy`

- `global_settings.policy_attachments`
  Supplies default policy names for port policy references

- `uplink_profiles`
  Maps to `intersight_port_policy.ethernet_uplink_ports` or
  `intersight_port_policy.ethernet_uplink_port_channels` depending on how we
  decide to model bundles

- `port_config_yaml`
  Overrides or supplements concrete port selections for the port policy

## Immediate Gaps To Close

- Validate that every `uplink_profiles.vlan_groups[]` reference exists.
- Decide whether `uplink_profiles` represent:
  - standalone uplink ports, or
  - uplink port-channels by default.
- Define exact name-generation rules for each policy type.
- Confirm the exact request body shape for `fabric.SwitchProfile` and whether
  your tenant expects a MoRef object or accepts the bare cluster-profile Moid.
