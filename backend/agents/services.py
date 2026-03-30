import os
import subprocess
from pathlib import Path
import sys
from unittest import result
from django.conf import settings

PROJECT_ROOT = Path(settings.BASE_DIR).parent
AGENTS_DATA_DIR = PROJECT_ROOT / "AgentsData"
SETUP_SCRIPT = PROJECT_ROOT / "Setup" / "build_all_embeddings.py"


def list_branches():
    if not AGENTS_DATA_DIR.exists():
        return []

    return [
        folder.name
        for folder in AGENTS_DATA_DIR.iterdir()
        if folder.is_dir()
    ]


def create_branch(name: str):

    branch_path = AGENTS_DATA_DIR / name

    if branch_path.exists():
        raise Exception("La rama ya existe")

    branch_path.mkdir(parents=True)


def list_branch_files(branch: str):

    branch_path = AGENTS_DATA_DIR / branch

    if not branch_path.exists():
        raise Exception("La rama no existe")

    return [
        file.name
        for file in branch_path.iterdir()
        if file.suffix.lower() == ".pdf"
    ]


def save_pdfs(branch: str, files):

    branch_path = AGENTS_DATA_DIR / branch

    if not branch_path.exists():
        raise Exception("La rama no existe")

    saved_files = []

    for f in files:

        file_path = branch_path / f.name

        with open(file_path, "wb+") as dest:
            for chunk in f.chunks():
                dest.write(chunk)

        saved_files.append(f.name)

    return saved_files


def rebuild_embeddings():

    process = subprocess.run(
        [sys.executable, str(SETUP_SCRIPT)],
        stdout=sys.stdout,
        stderr=sys.stderr
    )

    if process.returncode != 0:
        raise Exception("Error regenerando embeddings")

    return "Proceso completado"

def delete_branch(branch: str):

    branch_path = AGENTS_DATA_DIR / branch

    if not branch_path.exists():
        raise Exception("La rama no existe")

    for file in branch_path.iterdir():
        file.unlink()

    branch_path.rmdir()

    return True

def delete_pdf(branch: str, filename: str):

    branch_path = AGENTS_DATA_DIR / branch

    if not branch_path.exists():
        raise Exception("La rama no existe")

    file_path = branch_path / filename

    if not file_path.exists():
        raise Exception("El archivo no existe")

    file_path.unlink()

    return True