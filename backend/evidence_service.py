import hashlib
import os


def calculate_sha256(file_path: str) -> str:
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        while chunk := file.read(1024 * 1024):
            sha256.update(chunk)

    return sha256.hexdigest()


def generate_evidence_id() -> str:
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"EV-{timestamp}"