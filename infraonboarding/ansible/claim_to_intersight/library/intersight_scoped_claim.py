#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: intersight_scoped_claim
short_description: Claim an Intersight target with optional organization-aware reservation handling
description:
- Uses the official Cisco Intersight module utilities for HTTP signing and API calls.
- Provides the missing claim workflow that is not covered by C(cisco.intersight.intersight_target_claim).
- When C(organization) is supplied, the module looks up the organization, reuses or creates a same-name resource group,
  creates a reservation, and submits the device claim using that reservation.
extends_documentation_fragment: cisco.intersight.intersight
options:
  serial_number:
    description:
    - Device serial number from the device connector.
    type: str
    required: true
  claim_code:
    description:
    - Device claim code from the device connector.
    type: str
    required: true
    no_log: true
  organization:
    description:
    - Optional Intersight organization name.
    - When supplied, the module scopes the claim through a same-name resource group and reservation.
    type: str
    default: ''
  state:
    description:
    - Currently only C(present) is supported.
    type: str
    choices: [present]
    default: present
author:
- Raghu Krishnan
'''

EXAMPLES = r'''
- name: Claim device in default scope
  intersight_scoped_claim:
    api_private_key: "{{ api_private_key }}"
    api_key_id: "{{ api_key_id }}"
    api_uri: "{{ api_uri }}"
    validate_certs: "{{ validate_certs }}"
    serial_number: "{{ serial_number }}"
    claim_code: "{{ claim_code }}"

- name: Claim device in an organization-backed scope
  intersight_scoped_claim:
    api_private_key: "{{ api_private_key }}"
    api_key_id: "{{ api_key_id }}"
    api_uri: "{{ api_uri }}"
    validate_certs: "{{ validate_certs }}"
    serial_number: "{{ serial_number }}"
    claim_code: "{{ claim_code }}"
    organization: "{{ organization }}"
'''

RETURN = r'''
api_response:
  description: Raw API response from the asset.DeviceClaim POST.
  returned: always
  type: dict
organization_moid:
  description: Resolved organization Moid when organization input is supplied.
  returned: always
  type: str
resource_group_moid:
  description: Reused or created resource group Moid when organization input is supplied.
  returned: always
  type: str
reservation_moid:
  description: Reservation Moid used during the claim.
  returned: always
  type: str
'''

import json

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cisco.intersight.plugins.module_utils.intersight import IntersightModule, intersight_argument_spec


def first_result(payload):
    if isinstance(payload, dict):
        for key in ('Results', 'results', 'Items', 'items'):
            if key in payload:
                results = payload.get(key) or []
                if isinstance(results, list) and results:
                    return results[0]
                return {}
        return payload
    if isinstance(payload, list):
        return payload[0] if payload else {}
    return {}


def api_get(intersight, resource_path, query_params):
    return intersight.call_api(
        http_method='get',
        resource_path=resource_path,
        query_params=query_params,
    )


def api_post(intersight, resource_path, body):
    return intersight.call_api(
        http_method='post',
        resource_path=resource_path,
        body=body,
    )


def get_organization(intersight, name):
    payload = api_get(
        intersight,
        '/organization/Organizations',
        {'$filter': "Name eq '%s'" % name, '$top': 1},
    )
    return first_result(payload)


def get_resource_group(intersight, name):
    payload = api_get(
        intersight,
        '/resource/Groups',
        {'$filter': "Name eq '%s'" % name, '$top': 1},
    )
    return first_result(payload)


def create_resource_group(intersight, name, organization_moid):
    return api_post(
        intersight,
        '/resource/Groups',
        {
            'ClassId': 'resource.Group',
            'ObjectType': 'resource.Group',
            'Name': name,
            'Qualifier': 'Allow-Selectors',
            'Organizations': [
                {
                    'ClassId': 'mo.MoRef',
                    'ObjectType': 'organization.Organization',
                    'Moid': organization_moid,
                }
            ],
        },
    )


def create_reservation(intersight, resource_group_moid):
    return api_post(
        intersight,
        '/resource/Reservations',
        {
            'Groups': [
                {
                    'ObjectType': 'resource.Group',
                    'Moid': resource_group_moid,
                }
            ],
            'ResourceType': 'asset.DeviceRegistration',
        },
    )


def build_claim_body(serial_number, claim_code, reservation_moid):
    body = {
        'SecurityToken': claim_code,
        'SerialNumber': serial_number,
    }
    if reservation_moid:
        body['Reservation'] = {
            'ObjectType': 'resource.Reservation',
            'Moid': reservation_moid,
        }
    return body


def normalize_error(exc):
    try:
        return json.loads(str(exc))
    except Exception:
        return {'message': str(exc)}


def main():
    argument_spec = intersight_argument_spec.copy()
    argument_spec.update(
        serial_number=dict(type='str', required=True),
        claim_code=dict(type='str', required=True, no_log=True),
        organization=dict(type='str', default=''),
        state=dict(type='str', choices=['present'], default='present'),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    intersight = IntersightModule(module)

    serial_number = module.params['serial_number'].strip()
    claim_code = module.params['claim_code'].strip()
    organization = module.params['organization'].strip()

    result = {
        'changed': False,
        'failed': False,
        'msg': '',
        'api_response': {},
        'organization_moid': '',
        'resource_group_moid': '',
        'reservation_moid': '',
    }

    try:
        if not serial_number or not claim_code:
            raise ValueError('serial_number and claim_code are required')

        reservation_moid = ''
        if organization:
            organization_result = get_organization(intersight, organization)
            organization_moid = str(organization_result.get('Moid', '')).strip()
            if not organization_moid:
                raise ValueError("Organization '%s' was not found in Intersight" % organization)
            result['organization_moid'] = organization_moid

            resource_group_result = get_resource_group(intersight, organization)
            if not resource_group_result:
                resource_group_result = create_resource_group(intersight, organization, organization_moid)
            resource_group_moid = str(resource_group_result.get('Moid', '')).strip()
            if not resource_group_moid:
                raise ValueError("Resource Group '%s' did not return a Moid" % organization)
            result['resource_group_moid'] = resource_group_moid

            reservation_result = create_reservation(intersight, resource_group_moid)
            reservation_moid = str(reservation_result.get('Moid', '')).strip()
            if not reservation_moid:
                raise ValueError("Reservation creation for '%s' did not return a Moid" % organization)
            result['reservation_moid'] = reservation_moid

        if not module.check_mode:
            claim_response = api_post(
                intersight,
                '/asset/DeviceClaims',
                build_claim_body(serial_number, claim_code, reservation_moid),
            )
            result['api_response'] = claim_response
        result['changed'] = True
    except Exception as exc:
        result['failed'] = True
        result['msg'] = json.dumps(normalize_error(exc))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
