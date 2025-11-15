"""General utility functions for DataForge platform."""

import hashlib
import json
import os
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

T = TypeVar("T")


def retry_on_failure(
    max_attempts: int = 3,
    wait_multiplier: int = 1,
    wait_max: int = 10,
    exceptions: tuple = (Exception,),
):
    """
    Decorator to retry function on failure with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        wait_multiplier: Multiplier for exponential backoff
        wait_max: Maximum wait time between retries (seconds)
        exceptions: Tuple of exceptions to retry on

    Example:
        @retry_on_failure(max_attempts=3)
        def fetch_data_from_api():
            # API call that might fail
            pass
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=wait_multiplier, max=wait_max),
        retry=retry_if_exception_type(exceptions),
    )


def timer(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to measure and log function execution time.

    Example:
        @timer
        def slow_function():
            time.sleep(1)
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        print(f"{func.__name__} took {duration:.2f} seconds")
        return result

    return wrapper


def generate_id(prefix: str = "", length: int = 8) -> str:
    """
    Generate a unique ID with optional prefix.

    Args:
        prefix: Prefix for the ID
        length: Length of random portion

    Returns:
        str: Generated ID

    Example:
        id = generate_id(prefix="pipe", length=8)
        # Returns: "pipe-1a2b3c4d"
    """
    import secrets

    random_part = secrets.token_hex(length // 2)
    if prefix:
        return f"{prefix}-{random_part}"
    return random_part


def generate_hash(data: Union[str, bytes, Dict], algorithm: str = "sha256") -> str:
    """
    Generate hash for data.

    Args:
        data: Data to hash (string, bytes, or dict)
        algorithm: Hash algorithm (md5, sha1, sha256, etc.)

    Returns:
        str: Hex digest of hash

    Example:
        hash_val = generate_hash({"key": "value"})
    """
    if isinstance(data, dict):
        data = json.dumps(data, sort_keys=True).encode()
    elif isinstance(data, str):
        data = data.encode()

    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return hasher.hexdigest()


def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.

    Args:
        dict1: Base dictionary
        dict2: Dictionary to merge (overwrites dict1)

    Returns:
        dict: Merged dictionary

    Example:
        merged = deep_merge({"a": {"b": 1}}, {"a": {"c": 2}})
        # Returns: {"a": {"b": 1, "c": 2}}
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def parse_size(size_str: str) -> int:
    """
    Parse human-readable size string to bytes.

    Args:
        size_str: Size string (e.g., "10MB", "1.5GB")

    Returns:
        int: Size in bytes

    Example:
        bytes = parse_size("10MB")  # Returns: 10485760
    """
    size_str = size_str.strip().upper()
    units = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3,
        "TB": 1024 ** 4,
    }

    for unit, multiplier in units.items():
        if size_str.endswith(unit):
            number = float(size_str[: -len(unit)])
            return int(number * multiplier)

    raise ValueError(f"Invalid size string: {size_str}")


def format_size(size_bytes: int) -> str:
    """
    Format bytes to human-readable size.

    Args:
        size_bytes: Size in bytes

    Returns:
        str: Human-readable size

    Example:
        size = format_size(10485760)  # Returns: "10.0 MB"
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def safe_get(
    dictionary: Dict[str, Any],
    path: str,
    default: Any = None,
    separator: str = ".",
) -> Any:
    """
    Safely get nested dictionary value using dot notation.

    Args:
        dictionary: Dictionary to search
        path: Dot-separated path (e.g., "user.profile.name")
        default: Default value if path not found
        separator: Path separator

    Returns:
        Any: Value at path or default

    Example:
        name = safe_get({"user": {"profile": {"name": "John"}}}, "user.profile.name")
    """
    keys = path.split(separator)
    value = dictionary

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default

    return value


def chunk_list(items: list, chunk_size: int) -> list[list]:
    """
    Split list into chunks of specified size.

    Args:
        items: List to chunk
        chunk_size: Size of each chunk

    Returns:
        list: List of chunks

    Example:
        chunks = chunk_list([1, 2, 3, 4, 5], 2)
        # Returns: [[1, 2], [3, 4], [5]]
    """
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def timestamp_to_iso(timestamp: Union[int, float]) -> str:
    """
    Convert Unix timestamp to ISO 8601 string.

    Args:
        timestamp: Unix timestamp (seconds or milliseconds)

    Returns:
        str: ISO 8601 formatted datetime

    Example:
        iso = timestamp_to_iso(1609459200)
        # Returns: "2021-01-01T00:00:00Z"
    """
    # Handle milliseconds
    if timestamp > 10**10:
        timestamp = timestamp / 1000

    dt = datetime.fromtimestamp(timestamp)
    return dt.isoformat() + "Z"


def iso_to_timestamp(iso_str: str) -> float:
    """
    Convert ISO 8601 string to Unix timestamp.

    Args:
        iso_str: ISO 8601 formatted datetime

    Returns:
        float: Unix timestamp

    Example:
        ts = iso_to_timestamp("2021-01-01T00:00:00Z")
    """
    iso_str = iso_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(iso_str)
    return dt.timestamp()


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing/replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename

    Example:
        safe = sanitize_filename("my/file:name?.txt")
        # Returns: "my_file_name_.txt"
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    return filename


def ensure_dir(path: str) -> str:
    """
    Ensure directory exists, create if necessary.

    Args:
        path: Directory path

    Returns:
        str: The path (for chaining)

    Example:
        ensure_dir("/tmp/data/processed")
    """
    os.makedirs(path, exist_ok=True)
    return path


def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    Load JSON file safely.

    Args:
        file_path: Path to JSON file

    Returns:
        dict: Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(data: Dict[str, Any], file_path: str, indent: int = 2) -> None:
    """
    Save data to JSON file.

    Args:
        data: Data to save
        file_path: Path to save file
        indent: JSON indentation

    Example:
        save_json_file({"key": "value"}, "/tmp/data.json")
    """
    ensure_dir(os.path.dirname(file_path))
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


class Singleton:
    """
    Singleton base class.

    Example:
        class MyConfig(Singleton):
            def __init__(self):
                self.value = "config"

        config1 = MyConfig()
        config2 = MyConfig()
        assert config1 is config2
    """

    _instances: Dict[type, Any] = {}

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__new__(cls)
        return cls._instances[cls]
