import jwt

token = jwt.encode({
    "sub": "admin",
    "email": "admin@unlocked.local",
    "role": "admin",
    "student_id": None
}, "mock_secret", algorithm="HS256")

print("Token:", token)

decoded = jwt.decode(token, options={"verify_signature": False})
print("Decoded:", decoded)
