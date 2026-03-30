# Unclaim Status

## Current status

Forward claim is validated.

Destroy/unclaim is now validated for the tested IMC path when the teardown uses the regional
Intersight API endpoint and verifies the result asynchronously after the delete call.

## Current destroy modes

### `noop`

- safest default
- does not attempt unregister or unclaim

### `unclaim_input_targets`

Current implementation:

1. rebuild target inventory from original launch inputs
2. resolve endpoint serial numbers from the device itself
3. look up `asset.DeviceRegistrations` by serial
4. follow the linked `DeviceClaim.Moid`
5. issue `DELETE` on `asset.DeviceClaims/<moid>`
6. poll `asset.DeviceRegistrations` until the linked claim disappears or timeout expires
7. recheck the endpoint claim state when needed

## What has been validated

- teardown input validation
- inventory reconstruction during destroy
- endpoint serial resolution
- registration lookup
- `DeviceClaim`-based delete path execution
- asynchronous verification after delete acceptance
- live endpoint transition from `Claimed` to `Not Claimed` on `10.29.135.107`
- accurate destroy result reporting after duplicate-result cleanup

## Validated live behavior

For the tested IMC environment:

- `DELETE /asset/DeviceClaims/<moid>` returned success through the regional API endpoint
- the linked claim disappeared during registration polling
- the endpoint later reported:
  - `account_ownership_state = Not Claimed`
  - `claim_submission_required = true`

## Important operational note

The tested successful path used the regional API endpoint:

- `https://us-east-1.intersight.com/api/v1`

The global SaaS endpoint remains the default blueprint value because it works for forward claim,
but destroy/unclaim may require the regional endpoint to match UI behavior.

## Remaining follow-up

- validate unclaim on more than one IMC target
- validate behavior across more org/account scopes
- decide whether the blueprint should keep the global API default or expose a clearer regional recommendation for destroy runs
