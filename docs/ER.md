# ER-диаграммы

Сгенерировано из моделей Django: `python manage.py er_diagram --output docs/ER.md`.
Сущности из соседних доменов показаны без полей — только чтобы были видны связи между модулями.
Обозначения: `||--o{` — один ко многим, `||--o|` — один к одному, `|o` — связь необязательна (null).
Поля `created_by`, `posted_by` и т. п. — автор операции (связь с `User`); линиями не показаны, чтобы не загромождать схемы.

## Пользователи и кадры

`User` — Пользователь, `Department` — Подразделение, `Position` — Должность, `Employee` — Сотрудник, `HROrder` — Кадровый приказ, `Absence` — Отсутствие, `Holiday` — Праздничный день

```mermaid
erDiagram
    User |o--o| Employee : "Учётная запись"
    Department ||--o{ Employee : "Подразделение"
    Position ||--o{ Employee : "Должность"
    Employee ||--o{ HROrder : "Сотрудник"
    Department |o--o{ HROrder : "Из подразделения"
    Department |o--o{ HROrder : "В подразделение"
    Position |o--o{ HROrder : "С должности"
    Position |o--o{ HROrder : "На должность"
    Employee ||--o{ Absence : "Сотрудник"
    User {
        int id PK
        string username UK "имя пользователя"
        string first_name "имя"
        string last_name "фамилия"
        bool is_active "активный"
        string role "Роль"
    }
    Department {
        int id PK
        string name UK "Название"
        bool is_production "Производственный цех"
        bool is_active "Действует"
    }
    Position {
        int id PK
        string name UK "Название"
        decimal base_salary "Базовый оклад"
    }
    Employee {
        int id PK
        int user_id FK "Учётная запись"
        string last_name "Фамилия"
        string first_name "Имя"
        string middle_name "Отчество"
        date birth_date "Дата рождения"
        string tax_id "ИИН/ИНН"
        string phone "Телефон"
        string address "Адрес"
        int department_id FK "Подразделение"
        int position_id FK "Должность"
        date hire_date "Дата приёма"
        date fire_date "Дата увольнения"
        string status "Статус"
        decimal salary "Оклад"
    }
    HROrder {
        int id PK
        string number UK "Номер"
        string kind "Вид приказа"
        int employee_id FK "Сотрудник"
        date date "Дата вступления в силу"
        int from_department_id FK "Из подразделения"
        int to_department_id FK "В подразделение"
        int from_position_id FK "С должности"
        int to_position_id FK "На должность"
        decimal from_salary "Прежний оклад"
        decimal to_salary "Новый оклад"
        string reason "Основание"
        int created_by_id FK "Автор"
        datetime created_at "Создан"
    }
    Absence {
        int id PK
        int employee_id FK "Сотрудник"
        string kind "Вид"
        date date_from "С"
        date date_to "По"
        string comment "Комментарий"
        int created_by_id FK "Автор"
    }
    Holiday {
        int id PK
        date date UK "Дата"
        string name "Название"
    }
```

## Каталог и рецептуры

`Unit` — Единица измерения, `Category` — Категория, `Item` — Номенклатура, `Supplier` — Поставщик, `Recipe` — Рецептура, `RecipeLine` — Строка рецептуры

Связи с другими доменами: Department.

```mermaid
erDiagram
    Category |o--o{ Item : "Категория"
    Unit ||--o{ Item : "Единица измерения"
    Department |o--o{ Item : "Цех-изготовитель"
    Item ||--o{ Recipe : "Продукт"
    Recipe ||--o{ RecipeLine : "Рецептура"
    Item ||--o{ RecipeLine : "Сырьё"
    Unit {
        int id PK
        string code UK "Обозначение"
        string name "Название"
        bool is_fractional "Делимая"
    }
    Category {
        int id PK
        string name "Название"
        string kind "Тип номенклатуры"
    }
    Item {
        int id PK
        string kind "Тип"
        string code UK "Артикул"
        string name "Название"
        int category_id FK "Категория"
        int unit_id FK "Единица измерения"
        int department_id FK "Цех-изготовитель"
        int shelf_life_days "Срок годности, дней"
        decimal min_stock "Минимальный остаток"
        decimal sale_price "Отпускная цена"
        bool is_active "Используется"
    }
    Supplier {
        int id PK
        string name UK "Название"
        string tax_id "БИН/ИНН"
        string contact_person "Контактное лицо"
        string phone "Телефон"
        string email "Email"
        string address "Адрес"
        text note "Примечание"
        bool is_active "Активен"
    }
    Recipe {
        int id PK
        int product_id FK "Продукт"
        int version "Версия"
        string status "Статус"
        decimal output_qty "Выход партии"
        text note "Технологические указания"
        int created_by_id FK "Автор"
        datetime created_at "Создана"
        datetime activated_at "Введена в действие"
    }
    RecipeLine {
        int id PK
        int recipe_id FK "Рецептура"
        int ingredient_id FK "Сырьё"
        decimal quantity "Количество нетто"
        decimal loss_percent "Потери, %"
    }
```

## Склад и закупки

`Lot` — Партия, `StockMove` — Движение, `PurchaseOrder` — Заявка поставщику, `PurchaseOrderLine` — Строка заявки, `Receipt` — Приёмка, `ReceiptLine` — Строка приёмки

Связи с другими доменами: Item, Supplier.

```mermaid
erDiagram
    Item ||--o{ Lot : "Номенклатура"
    Supplier |o--o{ Lot : "Поставщик"
    Lot ||--o{ StockMove : "Партия"
    Supplier ||--o{ PurchaseOrder : "Поставщик"
    PurchaseOrder ||--o{ PurchaseOrderLine : "Заявка"
    Item ||--o{ PurchaseOrderLine : "Сырьё"
    Supplier ||--o{ Receipt : "Поставщик"
    PurchaseOrder |o--o{ Receipt : "По заявке"
    Receipt ||--o{ ReceiptLine : "Приёмка"
    Item ||--o{ ReceiptLine : "Сырьё"
    PurchaseOrderLine |o--o{ ReceiptLine : "Строка заявки"
    Lot |o--o| ReceiptLine : "Созданная партия"
    Lot {
        int id PK
        string number UK "Номер"
        int item_id FK "Номенклатура"
        int supplier_id FK "Поставщик"
        date date "Дата поступления / производства"
        date expiry_date "Годен до"
        decimal unit_cost "Себестоимость единицы"
        datetime created_at "Создана"
    }
    StockMove {
        int id PK
        int lot_id FK "Партия"
        string kind "Вид движения"
        decimal quantity "Количество"
        string reference "Основание"
        int created_by_id FK "Кто провёл"
        datetime created_at "Дата и время"
    }
    PurchaseOrder {
        int id PK
        string number UK "Номер"
        int supplier_id FK "Поставщик"
        string status "Статус"
        date expected_date "Ожидаемая дата поставки"
        text comment "Комментарий"
        int created_by_id FK "Автор"
        datetime created_at "Создана"
    }
    PurchaseOrderLine {
        int id PK
        int order_id FK "Заявка"
        int item_id FK "Сырьё"
        decimal quantity "Количество"
        decimal price "Цена за единицу"
    }
    Receipt {
        int id PK
        string number UK "Номер"
        int supplier_id FK "Поставщик"
        int order_id FK "По заявке"
        date date "Дата приёмки"
        string invoice_number "Номер накладной поставщика"
        string status "Статус"
        text comment "Комментарий"
        int created_by_id FK "Автор"
        datetime created_at "Создана"
        int posted_by_id FK "Провёл"
        datetime posted_at "Проведена"
    }
    ReceiptLine {
        int id PK
        int receipt_id FK "Приёмка"
        int item_id FK "Сырьё"
        decimal quantity "Количество"
        decimal price "Цена за единицу"
        date expiry_date "Годен до"
        int order_line_id FK "Строка заявки"
        int lot_id FK "Созданная партия"
    }
```

## Продажи, отгрузка и производство

`Client` — Клиент, `SalesOrder` — Заказ клиента, `SalesOrderLine` — Строка заказа, `Shipment` — Отгрузка, `ShipmentItem` — Строка отгрузки, `ProductionTask` — Производственное задание, `TaskAllocation` — Распределение по заказу, `TaskConsumption` — Списание сырья

Связи с другими доменами: Department, Item, Lot, Recipe, StockMove.

```mermaid
erDiagram
    Client ||--o{ SalesOrder : "Клиент"
    SalesOrder ||--o{ SalesOrderLine : "Заказ"
    Item ||--o{ SalesOrderLine : "Продукция"
    SalesOrder ||--o| Shipment : "Заказ"
    Shipment ||--o{ ShipmentItem : "Отгрузка"
    SalesOrderLine ||--o{ ShipmentItem : "Строка заказа"
    StockMove ||--o| ShipmentItem : "Движение"
    Department ||--o{ ProductionTask : "Цех"
    Item ||--o{ ProductionTask : "Продукт"
    Recipe ||--o{ ProductionTask : "Рецептура"
    Lot |o--o| ProductionTask : "Выпущенная партия"
    ProductionTask ||--o{ TaskAllocation : "Задание"
    SalesOrderLine ||--o{ TaskAllocation : "Строка заказа"
    ProductionTask ||--o{ TaskConsumption : "Задание"
    StockMove ||--o| TaskConsumption : "Движение"
    Client {
        int id PK
        string kind "Тип клиента"
        string name UK "Название"
        string tax_id "БИН/ИНН"
        string contact_person "Контактное лицо"
        string phone "Телефон"
        string email "Email"
        string legal_address "Юридический адрес"
        string delivery_address "Адрес доставки"
        decimal discount_percent "Скидка, %"
        int payment_delay_days "Отсрочка платежа, дней"
        text note "Примечание"
        bool is_active "Активен"
    }
    SalesOrder {
        int id PK
        string number UK "Номер"
        int client_id FK "Клиент"
        string status "Статус"
        date delivery_date "Дата отгрузки"
        string delivery_address "Адрес доставки"
        decimal discount_percent "Скидка, %"
        text comment "Комментарий"
        int created_by_id FK "Менеджер"
        datetime created_at "Создан"
        int confirmed_by_id FK "Подтвердил"
        datetime confirmed_at "Подтверждён"
    }
    SalesOrderLine {
        int id PK
        int order_id FK "Заказ"
        int item_id FK "Продукция"
        decimal quantity "Количество"
        decimal price "Цена со скидкой"
        decimal reserved_qty "Зарезервировано со склада"
        decimal to_produce "Требуется произвести"
    }
    Shipment {
        int id PK
        string number UK "Номер"
        int order_id FK "Заказ"
        date date "Дата отгрузки"
        string vehicle "Транспорт"
        string driver "Водитель"
        text comment "Комментарий"
        int created_by_id FK "Отгрузил"
        datetime created_at "Создана"
    }
    ShipmentItem {
        int id PK
        int shipment_id FK "Отгрузка"
        int order_line_id FK "Строка заказа"
        int move_id FK "Движение"
    }
    ProductionTask {
        int id PK
        string number UK "Номер"
        int department_id FK "Цех"
        int product_id FK "Продукт"
        int recipe_id FK "Рецептура"
        decimal planned_qty "План"
        date planned_date "Плановая дата"
        string status "Статус"
        decimal actual_qty "Выпущено годной"
        decimal defect_qty "Брак"
        decimal raw_cost "Стоимость списанного сырья"
        int output_lot_id FK "Выпущенная партия"
        text comment "Комментарий"
        int created_by_id FK "Создал"
        datetime created_at "Создано"
        int started_by_id FK "Запустил"
        datetime started_at "Запущено"
        int finished_by_id FK "Завершил"
        datetime finished_at "Завершено"
    }
    TaskAllocation {
        int id PK
        int task_id FK "Задание"
        int order_line_id FK "Строка заказа"
        decimal quantity "Количество"
        decimal fulfilled "Выполнено"
    }
    TaskConsumption {
        int id PK
        int task_id FK "Задание"
        int move_id FK "Движение"
    }
```

## Бухгалтерия и зарплата

`Account` — Счёт, `JournalEntry` — Операция, `Posting` — Проводка, `Invoice` — Счёт покупателю, `Payment` — Платёж, `PaymentAllocation` — Разнесение платежа, `PayrollRate` — Ставка удержания / взноса, `PayrollPeriod` — Расчётная ведомость, `Payslip` — Расчётный листок, `PayslipLine` — Строка расчётного листка

Связи с другими доменами: Client, Department, Employee, Position, Shipment, Supplier.

```mermaid
erDiagram
    JournalEntry ||--o{ Posting : "Операция"
    Account ||--o{ Posting : "Дебет"
    Account ||--o{ Posting : "Кредит"
    Client |o--o{ Posting : "Клиент"
    Supplier |o--o{ Posting : "Поставщик"
    Client ||--o{ Invoice : "Клиент"
    Shipment |o--o| Invoice : "Отгрузка"
    Client |o--o{ Payment : "Клиент"
    Supplier |o--o{ Payment : "Поставщик"
    Invoice |o--o{ Payment : "В оплату счёта"
    Payment ||--o{ PaymentAllocation : "Платёж"
    Invoice ||--o{ PaymentAllocation : "Счёт"
    PayrollPeriod ||--o{ Payslip : "Ведомость"
    Employee ||--o{ Payslip : "Сотрудник"
    Department ||--o{ Payslip : "Подразделение"
    Position ||--o{ Payslip : "Должность"
    Payslip ||--o{ PayslipLine : "Листок"
    PayrollRate ||--o{ PayslipLine : "Ставка"
    Account {
        int id PK
        string code UK "Код"
        string name "Название"
        string type "Тип"
        bool is_active "Используется"
    }
    JournalEntry {
        int id PK
        date date "Дата"
        string description "Содержание"
        string source_type "Основание"
        int source_id "ID документа"
        int created_by_id FK "Автор"
        datetime created_at "Создана"
    }
    Posting {
        int id PK
        int entry_id FK "Операция"
        int debit_id FK "Дебет"
        int credit_id FK "Кредит"
        decimal amount "Сумма"
        int client_id FK "Клиент"
        int supplier_id FK "Поставщик"
        string comment "Комментарий"
    }
    Invoice {
        int id PK
        string number UK "Номер"
        int client_id FK "Клиент"
        int shipment_id FK "Отгрузка"
        date date "Дата"
        date due_date "Оплатить до"
        decimal amount "Сумма"
        datetime created_at "Создан"
    }
    Payment {
        int id PK
        string number UK "Номер"
        string direction "Направление"
        string method "Способ"
        date date "Дата"
        decimal amount "Сумма"
        int client_id FK "Клиент"
        int supplier_id FK "Поставщик"
        int invoice_id FK "В оплату счёта"
        string comment "Назначение платежа"
        int created_by_id FK "Автор"
        datetime created_at "Создан"
    }
    PaymentAllocation {
        int id PK
        int payment_id FK "Платёж"
        int invoice_id FK "Счёт"
        decimal amount "Сумма"
    }
    PayrollRate {
        int id PK
        string code UK "Код"
        string name "Название"
        string payer "Кто платит"
        string base "База"
        decimal percent "Ставка, %"
        string account_code "Счёт обязательства"
        bool is_active "Применяется"
    }
    PayrollPeriod {
        int id PK
        int year "Год"
        int month "Месяц"
        string status "Статус"
        datetime calculated_at "Рассчитана"
        datetime posted_at "Проведена"
        datetime paid_at "Выплачена"
        int created_by_id FK "Автор"
    }
    Payslip {
        int id PK
        int period_id FK "Ведомость"
        int employee_id FK "Сотрудник"
        int department_id FK "Подразделение"
        int position_id FK "Должность"
        decimal salary "Оклад"
        int norm_days "Норма, раб. дней"
        int worked_days "Отработано, дней"
        int vacation_days "Отпуск, календ. дней"
        int sick_days "Больничный, раб. дней"
        int unpaid_days "Без содержания, дней"
        decimal salary_accrued "Оклад за отработанное"
        decimal vacation_pay "Отпускные"
        decimal sick_pay "Больничные"
        decimal bonus "Премия"
        decimal gross "Начислено"
        decimal withheld "Удержано"
        decimal net "К выплате"
        decimal employer_total "Взносы работодателя"
    }
    PayslipLine {
        int id PK
        int payslip_id FK "Листок"
        int rate_id FK "Ставка"
        string payer "Кто платит"
        decimal base "База"
        decimal percent "Ставка, %"
        decimal amount "Сумма"
    }
```
