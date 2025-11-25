from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal

# ==================== USER MODELS ====================

class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# ==================== CALCULATOR MODELS ====================

class TaxRegime(str):
    MEI = "MEI"
    PJ_SIMPLES = "PJ_SIMPLES"
    PJ_PRESUMIDO = "PJ_PRESUMIDO"
    AUTONOMO = "AUTONOMO"

class CalculatorInput(BaseModel):
    # Pretensões
    desired_monthly_income: Decimal = Field(gt=0, description="Pró-labore desejado")
    hours_per_day: int = Field(ge=1, le=16, description="Horas trabalhadas por dia")
    days_per_week: int = Field(ge=1, le=7, description="Dias trabalhados por semana")
    vacation_weeks: int = Field(ge=0, le=8, default=4, description="Semanas de férias por ano")
    
    # Regime tributário
    tax_regime: Literal["MEI", "PJ_SIMPLES", "PJ_PRESUMIDO", "AUTONOMO"]
    
    # Provisões
    include_13th_salary: bool = Field(default=True)
    include_vacation_bonus: bool = Field(default=True)
    
    # Despesas
    monthly_expenses: Decimal = Field(ge=0, default=0, description="Despesas fixas mensais")
    variable_expenses: Decimal = Field(ge=0, default=0, description="Despesas variáveis mensais")
    
    # Margem
    profit_margin_percentage: Decimal = Field(ge=0, le=100, default=20, description="Margem de lucro desejada")

class CalculatorResult(BaseModel):
    # Valores calculados
    hourly_rate: Decimal
    daily_rate: Decimal
    weekly_rate: Decimal
    monthly_rate: Decimal
    
    # Detalhamento
    total_monthly_costs: Decimal
    total_annual_costs: Decimal
    monthly_taxes: Decimal
    monthly_provisions: Decimal
    net_monthly_income: Decimal
    
    # Informações adicionais
    working_hours_per_month: int
    working_days_per_month: int
    tax_regime: str
    
    # Sugestões de projeto
    small_project_value: Decimal  # 20-40h
    medium_project_value: Decimal  # 80-120h
    large_project_value: Decimal  # 160-240h

class CalculatorSaved(BaseModel):
    id: str
    user_id: str
    name: str
    input_data: dict
    result_data: dict
    created_at: datetime

# ==================== CLIENT MODELS ====================

class ClientBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None

class Client(ClientBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# ==================== PROJECT MODELS ====================

class ProjectStatus(str):
    PROPOSAL = "PROPOSAL"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class ProjectBase(BaseModel):
    client_id: str
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    value: Decimal = Field(gt=0)
    estimated_hours: Optional[int] = Field(ge=0, default=None)
    status: Literal["PROPOSAL", "IN_PROGRESS", "COMPLETED", "CANCELLED"] = "PROPOSAL"
    start_date: Optional[datetime] = None
    deadline: Optional[datetime] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    value: Optional[Decimal] = None
    estimated_hours: Optional[int] = None
    status: Optional[Literal["PROPOSAL", "IN_PROGRESS", "COMPLETED", "CANCELLED"]] = None
    start_date: Optional[datetime] = None
    deadline: Optional[datetime] = None

class Project(ProjectBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# ==================== PAYMENT MODELS ====================

class PaymentStatus(str):
    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"

class PaymentBase(BaseModel):
    project_id: str
    amount: Decimal = Field(gt=0)
    due_date: datetime
    status: Literal["PENDING", "PAID", "OVERDUE", "CANCELLED"] = "PENDING"
    payment_date: Optional[datetime] = None
    notes: Optional[str] = None

class PaymentCreate(PaymentBase):
    pass

class PaymentUpdate(BaseModel):
    amount: Optional[Decimal] = None
    due_date: Optional[datetime] = None
    status: Optional[Literal["PENDING", "PAID", "OVERDUE", "CANCELLED"]] = None
    payment_date: Optional[datetime] = None
    notes: Optional[str] = None

class Payment(PaymentBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# ==================== DASHBOARD MODELS ====================

class DashboardStats(BaseModel):
    # Resumo financeiro
    total_revenue_current_month: Decimal
    total_revenue_last_month: Decimal
    pending_payments: Decimal
    overdue_payments: Decimal
    
    # Projetos
    active_projects_count: int
    completed_projects_count: int
    total_projects_value: Decimal
    
    # Clientes
    total_clients: int
    active_clients_current_month: int
    
    # Calculado
    average_project_value: Decimal
    monthly_growth_percentage: Decimal
