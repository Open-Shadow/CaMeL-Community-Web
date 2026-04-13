"""Go-compatible bcrypt password hasher for Django."""
import bcrypt
from django.contrib.auth.hashers import BasePasswordHasher


class GoBCryptPasswordHasher(BasePasswordHasher):
    """
    Handles bcrypt hashes stored by Go (golang.org/x/crypto/bcrypt).
    Go stores raw bcrypt: $2a$10$...
    Django's built-in BCryptPasswordHasher expects: bcrypt$$2b$...
    """
    algorithm = "go_bcrypt"

    def salt(self):
        return bcrypt.gensalt().decode("ascii")

    def encode(self, password, salt):
        if isinstance(salt, str):
            salt = salt.encode("ascii")
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("ascii")

    def verify(self, password, encoded):
        if isinstance(encoded, str):
            encoded = encoded.encode("ascii")
        return bcrypt.checkpw(password.encode("utf-8"), encoded)

    def safe_summary(self, encoded):
        return {"algorithm": self.algorithm, "hash": encoded[:20] + "..."}

    def must_update(self, encoded):
        return False
