# Network Intent Provisioning Grain

This grain is the phase-2 companion to domain onboarding. It resolves
solution intent, validates VLAN and VLAN-group contracts, builds the network
intent payload, and can create VLAN-side Intersight policies without changing
the onboarding grain.

The current implementation focuses on:
- multicast policy
- VLAN policy
- Ethernet network group policies
- VLAN policy attachment to the A/B switch profiles
- uplink attachment onto the onboarding-created port policy using live
  Intersight state

## Inputs

### Blueprint-facing inputs

- `api_key_id`: Intersight API key ID.
- `api_private_key`: Intersight API private key.
- `api_uri`: Optional custom Intersight endpoint.
- `deployment_name`: Required deployment prefix used for all created objects.
- `organization`: Required Intersight organization. The organization must
  already exist in Intersight; this workflow validates it but does not create
  it.
- `solution_intent`: Optional explicit solution intent name.
- `customer_overrides_json`: Optional JSON object for VLAN, VLAN-group,
  uplink-profile, or global-setting overrides.
- `deploy_network_intent_changes`: Optional boolean-like string. Defaults to
  `true`. When `true`, the grain deploys switch profiles that enter
  `Pending-changes` after logical policy attachment and waits for them to
  settle back to `Associated`. Set to `false` to stage changes only.

### Internal playbook variables

The playbook also accepts internal variables such as `catalog_solution_key`,
`create_network_intent`, `onboarding_payload_json`, and `validate_certs`. Those
are used by local runs or blueprint wiring, but they are not part of the
intended end-user Torque launch surface.

## Outputs

- `validations_passed`
- `solution_intent_resolved`
- `network_intent_payload_json`
- `onboarding_context_json`
- `intersight_resource_plan_json`
- `vlans_json`
- `vlan_groups_json`
- `uplink_profiles_json`
- `vlan_policy_vlans_json`
- `ethernet_network_group_policies_json`
- `network_intent_tac_handoff_json`
- `intersight_trace_ids_json`

## Destroy Behavior

`teardown.yaml` removes the VLAN-side policy objects created by this grain:
- multicast policy
- VLAN policy
- Ethernet network group policies

It does not remove phase-1 onboarding objects, but it does clear Ethernet
network group references from the onboarding-created uplink constructs before
deleting the phase-2 objects.

## Current Scope

- Solution intent is sourced from `catalog/solution_intents/`.
- VLANs and VLAN groups remain independent of FI model defaults.
- This grain can also update the existing onboarding-created port policy to
  attach Ethernet network group policies to uplink ports or port channels by
  reading the live port-policy state from Intersight.
- This grain attaches the created VLAN policy to the
  `{{ deployment_name }}-A` and `{{ deployment_name }}-B` switch profiles so
  the logical network intent is associated with the domain. Multicast is
  associated per-VLAN inside the VLAN policy.
- The phase-2 policy names follow the same readable convention, for example
  `{{ deployment_name }}-VLAN-Policy`, `{{ deployment_name }}-Multicast-Policy`,
  and the phase-1-created `{{ deployment_name }}-Port-Policy`.
- Individual VLAN objects are created with readable names derived from the
  deployment name and catalog VLAN name, for example `vf1_esxi-mgmt`,
  `vf1_vmotion`, `vf1_vsan`, and `vf1_tenant-vm`.
- When using disjoint Layer 2 behavior through Ethernet network group
  policies, VLANs that participate in the disjoint set must disable
  `auto_allow_on_uplinks` in the VLAN policy data. Leaving auto-allow enabled
  causes the domain-profile deploy to fail validation.
- By default, the grain deploys those switch profile changes and waits for the
  switch profiles to return to a clean terminal state. Set
  `deploy_network_intent_changes=false` when you want staging-only behavior.
- When a solution intent defines exactly one uplink profile and omits
  `target_ports`, the grain treats that as "apply to all discovered uplinks"
  instead of requiring physical port placement in the intent file.
- The target `organization` is validated in preflight and must already exist
  in Intersight.
- If the onboarding-created port policy does not exist yet, the grain still
  creates the VLAN-side policies and exports the attachment plan, but skips
  live uplink attachment.
- If the solution-intent target uplinks do not match the discovered onboarding
  uplinks, the grain now fails instead of silently producing an unused policy
  set.
