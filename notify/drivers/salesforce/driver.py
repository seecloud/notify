# Copyright 2016: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging

from notify import config
from notify.drivers.salesforce import salesforce


LOG = logging.getLogger("api")
SFDC_CLIENTS = {}


def sfdc_client(backend, driver):
    global SFDC_CLIENTS

    cfg = config.get_config()['notify_backends'][backend][driver]
    sfdc_config = cfg['properties']

    if not (backend in SFDC_CLIENTS.keys()):
        SFDC_CLIENTS[backend] = {}
        sfdc_oauth2 = salesforce.OAuth2(
            client_id=sfdc_config['client_id'],
            client_secret=sfdc_config['client_secret'],
            username=sfdc_config['username'],
            password=sfdc_config['password'],
            auth_url=sfdc_config['auth_url'],
            organizationId=sfdc_config['organization_id'])

        SFDC_CLIENTS[backend][driver] = salesforce.Client(sfdc_oauth2)

    elif not (driver in SFDC_CLIENTS[backend].keys()):

        sfdc_oauth2 = salesforce.OAuth2(
            client_id=sfdc_config['client_id'],
            client_secret=sfdc_config['client_secret'],
            username=sfdc_config['username'],
            password=sfdc_config['password'],
            auth_url=sfdc_config['auth_url'],
            organizationId=sfdc_config['organization_id'])

        SFDC_CLIENTS[backend][driver] = salesforce.Client(sfdc_oauth2)

    else:
        pass


def send_to_salesforce(backend, driver, content):

    cfg = config.get_config()['notify_backends'][backend][driver]
    sfdc_config = cfg['properties']

    sfdc_client(backend, driver)
    if salesforce.validate_alert_data(alert=content):
        try:
            salesforce.send_to_sfdc(alert=content,
                                    sfdc_client=SFDC_CLIENTS[backend][driver],
                                    environment=sfdc_config['environment'])
            return(200, {"result": "success"})
        except Exception as e:
            LOG.debug("Failed to send data: {}".format(e))
            return(409, {"result": "fail"})
    else:
        return(409, {"result": "fail"})
