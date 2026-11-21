from pydantic import BaseModel, ConfigDict


class SummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    range: str
    revenue_paise: int
    collected_paise: int
    outstanding_paise: int
    jobs_completed: int
    jobs_unfinished: int
    open_tickets: int
    low_stock_count: int


class ProfitJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: int
    order_number: str
    customer_name: str
    revenue_paise: int
    parts_paise: int
    labour_paise: int
    profit_paise: int


class UnfinishedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    awaiting_survey: int
    awaiting_payment: int
    awaiting_dispatch: int
    awaiting_install: int


class TechHoursOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str
    hours_worked: float
    hourly_rate_paise: int
    amount_due_paise: int
