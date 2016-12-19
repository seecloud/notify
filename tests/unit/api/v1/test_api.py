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

from tests.unit import test


class ApiTestCase(test.TestCase):

    def test_send_notification_bad_request(self):
        status, data = self.post("/api/v1/notify/foo", data={"var1": "data1"})
        self.assertEqual(400, status)
        self.assertTrue(data["errors"])
        self.assertEqual(data["status"], 400)
        self.assertEqual(data["results"], [])

    def _get_payload(self):
        return {
            "region": "My region",
            "description": "something went wrong",
            "severity": "WARNING",
            "who": ["host-1", "host-2"],
            "what": "glance"
        }

    @mock.patch("notify.api.v1.api.config")
    def test_send_notification_no_backand(self, mock_config):
        mock_config.get_config.return_value = {"notify_backends": {}}

        payload = self._get_payload()
        status, data = self.post("/api/v1/notify/foo",
                                 data={"payload": json.dumps(payload)})

        self.assertEqual(200, status)
        self.assertTrue(data["errors"])
        self.assertEqual(1, len(data["results"]))
        self.assertEqual(404, data["results"][0]["status"])
        self.assertEqual(True, data["results"][0]["errors"])

    @mock.patch("notify.api.v1.api.driver.importlib")
    @mock.patch("notify.api.v1.api.config")
    def test_send_notification(self, mock_config, mock_importlib):
        mock_driver = mock_importlib.import_module.return_value.Driver

        mock_config.get_config.return_value = {
            "notify_backends": {"boo": {"some_driver": {"a": "42"}}}
        }

        payload = self._get_payload()
        status, data = self.post("/api/v1/notify/boo",
                                 data={"payload": json.dumps(payload)})

        self.assertEqual(200, status)
        self.assertFalse(data["errors"], data["description"])
        self.assertEqual(1, len(data["results"]))
        self.assertEqual(200, data["results"][0]["status"])

        mock_importlib.import_module.assert_called_once_with(
            ".some_driver.driver", "notify.drivers")

        mock_driver.assert_called_once_with({"a": "42"})
        mock_driver.return_value.notify.assert_called_once_with(payload)
