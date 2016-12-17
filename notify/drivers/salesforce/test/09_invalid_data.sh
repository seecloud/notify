#!/bin/bash 

NOTIFY_API_URL=${NOTIFY_API_URL-"http://127.0.0.1:5000/api/v1/notify"}

curl -v  ${NOTIFY_API_URL}/ok -XPOST -d '
{
    "description":   {
    "affected_hosts": "INVALID_FORMAT",
    "description": "Test     The CPU usage is too high (controller node).             (CRITICAL, rule=avg(cpu_idle)=5, current=1.65, host=ic3-ctl01-scc)                     No datapoint have been received over the last 60 seconds                     (UNKNOWN, rule=min(fs_space_percent_free[fs=/var/log])2, \n",
    "long_date_time": "Fri Dec 2 14:14:53 UTC 2016",
    "service": "glance1"
    },
    "severity":    "INFO",
    "who":         "00-global-clusters-SIT12",
    "what":        "glance1"
}
'
