"""Persist the set of announcement IDs already seen, so each is notified only once."""

import json
import os
from pathlib import Path


class SeenStore:
    """A JSON-file-backed set of announcement IDs, written atomically."""

    def __init__(self, path):
        self._path = Path(path)
        self._seen = self._load()

    def is_seen(self, listing_id):
        return listing_id in self._seen

    def mark_seen(self, listing_id):
        self.add_many([listing_id])

    def add_many(self, listing_ids):
        new_ids = set(listing_ids) - self._seen
        if new_ids:
            self._seen |= new_ids
            self._save()

    def __len__(self):
        return len(self._seen)

    def _load(self):
        if not self._path.exists():
            return set()

        try:
            return set(json.loads(self._path.read_text(encoding='utf-8')))
        except (ValueError, TypeError):
            return set()

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_name(f'{self._path.name}.tmp')
        tmp_path.write_text(json.dumps(sorted(self._seen)), encoding='utf-8')
        os.replace(tmp_path, self._path)


class BacklogCursor:
    """Remembers which page the backlog sweep resumes from, persisted across runs."""

    def __init__(self, path):
        self._path = Path(path)

    def page(self):
        try:
            return max(1, int(self._path.read_text(encoding='utf-8')))
        except (FileNotFoundError, ValueError):
            return 1

    def set_page(self, page):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_name(f'{self._path.name}.tmp')
        tmp_path.write_text(str(page), encoding='utf-8')
        os.replace(tmp_path, self._path)
