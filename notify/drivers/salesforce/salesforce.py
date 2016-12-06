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

import json
import logging
import xml.dom.minidom

import jsonschema
import jxmlease
import requests

from notify import config

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

LOG = logging.getLogger("salesforce")
LOG.setLevel(config.get_config().get("logging", {}).get("level", "INFO"))


ALERT_SCHEMA = {
    "type": "object",
    "description": "Alert Data",
    "properties": {
        "description": {"type": "object",
                            "properties": {
                                "affected_hosts": {"type": "array"}
                            }
                        },
        "severity":    {"enum": ["OK", "INFO", "UNKNOWN",
                                 "WARNING", "CRITICAL", "DOWN"]},
        "who":         {"type": "string"},
        "what":        {"type": "string"}
    },
    "required": ["description", "severity", "who", "what"]
}


def json_f(x):
    return json.dumps(x, sort_keys=True, indent=4)


def validate_alert_data(alert):
    global ALERT_SCHEMA
    try:
        jsonschema.validate(alert, ALERT_SCHEMA)
        return True
    except (jsonschema.exceptions.ValidationError) as e:
        LOG.debug("Failed to validate: {}".format(e))
        return False


def send_to_sfdc(alert, sfdc_client, environment=None):

    severity = {
        'OK':       '060 Informational',
        'INFO':     '060 Informational',
        'UNKNOWN':  '070 Unknown',
        'WARNING':  '080 Warning',
        'CRITICAL': '090 Critical',
        'DOWN':     '090 Critical'
        }

    alertPriority = severity[alert['severity']]

    alertId = '{}--{}--{}'.format(environment,
                                  alert['what'], alert['who'])

    if 'affected_hosts' in alert['description']:
        who = ' '.join(alert['description']['affected_hosts'])
    else:
        who = alert['who']

    subject = '{}--{}--{}'.format(environment, alert['what'], who)

    sfdc_alert = {
        'IsMosAlert__c':     'true',
        'Description':       json_f(alert['description']),
        'Alert_ID__c':       alertId,
        'Subject':           subject,
        'Environment2__c':   environment,
        'Alert_Priority__c': alertPriority,
        'Alert_Host__c':     alert['who'],
        'Alert_Service__c':  alert['what']
        }

    feeditem_body = {
        'Description':    json_f(alert['description']),
        'Alert_Id':       alertId,
        'Cloud_ID':       environment,
        'Alert_Priority': alertPriority,
        'Status':         'New',
        }

    LOG.debug('Alert Data:\n{}\n'.format(json.dumps(sfdc_alert,
                                                    sort_keys=True,
                                                    indent=4)))

    try:
        new_case = sfdc_client.create_case(sfdc_alert)

        LOG.debug('New Case status code: {} '.format(new_case.status_code))
        LOG.debug('New Case data: {} '.format(new_case.text))

        #  If Case exist
        if ((new_case.status_code == 400) and
           (new_case.json()[0]['errorCode'] == 'DUPLICATE_VALUE')):
            LOG.debug("Code: {}, Error message: {} "
                      "".format(new_case.status_code, new_case.text))
            # Find Case ID
            ExistingCaseId = new_case.json()[0]['message'].split(' ')[-1]

            current_case = sfdc_client.get_case(ExistingCaseId).json()
            LOG.debug("Existing Case: \n {}".format(json_f(current_case)))
            feeditem_body['Status'] = current_case['Status']
            sfdc_alert['Subject'] = current_case['Subject']

            u = sfdc_client.update_case(id=ExistingCaseId, data=sfdc_alert)
            LOG.debug('Upate status code: {} '.format(u.status_code))

            feeditem_data = {
                'ParentId':    ExistingCaseId,
                'Visibility': 'AllUsers',
                'Body':        json_f(feeditem_body)
            }

            LOG.debug('FeedItem Data: {}'.format(json_f(feeditem_data)))
            add_feed_item = sfdc_client.create_feeditem(feeditem_data)
            LOG.debug("Add FeedItem status code: {} \n Add FeedItem reply: {} "
                      "".format(add_feed_item.status_code, add_feed_item.text))
            return True
        # Else If Case did not exist before and was just created
        elif (new_case.status_code == 201):
            LOG.debug('Case was just created')
            # Add commnet, because Case head should conains
            # LAST data  overriden on any update
            CaseId = new_case.json()['id']
            feeditem_data = {
                'ParentId':   CaseId,
                'Visibility': 'AllUsers',
                'Body': json_f(feeditem_body),
            }
            LOG.debug('FeedItem Data: {}'.format(json_f(feeditem_data)))
            add_feed_item = sfdc_client.create_feeditem(feeditem_data)
            LOG.debug("Add FeedItem status code: {} \n Add FeedItem reply: {} "
                      "".format(add_feed_item.status_code, add_feed_item.text))
            return True
        else:
            LOG.debug("Unexpected error: Case was not created (code != 201) "
                      "and Case does not exist (code != 400)")
            return False

    except requests.exceptions.ConnectionError as e:
        LOG.debug('Exception: {}'.format(e))
        LOG.debug('Unexpected error: Case was not created: Connection error.')
        return False


class OAuth2(object):
    def __init__(self,
                 client_id,
                 client_secret,
                 username,
                 password,
                 auth_url=None,
                 organizationId=None):

        if not auth_url:
            auth_url = 'https://login.salesforce.com'

        self.auth_url = auth_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.organizationId = organizationId

    def get_first_node_value(self, xml_str, node_name):
        els = xml.dom.minidom.parseString(xml_str).getElementsByTagName(
                                                                 node_name)
        if els:
            return els[0].firstChild.nodeValue
        return None

    def authenticate_soap(self):
        soap_url = '{}/services/Soap/u/36.0'.format(self.auth_url)

        login_soap_request_body = """<?xml version="1.0" encoding="utf-8" ?>
        <soapenv:Envelope
                xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                xmlns:urn="urn:partner.soap.sforce.com">
            <soapenv:Header>
                <urn:CallOptions>
                    <urn:client>RestForce</urn:client>
                    <urn:defaultNamespace>sf</urn:defaultNamespace>
                </urn:CallOptions>
                <urn:LoginScopeHeader>
                    <urn:organizationId></urn:organizationId>
                </urn:LoginScopeHeader>
            </soapenv:Header>
            <soapenv:Body>
                <urn:login>
                    <urn:username></urn:username>
                    <urn:password></urn:password>
                </urn:login>
            </soapenv:Body>
        </soapenv:Envelope>"""

        E = 'soapenv:Envelope'
        B = 'soapenv:Body'
        l = 'urn:login'
        H = 'soapenv:Header'
        LS = 'urn:LoginScopeHeader'
        xml = jxmlease.parse(login_soap_request_body)
        xml[E][B][l]['urn:username'] = self.username
        xml[E][B][l]['urn:password'] = self.password
        xml[E][H][LS]['urn:organizationId'] = self.organizationId

        login_soap_request_body = jxmlease.emit_xml(xml)

        login_soap_request_headers = {
            'content-type': 'text/xml',
            'charset': 'UTF-8',
            'SOAPAction': 'login'
        }

        response = requests.post(soap_url,
                                 login_soap_request_body,
                                 verify=None,
                                 headers=login_soap_request_headers)

        LOG.debug('Response: {}'.format(response))
        LOG.debug('Status code: {}'.format(response.status_code))
        LOG.debug('Response text: {}'.format(response.text))

        session_id = self.get_first_node_value(response.content, 'sessionId')

        response_json = {
            'access_token': session_id,
            'instance_url': self.auth_url
        }

        response.raise_for_status()
        return response_json

    def authenticate_rest(self):
        data = {
            'grant_type': 'password',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'username': self.username,
            'password': self.password,
        }

        url = '{}/services/oauth2/token'.format(self.auth_url)
        response = requests.post(url, verify=None, data=data)
        response.raise_for_status()
        return response.json()

    def authenticate(self, **kwargs):
        if self.organizationId:
            LOG.debug('self.organizationId={}'.format(self.organizationId))
            LOG.debug('Auth method = SOAP')
            return self.authenticate_soap(**kwargs)
        else:
            LOG.debug('Auth method = REST')
            return self.authenticate_rest(**kwargs)


class Client(object):
    def __init__(self, oauth2):
        self.oauth2 = oauth2

        self.access_token = None
        self.instance_url = None

    sfdc_base_path = '/services/data/v36.0'
    sfdc_path = sfdc_base_path + '/sobjects'

    def create_feeditem(self, data, sfdc_path=sfdc_path):
        return self.post(sfdc_path + '/FeedItem',
                         data=json.dumps(data),
                         headers={"content-type": "application/json"})

    def create_case(self, data, sfdc_path=sfdc_path):
        return self.post(sfdc_path + '/Case',
                         data=json.dumps(data),
                         headers={"content-type": "application/json"})

    def get_case(self, id, sfdc_path=sfdc_path):
        return self.get(sfdc_path + '/Case/{}'.format(id))

    def update_case(self, id, data, sfdc_path=sfdc_path):
        return self.patch(sfdc_path + '/Case/{}'.format(id),
                          data=json.dumps(data),
                          headers={"content-type": "application/json"})

    def environment(self, id, sfdc_path=sfdc_path):
        return self.get(sfdc_path + '/Environment__c/{}'.format(id)).json()

    def get(self, url, **kwargs):
        return self._request('get', url, **kwargs)

    def patch(self, url, **kwargs):
        return self._request('patch', url, **kwargs)

    def post(self, url, **kwargs):
        return self._request('post', url, **kwargs)

    def delete(self, url, **kwargs):
        return self._request('delete', url, **kwargs)

    def _request(self, method, url, headers=None, **kwargs):
        if not headers:
            headers = {}

        if not self.access_token or not self.instance_url:
            result = self.oauth2.authenticate()
            self.access_token = result['access_token']
            self.instance_url = result['instance_url']

        headers['Authorization'] = 'Bearer {}'.format(self.access_token)

        url = self.instance_url + url
        response = requests.request(method,
                                    url,
                                    headers=headers,
                                    verify=None,
                                    **kwargs)

        LOG.debug("salesforce.py: Response code: {}"
                  "".format(response.status_code))
        try:
            msg = json.dumps(response.json(),
                             sort_keys=True,
                             indent=4,
                             separators=(',', ': '))
            LOG.debug("salesforce.py: Response content: {}".format(msg))

            if (response.json()[0]['errorCode'] == 'INVALID_SESSION_ID'):
                LOG.debug("salesforce.py: Trying  again")
                result = self.oauth2.authenticate()
                self.access_token = result['access_token']
                self.instance_url = result['instance_url']
                headers['Authorization'] = (
                    'Bearer {}'.format(self.access_token))
                response = requests.request(method,
                                            url,
                                            headers=headers,
                                            verify=None,
                                            **kwargs)
        except Exception:
            LOG.debug("salesforce.py: Response content: {}"
                      "".format(response.content))

        return response
