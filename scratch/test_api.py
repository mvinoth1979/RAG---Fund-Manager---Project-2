import requests

url = "http://localhost:8000/api/chat"
payload = {"query": "What is the NAV of The Wealth Company Small Cap Fund?"}
response = requests.post(url, json=payload)
print(response.json())
