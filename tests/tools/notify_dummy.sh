curl -XPOST -H 'Content-Type: application/json' http://localhost:5000/api/v1/notify/dummy,dummyrand,dummyerr -d '
{
  "region": "farfaraway",
  "description": "This is a dummy payload, just for testing.",
  "severity": "INFO",
  "who": "JohnDoe",
  "what": "Hooray!"
}'
