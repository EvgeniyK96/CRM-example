"""
Упрощённый план счетов (по образцу типового плана счетов РК) и счета, которые используют автопроводки.
Учебная модель: без НДС, без субсчетов, авансы покупателей — кредитовым сальдо счёта 1210.
"""

CASH = "1010"
BANK = "1030"
RECEIVABLES = "1210"
RAW_MATERIALS = "1310"
FINISHED_GOODS = "1320"
INCOME_TAX = "3120"
SOCIAL_CONTRIBUTIONS = "3211"
HEALTH_INSURANCE = "3213"
PENSION = "3220"
PAYABLES = "3310"
PAYROLL = "3350"
RETAINED_EARNINGS = "5510"
REVENUE = "6010"
COST_OF_SALES = "7010"
PRODUCTION_LABOR = "7110"
ADMIN_EXPENSES = "7210"
OTHER_EXPENSES = "7470"
PRODUCTION = "8110"

# код, название, тип
CHART = [
    (CASH, "Денежные средства в кассе", "asset"),
    (BANK, "Денежные средства на текущих банковских счетах", "asset"),
    (RECEIVABLES, "Краткосрочная дебиторская задолженность покупателей", "asset"),
    (RAW_MATERIALS, "Сырьё и материалы", "asset"),
    (FINISHED_GOODS, "Готовая продукция", "asset"),
    (INCOME_TAX, "Индивидуальный подоходный налог", "liability"),
    (SOCIAL_CONTRIBUTIONS, "Обязательства по социальным отчислениям", "liability"),
    (HEALTH_INSURANCE, "Обязательства по взносам на ОСМС", "liability"),
    (PENSION, "Обязательства по пенсионным взносам", "liability"),
    (PAYABLES, "Краткосрочная кредиторская задолженность поставщикам", "liability"),
    (PAYROLL, "Краткосрочная задолженность по оплате труда", "liability"),
    (RETAINED_EARNINGS, "Нераспределённая прибыль (непокрытый убыток)", "equity"),
    (REVENUE, "Доход от реализации продукции", "income"),
    (COST_OF_SALES, "Себестоимость реализованной продукции", "expense"),
    (PRODUCTION_LABOR, "Расходы на оплату труда производства (директ-костинг)", "expense"),
    (ADMIN_EXPENSES, "Административные расходы", "expense"),
    (OTHER_EXPENSES, "Прочие расходы (потери, брак, порча)", "expense"),
    (PRODUCTION, "Основное производство", "asset"),
]
