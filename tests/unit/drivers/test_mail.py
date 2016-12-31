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
from notify.drivers import mail
from tests.unit import test


class MailDriverTestCase(test.TestCase):

    def test___init__(self):
        self.assertRaises(KeyError, mail.Driver, {})
        self.assertRaises(KeyError, mail.Driver, {"sender_domain": "foo"})
        self.assertRaises(KeyError, mail.Driver, {"recipients": ["bar"]})
        drv = mail.Driver({"sender_domain": "foo", "recipients": ["bar"]})
        self.assertIsInstance(drv, driver.Driver)

    def _driver(self, **config):
        config.setdefault("sender_domain", "foo_domain")
        config.setdefault("recipients", ["foo@example.org"])
        return mail.Driver(config)

    def _payload(self):
        return {"description": "Message body",
                "region": "fooenv42",
                "severity": "INFO",
                "what": "Foo subject",
                "who": "John Doe"}

    def test_sanitize_name(self):
        drv = self._driver()
        self.assertEqual("foo123", drv._sanitize_name("foo123"))
        self.assertEqual("foo-12-3.bar",
                         drv._sanitize_name(" foo- 1+2_3 . bar "))

    @mock.patch("notify.drivers.mail.smtplib")
    @mock.patch("notify.drivers.mail.mime_text.MIMEText")
    @mock.patch("notify.drivers.mail.LOG")
    def test_notify(self, mock_log, mock_mimetext, mock_smtplib):
        mock_mimetext.return_value.as_string.return_value = "message body"
        mock_smtp = mock.Mock()
        mock_smtp.sendmail.return_value = {}
        mock_smtplib.SMTP.return_value = mock_smtp
        drv = self._driver()
        self.assertTrue(drv.notify(self._payload()))

        calls = [mock.call("Subject", "John Doe: Foo subject"),
                 mock.call("From", "fooenv42@foo_domain"),
                 mock.call("To", "foo@example.org")]
        self.assertEqual(calls,
                         mock_mimetext.return_value.__setitem__.mock_calls)
        mock_mimetext.assert_called_once_with("Message body", "plain")
        mock_smtplib.SMTP.assert_called_once_with(host="localhost", port=None)
        mock_smtp.sendmail.assert_called_once_with(
            "fooenv42@foo_domain", ["foo@example.org"], "message body")
        mock_smtp.quit.assert_called_once_with()
        self.assertFalse(mock_log.error.called)

    @mock.patch("notify.drivers.mail.smtplib")
    @mock.patch("notify.drivers.mail.mime_text.MIMEText")
    @mock.patch("notify.drivers.mail.LOG")
    def test_notify_some_fails(self, mock_log, mock_mimetext, mock_smtplib):
        mock_mimetext.return_value.as_string.return_value = "message body"
        mock_smtp = mock.Mock()
        mock_smtp.sendmail.return_value = {"foo": "error details"}
        mock_smtplib.SMTP.return_value = mock_smtp
        drv = self._driver()
        payload = self._payload()
        payload["affected_hosts"] = ["srv1", "srv2"]
        self.assertTrue(drv.notify(payload))

        calls = [mock.call("Subject", "John Doe: Foo subject (srv1,srv2)"),
                 mock.call("From", "fooenv42@foo_domain"),
                 mock.call("To", "foo@example.org")]
        self.assertEqual(calls,
                         mock_mimetext.return_value.__setitem__.mock_calls)
        mock_mimetext.assert_called_once_with("Message body", "plain")
        mock_smtplib.SMTP.assert_called_once_with(host="localhost", port=None)
        mock_smtp.sendmail.assert_called_once_with(
            "fooenv42@foo_domain", ["foo@example.org"], "message body")
        mock_smtp.quit.assert_called_once_with()
        mock_log.error.assert_called_once_with(
            "Fail to notify {} via email: {}", "foo", "error details")
