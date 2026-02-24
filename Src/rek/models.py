"""
Модели базы данных: Система аудита и учёта склада радиоэлектронных компонентов
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey,
    Text, Boolean, Enum as SAEnum
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


# ─────────────────────────────────────────────
#  СПРАВОЧНИКИ
# ─────────────────────────────────────────────

class ComponentCategory(Base):
    """Категория радиоэлектронных компонентов (конденсаторы, резисторы, ИС и т.д.)"""
    __tablename__ = "component_categories"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), unique=True, nullable=False, comment="Название категории")
    code        = Column(String(20), unique=True, nullable=False, comment="Буквенный код")
    description = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    components  = relationship("Component", back_populates="category")


class Manufacturer(Base):
    """Производитель компонента"""
    __tablename__ = "manufacturers"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(150), unique=True, nullable=False)
    country     = Column(String(100), nullable=True)
    website     = Column(String(255), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    components  = relationship("Component", back_populates="manufacturer")


class Supplier(Base):
    """Поставщик"""
    __tablename__ = "suppliers"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(150), unique=True, nullable=False)
    contact_name = Column(String(150), nullable=True)
    phone        = Column(String(50), nullable=True)
    email        = Column(String(150), nullable=True)
    address      = Column(Text, nullable=True)
    inn          = Column(String(20), nullable=True, comment="ИНН")
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    receipts     = relationship("Receipt", back_populates="supplier")


class StorageLocation(Base):
    """Место хранения на складе (стеллаж / ячейка)"""
    __tablename__ = "storage_locations"

    id          = Column(Integer, primary_key=True, index=True)
    code        = Column(String(30), unique=True, nullable=False, comment="Код ячейки, напр. A1-03")
    rack        = Column(String(20), nullable=False, comment="Стеллаж")
    shelf       = Column(Integer, nullable=False, comment="Полка")
    cell        = Column(Integer, nullable=False, comment="Ячейка")
    description = Column(Text, nullable=True)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    stocks      = relationship("Stock", back_populates="location")


# ─────────────────────────────────────────────
#  КОМПОНЕНТЫ
# ─────────────────────────────────────────────

class Component(Base):
    """Радиоэлектронный компонент"""
    __tablename__ = "components"

    id              = Column(Integer, primary_key=True, index=True)
    part_number     = Column(String(100), unique=True, nullable=False, comment="Артикул / Part Number")
    name            = Column(String(200), nullable=False, comment="Наименование")
    category_id     = Column(Integer, ForeignKey("component_categories.id"), nullable=False)
    manufacturer_id = Column(Integer, ForeignKey("manufacturers.id"), nullable=True)
    description     = Column(Text, nullable=True, comment="Описание / характеристики")
    unit            = Column(String(20), default="шт.", comment="Единица измерения")
    package         = Column(String(50), nullable=True, comment="Корпус (SMD 0402, DIP-8, ...)")
    min_stock       = Column(Float, default=0, comment="Минимальный остаток")
    price_rub       = Column(Float, nullable=True, comment="Цена за единицу, руб.")
    datasheet_url   = Column(String(255), nullable=True)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    category        = relationship("ComponentCategory", back_populates="components")
    manufacturer    = relationship("Manufacturer", back_populates="components")
    stocks          = relationship("Stock", back_populates="component")
    receipt_items   = relationship("ReceiptItem", back_populates="component")
    issue_items     = relationship("IssueItem", back_populates="component")
    inventory_items = relationship("InventoryItem", back_populates="component")


class Stock(Base):
    """Остаток компонента в конкретной ячейке хранения"""
    __tablename__ = "stocks"

    id          = Column(Integer, primary_key=True, index=True)
    component_id = Column(Integer, ForeignKey("components.id"), nullable=False)
    location_id  = Column(Integer, ForeignKey("storage_locations.id"), nullable=False)
    quantity     = Column(Float, default=0, nullable=False, comment="Текущий остаток")
    reserved     = Column(Float, default=0, comment="Зарезервировано")
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    component    = relationship("Component", back_populates="stocks")
    location     = relationship("StorageLocation", back_populates="stocks")


# ─────────────────────────────────────────────
#  ПРИХОДНЫЕ НАКЛАДНЫЕ
# ─────────────────────────────────────────────

class ReceiptStatus(str, enum.Enum):
    draft     = "draft"      # черновик
    confirmed = "confirmed"  # подтверждена
    cancelled = "cancelled"  # отменена


class Receipt(Base):
    """Приходная накладная (поступление компонентов)"""
    __tablename__ = "receipts"

    id            = Column(Integer, primary_key=True, index=True)
    number        = Column(String(50), unique=True, nullable=False, comment="Номер накладной")
    supplier_id   = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    status        = Column(SAEnum(ReceiptStatus), default=ReceiptStatus.draft)
    received_at   = Column(DateTime(timezone=True), nullable=True, comment="Дата фактического получения")
    invoice_number = Column(String(100), nullable=True, comment="Номер счёта поставщика")
    notes         = Column(Text, nullable=True)
    created_by    = Column(String(100), nullable=True, comment="Кто создал")
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    supplier      = relationship("Supplier", back_populates="receipts")
    items         = relationship("ReceiptItem", back_populates="receipt", cascade="all, delete-orphan")


class ReceiptItem(Base):
    """Позиция приходной накладной"""
    __tablename__ = "receipt_items"

    id           = Column(Integer, primary_key=True, index=True)
    receipt_id   = Column(Integer, ForeignKey("receipts.id"), nullable=False)
    component_id = Column(Integer, ForeignKey("components.id"), nullable=False)
    location_id  = Column(Integer, ForeignKey("storage_locations.id"), nullable=True)
    quantity     = Column(Float, nullable=False)
    price_rub    = Column(Float, nullable=True, comment="Цена за ед. по накладной, руб.")

    receipt      = relationship("Receipt", back_populates="items")
    component    = relationship("Component", back_populates="receipt_items")
    location     = relationship("StorageLocation")


# ─────────────────────────────────────────────
#  РАСХОДНЫЕ НАКЛАДНЫЕ
# ─────────────────────────────────────────────

class IssueStatus(str, enum.Enum):
    draft     = "draft"
    confirmed = "confirmed"
    cancelled = "cancelled"


class Issue(Base):
    """Расходная накладная (выдача / списание компонентов)"""
    __tablename__ = "issues"

    id          = Column(Integer, primary_key=True, index=True)
    number      = Column(String(50), unique=True, nullable=False)
    department  = Column(String(150), nullable=True, comment="Подразделение / проект")
    requester   = Column(String(150), nullable=True, comment="Заявитель")
    status      = Column(SAEnum(IssueStatus), default=IssueStatus.draft)
    issued_at   = Column(DateTime(timezone=True), nullable=True)
    purpose     = Column(Text, nullable=True, comment="Цель / назначение")
    notes       = Column(Text, nullable=True)
    created_by  = Column(String(100), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    items       = relationship("IssueItem", back_populates="issue", cascade="all, delete-orphan")


class IssueItem(Base):
    """Позиция расходной накладной"""
    __tablename__ = "issue_items"

    id           = Column(Integer, primary_key=True, index=True)
    issue_id     = Column(Integer, ForeignKey("issues.id"), nullable=False)
    component_id = Column(Integer, ForeignKey("components.id"), nullable=False)
    location_id  = Column(Integer, ForeignKey("storage_locations.id"), nullable=True)
    quantity     = Column(Float, nullable=False)

    issue        = relationship("Issue", back_populates="items")
    component    = relationship("Component", back_populates="issue_items")
    location     = relationship("StorageLocation")


# ─────────────────────────────────────────────
#  ИНВЕНТАРИЗАЦИЯ
# ─────────────────────────────────────────────

class InventoryStatus(str, enum.Enum):
    in_progress = "in_progress"
    completed   = "completed"
    cancelled   = "cancelled"


class Inventory(Base):
    """Акт инвентаризации"""
    __tablename__ = "inventories"

    id          = Column(Integer, primary_key=True, index=True)
    number      = Column(String(50), unique=True, nullable=False)
    status      = Column(SAEnum(InventoryStatus), default=InventoryStatus.in_progress)
    started_at  = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    notes       = Column(Text, nullable=True)
    created_by  = Column(String(100), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    items       = relationship("InventoryItem", back_populates="inventory", cascade="all, delete-orphan")


class InventoryItem(Base):
    """Строка акта инвентаризации"""
    __tablename__ = "inventory_items"

    id                  = Column(Integer, primary_key=True, index=True)
    inventory_id        = Column(Integer, ForeignKey("inventories.id"), nullable=False)
    component_id        = Column(Integer, ForeignKey("components.id"), nullable=False)
    location_id         = Column(Integer, ForeignKey("storage_locations.id"), nullable=True)
    expected_quantity   = Column(Float, nullable=False, comment="Учётный остаток")
    actual_quantity     = Column(Float, nullable=False, comment="Фактический остаток")
    discrepancy         = Column(Float, nullable=False, comment="Расхождение (факт - учёт)")

    inventory   = relationship("Inventory", back_populates="items")
    component   = relationship("Component", back_populates="inventory_items")
    location    = relationship("StorageLocation")


# ─────────────────────────────────────────────
#  ЖУРНАЛ АУДИТА
# ─────────────────────────────────────────────

class AuditActionType(str, enum.Enum):
    create   = "create"
    update   = "update"
    delete   = "delete"
    receipt  = "receipt"    # поступление
    issue    = "issue"      # выдача
    adjust   = "adjust"     # ручная корректировка
    inventory = "inventory" # инвентаризация


class AuditLog(Base):
    """Журнал всех изменений в системе (неизменяемый)"""
    __tablename__ = "audit_logs"

    id           = Column(Integer, primary_key=True, index=True)
    action_type  = Column(SAEnum(AuditActionType), nullable=False)
    entity_type  = Column(String(50), nullable=False, comment="Тип сущности (component, stock, ...)")
    entity_id    = Column(Integer, nullable=True, comment="ID изменённой записи")
    component_id = Column(Integer, ForeignKey("components.id"), nullable=True)
    location_id  = Column(Integer, ForeignKey("storage_locations.id"), nullable=True)
    quantity_before = Column(Float, nullable=True)
    quantity_after  = Column(Float, nullable=True)
    description  = Column(Text, nullable=True, comment="Описание изменения")
    payload      = Column(Text, nullable=True, comment="JSON с деталями")
    performed_by = Column(String(100), nullable=True, comment="Оператор")
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
