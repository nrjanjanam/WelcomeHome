import os

from database import hash_password


salt = os.urandom(16).hex()
print(f"{salt}:{hash_password('susan_t', salt)}")
