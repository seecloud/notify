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

from email.mime import text as mime_text
import logging
import smtplib

from notify import driver

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)


class Driver(driver.Driver):
    """Mail notification driver."""

    CONFIG_SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema",
        "type": "object",
        "properties": {
            "sender_domain": {"type": "string"},
            "recipients": {"type": "array", "minItems": 1},
            "smtp_host": {"type": "string"},
            "smtp_port": {"type": "integer"},
            "mimetype": {"enum": ["plain", "html"]},
        },
        "required": ["sender_domain"],
        "additionalProperties": False
    }

    def __init__(self, config):
        super(Driver, self).__init__(config)
        self._sender_domain = self.config["sender_domain"]
        self._recipients = self.config["recipients"]
        self._smtp_host = self.config.get("smtp_host", "localhost")
        self._smtp_port = self.config.get("smtp_port")
        self._mime = self.config.get("mimetype", "plain")

    def _sanitize_name(self, name):
        sanitized_name = ""
        for c in name.lower().replace("_", "-"):
            if c.isalnum() or c in "-.":
                sanitized_name += c
        return sanitized_name

    def notify(self, payload):
        subject = "{}: {}".format(payload["who"], payload["what"])
        if payload.get("affected_hosts"):
            subject += " ({})".format(",".join(payload["affected_hosts"]))

        sender = "{}@{}".format(self._sanitize_name(payload["region"]),
                                self._sender_domain)

        msg = mime_text.MIMEText(payload["description"], self._mime)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = self._recipients[0]
        smtp = smtplib.SMTP(host=self._smtp_host, port=self._smtp_port)
        try:
            fails = smtp.sendmail(sender, self._recipients, msg.as_string())
            for recipient, err in fails.items():
                LOG.error("Fail to notify {} via email: {}", recipient, err)
            # NOTE(maretskiy): True is returned in case of non-empty `fails',
            #     because smtp.sendmail returns if there is at least one
            #     recipient successfully got a messag.
            #     But in case of total failure it raises some exception.
        finally:
            smtp.quit()
        return True
