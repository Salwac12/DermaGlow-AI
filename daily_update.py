# ==========================================================
# DERMAGLOW AI
# AUTOMATIC DAILY PRODUCT UPDATE
#
# Developer: Salwa Choudhari
#
# Features:
# - SQLite database backup
# - Automatic product importer execution
# - Import logs
# - Error reporting
# - Protection against overlapping imports
# ==========================================================

import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

DATABASE = BASE_DIR / "dermaglow.db"

IMPORTER = BASE_DIR / "product_importer.py"

BACKUP_DIR = BASE_DIR / "backups"

LOG_DIR = BASE_DIR / "logs"

LOCK_FILE = BASE_DIR / ".daily_import.lock"


# ==========================================================
# CREATE REQUIRED FOLDERS
# ==========================================================

def prepare_folders():

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


# ==========================================================
# CREATE DATABASE BACKUP
# ==========================================================

def backup_database():

    if not DATABASE.exists():

        print(
            "No existing database found. "
            "Skipping backup."
        )

        return None

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_path = (
        BACKUP_DIR
        / f"dermaglow_backup_{timestamp}.db"
    )

    source = sqlite3.connect(
        str(DATABASE),
        timeout=30
    )

    destination = sqlite3.connect(
        str(backup_path)
    )

    try:

        with destination:

            source.backup(
                destination
            )

    finally:

        destination.close()

        source.close()

    print(
        f"Database backup created: {backup_path.name}"
    )

    return backup_path


# ==========================================================
# RUN PRODUCT IMPORTER
# ==========================================================

def run_importer():

    if not IMPORTER.exists():

        raise FileNotFoundError(
            "product_importer.py was not found."
        )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    log_path = (
        LOG_DIR
        / f"import_{timestamp}.log"
    )

    print()
    print("Starting product importer...")
    print()

    with open(
        log_path,
        "w",
        encoding="utf-8"
    ) as log_file:

        log_file.write(
            "DermaGlow AI Daily Import\n"
        )

        log_file.write(
            f"Started: {datetime.now()}\n\n"
        )

        log_file.flush()

        result = subprocess.run(

            [
                sys.executable,
                str(IMPORTER)
            ],

            cwd=str(BASE_DIR),

            stdout=log_file,

            stderr=subprocess.STDOUT,

            check=False

        )

        log_file.write(
            f"\nFinished: {datetime.now()}\n"
        )

        log_file.write(
            f"Exit code: {result.returncode}\n"
        )

    print(
        f"Import log saved: {log_path.name}"
    )

    if result.returncode != 0:

        raise RuntimeError(
            "Product importer failed. "
            "Check the latest file in the logs folder."
        )

    print(
        "Product importer process completed."
    )

    return log_path


# ==========================================================
# MAIN DAILY UPDATE
# ==========================================================

def main():

    prepare_folders()

    print()
    print("====================================")
    print("DERMAGLOW AI - DAILY UPDATE")
    print("====================================")

    print(
        "Started:",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    # Prevent two overlapping executions.
    # Exclusive file creation is atomic.

    try:

        lock_fd = os.open(
            str(LOCK_FILE),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY
        )

    except FileExistsError:

        print(
            "Another import may already be running."
        )

        print(
            "If an earlier run crashed, verify "
            "that it has stopped before deleting "
            ".daily_import.lock."
        )

        return 1

    try:

        with os.fdopen(
            lock_fd,
            "w",
            encoding="utf-8"
        ) as lock:

            lock.write(
                f"Started: {datetime.now()}\n"
            )

            lock.write(
                f"PID: {os.getpid()}\n"
            )

        backup_database()

        run_importer()

        print()
        print("====================================")
        print("DAILY UPDATE PROCESS COMPLETED")
        print("====================================")

        print(
            "Finished:",
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        return 0

    except Exception as error:

        print()
        print("UPDATE FAILED")
        print(str(error))

        return 1

    finally:

        LOCK_FILE.unlink(
            missing_ok=True
        )


# ==========================================================
# START
# ==========================================================

if __name__ == "__main__":

    sys.exit(
        main()
    )