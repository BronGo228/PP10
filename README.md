Бронгулеев Даниил Дмитриевич

Студент группы - ИС-43

Сроки прохождения практики - 16.02.2026 по 01.03.2026

Тема практики - Администрирование информационных ресурсов

# Склад РЭК — Система аудита и учёта склада радиоэлектронных компонентов

REST API на базе **FastAPI + SQLAlchemy + SQLite**.

---

## Структура базы данных

```
component_categories   — категории компонентов (резисторы, конденсаторы, ИС …)
manufacturers          — производители
suppliers              — поставщики
storage_locations      — ячейки хранения (стеллаж / полка / ячейка)

components             — каталог радиоэлектронных компонентов
stocks                 — текущий остаток компонента в ячейке

receipts               — приходные накладные
receipt_items          — позиции приходной накладной

issues                 — расходные накладные
issue_items            — позиции расходной накладной

inventories            — акты инвентаризации
inventory_items        — позиции акта (учётный / фактический остаток)

audit_logs             — неизменяемый журнал всех движений и изменений
```

### ER-диаграмма (упрощённая)

```
component_categories ──< components >── manufacturers
                              │
                          stocks ──── storage_locations
                              │
               ┌─────────────┴──────────────┐
          receipt_items              issue_items
               │                        │
           receipts                  issues
               │
           suppliers
               │
          audit_logs ◄──── (все изменения остатков)
```

---

## Установка и запуск

```bash
# 1. Создайте виртуальное окружение
cd C:\Users\ИМЯ\rek
python -m venv venv
venv\Scripts\activate

# 2. Установить зависимости
pip install -r requirements.txt

# 2. Запустить сервер (БД создаётся и заполняется автоматически)
python main.py

# Swagger UI:  http://localhost:8000/docs
# ReDoc:       http://localhost:8000/redoc
```

---

## API — краткий справочник

### Справочники

| Метод | URL | Описание |
|-------|-----|----------|
| GET | /categories | Список категорий |
| POST | /categories | Создать категорию |
| DELETE | /categories/{id} | Удалить категорию |
| GET | /manufacturers | Список производителей |
| POST | /manufacturers | Создать производителя |
| GET | /suppliers | Список поставщиков |
| POST | /suppliers | Создать поставщика |
| PATCH | /suppliers/{id} | Обновить поставщика |
| DELETE | /suppliers/{id} | Деактивировать поставщика |
| GET | /locations | Список ячеек хранения |
| POST | /locations | Добавить ячейку |

### Компоненты

| Метод | URL | Описание |
|-------|-----|----------|
| GET | /components | Список компонентов (фильтры: category_id, search) |
| GET | /components/{id} | Карточка компонента |
| POST | /components | Добавить компонент |
| PATCH | /components/{id} | Обновить компонент |
| DELETE | /components/{id} | Деактивировать |

### Остатки

| Метод | URL | Описание |
|-------|-----|----------|
| GET | /stocks | Остатки (фильтры: component_id, location_id) |
| POST | /stocks/adjust | Ручная корректировка остатка |

### Приход

| Метод | URL | Описание |
|-------|-----|----------|
| GET | /receipts | Список приходных накладных |
| POST | /receipts | Создать накладную (черновик) |
| POST | /receipts/{id}/confirm | Подтвердить — увеличить остатки |
| POST | /receipts/{id}/cancel | Отменить черновик |

### Расход

| Метод | URL | Описание |
|-------|-----|----------|
| GET | /issues | Список расходных накладных |
| POST | /issues | Создать накладную (черновик) |
| POST | /issues/{id}/confirm | Подтвердить — уменьшить остатки |
| POST | /issues/{id}/cancel | Отменить черновик |

### Инвентаризация

| Метод | URL | Описание |
|-------|-----|----------|
| GET | /inventories | Список актов инвентаризации |
| POST | /inventories | Провести инвентаризацию (корректирует остатки) |

### Аудит и отчёты

| Метод | URL | Описание |
|-------|-----|----------|
| GET | /audit | Журнал изменений (фильтры: component_id, action_type) |
| GET | /reports/stock | Сводный отчёт по остаткам |
| GET | /reports/stock?below_min_only=true | Только дефицитные позиции |
| GET | /reports/movements | История движений компонента |

---

## Примеры запросов

### Создать приходную накладную и подтвердить

```bash
# Создание черновика
curl -X POST http://localhost:8000/receipts \
  -H "Content-Type: application/json" \
  -d '{
    "number": "ПН-2024-001",
    "supplier_id": 1,
    "created_by": "Иванов А.А.",
    "items": [
      {"component_id": 1, "location_id": 1, "quantity": 5000, "price_rub": 0.15},
      {"component_id": 3, "location_id": 3, "quantity": 2000, "price_rub": 1.20}
    ]
  }'

# Подтверждение (остатки увеличиваются)
curl -X POST http://localhost:8000/receipts/1/confirm \
  -H "Content-Type: application/json" \
  -d '{"performed_by": "Иванов А.А."}'
```

### Выдать компоненты

```bash
curl -X POST http://localhost:8000/issues \
  -H "Content-Type: application/json" \
  -d '{
    "number": "РН-2024-001",
    "department": "Производство",
    "requester": "Петров К.Б.",
    "purpose": "Сборка платы управления",
    "items": [
      {"component_id": 1, "location_id": 1, "quantity": 100},
      {"component_id": 8, "location_id": 8, "quantity": 5}
    ]
  }'

curl -X POST http://localhost:8000/issues/1/confirm?performed_by=Кладовщик
```

### Провести инвентаризацию

```bash
curl -X POST http://localhost:8000/inventories \
  -H "Content-Type: application/json" \
  -d '{
    "number": "ИНВ-2024-01",
    "created_by": "Комиссия",
    "items": [
      {"component_id": 1, "location_id": 1, "actual_quantity": 4890},
      {"component_id": 3, "location_id": 3, "actual_quantity": 8050}
    ]
  }'
```

### Получить дефицитные позиции

```bash
curl "http://localhost:8000/reports/stock?below_min_only=true"
```

---

## Журнал аудита

Все изменения остатков записываются автоматически в таблицу `audit_logs`.
Записи **не изменяются и не удаляются** — только добавляются.

Типы событий: `receipt` · `issue` · `adjust` · `inventory` · `create` · `update` · `delete`

```bash
# Вся история компонента с id=1
curl "http://localhost:8000/audit?component_id=1"

# Только приходы
curl "http://localhost:8000/audit?action_type=receipt"
```

---

## Структура файлов

```
rek/
├── main.py          # FastAPI-приложение, все эндпоинты
├── models.py        # SQLAlchemy-модели (схема БД)
├── schemas.py       # Pydantic-схемы (валидация)
├── database.py      # Подключение к БД, seed-данные
├── requirements.txt
└── README.md
```


