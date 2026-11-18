import json
import logging


def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")


def job_key(job):
    return job.get("link", "").split("?")[0]


def dedupe_jobs(jobs):
    """依 link 去重,保留第一筆。"""
    seen, result = set(), []
    for job in jobs:
        key = job_key(job)
        if key and key not in seen:
            seen.add(key)
            result.append(job)
    return result


def load_seen(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen(path, seen):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=0)
