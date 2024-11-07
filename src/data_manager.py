import json


def check_exists(file_path: str | None) -> bool:
    """
    Check if the file exists.

    :param file_path: The path to the file.
    :return: True if the file exists, False otherwise.
    """
    
    if not file_path:
        return False

    try:
        with open(file_path, 'r') as f:
            return True
    except FileNotFoundError:
        return False


def load_json(file_path: str | None) -> dict | None:
    """
    Load a JSON file.

    :param file_path: The path to the JSON file.
    :return: The JSON file as a dictionary.
    """

    if check_exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
        
    return None