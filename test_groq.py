import os
import json
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

print(f"[+] Loaded GROQ_API_KEY: {GROQ_API_KEY[:8]}...")

def test_groq():
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are unlockED AI. Return JSON response format with a field 'status': 'success'."},
            {"role": "user", "content": "Hello! Confirm connection."}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"[+] Status Code: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            content = result["choices"][0]["message"]["content"]
            print("[+] Groq Response JSON:")
            print(content)
            return True
        else:
            print(f"[-] Error Output: {resp.text}")
            return False
    except Exception as e:
        print(f"[-] Exception: {e}")
        return False

if __name__ == "__main__":
    test_groq()
