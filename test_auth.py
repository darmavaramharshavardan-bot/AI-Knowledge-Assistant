from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token
)


password = "testpassword123"


# Hash password
hashed = hash_password(password)

print("Password hashed successfully:")
print(hashed)


# Verify password
valid = verify_password(
    password,
    hashed
)

print("\nPassword verification:", valid)


# Create JWT
token = create_access_token(
    user_id=1
)

print("\nJWT created successfully:")
print(token)