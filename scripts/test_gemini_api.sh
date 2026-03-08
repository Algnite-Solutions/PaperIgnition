API_KEY="${GEMINI_API_KEY}"

# The API endpoint for the gemini-2.5-flash-preview-09-2025 model
URL="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${API_KEY}"

# The data payload (a simple "Hello" prompt)
DATA_PAYLOAD='{
  "contents": [{
    "parts":[{
      "text": "Hello, world!"
    }]
  }]
}'

# Make the POST request with curl
# -X POST specifies the HTTP method
# -H "Content-Type: application/json" sets the content type header
# -d "${DATA_PAYLOAD}" provides the JSON data for the request body
# "${URL}" is the full URL with your API key
curl -X POST \
     -H "Content-Type: application/json" \
     -d "${DATA_PAYLOAD}" \
     "${URL}"