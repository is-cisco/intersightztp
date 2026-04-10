# create-and-deploy-rack-server-profile

Focused grain for creating or reconciling a standalone rack `server.Profile`,
realizing named policy objects, attaching those policies to the profile, and
optionally deploying the profile to a claimed rack server in Cisco Intersight.

## Intent

- keep the public workflow narrow and rack-server-specific
- accept one normalized rack target contract plus one normalized server-profile
  contract
- realize policies before profile reconciliation so profile attachment can stay
  deterministic
- support safe local planning with `validation_mode: strict` and
  `execution_intent: validate_only`
- use pending-change driven deploy behavior instead of blindly redeploying on
  every run

## Required inputs

- `platform_yaml` when `validation_mode=live` or `execution_intent=apply`
- `rack_server_json`
- `server_profile_json`

## Optional inputs

- `placement_yaml`
- `organization`
- `policy_definitions_json`
- `validation_mode`
- `execution_intent`
- `wait_for_completion`
- `deployment_poll_interval`
- `deployment_timeout_seconds`
- `local_output_dir`
- `bootstrap_python_requirements`

## Contract shape

`rack_server_json` accepts either a root object or a `rack_server` wrapper:

```json
{
  "rack_server": {
    "serial": "WZP270500PQ",
    "name": "rack-server-01"
  }
}
```

`server_profile_json` accepts either a root object or a `server_profile`
wrapper:

```json
{
  "server_profile": {
    "name": "ai-prod-rack-01",
    "description": "Standalone rack server profile",
    "target_platform": "Standalone",
    "uuid_address_type": "NONE",
    "server_assignment_mode": "Static",
    "deploy_action": "ConfigChange",
    "tags": [
      {
        "Key": "environment",
        "Value": "prod"
      }
    ],
    "settings": {}
  }
}
```

`policy_definitions_json` accepts either a root list or a `policies` wrapper:

```json
{
  "policies": [
    {
      "key": "bios_policy",
      "name": "ai-prod-rack-01-bios",
      "resource_path": "/bios/Policies",
      "object_type": "bios.Policy",
      "api_body": {
        "Description": "Rack BIOS policy"
      }
    }
  ]
}
```

## Current behavior

- `strict` + `validate_only` builds a fully normalized plan without making
  Intersight API calls
- `live` + `validate_only` validates organization, rack-target, policy, and
  profile presence without mutating remote state
- `apply` realizes missing or drifted policy objects, reconciles the
  `server.Profile`, triggers a deploy action when the live profile shows
  pending change semantics, and can wait for `Associated`
- policy realization is generic by resource path and object type so the grain
  can support multiple policy families without baking each schema into the
  playbook
- the deploy action defaults to `ConfigChange` to align with the referenced
  Cisco DevNet server-profile example, but it can be overridden in
  `server_profile_json.deploy_action`

## Internal implementation

- `tasks/lib_normalize_policy_definition.yaml`
- `tasks/lib_resolve_rack_server.yaml`
- `tasks/lib_realize_policy.yaml`
- `tasks/lib_reconcile_server_profile.yaml`
- `tasks/lib_wait_for_server_profile.yaml`
- `library/intersight_policy_bucket_merge.py`
- `tools/validate_rack_server_profile_contract.py`

## Outputs

- `profile_ready`
- `profile_status`
- `profile_summary_json`
- `profile_result_json`
- `policy_results_json`
- `realized_policy_moids_json`

## Notes

- this grain currently targets directly managed standalone rack
  `server.Profile` objects rather than template-derived profiles because the
  requested workflow is a focused rack-profile operation and the referenced
  Cisco examples use direct server-profile assignment semantics
- the structure is intentionally compatible with later promotion to a
  template-driven server-profile flow if the broader resource phase grows in
  that direction
