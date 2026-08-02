import os
import requests

# Test firestore emulator directly via REST API to see what students exist
url = "http://127.0.0.1:8080/v1/projects/dummy-project-id/databases/(default)/documents/students"
try:
    r = requests.get(url)
    print(r.text)
except Exception as e:
    print(e)
