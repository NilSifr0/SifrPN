from cryptography.fernet import Fernet


class Encryptor:
    def _create_key(self) -> bytes:
        # fernet used base64.urlsafe_b64encode(os.urandom(32))
        key = Fernet.generate_key()

        return key

    def _encrypt_input(self, key: bytes, input_string) -> bytes:
        # fernet used base64.urlsafe_b64encode(basic_parts + hmac)
        f = Fernet(key)
        token = f.encrypt(input_string.encode())

        return token

    def encrypt(self, input_string: str) -> tuple[bytes, bytes]:
        key = self._create_key()
        token = self._encrypt_input(key, input_string)

        return key, token
