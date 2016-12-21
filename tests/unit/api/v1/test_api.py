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

import mock

from notify import driver
from tests.unit import test


class ApiTestCase(test.TestCase):

    def test_send_notification_request_without_data(self):
        code, resp = self.post("/api/v1/notify/foo")
        self.assertEqual(400, code)
        self.assertEqual({"error": "Missed Payload"}, resp)

    def test_send_notification_request_with_bad_payload(self):
        code, resp = self.post("/api/v1/notify/foo",
                               data=json.dumps({"strange": "data"}))
        self.assertEqual(400, code)
        self.assertIn("Bad Payload:", resp["error"])

    @mock.patch("notify.api.v1.api.config")
    def test_send_notification_no_backend(self, mock_config):
        mock_config.get_config.return_value = {"notify_backends": {}}
        code, resp = self.post("/api/v1/notify/foo",
                               data=json.dumps(self.payload))
        self.assertEqual(400, code)
        self.assertEqual({"error": "Unexpected backends: foo"}, resp)

    @mock.patch("notify.api.v1.api.config")
    @mock.patch("notify.driver.get_driver")
    def test_send_notification(self, mock_get_driver, mock_config):
        mock_config.get_config.return_value = {
            "notify_backends": {b: {"drvname": {"conf": 42}}
                                for b in ("backend1", "backend2")}}
        mock_get_driver.return_value.notify.return_value = True
        code, resp = self.post("/api/v1/notify/backend1,backend2",
                               data=json.dumps(self.payload))

        self.assertEqual(200, code)
        expected = {"payload": self.payload,
                    "total": 2, "errors": 0, "failed": 0, "passed": 2,
                    "result": {"backend1": {"drvname": {"status": True}},
                               "backend2": {"drvname": {"status": True}}}}
        self.assertEqual(expected, resp)

    @mock.patch("notify.api.v1.api.config")
    @mock.patch("notify.driver.get_driver")
    def test_send_notification_got_error(self, mock_get_driver, mock_config):
        mock_config.get_config.return_value = {
            "notify_backends": {"b1": {"foo": {"x": 123}}}}
        mock_get_driver.return_value.notify.side_effect = ValueError
        code, resp = self.post("/api/v1/notify/b1",
                               data=json.dumps(self.payload))
        self.assertEqual(200, code)
        expected = {
            "payload": self.payload,
            "total": 1, "errors": 1, "failed": 0, "passed": 0,
            "result": {"b1": {"foo": {"error": "Something has went wrong!"}}}}
        self.assertEqual(expected, resp)

    @mock.patch("notify.api.v1.api.config")
    @mock.patch("notify.driver.get_driver")
    def test_send_notification_got_explained_error(self, mock_get_driver,
                                                   mock_config):
        mock_config.get_config.return_value = {
            "notify_backends": {"b1": {"bar": {"x": 123}}}}
        side_effect = driver.ExplainedError("Spam!")
        mock_get_driver.return_value.notify.side_effect = side_effect
        code, resp = self.post("/api/v1/notify/b1",
                               data=json.dumps(self.payload))
        self.assertEqual(200, code)
        expected = {"payload": self.payload,
                    "total": 1, "errors": 1, "failed": 0, "passed": 0,
                    "result": {"b1": {"bar": {"error": "Spam!"}}}}
        self.assertEqual(expected, resp)
