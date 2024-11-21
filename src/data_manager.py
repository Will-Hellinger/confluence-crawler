import os
import json
import base64
import cryptography.fernet


def generate_key(master_password: str) -> bytes:
    """
    Generates a key from the master password.

    :param master_password: Master password to generate the key.
    :return: Key generated from the master password.
    """

    return base64.urlsafe_b64encode(master_password.encode().ljust(32))


def encrypt_data(data: str, key: bytes) -> str:
    """
    Encrypt data using a key.

    :param data: The data to encrypt.
    :param key: The key to use for encryption.
    :return: The encrypted data.
    """

    fernet = cryptography.fernet.Fernet(key)
    encrypted_data = fernet.encrypt(data.encode())

    return encrypted_data


def decrypt_data(encrypted_data: bytes, key: bytes) -> str:
    """
    Decrypts the data using the key.

    :param encrypted_data: Encrypted data to decrypt.
    :param key: Key to use for decryption.
    :return: Decrypted data.
    """

    fernet = cryptography.fernet.Fernet(key)
    decrypted_data = fernet.decrypt(encrypted_data).decode()

    return decrypted_data


def load_json(file_path: str | None) -> dict | None:
    """
    Load a JSON file.

    :param file_path: The path to the JSON file.
    :return: The JSON file as a dictionary.
    """

    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
        
    return None


def dump_json(file_path: str, data: dict) -> None:
    """
    Dump a dictionary to a JSON file.

    :param file_path: The path to the JSON file.
    :param data: The data to dump.
    """

    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)