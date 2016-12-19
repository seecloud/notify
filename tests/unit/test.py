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
import testtools

from notify import main


class TestCase(testtools.TestCase):

    def setUp(self):
        super(TestCase, self).setUp()
        self.client = main.app.test_client()
        self.addCleanup(mock.patch.stopall)

    def get(self, *args, **kwargs):
        rv = self.client.get(*args, **kwargs)
        return rv.status_code, json.loads(rv.data.decode())

    def post(self, *args, **kwargs):
        rv = self.client.post(*args, **kwargs)
        return rv.status_code, json.loads(rv.data.decode())
