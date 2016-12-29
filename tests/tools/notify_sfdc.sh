#!/bin/sh

REGION=some_region
USE_AFFECTED_HOSTS=0


if test ${USE_AFFECTED_HOSTS} -ne 0
then
    BODY='
{
  "region": "'${REGION}'",
  "description": "This is a dummy payload, just for testing.",
  "severity": "INFO",
  "who": "JohnDoe",
  "what": "Hi there!",
  "affected_hosts": ["foo.srv", "bar.srv"]
}'
else
    BODY='
{
  "region": "'${REGION}'",
  "description": "This is a dummy payload, just for testing.",
  "severity": "INFO",
  "who": "JohnDoe",
  "what": "Hooray!"
}'
fi

set -x

curl -XPOST -H 'Content-Type: application/json' http://localhost:5000/api/v1/notify/sf -d "${BODY}"
