"""
Pydantic-схемы для валидации запросов и ответов API
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from models import ReceiptStatus, IssueStatus, InventoryStatus, AuditActionType


# ─────────────────────────────────────────────
#  КАТЕГОРИИ
# ─────────────────────────────────────────────

class ComponentCategoryCreate(BaseModel):
    name: str = Field(..., max_length=100, example="Конденсаторы")
    code: str = Field(..., max_length=20, example="CAP")
    description: Optional[str] = None


class ComponentCategoryRead(ComponentCategoryCreate):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
#  ПРОИЗВОДИТЕЛИ
# ─────────────────────────────────────────────

class ManufacturerCreate(BaseModel):
    name: str = Field(..., max_length=150, example="Samsung Electro-Mechanics")
    country: Optional[str] = Field(None, example="Южная Корея")
    website: Optional[str] = None


class ManufacturerRead(ManufacturerCreate):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
#  ПОСТАВЩИКИ
# ─────────────────────────────────────────────

class SupplierCreate(BaseModel):
    name: str = Field(..., max_length=150, example='ООО "ЧипДип"')
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    inn: Optional[str] = None
    is_active: bool = True


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    inn: Optional[str] = None
    is_active: Optional[bool] = None


class SupplierRead(SupplierCreate):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
#  МЕСТА ХРАНЕНИЯ
# ─────────────────────────────────────────────

class StorageLocationCreate(BaseModel):
    code: str = Field(..., max_length=30, example="A1-03")
    rack: str = Field(..., max_length=20, example="A1")
    shelf: int = Field(..., ge=1)
    cell: int = Field(..., ge=1)
    description: Optional[str] = None
    is_active: bool = True


class StorageLocationRead(StorageLocationCreate):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
#  КОМПОНЕНТЫ
# ─────────────────────────────────────────────

class ComponentCreate(BaseModel):
    part_number: str = Field(..., max_length=100, example="GRM155R61A105KE15D")
    name: str = Field(..., max_length=200, example="Конденсатор 1мкФ 10В X5R 0402")
    category_id: int
    manufacturer_id: Optional[int] = None
    description: Optional[str] = None
    unit: str = Field("шт.", max_length=20)
    package: Optional[str] = Field(None, example="0402")
    min_stock: float = Field(0, ge=0)
    price_rub: Optional[float] = Field(None, ge=0)
    datasheet_url: Optional[str] = None
    is_active: bool = True


class ComponentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    package: Optional[str] = None
    min_stock: Optional[float] = None
    price_rub: Optional[float] = None
    datasheet_url: Optional[str] = None
    is_active: Optional[bool] = None


class ComponentRead(ComponentCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = {"from_attributes": True}


class ComponentWithStock(ComponentRead):
    total_stock: float = 0.0
    is_below_min: bool = False


# ─────────────────────────────────────────────
#  ОСТАТКИ
# ─────────────────────────────────────────────

class StockAdjust(BaseModel):
    """Ручная корректировка остатка"""
    component_id: int
    location_id: int
    quantity: float = Field(..., description="Новое количество (абсолютное)")
    reason: Optional[str] = Field(None, description="Причина корректировки")
    performed_by: Optional[str] = None


class StockRead(BaseModel):
    id: int
    component_id: int
    location_id: int
    quantity: float
    reserved: float
    updated_at: datetime
    model_config = {"from_attributes": True}


class StockDetailRead(StockRead):
    component: ComponentRead
    location: StorageLocationRead


# ─────────────────────────────────────────────
#  ПРИХОД
# ─────────────────────────────────────────────

class ReceiptItemCreate(BaseModel):
    component_id: int
    location_id: Optional[int] = None
    quantity: float = Field(..., gt=0)
    price_rub: Optional[float] = None


class ReceiptCreate(BaseModel):
    number: str = Field(..., example="ПН-2024-001")
    supplier_id: int
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    items: List[ReceiptItemCreate] = []


class ReceiptConfirm(BaseModel):
    performed_by: Optional[str] = None


class ReceiptItemRead(BaseModel):
    id: int
    component_id: int
    location_id: Optional[int]
    quantity: float
    price_rub: Optional[float]
    model_config = {"from_attributes": True}


class ReceiptRead(BaseModel):
    id: int
    number: str
    supplier_id: int
    status: ReceiptStatus
    received_at: Optional[datetime]
    invoice_number: Optional[str]
    notes: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    items: List[ReceiptItemRead] = []
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
#  РАСХОД
# ─────────────────────────────────────────────

class IssueItemCreate(BaseModel):
    component_id: int
    location_id: Optional[int] = None
    quantity: float = Field(..., gt=0)


class IssueCreate(BaseModel):
    number: str = Field(..., example="РН-2024-001")
    department: Optional[str] = None
    requester: Optional[str] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    items: List[IssueItemCreate] = []


class IssueItemRead(BaseModel):
    id: int
    component_id: int
    location_id: Optional[int]
    quantity: float
    model_config = {"from_attributes": True}


class IssueRead(BaseModel):
    id: int
    number: str
    department: Optional[str]
    requester: Optional[str]
    status: IssueStatus
    issued_at: Optional[datetime]
    purpose: Optional[str]
    notes: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    items: List[IssueItemRead] = []
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
#  ИНВЕНТАРИЗАЦИЯ
# ─────────────────────────────────────────────

class InventoryItemCreate(BaseModel):
    component_id: int
    location_id: Optional[int] = None
    actual_quantity: float = Field(..., ge=0)


class InventoryCreate(BaseModel):
    number: str = Field(..., example="ИНВ-2024-001")
    notes: Optional[str] = None
    created_by: Optional[str] = None
    items: List[InventoryItemCreate] = []


class InventoryItemRead(BaseModel):
    id: int
    component_id: int
    location_id: Optional[int]
    expected_quantity: float
    actual_quantity: float
    discrepancy: float
    model_config = {"from_attributes": True}


class InventoryRead(BaseModel):
    id: int
    number: str
    status: InventoryStatus
    started_at: datetime
    finished_at: Optional[datetime]
    notes: Optional[str]
    created_by: Optional[str]
    items: List[InventoryItemRead] = []
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
#  ЖУРНАЛ АУДИТА
# ─────────────────────────────────────────────

class AuditLogRead(BaseModel):
    id: int
    action_type: AuditActionType
    entity_type: str
    entity_id: Optional[int]
    component_id: Optional[int]
    location_id: Optional[int]
    quantity_before: Optional[float]
    quantity_after: Optional[float]
    description: Optional[str]
    performed_by: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
#  ОТЧЁТЫ
# ─────────────────────────────────────────────

class StockReport(BaseModel):
    component_id: int
    part_number: str
    component_name: str
    category: str
    total_quantity: float
    reserved: float
    available: float
    min_stock: float
    is_below_min: bool
    price_rub: Optional[float]
    total_value: Optional[float]
