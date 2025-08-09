import requests

# Test locally on the EC2 instance
url = "http://127.0.0.1:5001/products"
response = requests.get(url)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")