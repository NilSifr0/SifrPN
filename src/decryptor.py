from cryptography.fernet import Fernet


class Decryptor:
    def decrypt(self, key: str | bytes, token: str | bytes):
        f = Fernet(key)
        return f.decrypt(token)
