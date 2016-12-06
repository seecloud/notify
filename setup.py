#!/usr/bin/env python

from setuptools import setup

setup(name="notify",
      version="0.1",
      description="Notify service",
      url="https://github.com/seecloud/notify",
      author="<name>",
      author_email="<name>@mirantis.com",
      packages=["notify"],
      entry_points={
          "console_scripts": [
              "notify-api = notify.main:main"
          ],
      })
