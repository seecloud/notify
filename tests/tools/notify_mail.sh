curl -XPOST -H 'Content-Type: application/json' http://localhost:5000/api/v1/notify/mail -d '
{
  "region": "sender-username",
  "description": "This is a test message that sent via mail notification driver!",
  "severity": "INFO",
  "who": "John Doe",
  "what": "This is a subject of test message"
}'
