"""
Система аудита и учёта склада радиоэлектронных компонентов
REST API — FastAPI + SQLAlchemy + SQLite

Запуск:
    pip install fastapi uvicorn sqlalchemy
    python main.py

Документация:  http://localhost:8000/docs
"""
import json
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db, init_db
from models import (
    Component, ComponentCategory, Manufacturer, Supplier,
    StorageLocation, Stock, Receipt, ReceiptItem,
    Issue, IssueItem, Inventory, InventoryItem, AuditLog,
    ReceiptStatus, IssueStatus, InventoryStatus, AuditActionType
)
from schemas import (
    ComponentCategoryCreate, ComponentCategoryRead,
    ManufacturerCreate, ManufacturerRead,
    SupplierCreate, SupplierUpdate, SupplierRead,
    StorageLocationCreate, StorageLocationRead,
    ComponentCreate, ComponentUpdate, ComponentRead, ComponentWithStock,
    StockAdjust, StockRead, StockDetailRead,
    ReceiptCreate, ReceiptRead, ReceiptConfirm,
    IssueCreate, IssueRead,
    InventoryCreate, InventoryRead,
    AuditLogRead, StockReport
)

# ─────────────────────────────────────────────
app = FastAPI(
    title="Склад РЭК — API",
    description=(
        "REST API для системы аудита и учёта склада радиоэлектронных компонентов.\n\n"
        "Функциональность:\n"
        "- CRUD для компонентов, поставщиков, мест хранения\n"
        "- Приходные / расходные накладные\n"
        "- Инвентаризация\n"
        "- Автоматический журнал аудита всех изменений остатков\n"
        "- Отчёт о текущих остатках и нехватке компонентов"
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ─────────────────────────────────────────────

def _write_audit(db: Session, *, action_type: AuditActionType,
                 entity_type: str, entity_id: int = None,
                 component_id: int = None, location_id: int = None,
                 quantity_before: float = None, quantity_after: float = None,
                 description: str = None, payload: dict = None,
                 performed_by: str = None):
    log = AuditLog(
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        component_id=component_id,
        location_id=location_id,
        quantity_before=quantity_before,
        quantity_after=quantity_after,
        description=description,
        payload=json.dumps(payload, ensure_ascii=False, default=str) if payload else None,
        performed_by=performed_by,
    )
    db.add(log)


def _get_or_404(db, model, obj_id: int):
    obj = db.query(model).filter(model.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"{model.__tablename__} id={obj_id} не найден")
    return obj


def _stock_upsert(db: Session, component_id: int, location_id: int,
                  delta: float, performed_by: str = None,
                  action_type: AuditActionType = AuditActionType.adjust,
                  description: str = None) -> Stock:
    """Изменяет остаток, пишет аудит. delta может быть отрицательным."""
    stock = (db.query(Stock)
               .filter(Stock.component_id == component_id,
                       Stock.location_id == location_id)
               .first())
    if stock is None:
        stock = Stock(component_id=component_id, location_id=location_id, quantity=0)
        db.add(stock)
        db.flush()

    before = stock.quantity
    after = before + delta

    if after < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Недостаточно компонентов: доступно {before}, запрошено {abs(delta)}"
        )

    stock.quantity = after
    _write_audit(db, action_type=action_type, entity_type="stock",
                 entity_id=stock.id, component_id=component_id,
                 location_id=location_id, quantity_before=before,
                 quantity_after=after, description=description,
                 performed_by=performed_by)
    return stock


# ═══════════════════════════════════════════════════════════════════════
#  СПРАВОЧНИКИ
# ═══════════════════════════════════════════════════════════════════════

# ─── Категории ───────────────────────────────

@app.get("/categories", response_model=List[ComponentCategoryRead], tags=["Справочники"])
def list_categories(db: Session = Depends(get_db)):
    """Список категорий компонентов."""
    return db.query(ComponentCategory).all()


@app.post("/categories", response_model=ComponentCategoryRead, status_code=201, tags=["Справочники"])
def create_category(data: ComponentCategoryCreate, db: Session = Depends(get_db)):
    """Создать категорию."""
    obj = ComponentCategory(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/categories/{cat_id}", status_code=204, tags=["Справочники"])
def delete_category(cat_id: int, db: Session = Depends(get_db)):
    obj = _get_or_404(db, ComponentCategory, cat_id)
    db.delete(obj)
    db.commit()


# ─── Производители ───────────────────────────

@app.get("/manufacturers", response_model=List[ManufacturerRead], tags=["Справочники"])
def list_manufacturers(db: Session = Depends(get_db)):
    return db.query(Manufacturer).all()


@app.post("/manufacturers", response_model=ManufacturerRead, status_code=201, tags=["Справочники"])
def create_manufacturer(data: ManufacturerCreate, db: Session = Depends(get_db)):
    obj = Manufacturer(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# ─── Поставщики ──────────────────────────────

@app.get("/suppliers", response_model=List[SupplierRead], tags=["Справочники"])
def list_suppliers(active_only: bool = True, db: Session = Depends(get_db)):
    q = db.query(Supplier)
    if active_only:
        q = q.filter(Supplier.is_active == True)
    return q.all()


@app.get("/suppliers/{sup_id}", response_model=SupplierRead, tags=["Справочники"])
def get_supplier(sup_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, Supplier, sup_id)


@app.post("/suppliers", response_model=SupplierRead, status_code=201, tags=["Справочники"])
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db)):
    obj = Supplier(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.patch("/suppliers/{sup_id}", response_model=SupplierRead, tags=["Справочники"])
def update_supplier(sup_id: int, data: SupplierUpdate, db: Session = Depends(get_db)):
    obj = _get_or_404(db, Supplier, sup_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/suppliers/{sup_id}", status_code=204, tags=["Справочники"])
def delete_supplier(sup_id: int, db: Session = Depends(get_db)):
    obj = _get_or_404(db, Supplier, sup_id)
    obj.is_active = False   # мягкое удаление
    db.commit()


# ─── Места хранения ──────────────────────────

@app.get("/locations", response_model=List[StorageLocationRead], tags=["Справочники"])
def list_locations(db: Session = Depends(get_db)):
    return db.query(StorageLocation).filter(StorageLocation.is_active == True).all()


@app.post("/locations", response_model=StorageLocationRead, status_code=201, tags=["Справочники"])
def create_location(data: StorageLocationCreate, db: Session = Depends(get_db)):
    obj = StorageLocation(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# ═══════════════════════════════════════════════════════════════════════
#  КОМПОНЕНТЫ
# ═══════════════════════════════════════════════════════════════════════

@app.get("/components", response_model=List[ComponentRead], tags=["Компоненты"])
def list_components(
    category_id: Optional[int] = None,
    manufacturer_id: Optional[int] = None,
    search: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Список компонентов с фильтрацией."""
    q = db.query(Component)
    if active_only:
        q = q.filter(Component.is_active == True)
    if category_id:
        q = q.filter(Component.category_id == category_id)
    if manufacturer_id:
        q = q.filter(Component.manufacturer_id == manufacturer_id)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            Component.name.ilike(pattern) | Component.part_number.ilike(pattern)
        )
    return q.all()


@app.get("/components/{comp_id}", response_model=ComponentRead, tags=["Компоненты"])
def get_component(comp_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, Component, comp_id)


@app.post("/components", response_model=ComponentRead, status_code=201, tags=["Компоненты"])
def create_component(data: ComponentCreate, db: Session = Depends(get_db)):
    """Добавить новый компонент в каталог."""
    obj = Component(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    _write_audit(db, action_type=AuditActionType.create, entity_type="component",
                 entity_id=obj.id, description=f"Создан компонент {obj.part_number}")
    db.commit()
    return obj


@app.patch("/components/{comp_id}", response_model=ComponentRead, tags=["Компоненты"])
def update_component(comp_id: int, data: ComponentUpdate, db: Session = Depends(get_db)):
    """Обновить атрибуты компонента."""
    obj = _get_or_404(db, Component, comp_id)
    changes = data.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    _write_audit(db, action_type=AuditActionType.update, entity_type="component",
                 entity_id=obj.id, description=f"Обновлён компонент {obj.part_number}",
                 payload=changes)
    db.commit()
    return obj


@app.delete("/components/{comp_id}", status_code=204, tags=["Компоненты"])
def deactivate_component(comp_id: int, db: Session = Depends(get_db)):
    """Деактивировать компонент (мягкое удаление)."""
    obj = _get_or_404(db, Component, comp_id)
    obj.is_active = False
    _write_audit(db, action_type=AuditActionType.delete, entity_type="component",
                 entity_id=obj.id, description=f"Деактивирован компонент {obj.part_number}")
    db.commit()


# ═══════════════════════════════════════════════════════════════════════
#  ОСТАТКИ
# ═══════════════════════════════════════════════════════════════════════

@app.get("/stocks", response_model=List[StockRead], tags=["Остатки"])
def list_stocks(component_id: Optional[int] = None,
                location_id: Optional[int] = None,
                db: Session = Depends(get_db)):
    """Текущие остатки по ячейкам."""
    q = db.query(Stock)
    if component_id:
        q = q.filter(Stock.component_id == component_id)
    if location_id:
        q = q.filter(Stock.location_id == location_id)
    return q.all()


@app.post("/stocks/adjust", response_model=StockRead, tags=["Остатки"])
def adjust_stock(data: StockAdjust, db: Session = Depends(get_db)):
    """
    Ручная корректировка остатка (абсолютное значение).
    Создаёт запись в журнале аудита.
    """
    _get_or_404(db, Component, data.component_id)
    _get_or_404(db, StorageLocation, data.location_id)

    stock = (db.query(Stock)
               .filter(Stock.component_id == data.component_id,
                       Stock.location_id == data.location_id)
               .first())

    before = stock.quantity if stock else 0

    if stock is None:
        stock = Stock(component_id=data.component_id, location_id=data.location_id,
                      quantity=data.quantity)
        db.add(stock)
        db.flush()
    else:
        stock.quantity = data.quantity

    _write_audit(db, action_type=AuditActionType.adjust,
                 entity_type="stock", entity_id=stock.id,
                 component_id=data.component_id, location_id=data.location_id,
                 quantity_before=before, quantity_after=data.quantity,
                 description=data.reason, performed_by=data.performed_by)
    db.commit()
    db.refresh(stock)
    return stock


# ═══════════════════════════════════════════════════════════════════════
#  ПРИХОДНЫЕ НАКЛАДНЫЕ
# ═══════════════════════════════════════════════════════════════════════

@app.get("/receipts", response_model=List[ReceiptRead], tags=["Приход"])
def list_receipts(status: Optional[ReceiptStatus] = None, db: Session = Depends(get_db)):
    q = db.query(Receipt)
    if status:
        q = q.filter(Receipt.status == status)
    return q.order_by(Receipt.created_at.desc()).all()


@app.get("/receipts/{rec_id}", response_model=ReceiptRead, tags=["Приход"])
def get_receipt(rec_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, Receipt, rec_id)


@app.post("/receipts", response_model=ReceiptRead, status_code=201, tags=["Приход"])
def create_receipt(data: ReceiptCreate, db: Session = Depends(get_db)):
    """Создать приходную накладную (статус: черновик)."""
    _get_or_404(db, Supplier, data.supplier_id)
    receipt = Receipt(
        number=data.number,
        supplier_id=data.supplier_id,
        invoice_number=data.invoice_number,
        notes=data.notes,
        created_by=data.created_by,
        status=ReceiptStatus.draft,
    )
    db.add(receipt)
    db.flush()

    for item_data in data.items:
        _get_or_404(db, Component, item_data.component_id)
        item = ReceiptItem(
            receipt_id=receipt.id,
            component_id=item_data.component_id,
            location_id=item_data.location_id,
            quantity=item_data.quantity,
            price_rub=item_data.price_rub,
        )
        db.add(item)

    db.commit()
    db.refresh(receipt)
    return receipt


@app.post("/receipts/{rec_id}/confirm", response_model=ReceiptRead, tags=["Приход"])
def confirm_receipt(rec_id: int, data: ReceiptConfirm, db: Session = Depends(get_db)):
    """
    Подтвердить приход — остатки увеличиваются, пишется аудит.
    """
    receipt = _get_or_404(db, Receipt, rec_id)
    if receipt.status != ReceiptStatus.draft:
        raise HTTPException(400, "Накладная уже обработана")

    for item in receipt.items:
        loc_id = item.location_id or 1   # fallback — первая ячейка
        _stock_upsert(db, component_id=item.component_id, location_id=loc_id,
                      delta=item.quantity,
                      action_type=AuditActionType.receipt,
                      description=f"Приход по накладной {receipt.number}",
                      performed_by=data.performed_by)

    receipt.status = ReceiptStatus.confirmed
    receipt.received_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(receipt)
    return receipt


@app.post("/receipts/{rec_id}/cancel", response_model=ReceiptRead, tags=["Приход"])
def cancel_receipt(rec_id: int, db: Session = Depends(get_db)):
    receipt = _get_or_404(db, Receipt, rec_id)
    if receipt.status == ReceiptStatus.confirmed:
        raise HTTPException(400, "Нельзя отменить подтверждённую накладную")
    receipt.status = ReceiptStatus.cancelled
    db.commit()
    db.refresh(receipt)
    return receipt


# ═══════════════════════════════════════════════════════════════════════
#  РАСХОДНЫЕ НАКЛАДНЫЕ
# ═══════════════════════════════════════════════════════════════════════

@app.get("/issues", response_model=List[IssueRead], tags=["Расход"])
def list_issues(status: Optional[IssueStatus] = None, db: Session = Depends(get_db)):
    q = db.query(Issue)
    if status:
        q = q.filter(Issue.status == status)
    return q.order_by(Issue.created_at.desc()).all()


@app.get("/issues/{iss_id}", response_model=IssueRead, tags=["Расход"])
def get_issue(iss_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, Issue, iss_id)


@app.post("/issues", response_model=IssueRead, status_code=201, tags=["Расход"])
def create_issue(data: IssueCreate, db: Session = Depends(get_db)):
    """Создать расходную накладную (черновик)."""
    issue = Issue(
        number=data.number,
        department=data.department,
        requester=data.requester,
        purpose=data.purpose,
        notes=data.notes,
        created_by=data.created_by,
        status=IssueStatus.draft,
    )
    db.add(issue)
    db.flush()

    for item_data in data.items:
        _get_or_404(db, Component, item_data.component_id)
        item = IssueItem(
            issue_id=issue.id,
            component_id=item_data.component_id,
            location_id=item_data.location_id,
            quantity=item_data.quantity,
        )
        db.add(item)

    db.commit()
    db.refresh(issue)
    return issue


@app.post("/issues/{iss_id}/confirm", response_model=IssueRead, tags=["Расход"])
def confirm_issue(iss_id: int, performed_by: Optional[str] = None,
                  db: Session = Depends(get_db)):
    """
    Подтвердить выдачу — остатки уменьшаются.
    Если компонентов недостаточно — вернётся ошибка 400.
    """
    issue = _get_or_404(db, Issue, iss_id)
    if issue.status != IssueStatus.draft:
        raise HTTPException(400, "Накладная уже обработана")

    for item in issue.items:
        loc_id = item.location_id or 1
        _stock_upsert(db, component_id=item.component_id, location_id=loc_id,
                      delta=-item.quantity,
                      action_type=AuditActionType.issue,
                      description=f"Выдача по накладной {issue.number}",
                      performed_by=performed_by)

    issue.status = IssueStatus.confirmed
    issue.issued_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(issue)
    return issue


@app.post("/issues/{iss_id}/cancel", response_model=IssueRead, tags=["Расход"])
def cancel_issue(iss_id: int, db: Session = Depends(get_db)):
    issue = _get_or_404(db, Issue, iss_id)
    if issue.status == IssueStatus.confirmed:
        raise HTTPException(400, "Нельзя отменить подтверждённую накладную")
    issue.status = IssueStatus.cancelled
    db.commit()
    db.refresh(issue)
    return issue


# ═══════════════════════════════════════════════════════════════════════
#  ИНВЕНТАРИЗАЦИЯ
# ═══════════════════════════════════════════════════════════════════════

@app.get("/inventories", response_model=List[InventoryRead], tags=["Инвентаризация"])
def list_inventories(db: Session = Depends(get_db)):
    return db.query(Inventory).order_by(Inventory.started_at.desc()).all()


@app.get("/inventories/{inv_id}", response_model=InventoryRead, tags=["Инвентаризация"])
def get_inventory(inv_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, Inventory, inv_id)


@app.post("/inventories", response_model=InventoryRead, status_code=201, tags=["Инвентаризация"])
def create_inventory(data: InventoryCreate, db: Session = Depends(get_db)):
    """
    Провести инвентаризацию:
    - для каждой позиции фиксируется учётный и фактический остаток
    - вычисляется расхождение
    - остатки приводятся к фактическим значениям
    - пишется аудит
    """
    inventory = Inventory(
        number=data.number,
        notes=data.notes,
        created_by=data.created_by,
        status=InventoryStatus.in_progress,
    )
    db.add(inventory)
    db.flush()

    for item_data in data.items:
        comp = _get_or_404(db, Component, item_data.component_id)
        loc_id = item_data.location_id or 1

        stock = (db.query(Stock)
                   .filter(Stock.component_id == item_data.component_id,
                           Stock.location_id == loc_id)
                   .first())
        expected = stock.quantity if stock else 0
        actual   = item_data.actual_quantity
        delta    = actual - expected

        inv_item = InventoryItem(
            inventory_id=inventory.id,
            component_id=item_data.component_id,
            location_id=loc_id,
            expected_quantity=expected,
            actual_quantity=actual,
            discrepancy=delta,
        )
        db.add(inv_item)

        # Корректируем остаток если есть расхождение
        if delta != 0:
            if stock is None:
                stock = Stock(component_id=item_data.component_id,
                              location_id=loc_id, quantity=actual)
                db.add(stock)
                db.flush()
            else:
                stock.quantity = actual

            _write_audit(db, action_type=AuditActionType.inventory,
                         entity_type="stock", entity_id=stock.id,
                         component_id=item_data.component_id, location_id=loc_id,
                         quantity_before=expected, quantity_after=actual,
                         description=f"Инвентаризация {data.number}, расхождение: {delta:+.2f}",
                         performed_by=data.created_by)

    inventory.status = InventoryStatus.completed
    inventory.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(inventory)
    return inventory


# ═══════════════════════════════════════════════════════════════════════
#  ЖУРНАЛ АУДИТА
# ═══════════════════════════════════════════════════════════════════════

@app.get("/audit", response_model=List[AuditLogRead], tags=["Аудит"])
def get_audit_log(
    component_id: Optional[int] = None,
    action_type: Optional[AuditActionType] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Журнал всех изменений остатков. Доступен только для чтения."""
    q = db.query(AuditLog)
    if component_id:
        q = q.filter(AuditLog.component_id == component_id)
    if action_type:
        q = q.filter(AuditLog.action_type == action_type)
    return q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()


# ═══════════════════════════════════════════════════════════════════════
#  ОТЧЁТЫ
# ═══════════════════════════════════════════════════════════════════════

@app.get("/reports/stock", response_model=List[StockReport], tags=["Отчёты"])
def report_stock(below_min_only: bool = False, db: Session = Depends(get_db)):
    """
    Сводный отчёт об остатках: суммарное количество по каждому компоненту,
    статус относительно минимального уровня, стоимость.
    """
    rows = (
        db.query(
            Component,
            ComponentCategory,
            func.coalesce(func.sum(Stock.quantity), 0).label("total_qty"),
            func.coalesce(func.sum(Stock.reserved), 0).label("total_reserved"),
        )
        .outerjoin(Stock, Stock.component_id == Component.id)
        .join(ComponentCategory, ComponentCategory.id == Component.category_id)
        .filter(Component.is_active == True)
        .group_by(Component.id, ComponentCategory.id)
        .all()
    )

    result = []
    for comp, cat, total_qty, total_reserved in rows:
        available = total_qty - total_reserved
        is_below = total_qty < comp.min_stock
        if below_min_only and not is_below:
            continue
        result.append(StockReport(
            component_id=comp.id,
            part_number=comp.part_number,
            component_name=comp.name,
            category=cat.name,
            total_quantity=total_qty,
            reserved=total_reserved,
            available=available,
            min_stock=comp.min_stock,
            is_below_min=is_below,
            price_rub=comp.price_rub,
            total_value=(total_qty * comp.price_rub) if comp.price_rub else None,
        ))
    return result


@app.get("/reports/movements", tags=["Отчёты"])
def report_movements(
    component_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """История движения компонента (приход + расход из журнала аудита)."""
    q = db.query(AuditLog).filter(
        AuditLog.action_type.in_([
            AuditActionType.receipt, AuditActionType.issue,
            AuditActionType.adjust, AuditActionType.inventory
        ])
    )
    if component_id:
        q = q.filter(AuditLog.component_id == component_id)
    if date_from:
        q = q.filter(AuditLog.created_at >= date_from)
    if date_to:
        q = q.filter(AuditLog.created_at <= date_to)
    logs = q.order_by(AuditLog.created_at.desc()).limit(500).all()

    return [
        {
            "id": l.id,
            "date": l.created_at,
            "action": l.action_type,
            "component_id": l.component_id,
            "location_id": l.location_id,
            "quantity_before": l.quantity_before,
            "quantity_after": l.quantity_after,
            "delta": (
                round(l.quantity_after - l.quantity_before, 4)
                if l.quantity_before is not None and l.quantity_after is not None
                else None
            ),
            "description": l.description,
            "performed_by": l.performed_by,
        }
        for l in logs
    ]


# ─────────────────────────────────────────────
#  ТОЧКА ВХОДА
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    print("🔧 Инициализация базы данных...")
    init_db()
    print("🚀 Запуск сервера на http://localhost:8000")
    print("📖 Swagger UI: http://localhost:8000/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
