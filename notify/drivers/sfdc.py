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
from xml.dom import minidom

import requests
from requests.packages.urllib3 import exceptions as urllib_exc

from notify import config
from notify import driver

requests.packages.urllib3.disable_warnings(urllib_exc.InsecureRequestWarning)


LOG = logging.getLogger("sfdc")
LOG.setLevel(config.get_config().get("logging", {}).get("level", "INFO"))


class OAuth2(object):

    def __init__(self,
                 client_id,
                 client_secret,
                 username,
                 password,
                 auth_url=None,
                 organizationId=None):
        self.auth_url = auth_url or "https://login.salesforce.com"
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.organization = organizationId

    def authenticate_soap(self):
        LOG.debug("Making SFDC SOAP auth for {}".format(self.username))
        doc = minidom.Document()
        env = doc.appendChild(doc.createElement("soapenv:Envelope"))
        env.setAttribute("xmlns:soapenv",
                         "http://schemas.xmlsoap.org/soap/envelope/")
        env.setAttribute("xmlns:urn", "urn:partner.soap.sforce.com")

        head = ("Header", [("CallOptions", [("client", "RestForce"),
                                            ("defaultNamespace", "sf")]),
                           ("LoginScopeHeader", [("organizationId",
                                                  self.organization)])])
        body = ("Body", [("login", [("username", self.username),
                                    ("password", self.password)])])
        for name1, nested1 in head, body:
            e1 = env.appendChild(doc.createElement("soapenv:" + name1))
            for name2, nested2 in nested1:
                e2 = e1.appendChild(doc.createElement("urn:" + name2))
                for name3, value in nested2:
                    e3 = e2.appendChild(doc.createElement("urn:" + name3))
                    e3.appendChild(doc.createTextNode(value))

        envelope = doc.toxml(encoding="utf-8").decode("utf-8")
        url = "{}/services/Soap/u/36.0".format(self.auth_url)
        headers = {"Charset": "UTF-8",
                   "SOAPAction": "login",
                   "Content-Type": "text/xml"}

        resp = requests.post(url, envelope, verify=None, headers=headers)

        LOG.debug(("SFDC OAuth2 SOAP Response "
                   "({}): {}").format(resp.status_code, resp.text))
        resp.raise_for_status()

        resp_xml = minidom.parseString(resp.text)
        elements = resp_xml.getElementsByTagName("sessionId")
        token = elements and elements[0].firstChild.nodeValue or None

        return {"access_token": token, "instance_url": self.auth_url}

    def authenticate_rest(self):
        LOG.debug("Making SFDC REST auth for {}".format(self.client_id))
        data = {"grant_type": "password",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "username": self.username,
                "password": self.password}
        url = "{}/services/oauth2/token".format(self.auth_url)

        resp = requests.post(url, data=data, verify=None)

        LOG.debug(("SFDC OAuth2 REST Response "
                   "({}): {}").format(resp.status_code, resp.text))
        resp.raise_for_status()
        return resp.json()

    def authenticate(self):
        if self.organization:
            return self.authenticate_soap()
        return self.authenticate_rest()


class Client(object):

    def __init__(self, oauth2, base_path="/services/data/v36.0"):
        self.oauth2 = oauth2
        self.base_path = base_path

        self.path = "{}/sobjects".format(base_path)
        self.access_token = None
        self.instance_url = None

    def authenticate(self):
        result = self.oauth2.authenticate()
        self.access_token = result["access_token"]
        self.instance_url = result["instance_url"]

    def _request(self, method, url, headers=None, repeat=True, **kwargs):
        if not self.access_token:
            self.authenticate()

        headers = headers or {}
        headers["Authorization"] = "Bearer {}".format(self.access_token)
        if method in ("POST", "PUT", "PATCH"):
            headers["Content-Type"] = "application/json"

        request_url = self.instance_url + url

        LOG.debug("SFDC {} Request: {} {} {}".format(method, url, headers,
                                                     kwargs))
        try:
            resp = requests.request(
                method, request_url, headers=headers, verify=None, **kwargs)
        except Exception as e:
            LOG.error("SFDC Request has failed: {}: {}".format(type(e), e))
            return None, None, None

        LOG.debug("SFDC ({}) Response: {}".format(resp.status_code,
                                                  resp.text))
        if not resp.text:
            return resp.status_code, {}, None

        try:
            data = resp.json()
        except Exception as e:
            LOG.error("SFDC Response JSON error: {}: {}".format(type(e), e))
            return resp.status_code, {}, None

        # NOTE(maretskiy): this simplifies further error checks
        if data and type(data) == list and "errorCode" in data[0]:
            sfdc_error = (data[0]["errorCode"], data[0]["message"])
            LOG.error("SFDC ({}) Response: {}".format(resp.status_code, data))
        else:
            sfdc_error = None

        if repeat and sfdc_error and sfdc_error[0] == "INVALID_SESSION_ID":
            LOG.debug("SFDC token has expired, authenticating...")
            self.authenticate()
            return self._request(method, url, headers=headers, repeat=False,
                                 **kwargs)

        return resp.status_code, data, sfdc_error

    def create_feeditem(self, data):
        url = "{}/FeedItem".format(self.path)
        return self._request("POST", url, data=json.dumps(data))

    def create_case(self, data):
        url = "{}/Case".format(self.path)
        return self._request("POST", url, data=json.dumps(data))

    def update_case(self, id_, data):
        url = "{}/Case/{}".format(self.path, id_)
        return self._request("PATCH", url, data=json.dumps(data))

    def get_case(self, id_):
        return self._request("GET", "{}/Case/{}".format(self.path, id_))


class Driver(driver.Driver):
    """SalesForce notification driver."""

    CONFIG_SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema",
        "type": "object",
        "properties": {
            "username": {"type": "string"},
            "password": {"type": "string"},
            "client_id": {"type": "string"},
            "client_secret": {"type": "string"},
            "auth_url": {"type": "string"},
            "organization_id": {"type": "string"},
        },
        "required": ["username", "password", "client_id", "client_secret"],
        "additionalProperties": False
    }

    SEVERITY = {
        "OK": "060 Informational",
        "INFO": "060 Informational",
        "UNKNOWN": "070 Unknown",
        "WARNING": "080 Warning",
        "CRITICAL": "090 Critical",
        "DOWN": "090 Critical"}

    def __init__(self, config):
        super(Driver, self).__init__(config)
        oauth2 = OAuth2(username=config["username"],
                        password=config["password"],
                        client_id=config["client_id"],
                        client_secret=config["client_secret"],
                        auth_url=config.get("auth_url"),
                        organizationId=config.get("organization_id"))
        self.client = Client(oauth2)

    def notify(self, payload):
        region = payload["region"]
        priority = self.SEVERITY[payload["severity"]]
        payload_id = "|".join([region, payload["what"], payload["who"]])
        if payload.get("affected_hosts"):
            subject = payload_id + "|" + ",".join(payload["affected_hosts"])
        else:
            subject = payload_id

        case = {"Subject": subject,
                "Description": payload["description"],
                "IsMosAlert__c": "true",
                "Alert_ID__c": payload_id,
                "Environment2__c": region,
                "Alert_Priority__c": priority,
                "Alert_Host__c": payload["who"],
                "Alert_Service__c": payload["what"]}

        item = {"Description": payload["description"],
                "Alert_Id": payload_id,
                "Cloud_ID": region,
                "Alert_Priority": priority,
                "Status": "New"}

        code, resp, sfdc_error = self.client.create_case(case)

        if resp and code in (200, 201):
            case_id = resp["id"]

        elif sfdc_error and sfdc_error[0] == "DUPLICATE_VALUE":
            LOG.info("SFDC ({}): Case is a duplicate: {}".format(code, resp))

            # NOTE(maretskiy): this parsing looks ugly, ideas?
            case_id = resp[0]["message"].strip().split(" ")[-1]

            code, resp, error = self.client.get_case(case_id)
            if code not in (200, 201, 202, 204):
                return False
            item["Status"] = resp["Status"]
            case["Subject"] = resp["Subject"]

            code, resp, error = self.client.update_case(case_id, data=case)
            if code not in (200, 201, 202, 204):
                return False
        else:
            LOG.error("SFDC ({}) Unexpected Case: {}".format(code, resp))
            return False

        body = json.dumps(item, sort_keys=True, indent=2)
        code, resp, error = self.client.create_feeditem(
            {"ParentId": case_id, "Visibility": "AllUsers", "Body": body})
        return code in (200, 201)
