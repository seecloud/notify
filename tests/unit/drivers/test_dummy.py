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

from notify import driver
from notify.drivers import dummy_err
from notify.drivers import dummy_err_explained
from notify.drivers import dummy_fail
from notify.drivers import dummy_pass
from notify.drivers import dummy_random
from tests.unit import test


class DummyErrDriverTestCase(test.TestCase):

    def test_notify(self):
        e = self.assertRaises(ValueError,
                              dummy_err.Driver({}).notify, self.payload)
        self.assertEqual("This error message is for logging only!", str(e))


class DummyErrExplainedDriverTestCase(test.TestCase):

    def test_notify(self):
        e = self.assertRaises(driver.ExplainedError,
                              dummy_err_explained.Driver({}).notify,
                              self.payload)
        self.assertEqual("This error message must appear in API response!",
                         str(e))


class DummyFailDriverTestCase(test.TestCase):

    def test_notify(self):
        self.assertFalse(dummy_fail.Driver({}).notify(self.payload))


class DummyPassDriverTestCase(test.TestCase):

    def test_notify(self):
        self.assertTrue(dummy_pass.Driver({}).notify(self.payload))


class DummyRandomDriverTestCase(test.TestCase):

    @mock.patch("notify.drivers.dummy_random.random.random")
    def test_notify(self, mock_random):
        drv = dummy_random.Driver({})

        mock_random.return_value = 0.49
        self.assertTrue(drv.notify(self.payload))

        mock_random.return_value = 0.51
        self.assertFalse(drv.notify(self.payload))

        drv = dummy_random.Driver({"probability": 0.53})
        self.assertTrue(drv.notify(self.payload))
