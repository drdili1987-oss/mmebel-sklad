"""Biznes mantiq qatlami. Bot ham, web panel ham faqat shu qatlam orqali bazaga murojaat qiladi."""
from __future__ import annotations

from ..store import Store
from .catalog import CatalogService
from .errors import Conflict, NotFound, ServiceError
from .finance import FinanceService
from .inventory import InventoryService
from .orders import OrderService
from .reports import ReportService
from .users import UserService

__all__ = ["Services", "ServiceError", "NotFound", "Conflict"]


class Services:
    def __init__(self, store: Store, owner_ids: list[int] | None = None):
        self.store = store
        self.users = UserService(store, owner_ids or [])
        self.catalog = CatalogService(store)
        self.inventory = InventoryService(store)
        self.finance = FinanceService(store, self.catalog)
        self.orders = OrderService(store, self.inventory, self.finance)
        self.reports = ReportService(store, self.finance)
