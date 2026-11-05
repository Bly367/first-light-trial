import csv
import shutil
from pathlib import Path


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def copy_raw(paths, raw_dir):
    raw_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        shutil.copyfile(path, raw_dir / Path(path).name)
