"""Ma'lumotlar ombori abstraksiyasi.

Ishlab chiqarishda Firebase Realtime Database, testlarda xotiradagi ombor ishlatiladi.
Barcha metodlar asinxron; Firebase SDK sinxron bo'lgani uchun alohida thread'da bajariladi.
"""
from __future__ import annotations

import asyncio
import copy
import json
import logging
import uuid
from typing import Any, Callable

log = logging.getLogger(__name__)


class Store:
    async def get(self, path: str) -> Any: ...
    async def set(self, path: str, value: Any) -> None: ...
    async def update(self, path: str, values: dict) -> None: ...
    async def push(self, path: str, value: Any) -> str: ...
    async def delete(self, path: str) -> None: ...
    async def transaction(self, path: str, fn: Callable[[Any], Any]) -> Any: ...
    async def get_last(self, path: str, n: int) -> Any: ...
    def new_key(self, path: str) -> str: ...


class FirebaseStore(Store):
    def __init__(self, db_module):
        self._db = db_module

    def _ref(self, path: str):
        return self._db.reference("/" + path.strip("/")) if path.strip("/") else self._db.reference("/")

    async def get(self, path: str) -> Any:
        return await asyncio.to_thread(self._ref(path).get)

    async def set(self, path: str, value: Any) -> None:
        await asyncio.to_thread(self._ref(path).set, value)

    async def update(self, path: str, values: dict) -> None:
        if values:
            await asyncio.to_thread(self._ref(path).update, values)

    async def push(self, path: str, value: Any) -> str:
        ref = await asyncio.to_thread(self._ref(path).push, value)
        return ref.key

    async def delete(self, path: str) -> None:
        await asyncio.to_thread(self._ref(path).delete)

    async def transaction(self, path: str, fn: Callable[[Any], Any]) -> Any:
        return await asyncio.to_thread(self._ref(path).transaction, fn)

    async def get_last(self, path: str, n: int) -> Any:
        """Push-kalitlar vaqt bo'yicha tartiblangan — oxirgi n ta yozuv."""
        return await asyncio.to_thread(self._ref(path).order_by_key().limit_to_last(n).get)

    def new_key(self, path: str) -> str:
        return self._ref(path).push().key  # mahalliy generatsiya, tarmoq so'rovisiz


class MemoryStore(Store):
    """Testlar uchun: Firebase semantikasiga yaqin xotiradagi ombor."""

    def __init__(self, data: dict | None = None):
        self.data: dict = copy.deepcopy(data) if data else {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _parts(path: str) -> list[str]:
        return [p for p in path.strip("/").split("/") if p]

    def _get(self, path: str):
        node: Any = self.data
        for p in self._parts(path):
            if not isinstance(node, dict) or p not in node:
                return None
            node = node[p]
        return copy.deepcopy(node)

    def _set(self, path: str, value):
        parts = self._parts(path)
        if not parts:
            self.data = copy.deepcopy(value) if isinstance(value, dict) else {}
            return
        node = self.data
        for p in parts[:-1]:
            nxt = node.get(p)
            if not isinstance(nxt, dict):
                if value is None:
                    return
                nxt = node[p] = {}
            node = nxt
        if value is None:
            node.pop(parts[-1], None)
        else:
            node[parts[-1]] = copy.deepcopy(value)

    async def get(self, path: str) -> Any:
        return self._get(path)

    async def set(self, path: str, value: Any) -> None:
        self._set(path, value)

    async def update(self, path: str, values: dict) -> None:
        base = path.strip("/")
        for k, v in values.items():
            self._set(f"{base}/{k}" if base else k, v)

    async def push(self, path: str, value: Any) -> str:
        key = self.new_key(path)
        self._set(f"{path.strip('/')}/{key}", value)
        return key

    async def delete(self, path: str) -> None:
        self._set(path, None)

    async def transaction(self, path: str, fn: Callable[[Any], Any]) -> Any:
        async with self._lock:
            new = fn(self._get(path))
            self._set(path, new)
            return copy.deepcopy(new)

    async def get_last(self, path: str, n: int) -> Any:
        node = self._get(path)
        if not isinstance(node, dict):
            return node
        return {k: node[k] for k in sorted(node)[-n:]}

    def new_key(self, path: str) -> str:
        return "-M" + uuid.uuid4().hex[:18]


def init_firebase(settings) -> FirebaseStore:
    import firebase_admin
    from firebase_admin import credentials, db

    if settings.firebase_credentials_json:
        info = json.loads(settings.firebase_credentials_json)
        cred = credentials.Certificate(info)
    else:
        cred = credentials.Certificate(settings.firebase_credentials_file)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {"databaseURL": settings.firebase_db_url})
    return FirebaseStore(db)
