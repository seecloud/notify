Notification as a Service
=========================

The service is a simple gateway that delivers notifications via configured backends.

.. contents::

Notification drivers
--------------------

Notification driver is a python code that knows how to send message to specific target.

For example, there is a driver named *dummy_pass* - this means that python module
*notify/drivers/dummy_pass.py* must exist and has class *Driver* properly implemented:

.. code::

  >>> from notify import driver
  >>> from notify.drivers import dummy_pass
  >>> issubclass(dummy_pass.Driver, driver.Driver)
  True

Since it is convenient to have ability to send message to several targets by single API call, the service actually operates with groups of drivers called *backends*.

Notification backends
---------------------

Backend is simple named group of notification drivers.

They configured in `notify_backends <#id1>`_ section of configuration file.

How to configure
----------------

Configuration file is specified via *NOTIFY_CONF* environment variable
and consists of these main parts: **flask**, **backend** and **notify_backends**.

flask
~~~~~

Section *flask* contains configuration for Flask application as described on
`official documentation <http://flask.pocoo.org/docs/0.11/config/>`_.

The only extra options are **HOST** and **PORT**.

backend
~~~~~~~~

Connection parameters to data storage.
Not in use currently, so this section can be omitted. 

notify_backends
~~~~~~~~~~~~~~~

This is the most important configuration section, since it describes notification backends.

Each configured backend groups some drivers with proper configuration.

The structure is the following:

.. code::

  {
    <backend_name>: {
      <driver_name>: { driver configuration parameters },
      <another_driver_name>: { driver configuration parameters }
    },
    ...
  }

Backend name can be arbitrary and affects only API calls where it is explicitly specified.

For example, there is a backend *foo* with drivers *bar* and *spam*:

.. code::

  "notify_backends": {
    "foo": {
      "bar": {"key": "value"},
      "spam": {"quiz": 42}
    }
  }

So if there is an API call *POST /api/v1/notify/foo* with specific message in request body, then this message will be sent by drivers *bar* and *spam*.

configuration example
~~~~~~~~~~~~~~~~~~~~~

Here is a simple configuration file example with `dummy drivers <#id2>`_ grouped into 3 backends:

.. code::

  {
      "flask": {
          "PORT": 5000,
          "HOST": "0.0.0.0"
      },
      "notify_backends": {
          "dummy": {
              "dummy_pass": {},
              "dummy_fail": {}
          },
          "dummy-rnd": {
              "dummy_random": {"probability": 0.5}
          },
          "dummy-err": {
              "dummy_err": {},
              "dummy_err_explained": {}
          }
      }
  }

How to run
----------

Initially, let's download and install the service into virtualenv:

.. code::

  $ virtualenv notify_env
  $ . notify_env/bin/activate
  $ git clone https://github.com/seecloud/notify/
  $ cd notify
  $ pip install -r requirements.txt

Now save configuration file (given above) as *config.json* and set proper env variable to its path:

.. code::

  export NOTIFY_CONF=$(pwd)/config.json

Finally, start the service (at http://localhost:5000):

.. code::

  $ python notify/main.py

How to test
-----------

When started, service provides RESTful API for notifications.
Let's use `CURL <https://curl.haxx.se/>`_ command line utility for convenience.

Dummy drivers
~~~~~~~~~~~~~

Dummy drivers are always available and are ready for use immediately,
however they do not actually send alerts.

These drivers are suitable for demonstrations and smoke testing.

Since the configuration already uses dummy drivers, let's see how this works.

There is an API call to all configured backends *dummy*, *dummy-rnd* and *dummy-err*:

.. code::

  $ curl -XPOST -H 'Content-Type: application/json' http://localhost:5000/api/v1/notify/dummy,dummy-rnd,dummy-err -d '
  {
    "region": "farfaraway",
    "description": "This is a dummy payload, just for testing.",
    "severity": "INFO",
    "who": "JohnDoe",
    "what": "Hooray!"
  }'

The response contains results from all 5 dummy drivers:

.. code::

  {
    "errors": 2,
    "failed": 1,
    "passed": 2,
    "payload": {
      "description": "This is a dummy payload, just for testing.",
      "region": "farfaraway",
      "severity": "INFO",
      "what": "Hooray!",
      "who": "JohnDoe"
    },
    "result": {
      "dummy": {
        "dummy_fail": {
          "status": false
        },
        "dummy_pass": {
          "status": true
        }
      },
      "dummy-err": {
        "dummy_err": {
          "error": "Something has went wrong!"
        },
        "dummy_err_explained": {
          "error": "This error message must appear in API response!"
        }
      },
      "dummy-rnd": {
        "dummy_random": {
          "status": true
        }
      }
    },
    "total": 5
  }

SFDC driver
~~~~~~~~~~~

There is a *SFDC* driver which transfers notifications to `SalesForce <https://www.salesforce.com/>`_ customers.

Let's configure backend and send notification to SalesForce.

**NOTE: To get started with this, obtain proper SFDC OAuth2 credentials.**

Create a *config.json* file with the content, having all values filled with proper credentials:

.. code::

  {
      "flask": {
          "PORT": 5000,
          "HOST": "0.0.0.0"
      },
      "notify_backends": {
          "sf": {
              "sfdc": {
                  "auth_url": "https://<specific-domain>.salesforce.com",
                  "username": "<username>",
                  "password": "<password>",
                  "organization_id": "<organization-id>",
                  "client_id":  "<client-id>",
                  "client_secret": "<client-secret-key>"
              }
          }
      }
  }

If not already done, set proper env variable to *config.json* path:

.. code::

  export NOTIFY_CONF=$(pwd)/config.json

Now send notification to the service with the following command.
Do not forget to specify proper environment in place of *<environment-id>*:

.. code::

  $ curl -XPOST -H 'Content-Type: application/json' localhost:5000/api/v1/notify/sf -d '
  {
    "region": "<environment-id>",
    "description": "This is a dummy payload, just for testing.",
    "severity": "INFO",
    "who": "JohnDoe",
    "what": "Hooray!"
  }
  '

The response includes *"status": true* so the notification is successful:

.. code::

  {
    "errors": 0,
    "failed": 0,
    "passed": 1,
    "payload": {
      "description": "This is a dummy payload, just for testing.",
      "region": "<environment-id>",
      "severity": "INFO",
      "what": "Hooray!",
      "who": "JohnDoe"
    },
    "result": {
      "sf": {
        "sfdc": {
          "status": true
        }
      }
    },
    "total": 1
  }
