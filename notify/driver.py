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

import importlib
import logging

import jsonschema


DRIVERS = {}


def get_driver(name, conf):
    """Get driver by name.

    :param name: driver name
    :param conf: dict, driver configuration
    :rtype: Driver
    :raises: RuntimeError
    """
    global DRIVERS
    if name not in DRIVERS:
        try:
            module = importlib.import_module("notify.drivers." + name)
            DRIVERS[name] = module.Driver
        except (ImportError, AttributeError):
            mesg = "Unexpected driver: '{}'".format(name)
            logging.error(mesg)
            raise RuntimeError(mesg)

    driver_cls = DRIVERS[name]

    try:
        driver_cls.validate_config(conf)
    except ValueError as e:
        mesg = "Bad configuration for driver '{}'".format(name)
        logging.error("{}: {}".format(mesg, e))
        raise RuntimeError(mesg)

    return driver_cls(conf)


class ExplainedError(Exception):
    """Error that should be delivered to end user."""


class Driver(object):
    """Base for notification drivers."""

    PAYLOAD_SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema",
        "type": "object",
        "properties": {
            "region": {"type": "string"},
            "description": {"type": "string"},
            "severity": {
                "enum": ["OK", "INFO", "UNKNOWN", "WARNING",
                         "CRITICAL", "DOWN"]},
            "who": {"type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "uniqueItems": True},
            "what": {"type": "string"},
            "affected_hosts": {"type": "array"}
        },
        "required": ["region", "description", "severity", "who", "what"],
        "additionalProperties": False
    }

    CONFIG_SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema",
        "type": "object"
    }

    @classmethod
    def validate_payload(cls, payload):
        """Payload validation.

        :param payload: notification payload
        :raises: ValueError
        """
        try:
            jsonschema.validate(payload, cls.PAYLOAD_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            raise ValueError(str(e))

    @classmethod
    def validate_config(cls, conf):
        """Driver configuration validation.

        :param conf: driver configuration
        :raises: ValueError
        """
        try:
            jsonschema.validate(conf, cls.CONFIG_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            raise ValueError(str(e))

    def __init__(self, config):
        self.config = config

    def notify(self, payload):
        """Send notification alert.

        This method must be overriden by specific driver implementation.

        :param payload: alert data
        :type payload: dict, validated api.PAYLOAD_SCHEMA
        :returns: status whether notification is successful
        :rtype: bool
        """
        raise NotImplementedError()
