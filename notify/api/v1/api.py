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

from notify import config
from notify.drivers.salesforce import driver as sf_driver


LOG = logging.getLogger("api")
LOG.setLevel(config.get_config().get("logging", {}).get("level", "INFO"))


def json_f(x):
    return json.dumps(x, sort_keys=True, indent=4)


bp = flask.Blueprint("notify", __name__)


def send_not_implemented(backend, driver, content):
    LOG.debug("Not implemented: backend={} driver={}".format(backend, driver))
    return(409, {"result": "not implewmented"})


def send_to_backend(backend, content):
    send_success = []
    send_error = []
    code = 200
    notify_backend_config = config.get_config()['notify_backends'][backend]

    LOG.debug("Backend: {}".format(backend))
    LOG.debug("Backend Config: {}".format(json_f(notify_backend_config)))

    for driver, driver_config in notify_backend_config.iteritems():
        LOG.debug("Driver: {}".format(driver))
        LOG.debug("Driver Config: {}".format(driver_config))

        if driver_config['type'] == 'salesforce':
            resp_code, result = sf_driver.send_to_salesforce(
                backend=backend, driver=driver, content=content)
        else:
            resp_code, result = send_not_implemented(backend=backend,
                                                     driver=driver,
                                                     content=content)

        LOG.debug("Results: resp_code: {} , result: {}".format(resp_code,
                                                               result))

        if (resp_code != 200):
            LOG.debug("If at least one error => code=409")
            code = resp_code
            send_error.append({driver: result})
        else:
            send_success.append({driver: result})

    LOG.debug("Errors: {}".format(send_error))
    LOG.debug("Success: {}".format(send_success))
    LOG.debug("Code: {}".format(code))

    return code, send_success, send_error


@bp.route("/notify/<backends>", methods=["POST"])
def send_notification(backends):

    LOG.debug("Backends: {}".format(backends))
    res = {}
    err = False
    content = flask.request.get_json(force=True)
    notify_backends_config = config.get_config()['notify_backends']

    not_supported_backends = []
    result_success = []
    result_error = []

    for backend in backends.split(","):
        if backend in notify_backends_config:
            LOG.debug("Backend: {}".format(backend))
            resp_code, send_success, send_error = send_to_backend(
                backend=backend,
                content=content)

            LOG.debug("Backend: {}: Send result: Success: {}, "
                      "Errors: {}, Code: {}".format(backend,
                                                    send_success,
                                                    send_error,
                                                    resp_code))
            if send_error:
                result_error.append({"backend": backend,
                                     "status": resp_code,
                                     "result": send_error})
            if send_success:
                result_success.append({"backend": backend,
                                       "status": resp_code,
                                       "result": send_success})

        else:
            LOG.debug("Backend {} is not configured".format(backend))
            not_supported_backends.append(backend)

    if not_supported_backends:
        result_error.append({"not_supported_backends":
                             not_supported_backends})
        resp_code = 409

    if (resp_code != 200):
        err = True

    res['status'] = resp_code

    if result_error:
        res['errors'] = result_error

    if result_success:
        res['success'] = result_success

    res['has_errors'] = err

    return flask.jsonify({"result": res})


def get_blueprints():
    return [["", bp]]
