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

import flask
import jsonschema

from notify import config
from notify.drivers import driver


LOG = logging.getLogger("api")
LOG.setLevel(config.get_config().get("logging", {}).get("level", "INFO"))


bp = flask.Blueprint("notify", __name__)


PAYLOAD_SCHEMA = {
    "type": "object",
    "$schema": "http://json-schema.org/draft-04/schema",

    "properties": {
        "region": {
            "type": "string"
        },
        "description": {
            "type": "string"
        },
        "severity": {
            "enum": ["OK", "INFO", "UNKNOWN", "WARNING", "CRITICAL", "DOWN"]
        },
        "who": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "minItems": 1,
            "uniqueItems": True
        },
        "what": {
            "type": "string"
        }
    },
    "required": ["description", "region", "severity", "who", "what"],
    "additionalProperties": False
}


# NOTE(boris-42): Use here pool of resources
CACHE = {}


@bp.route("/notify/<backends>", methods=["POST"])
def send_notification(backends):
    global CACHE

    try:
        content = json.loads(flask.request.form['payload'])
        jsonschema.validate(content, PAYLOAD_SCHEMA)
    except Exception as e:
        return flask.jsonify({
            "errors": True,
            "status": 400,
            "description": "Wrong payload: %s" % str(e),
            "results": []
        }), 400

    conf = config.get_config()
    resp = {
        "errors": False,
        "status": 200,
        "description": "",
        "results": []
    }

    for backend in backends.split(","):
        result = {
            "backend": backend,
            "status": 200,
            "errors": False,
            "description": "",
            "results": []
        }
        if backend in conf["notify_backends"]:
            for dr, driver_cfg in conf["notify_backends"][backend].items():
                r = {
                    "backend": backend,
                    "driver": dr,
                    "error": False,
                    "status": 200
                }
                try:

                    driver_key = "%s.%s" % (backend, dr)
                    if driver_key not in CACHE:
                        # NOTE(boris-42): We should use here pool with locks
                        CACHE[driver_key] = driver.get_driver(dr)(driver_cfg)

                    # NOTE(boris-42): It would be smarter to call all drivers
                    #                 notify in parallel
                    CACHE[driver_key].notify(content)

                except Exception as e:
                    print(e)
                    r["status"] = 500
                    r["error"] = True
                    resp["errors"] = True
                    result["errors"] = True
                    r["description"] = ("Something went wrong %s.%s"
                                        % (backend, dr))

                result["results"].append(r)
        else:
            result["status"] = 404
            result["errors"] = True
            resp["errors"] = True
            result["description"] = "Backend %s not found" % backend

        resp["results"].append(result)

    return flask.jsonify(resp), resp["status"]


def get_blueprints():
    return [["", bp]]
