curl -XPOST -H 'Content-Type: application/json' localhost:5000/api/v1/notify/dummy,dummyrand,dummyerr -d '
{
  "region": "farfaraway",
  "description": "This is a dummy payload, just for testing.",
  "severity": "INFO",
  "who": ["Alice", "Bob"],
  "what": "Hooray!"
}'
