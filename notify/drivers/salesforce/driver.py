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

from notify.drivers import driver
from notify.drivers.salesforce import salesforce


def sfdc_client(sfdc_config):
    return salesforce.Client(
        salesforce.OAuth2(
            client_id=sfdc_config["client_id"],
            client_secret=sfdc_config["client_secret"],
            username=sfdc_config["username"],
            password=sfdc_config["password"],
            auth_url=sfdc_config["auth_url"],
            organizationId=sfdc_config["organization_id"]
        )
    )


class Driver(driver.Driver):

    def __init__(self, config):
        super(Driver, self).__init__(config)
        self.client = sfdc_client(config)

    def notify(self, payload):
        salesforce.send_to_sfdc(alert=payload,
                                sfdc_client=self.client,
                                environment=self.config["environment"])
