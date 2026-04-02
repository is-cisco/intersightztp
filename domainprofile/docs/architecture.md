# Domain Onboarding And Network Intent Provisioning

This repository is structured to separate physical domain onboarding from later
network intent provisioning so the same FI hardware foundation can be reused
across multiple solution families without mixing port bring-up and VLAN design
in a single workflow.

The current scope is Ethernet-only. Fibre Channel, FCoE, and breakout handling
are deferred so the initial domain-profile workflow stays easier to validate.

## Workflow Model

### Domain Onboarding Workflow

1. User provides FI serial inventory, credentials, organization, deployment
   name, and optional onboarding overrides.
2. The grain queries Intersight by FI serial number to discover the actual
   model and inventory identity.
3. Repository model data supplies FI-specific hardware constraints and valid
   Ethernet port ranges.
4. Customer `port_config_yaml` is validated against the discovered model.
5. The grain builds baseline onboarding policies and the fabric
   switch-profile/domain-profile object graph.
6. Stable JSON outputs are exported for downstream grains or later workflows.

Baseline onboarding policies include:
- switch control
- System QoS
- NTP
- network connectivity
- port policy

### Network Intent Provisioning Workflow

1. A later workflow consumes deployment context from onboarding.
2. Solution intent or catalog metadata provides VLANs, VLAN groups, and
   solution-specific network policy.
3. VLAN-side policy objects are created independently from FI onboarding.
4. Network intent is attached to the already-onboarded uplink constructs.
5. Disjoint or non-disjoint network design is handled explicitly in that workflow.
6. Multicast is associated through VLAN membership in the VLAN policy rather
   than by attaching a multicast policy directly to the switch profiles.
7. Disjoint VLANs must disable `auto_allow_on_uplinks` in the VLAN policy
   input so the domain-profile deploy passes validation.
8. VLAN objects are created with readable names derived from deployment name
   and catalog VLAN name, for example `vf1_esxi-mgmt`.

## Input Strategy

- Keep complex inputs string-based for Torque safety.
- Prefer `fi_devices_json` for device inventory keyed by serial number.
- Prefer `customer_overrides_json` for structured overrides.
- Prefer `port_config_yaml` for onboarding port layouts that are easier to
  author in YAML.
- Prefer `deployment_name` as the unique naming prefix for all created
  Intersight objects in a deployment.
- Keep organization in the initial input contract, not in the intent layer.
- Keep VLANs and VLAN groups in the later network-intent layer, not in FI
  model defaults.
- Treat `solution_intent` and `catalog_solution_key` as deferred metadata in
  the domain onboarding workflow rather than active dependencies.
- Treat FI model discovery as mandatory and sourced from Intersight rather than
  a launch-form input.
- Use `deployment_name` plus readable object-type suffixes for created
  Intersight objects, for example `vf1-Domain-Profile`, `vf1-Port-Policy`,
  `vf1-Switch-Control`, `vf1-System-QoS`, `vf1-NTP`, and
  `vf1-Network-Connectivity`.

## Recommended Next Expansion

- Add a composed blueprint that chains onboarding outputs into network intent
  inputs when you want one-click end-to-end deployment.
- Keep teardown logic scoped so onboarding and network provisioning can be
  managed independently if needed.
