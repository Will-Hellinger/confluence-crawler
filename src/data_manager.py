import os
import json


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