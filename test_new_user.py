import urllib.request
import json

user = {
    "name": "Test Farmer",
    "email": "farmer@test.com",
    "password": "test123",
    "role": "farmer",
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