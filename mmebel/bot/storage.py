"""FSM holatlarini Firebase'da saqlash.

MemoryStorage server qayta ishga tushganda (Render'da tez-tez) foydalanuvchining
yarim yo'ldagi zakazini yo'qotardi. Bu ombor xotira keshi + Firebase'ga yozish bilan ishlaydi.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Mapping

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey

from ..store import Store

log = logging.getLogger(__name__)
_TTL = 6 * 3600  # 6 soatdan eski holatlar e'tiborsiz qoldiriladi


class PersistentStorage(BaseStorage):
    def __init__(self, store: Store, root: str = "fsm"):
        self.store = store
        self.root = root
        self._cache: dict[str, dict] = {}

    def _path(self, key: StorageKey) -> str:
        return f"{self.root}/{key.bot_id}_{key.chat_id}_{key.user_id}_{key.destiny}"

    async def _load(self, key: StorageKey) -> dict:
        path = self._path(key)
        rec = self._cache.get(path)
        if rec is None:
            try:
                raw = await self.store.get(path)
            except Exception as e:  # noqa: BLE001
                log.warning("FSM o'qib bo'lmadi: %s", e)
                raw = None
            rec = {"state": None, "data": {}, "ts": time.time()}
            if isinstance(raw, dict) and time.time() - float(raw.get("ts", 0)) < _TTL:
                rec["state"] = raw.get("state")
                try:
                    rec["data"] = json.loads(raw.get("data") or "{}")
                except (TypeError, ValueError):
                    rec["data"] = {}
            self._cache[path] = rec
        return rec

    async def _save(self, key: StorageKey, rec: dict) -> None:
        path = self._path(key)
        rec["ts"] = time.time()
        self._cache[path] = rec
        try:
            if rec["state"] is None and not rec["data"]:
                await self.store.delete(path)
            else:
                await self.store.set(path, {"state": rec["state"], "ts": rec["ts"],
                                            "data": json.dumps(rec["data"], ensure_ascii=False, default=str)})
        except Exception as e:  # noqa: BLE001
            log.warning("FSM saqlanmadi: %s", e)

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        rec = await self._load(key)
        rec["state"] = state.state if isinstance(state, State) else state
        await self._save(key, rec)

    async def get_state(self, key: StorageKey) -> str | None:
        return (await self._load(key))["state"]

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        rec = await self._load(key)
        rec["data"] = dict(data)
        await self._save(key, rec)

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        return dict((await self._load(key))["data"])

    async def close(self) -> None:
        self._cache.clear()
