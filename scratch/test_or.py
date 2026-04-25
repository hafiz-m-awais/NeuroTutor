import os
import requests
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("OPENROUTER_API_KEY")
print(f"Key loaded: '{key}'")

# Simple test request to OpenRouter
response = requests.get(
    url="https://openrouter.ai/api/v1/auth/key",
    headers={"Authorization": f"Bearer {key}"}
)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
