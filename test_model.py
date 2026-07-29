import os
import google.generativeai as genai

env_path = ".env"
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")

api_key = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=api_key)

try:
    model = genai.GenerativeModel("gemini-3.6-flash")
    resp = model.generate_content("Hello! Say hi.")
    print("Success with gemini-3.6-flash:", resp.text)
except Exception as e:
    print("Error with gemini-3.6-flash:", e)
