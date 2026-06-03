"""
Correction Log — record every human correction so patterns can be detected
and eventually promoted into glossary/style/entity memory.

This is the learning signal. Corrections sit here first (unapproved),
then the user can promote them to approved memory.
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
from typing import Optional
from enum import Enum

#Feedback: groups[c.original_text] is a bit simplistic — we might want to group by both original_text and correction_type, so we can see if the same term is being corrected for different reasons (e.g. sometimes it's terminology, sometimes style)

class CorrectionStatus(str, Enum):
    PENDING = "pending"       # logged, not yet promoted
    PROMOTED = "promoted"     # user promoted to glossary/style/entity
    DISMISSED = "dismissed"   # user decided not to keep


class CorrectionType(str, Enum):
    TERMINOLOGY = "terminology"   # wrong term translation
    ENTITY = "entity"             # wrong name/pronoun
    STYLE = "style"               # tone/register issue
    FACTUAL = "factual"           # wrong in-world fact
    OTHER = "other"


@dataclass
class Correction:
    correction_id: str
    project_id: str
    chapter_or_doc: str           # e.g. "ch001", "chapter-3", "oneshot"
    source_lang: str
    target_lang: str
    correction_type: CorrectionType
    original_text: str            # what the AI produced
    corrected_text: str           # what the human changed it to
    context_snippet: str = ""     # surrounding sentence for context
    note: str = ""                # human's optional comment
    status: CorrectionStatus = CorrectionStatus.PENDING
    logged_at: str = ""
    promoted_to: str = ""         # e.g. "glossary", "style", "entity"

    def __post_init__(self):
        if not self.logged_at:
            self.logged_at = datetime.now().isoformat(timespec="seconds")


class CorrectionLog:
    """
    Append-only log of human corrections for one project.

    File lives at: memory_store/corrections/{project_id}.yaml
    (separate from glossaries/styles/entities — corrections are staging area only)
    """

    def __init__(self, project_id: str, store_root: str | Path = "memory_store/corrections"):
        self.project_id = project_id
        self.path = Path(store_root) / f"{project_id}.yaml"
        self._corrections: list[Correction] = []
        self._load()

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or []
        norm: list[dict] = []
        for c in raw:
            # Normalize enum fields which are stored as plain strings in YAML
            if "correction_type" in c and isinstance(c["correction_type"], str):
                try:
                    c["correction_type"] = CorrectionType(c["correction_type"])
                except Exception:
                    # leave as-is; dataclass will raise if invalid
                    pass
            if "status" in c and isinstance(c["status"], str):
                try:
                    c["status"] = CorrectionStatus(c["status"])
                except Exception:
                    pass
            norm.append(c)
        self._corrections = [Correction(**c) for c in norm]
        # Auto-deduplicate by correction_id (keep latest)
        dedup = {}

        for c in self._corrections:
            old = dedup.get(c.correction_id)

            if old is None:
                dedup[c.correction_id] = c
            else:
                # keep newer record
                if c.logged_at > old.logged_at:
                    dedup[c.correction_id] = c

        cleaned = list(dedup.values())

        # Persist cleaned state if duplicates existed
        if len(cleaned) != len(self._corrections):
            self._corrections = cleaned
            self.save()
        else:
            self._corrections = cleaned

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = []
        for c in self._corrections:
            d = asdict(c)
            # Convert Enum values to primitive strings so YAML is portable
            if isinstance(d.get("correction_type"), CorrectionType):
                d["correction_type"] = d["correction_type"].value
            if isinstance(d.get("status"), CorrectionStatus):
                d["status"] = d["status"].value
            data.append(d)
        self.path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def log(self, correction: Correction) -> None:
        """Append a new correction. Called automatically during human review."""
        # Avoid duplicate entries with the same correction_id.
        for i, c in enumerate(self._corrections):
            if c.correction_id == correction.correction_id:
                # Replace existing record (update), then save.
                self._corrections[i] = correction
                self.save()
                return
        self._corrections.append(correction)
        self.save()

    def promote(self, correction_id: str, promoted_to: str) -> bool:
        """Mark a correction as promoted (moved into approved memory elsewhere)."""
        for c in self._corrections:
            if c.correction_id == correction_id:
                c.status = CorrectionStatus.PROMOTED
                c.promoted_to = promoted_to
                self.save()
                return True
        return False

    def dismiss(self, correction_id: str) -> bool:
        """Mark correction as dismissed — won't become approved memory."""
        for c in self._corrections:
            if c.correction_id == correction_id:
                c.status = CorrectionStatus.DISMISSED
                self.save()
                return True
        return False

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def get_pending(
        self,
        correction_type: Optional[CorrectionType] = None,
    ) -> list[Correction]:
        result = [c for c in self._corrections if c.status == CorrectionStatus.PENDING]
        if correction_type:
            result = [c for c in result if c.correction_type == correction_type]
        return result

    def get_by_chapter(self, chapter_or_doc: str) -> list[Correction]:
        return [c for c in self._corrections if c.chapter_or_doc == chapter_or_doc]

    def get_repeated_patterns(self, min_count: int = 2) -> dict[str, list[Correction]]:
        """
        Find corrections where the same original_text was corrected multiple times.
        Useful for surfacing what should become a glossary/style rule.
        """
        from collections import defaultdict
        groups: dict[str, list[Correction]] = defaultdict(list)
        for c in self._corrections:
            if c.status != CorrectionStatus.DISMISSED:
                groups[c.original_text].append(c)
        return {k: v for k, v in groups.items() if len(v) >= min_count}

    def summary(self) -> dict:
        """Quick stats for CLI display."""
        pending = [c for c in self._corrections if c.status == CorrectionStatus.PENDING]
        promoted = [c for c in self._corrections if c.status == CorrectionStatus.PROMOTED]
        dismissed = [c for c in self._corrections if c.status == CorrectionStatus.DISMISSED]
        return {
            "total": len(self._corrections),
            "pending": len(pending),
            "promoted": len(promoted),
            "dismissed": len(dismissed),
            "repeated_patterns": len(self.get_repeated_patterns()),
        }

    def __len__(self) -> int:
        return len(self._corrections)

    def __repr__(self) -> str:
        s = self.summary()
        return f"<CorrectionLog project={self.project_id!r} total={s['total']} pending={s['pending']}>"