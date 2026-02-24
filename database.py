"""
Конфигурация подключения к базе данных
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./warehouse.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}   # только для SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency для FastAPI — выдаёт сессию БД на время запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Создаёт таблицы и наполняет базу начальными данными."""
    from models import Base
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _seed(db)
    finally:
        db.close()


def _seed(db):
    from models import (ComponentCategory, Manufacturer, Supplier,
                        StorageLocation, Component, Stock)

    if db.query(ComponentCategory).count() > 0:
        return  # уже заполнено

    # Категории
    cats = [
        ComponentCategory(name="Резисторы",     code="RES", description="Постоянные резисторы"),
        ComponentCategory(name="Конденсаторы",  code="CAP", description="Ёмкостные компоненты"),
        ComponentCategory(name="Индуктивности", code="IND", description="Катушки и дроссели"),
        ComponentCategory(name="Диоды",         code="DIO", description="Полупроводниковые диоды"),
        ComponentCategory(name="Транзисторы",   code="TR",  description="Биполярные и полевые"),
        ComponentCategory(name="Микросхемы",    code="IC",  description="Интегральные схемы"),
        ComponentCategory(name="Разъёмы",       code="CON", description="Соединители"),
        ComponentCategory(name="Кварцы",        code="XTAL",description="Кварцевые резонаторы"),
    ]
    db.add_all(cats)
    db.flush()

    # Производители
    mans = [
        Manufacturer(name="Yageo",               country="Тайвань",       website="https://yageo.com"),
        Manufacturer(name="Murata",              country="Япония",        website="https://murata.com"),
        Manufacturer(name="Samsung Electro",     country="Южная Корея"),
        Manufacturer(name="Texas Instruments",   country="США",           website="https://ti.com"),
        Manufacturer(name="STMicroelectronics",  country="Швейцария",     website="https://st.com"),
        Manufacturer(name="Vishay",              country="США"),
    ]
    db.add_all(mans)
    db.flush()

    # Поставщики
    sups = [
        Supplier(name='ООО "ЧипДип"',      contact_name="Иванов А.А.",   phone="+7-495-100-10-10",
                 email="order@chipdip.ru",  inn="7701234567"),
        Supplier(name='АО "Компэл"',       contact_name="Петрова Е.В.",  phone="+7-495-200-20-20",
                 email="sales@compel.ru",   inn="7701234568"),
        Supplier(name='ООО "РадиоЭлемент"',contact_name="Сидоров К.П.", phone="+7-812-300-30-30",
                 inn="7801234569"),
    ]
    db.add_all(sups)
    db.flush()

    # Места хранения
    locs = []
    for rack in ["A", "B", "C"]:
        for shelf in range(1, 4):
            for cell in range(1, 6):
                locs.append(StorageLocation(
                    code=f"{rack}{shelf}-{cell:02d}",
                    rack=f"{rack}{shelf}",
                    shelf=shelf,
                    cell=cell,
                ))
    db.add_all(locs)
    db.flush()

    # Компоненты
    cat_map = {c.code: c.id for c in cats}
    man_map = {m.name: m.id for m in mans}

    components = [
        Component(part_number="RC0402FR-0710KL",    name="Резистор 10кОм 1% 0402",
                  category_id=cat_map["RES"], manufacturer_id=man_map["Yageo"],
                  package="0402", unit="шт.", min_stock=1000, price_rub=0.15),
        Component(part_number="RC0402FR-07100RL",   name="Резистор 100Ом 1% 0402",
                  category_id=cat_map["RES"], manufacturer_id=man_map["Yageo"],
                  package="0402", unit="шт.", min_stock=500, price_rub=0.15),
        Component(part_number="GRM155R61A105KE15D", name="Конденсатор 1мкФ 10В X5R 0402",
                  category_id=cat_map["CAP"], manufacturer_id=man_map["Murata"],
                  package="0402", unit="шт.", min_stock=2000, price_rub=1.20),
        Component(part_number="CL10A475KQ8NNNC",   name="Конденсатор 4.7мкФ 16В X5R 0603",
                  category_id=cat_map["CAP"], manufacturer_id=man_map["Samsung Electro"],
                  package="0603", unit="шт.", min_stock=500, price_rub=1.80),
        Component(part_number="LQH31PN100M23L",     name="Дроссель 10мкГн 500мА 1210",
                  category_id=cat_map["IND"], manufacturer_id=man_map["Murata"],
                  package="1210", unit="шт.", min_stock=200, price_rub=8.50),
        Component(part_number="BAV99",              name="Диод двойной BAV99 SOT-23",
                  category_id=cat_map["DIO"], manufacturer_id=man_map["Vishay"],
                  package="SOT-23", unit="шт.", min_stock=300, price_rub=2.50),
        Component(part_number="MMBT3904",           name="Транзистор NPN MMBT3904 SOT-23",
                  category_id=cat_map["TR"], manufacturer_id=man_map["Vishay"],
                  package="SOT-23", unit="шт.", min_stock=200, price_rub=3.00),
        Component(part_number="STM32F103C8T6",      name="МК STM32F103C8T6 LQFP-48",
                  category_id=cat_map["IC"], manufacturer_id=man_map["STMicroelectronics"],
                  package="LQFP-48", unit="шт.", min_stock=10, price_rub=350.00),
        Component(part_number="TLV1117-33",         name="Стабилизатор 3.3В 800мА SOT-223",
                  category_id=cat_map["IC"], manufacturer_id=man_map["Texas Instruments"],
                  package="SOT-223", unit="шт.", min_stock=50, price_rub=45.00),
    ]
    db.add_all(components)
    db.flush()

    # Начальные остатки
    loc_list = locs[:len(components)]
    stocks = []
    default_qtys = [5000, 3000, 8000, 2500, 400, 650, 480, 25, 120]
    for comp, loc, qty in zip(components, loc_list, default_qtys):
        stocks.append(Stock(component_id=comp.id, location_id=loc.id, quantity=qty))
    db.add_all(stocks)
    db.commit()
    print("✅ База данных заполнена начальными данными.")
