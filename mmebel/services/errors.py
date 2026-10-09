from __future__ import annotations


class ServiceError(Exception):
    """Foydalanuvchiga ko'rsatsa bo'ladigan biznes xatosi."""


class NotFound(ServiceError):
    pass


class Conflict(ServiceError):
    """Holat o'zgargan (masalan, buyurtma allaqachon bekor qilingan)."""


async def run_tx(store, path: str, fn):
    """Tranzaksiya; ichidagi ServiceError (Firebase o'rab yuborgan bo'lsa ham) tashqariga chiqariladi."""
    try:
        return await store.transaction(path, fn)
    except ServiceError:
        raise
    except Exception as e:
        cause = e.__cause__ or e.__context__
        if isinstance(cause, ServiceError):
            raise cause from None
        raise
