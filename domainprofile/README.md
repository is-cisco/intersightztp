# Domain Profile Repository

This repo contains a Torque-ready Ansible foundation for Cisco Intersight
domain onboarding, with network intent provisioning intentionally separated
into a later workflow.

## Structure

- `ansible/domain_profile_deployment/`: current domain onboarding grain,
  requirements, and teardown.
- `ansible/bootstrap_collections/`: worker bootstrap grain that installs the
  required Ansible collections before other grains run.
- `ansible/network_intent_provisioning/`: network intent provisioning grain,
  requirements, and teardown.
- `blueprints/`: spec version 2 Torque blueprint.
- `catalog/solution_intents/`: deferred network intent definitions and catalog
  mapping for the future provisioning phase.
- `defaults/fi_models/`: model-based FI port defaults.
- `docs/`: repository-level architecture notes.

## Current Scope

The current implementation validates inputs, discovers FI model details,
configures baseline domain onboarding objects, and exports a composed payload.
Domain onboarding is about physical and policy onboarding:
- server ports
- uplink ports
- uplink port-channels
- switch control
- System QoS
- port policy
- switch/domain profiles

Created object names follow the deployment prefix plus a readable suffix, for
example `vf1-Domain-Profile`, `vf1-Port-Policy`, `vf1-Switch-Control`, and
`vf1-System-QoS`.

VLANs, VLAN groups, and solution-specific network attachment are intentionally
deferred to a later network provisioning workflow.

Network intent provisioning has its own grain for:
- solution intent resolution
- VLAN validation
- VLAN group validation
- VLAN policy composition
- named VLAN object creation such as `vf1_esxi-mgmt`
- Ethernet network group policy composition
- multicast association through VLAN policy entries
- disjoint Layer 2 uplink attachment with explicit `auto_allow_on_uplinks`
  control for participating VLANs
- automatic deploy of switch-profile changes that enter `Pending-changes`
