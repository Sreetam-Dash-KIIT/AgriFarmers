import urllib.request
import json

login = {
    "email": "farmer@test.com",
    "password": "test123"
}

data = json.dumps(login).encode("utf-8")

request = urllib.request.Request(
    "http://127.0.0.1:5000/login",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

response = urllib.request.urlopen(request)

print(response.read().decode())