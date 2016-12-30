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

import mock

from notify.drivers import sfdc
from tests.unit import test


class OAuth2TestCase(test.TestCase):

    SIMPLIFIED_SOAP_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Body>
    <loginResponse>
      <!-- some data is cutted -->
      <result><sessionId>FooSessionID</sessionId></result>
      <!-- some data is cutted -->
    </loginResponse>
  </soapenv:Body>
</soapenv:Envelope>"""

    SOAP_REQUEST = (
        """<?xml version="1.0" encoding="utf-8"?>"""
        "<soapenv:Envelope"
        """ xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/\""""
        """ xmlns:urn="urn:partner.soap.sforce.com">"""
        "<soapenv:Header><urn:CallOptions>"
        "<urn:client>RestForce</urn:client>"
        "<urn:defaultNamespace>sf</urn:defaultNamespace>"
        "</urn:CallOptions><urn:LoginScopeHeader>"
        "<urn:organizationId>foo_corp</urn:organizationId>"
        "</urn:LoginScopeHeader></soapenv:Header>"
        "<soapenv:Body><urn:login>"
        "<urn:username>foo_user</urn:username>"
        "<urn:password>foo_pass</urn:password>"
        "</urn:login></soapenv:Body>"
        "</soapenv:Envelope>")

    @mock.patch("notify.drivers.sfdc.requests")
    @mock.patch("notify.drivers.sfdc.LOG")
    def test_authenticate_soap(self, mock_log, mock_requests):
        auth = sfdc.OAuth2("foo_id", "foo_secret", "foo_user", "foo_pass",
                           organizationId="foo_corp")
        mock_resp = mock.Mock(text=self.SIMPLIFIED_SOAP_RESPONSE)
        mock_requests.post.return_value = mock_resp
        self.assertEqual({"access_token": "FooSessionID",
                          "instance_url": "https://login.salesforce.com"},
                         auth.authenticate_soap())
        mock_resp.raise_for_status.assert_called_once_with()
        headers = {"SOAPAction": "login", "Charset": "UTF-8",
                   "Content-Type": "text/xml"}
        mock_requests.post.assert_called_once_with(
            "https://login.salesforce.com/services/Soap/u/36.0",
            self.SOAP_REQUEST, headers=headers, verify=None)

    @mock.patch("notify.drivers.sfdc.requests")
    @mock.patch("notify.drivers.sfdc.LOG")
    def test_authenticate_rest(self, mock_log, mock_requests):
        auth = sfdc.OAuth2("foo_id", "foo_secret", "foo_user", "foo_pass")
        mock_resp = mock.Mock()
        mock_resp.json.return_value = "foo_json"
        mock_requests.post.return_value = mock_resp
        self.assertEqual("foo_json", auth.authenticate_rest())
        mock_resp.raise_for_status.assert_called_once_with()
        expected = {"username": "foo_user", "client_secret": "foo_secret",
                    "password": "foo_pass", "grant_type": "password",
                    "client_id": "foo_id"}
        mock_requests.post.assert_called_once_with(
            "https://login.salesforce.com/services/oauth2/token",
            data=expected, verify=None)

    def test_authenticate_switches_to_soap(self):
        auth = sfdc.OAuth2("foo_id", "foo_secret", "foo_user", "foo_pass",
                           organizationId="foo_corp")
        auth.authenticate_soap = mock.Mock(return_value="soap_auth_result")
        auth.authenticate_rest = mock.Mock(return_value="dummy")
        self.assertEqual("soap_auth_result", auth.authenticate())
        auth.authenticate_soap.assert_called_once_with()
        self.assertFalse(auth.authenticate_rest.called)

    def test_authenticate_switches_to_rest(self):
        auth = sfdc.OAuth2("foo_id", "foo_secret", "foo_user", "foo_pass")
        auth.authenticate_soap = mock.Mock(return_value="dummy")
        auth.authenticate_rest = mock.Mock(return_value="rest_auth_result")
        self.assertEqual("rest_auth_result", auth.authenticate())
        auth.authenticate_rest.assert_called_once_with()
        self.assertFalse(auth.authenticate_soap.called)


class ClientTestCase(test.TestCase):

    def setUp(self):
        super(ClientTestCase, self).setUp()
        self.auth = mock.Mock()
        self.auth.authenticate.return_value = {"access_token": "foo_token",
                                               "instance_url": "foo_url"}

    def test_authenticate(self):
        client = sfdc.Client(self.auth)
        self.assertIsNone(client.access_token)
        self.assertIsNone(client.instance_url)
        self.assertIsNone(client.authenticate())
        self.assertEqual("foo_token", client.access_token)
        self.assertEqual("foo_url", client.instance_url)

    @mock.patch("notify.drivers.sfdc.requests")
    @mock.patch("notify.drivers.sfdc.LOG")
    def test__request(self, mock_log, mock_requests):
        mock_resp = mock.Mock(status_code=200, text="some data")
        mock_resp.json.return_value = {"json": 42}
        mock_requests.request.return_value = mock_resp

        client = sfdc.Client(self.auth)
        result = client._request("POST", "/foo/bar",
                                 headers={"Spam": "Quiz"}, foo=42)
        headers = {"Content-Type": "application/json",
                   "Authorization": "Bearer foo_token", "Spam": "Quiz"}
        mock_requests.request.assert_called_once_with(
            "POST", "foo_url/foo/bar", headers=headers, verify=None, foo=42)
        self.assertEqual((200, {"json": 42}, None), result)

    @mock.patch("notify.drivers.sfdc.requests")
    @mock.patch("notify.drivers.sfdc.LOG")
    def test__request_raises(self, mock_log, mock_requests):
        mock_requests.request.side_effect = ValueError

        client = sfdc.Client(self.auth)
        result = client._request("POST", "/foo/bar",
                                 headers={"Spam": "Quiz"}, foo=42)
        self.assertEqual((None, None, None), result)

    @mock.patch("notify.drivers.sfdc.requests")
    @mock.patch("notify.drivers.sfdc.LOG")
    def test__request_with_empty_response(self, mock_log, mock_requests):
        mock_resp = mock.Mock(status_code=200, text="")
        mock_resp.json.return_value = {"json": 42}
        mock_requests.request.return_value = mock_resp

        client = sfdc.Client(self.auth)
        result = client._request("POST", "/foo/bar",
                                 headers={"Spam": "Quiz"}, foo=42)
        self.assertEqual((200, {}, None), result)

    @mock.patch("notify.drivers.sfdc.requests")
    @mock.patch("notify.drivers.sfdc.LOG")
    def test__request_json_raises(self, mock_log, mock_requests):
        mock_resp = mock.Mock(status_code=200, text="some response body")
        mock_resp.json.side_effect = ValueError
        mock_requests.request.return_value = mock_resp

        client = sfdc.Client(self.auth)
        result = client._request("POST", "/foo/bar",
                                 headers={"Spam": "Quiz"}, foo=42)
        self.assertEqual((200, {}, None), result)

    @mock.patch("notify.drivers.sfdc.requests")
    @mock.patch("notify.drivers.sfdc.LOG")
    def test__request_got_error(self, mock_log, mock_requests):
        mock_resp = mock.Mock(status_code=400, text="some data")
        mock_resp.json.return_value = [{"errorCode": "FOO",
                                        "message": "Foo!"}]
        mock_requests.request.return_value = mock_resp

        client = sfdc.Client(self.auth)
        result = client._request("POST", "/foo/bar",
                                 headers={"Spam": "Quiz"}, foo=42)
        expected = (
            400, [{"errorCode": "FOO", "message": "Foo!"}], ("FOO", "Foo!"))
        self.assertEqual(expected, result)

    @mock.patch("notify.drivers.sfdc.requests")
    @mock.patch("notify.drivers.sfdc.LOG")
    def test__request_got_invalid_session_id(self, mock_log, mock_requests):
        mock_resp = mock.Mock(status_code=400, text="some data")
        mock_resp.json.return_value = [{"errorCode": "INVALID_SESSION_ID",
                                        "message": "Foo!"}]
        mock_requests.request.return_value = mock_resp

        client = sfdc.Client(self.auth)
        result = client._request("POST", "/foo/bar", foo=42)
        expected = (400,
                    [{"errorCode": "INVALID_SESSION_ID", "message": "Foo!"}],
                    ("INVALID_SESSION_ID", "Foo!"))
        self.assertEqual(expected, result)
        self.assertEqual(4, len(mock_requests.request.mock_calls))

    @mock.patch("notify.drivers.sfdc.json.dumps", return_value="json_data")
    def test_create_feeditem(self, mock_dumps):
        client = sfdc.Client(self.auth)
        client._request = mock.Mock(return_value="response")
        self.assertEqual("response", client.create_feeditem("feeditem_data"))
        client._request.assert_called_once_with(
            "POST", "/services/data/v36.0/sobjects/FeedItem",
            data="json_data")
        mock_dumps.assert_called_once_with("feeditem_data")

    @mock.patch("notify.drivers.sfdc.json.dumps", return_value="json_data")
    def test_create_case(self, mock_dumps):
        client = sfdc.Client(self.auth)
        client._request = mock.Mock(return_value="response")
        self.assertEqual("response", client.create_case("case_data"))
        client._request.assert_called_once_with(
            "POST", "/services/data/v36.0/sobjects/Case", data="json_data")
        mock_dumps.assert_called_once_with("case_data")

    @mock.patch("notify.drivers.sfdc.json.dumps", return_value="json_data")
    def test_update_case(self, mock_dumps):
        client = sfdc.Client(self.auth)
        client._request = mock.Mock(return_value="response")
        self.assertEqual("response", client.update_case(42, "case_data"))
        client._request.assert_called_once_with(
            "PATCH", "/services/data/v36.0/sobjects/Case/42",
            data="json_data")
        mock_dumps.assert_called_once_with("case_data")

    def test_get_case(self):
        client = sfdc.Client(self.auth)
        client._request = mock.Mock(return_value="response")
        self.assertEqual("response", client.get_case(42))
        client._request.assert_called_once_with(
            "GET", "/services/data/v36.0/sobjects/Case/42")


class DriverTestCase(test.TestCase):

    @mock.patch("notify.drivers.sfdc.Client")
    @mock.patch("notify.drivers.sfdc.OAuth2")
    @mock.patch("notify.drivers.sfdc.json.dumps")
    @mock.patch("notify.drivers.sfdc.LOG")
    def test_notify(self, mock_log, mock_dumps, mock_oauth, mock_client):
        mock_dumps.return_value = "json_data"
        driver = sfdc.Driver({"username": "foo_user", "password": "foo_pass",
                              "client_id": "c_id", "client_secret": "c_sec"})
        driver.client.create_case = mock.Mock(
            return_value=(200, {"id": "case_id"}, None))
        driver.client.create_feeditem = mock.Mock(
            return_value=(201, "", None))

        self.assertTrue(driver.notify(self.payload))

        case = {"IsMosAlert__c": "true",
                "Alert_Priority__c": "060 Informational",
                "Description": "This is a test data.",
                "Alert_Host__c": "John Doe",
                "Alert_Service__c": "Hooray!",
                "Environment2__c": "farfaraway",
                "Alert_ID__c": "farfaraway|Hooray!|John Doe",
                "Subject": "farfaraway|Hooray!|John Doe"}
        driver.client.create_case.assert_called_once_with(case)
        calls = [mock.call({"Status": "New",
                            "Alert_Id": "farfaraway|Hooray!|John Doe",
                            "Alert_Priority": "060 Informational",
                            "Description": "This is a test data.",
                            "Cloud_ID": "farfaraway"},
                           indent=2, sort_keys=True)]
        self.assertEqual(calls, mock_dumps.mock_calls)
        feeditem = {"Body": "json_data", "Visibility": "AllUsers",
                    "ParentId": "case_id"}
        driver.client.create_feeditem.assert_called_once_with(feeditem)

    @mock.patch("notify.drivers.sfdc.Client")
    @mock.patch("notify.drivers.sfdc.OAuth2")
    @mock.patch("notify.drivers.sfdc.json.dumps")
    @mock.patch("notify.drivers.sfdc.LOG")
    def test_notify_with_affected_hosts_and_duplicated_case(
            self, mock_log, mock_dumps, mock_oauth, mock_client):
        mock_dumps.return_value = "json_data"
        driver = sfdc.Driver({"username": "foo_user", "password": "foo_pass",
                              "client_id": "c_id", "client_secret": "c_sec"})
        driver.client.create_case = mock.Mock(
            return_value=(400, [{"message": "Duplicate case: foo_id"}],
                          ("DUPLICATE_VALUE", "dummy")))
        dup_case = {"Status": "Foo status", "Subject": "Foo subject"}
        driver.client.get_case = mock.Mock(return_value=(200, dup_case, None))
        driver.client.update_case = mock.Mock(return_value=(200, {}, None))
        driver.client.create_feeditem = mock.Mock(
            return_value=(201, "", None))

        self.payload["affected_hosts"] = ["foo.srv", "bar.srv"]
        self.assertTrue(driver.notify(self.payload))

        calls = [mock.call({"Status": "Foo status",
                            "Alert_Id": "farfaraway|Hooray!|John Doe",
                            "Alert_Priority": "060 Informational",
                            "Description": "This is a test data.",
                            "Cloud_ID": "farfaraway"},
                           indent=2, sort_keys=True)]
        self.assertEqual(calls, mock_dumps.mock_calls)
        feeditem = {"Body": "json_data", "Visibility": "AllUsers",
                    "ParentId": "foo_id"}
        driver.client.create_feeditem.assert_called_once_with(feeditem)
