import urllib.request
import json

user = {
    "name": "Rahul",
    "email": "buyer@example.com",
    "password": "test123",
    "role": "buyer",
    "location": "Bhubaneswar"
}

data = json.dumps(user).encode("utf-8")

request = urllib.request.Request(
    "http://127.0.0.1:5000/users",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

response = urllib.request.urlopen(request)

print(response.read().decode())