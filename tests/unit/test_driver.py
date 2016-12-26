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
from tests.unit import test


class ModuleTestCase(test.TestCase):

    @mock.patch("notify.driver.importlib.import_module")
    def test_get_driver(self, mock_import_module):
        foo, bar = mock.Mock(), mock.Mock()
        foo.Driver.return_value = "foo_driver"
        bar.Driver.return_value = "bar_driver"
        mock_import_module.side_effect = [foo, bar]

        driver.DRIVERS = {}
        foo_ins = driver.get_driver("foo", {"arg": 123})
        bar_ins = driver.get_driver("bar", {"arg": 321})
        self.assertEqual("foo_driver", foo_ins)
        self.assertEqual("bar_driver", bar_ins)
        self.assertEqual({"foo": foo.Driver, "bar": bar.Driver},
                         driver.DRIVERS)
        foo.Driver.assert_called_once_with({"arg": 123})
        foo.Driver.validate_config.assert_called_once_with({"arg": 123})
        bar.Driver.assert_called_once_with({"arg": 321})
        bar.Driver.validate_config.assert_called_once_with({"arg": 321})
        self.assertEqual([mock.call("notify.drivers.foo"),
                          mock.call("notify.drivers.bar")],
                         mock_import_module.mock_calls)

        foo.Driver.validate_config.side_effect = ValueError
        self.assertRaises(RuntimeError, driver.get_driver, "foo", {"arg": 1})
        foo.Driver.validate_config.side_effect = None

        driver.DRIVERS["foo"] = mock.Mock(return_value="cached_foo_driver")
        self.assertEqual("cached_foo_driver",
                         driver.get_driver("foo", {"arg": 123}))

        mock_import_module.side_effect = ImportError
        self.assertRaises(RuntimeError, driver.get_driver, "spam", {"arg": 1})


class DriverTestCase(test.TestCase):

    def test_validate_payload(self):
        self.assertIsNone(driver.Driver.validate_payload(self.payload))
        del self.payload["region"]
        self.assertRaises(ValueError,
                          driver.Driver.validate_payload, self.payload)

    def test_validate_config(self):
        self.assertIsNone(driver.Driver.validate_config({}))
        for cfg in (None, [], 42, "foo"):
            self.assertRaises(ValueError, driver.Driver.validate_config, cfg)

    def test_notify(self):
        drv = driver.Driver({})
        self.assertRaises(NotImplementedError, drv.notify, self.payload)
