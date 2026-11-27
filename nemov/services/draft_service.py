"""
nemov/services/draft_service.py
Universal, silent local draft persistence with 3-second debounce for unfinished forms.
Supports multi-instance drafts, atomic disk writes with AppData mirroring,
and live Sidebar Notification Bar synchronization.
"""
import json
import os
import re
import time
import uuid
import weakref
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

import config
from nemov.auth.authentication import CurrentUser
from nemov.utils.jalali_date import gregorian_to_shamsi

DEFAULT_DRAFT_DEBOUNCE_MS = 3000  # 3 seconds after typing stops


class _DraftNotifier(QObject):
    drafts_changed = pyqtSignal()


_NOTIFIER_INSTANCE: Optional[_DraftNotifier] = None
_ACTIVE_BINDERS: "weakref.WeakSet[DebouncedDraftBinder]" = weakref.WeakSet()


def get_draft_notifier() -> _DraftNotifier:
    global _NOTIFIER_INSTANCE
    if _NOTIFIER_INSTANCE is None:
        _NOTIFIER_INSTANCE = _DraftNotifier()
    return _NOTIFIER_INSTANCE


def _get_trainer_scope(trainer_scope: Optional[str] = None) -> str:
    if trainer_scope:
        clean = re.sub(r"[^0-9A-Za-z_\-]", "", str(trainer_scope))
        if clean:
            return clean
    u = CurrentUser.get()
    if u:
        phone = getattr(u, "phone", None)
        if phone:
            digits = re.sub(r"[^0-9A-Za-z_\-]", "", str(phone).replace(" ", ""))
            if digits:
                return digits
        uid = getattr(u, "id", None)
        if uid is not None:
            return f"uid_{uid}"
    return "default"


def _sanitize_draft_id(draft_id: str) -> str:
    clean = re.sub(r"[^0-9A-Za-z_\-.]", "_", str(draft_id or "").strip())
    return clean or f"draft_{uuid.uuid4().hex[:10]}"


def _get_drafts_dirs() -> list[Path]:
    primary = Path(config.DATA_DIR) / "drafts"
    appdata = Path(config.APPDATA_DATA_DIR) / "drafts"
    primary.mkdir(parents=True, exist_ok=True)
    if appdata != primary:
        appdata.mkdir(parents=True, exist_ok=True)
        return [primary, appdata]
    return [primary]


def _atomic_write_json(path: Path, data: dict) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        return True
    except Exception:
        return False


def _now_shamsi_hm() -> str:
    from datetime import datetime
    now = datetime.now()
    return f"{gregorian_to_shamsi(now.date())} {now.strftime('%H:%M')}"


class DraftService:
    """Manages local JSON drafts across all editable sections of Nemov."""

    @staticmethod
    def notify_changed():
        try:
            get_draft_notifier().drafts_changed.emit()
        except Exception:
            pass

    @staticmethod
    def save_draft(
        draft_id: str,
        section: str,
        section_title: str,
        title: str,
        summary: str,
        payload: dict,
        member_id: Optional[int] = None,
        member_name: str = "",
        entity_id: Optional[int] = None,
        trainer_scope: Optional[str] = None,
        emit_signal: bool = True,
    ) -> Optional[dict]:
        safe_id = _sanitize_draft_id(draft_id)
        scope = _get_trainer_scope(trainer_scope)
        record = {
            "draft_id": safe_id,
            "trainer_scope": scope,
            "section": section,
            "section_title": section_title,
            "title": (title or section_title).strip(),
            "summary": (summary or "").strip(),
            "member_id": member_id,
            "member_name": (member_name or "").strip(),
            "entity_id": entity_id,
            "updated_at": time.time(),
            "updated_shamsi": _now_shamsi_hm(),
            "payload": payload if isinstance(payload, dict) else {},
        }
        wrote_any = False
        for d_dir in _get_drafts_dirs():
            if _atomic_write_json(d_dir / f"{safe_id}.json", record):
                wrote_any = True
        if wrote_any and emit_signal:
            DraftService.notify_changed()
        return record if wrote_any else None

    @staticmethod
    def get_draft(draft_id: str) -> Optional[dict]:
        safe_id = _sanitize_draft_id(draft_id)
        for d_dir in _get_drafts_dirs():
            p = d_dir / f"{safe_id}.json"
            if p.exists():
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and data.get("draft_id") == safe_id:
                        return data
                except Exception:
                    continue
        return None

    @staticmethod
    def delete_draft(draft_id: str, emit_signal: bool = True) -> bool:
        if not draft_id:
            return False
        safe_id = _sanitize_draft_id(draft_id)
        removed = False
        for d_dir in _get_drafts_dirs():
            for p in (d_dir / f"{safe_id}.json", d_dir / f"{safe_id}.json.tmp"):
                if p.exists():
                    try:
                        p.unlink()
                        removed = True
                    except Exception:
                        pass
        if removed and emit_signal:
            DraftService.notify_changed()
        return removed

    @staticmethod
    def list_drafts(
        trainer_scope: Optional[str] = None,
        section: Optional[str] = None,
        exclude_draft_ids: Optional[set] = None,
    ) -> list[dict]:
        scope = _get_trainer_scope(trainer_scope)
        excluded = set(exclude_draft_ids or ())
        by_id: dict[str, dict] = {}
        for d_dir in _get_drafts_dirs():
            if not d_dir.exists():
                continue
            for p in d_dir.glob("*.json"):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if not isinstance(data, dict):
                    continue
                did = data.get("draft_id")
                if not did or did in excluded:
                    continue
                d_scope = data.get("trainer_scope", "default")
                if d_scope != scope and not (scope == "default" and len(_get_drafts_dirs()) > 0):
                    if d_scope != "default":
                        continue
                if section and data.get("section") != section:
                    continue
                existing = by_id.get(did)
                if existing is None or float(data.get("updated_at", 0)) > float(existing.get("updated_at", 0)):
                    by_id[did] = data

        items = list(by_id.values())
        items.sort(key=lambda x: float(x.get("updated_at", 0)), reverse=True)
        return items

    @staticmethod
    def clear_all_for_trainer(trainer_scope: Optional[str] = None):
        for item in DraftService.list_drafts(trainer_scope=trainer_scope):
            DraftService.delete_draft(item["draft_id"], emit_signal=False)
        DraftService.notify_changed()

    @staticmethod
    def flush_all_binders() -> int:
        count = 0
        for binder in list(_ACTIVE_BINDERS):
            try:
                if binder.flush_now(emit_signal=False):
                    count += 1
            except RuntimeError:
                # Underlying Qt C++ object was already deleted
                continue
            except Exception:
                continue
        if count > 0:
            DraftService.notify_changed()
        return count


class DebouncedDraftBinder(QObject):
    """
    Reusable 3-second debounced draft controller attached to any editable view/dialog.
    Saves unfinished edits silently without UI interruption or toast spam.
    """

    def __init__(
        self,
        parent: QObject,
        section: str,
        section_title: str,
        get_payload_fn: Callable[[], dict],
        is_dirty_fn: Callable[[], bool],
        get_meta_fn: Callable[[], dict],
        draft_id: Optional[str] = None,
        debounce_ms: int = DEFAULT_DRAFT_DEBOUNCE_MS,
    ):
        super().__init__(parent)
        self.section = section
        self.section_title = section_title
        self._get_payload = get_payload_fn
        self._is_dirty = is_dirty_fn
        self._get_meta = get_meta_fn
        self.draft_id = _sanitize_draft_id(draft_id or f"{section}_{uuid.uuid4().hex[:10]}")
        self._suppress_depth = 0
        self._has_saved_file = DraftService.get_draft(self.draft_id) is not None

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(max(100, int(debounce_ms)))
        self.timer.timeout.connect(self.flush_now)

        _ACTIVE_BINDERS.add(self)

    def new_draft_id(self) -> str:
        self.draft_id = _sanitize_draft_id(f"{self.section}_{uuid.uuid4().hex[:10]}")
        self._has_saved_file = False
        return self.draft_id

    def set_draft_id(self, draft_id: str):
        self.draft_id = _sanitize_draft_id(draft_id)
        self._has_saved_file = DraftService.get_draft(self.draft_id) is not None

    @contextmanager
    def suspended(self):
        self._suppress_depth += 1
        try:
            yield
        finally:
            self._suppress_depth = max(0, self._suppress_depth - 1)

    def schedule(self):
        if self._suppress_depth > 0:
            return
        self.timer.start()

    def flush_now(self, emit_signal: bool = True) -> bool:
        if self.timer.isActive():
            self.timer.stop()
        if self._suppress_depth > 0:
            return False
        try:
            dirty = bool(self._is_dirty())
        except Exception:
            dirty = False

        if not dirty:
            if self._has_saved_file:
                self._has_saved_file = False
                DraftService.delete_draft(self.draft_id, emit_signal=emit_signal)
            return False

        try:
            payload = self._get_payload() or {}
            meta = self._get_meta() or {}
        except Exception:
            return False

        res = DraftService.save_draft(
            draft_id=self.draft_id,
            section=self.section,
            section_title=self.section_title,
            title=meta.get("title", self.section_title),
            summary=meta.get("summary", ""),
            payload=payload,
            member_id=meta.get("member_id"),
            member_name=meta.get("member_name", ""),
            entity_id=meta.get("entity_id"),
            emit_signal=emit_signal,
        )
        self._has_saved_file = res is not None
        return self._has_saved_file

    def clear_draft(self, rotate_id: bool = True, emit_signal: bool = True):
        if self.timer.isActive():
            self.timer.stop()
        DraftService.delete_draft(self.draft_id, emit_signal=emit_signal)
        self._has_saved_file = False
        if rotate_id:
            self.new_draft_id()
