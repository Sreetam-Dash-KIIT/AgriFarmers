import urllib.request
import json

interest = {
    "buyer_id": 2,
    "product_id": 3
}

data = json.dumps(interest).encode("utf-8")

request = urllib.request.Request(
    "http://127.0.0.1:5000/interests",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

response = urllib.request.urlopen(request)

print(response.read().decode())