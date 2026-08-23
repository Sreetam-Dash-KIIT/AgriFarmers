import urllib.request
import json

product = {
   "farmer_id": 1,
    "crop": "Tomato",
    "quantity": 500,
    "price": 25,
    "location": "Bhubaneswar"
}

data = json.dumps(product).encode("utf-8")

request = urllib.request.Request(
    "http://127.0.0.1:5000/products",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

response = urllib.request.urlopen(request)

print(response.read().decode())