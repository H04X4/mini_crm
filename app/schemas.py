from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List


# ==================== Operator Schemas ====================

class OperatorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    is_active: bool = True
    max_active_contacts: int = Field(default=10, ge=1, le=1000)


class OperatorCreate(OperatorBase):
    pass


class OperatorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    max_active_contacts: Optional[int] = Field(None, ge=1, le=1000)


class OperatorResponse(OperatorBase):
    id: int
    created_at: datetime
    current_load: int = 0  # Текущая нагрузка (активные обращения)
    
    model_config = ConfigDict(from_attributes=True)


class OperatorWithStats(OperatorResponse):
    """Оператор с детальной статистикой"""
    sources: List["SourceAssignmentInfo"] = []


# ==================== Source Schemas ====================

class SourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    description: Optional[str] = None
    is_active: bool = True


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SourceResponse(SourceBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SourceWithOperators(SourceResponse):
    """Источник со списком назначенных операторов"""
    operators: List["OperatorAssignmentInfo"] = []


# ==================== Assignment Schemas ====================

class AssignmentCreate(BaseModel):
    operator_id: int
    source_id: int
    weight: int = Field(default=1, ge=1, le=1000)


class AssignmentUpdate(BaseModel):
    weight: int = Field(..., ge=1, le=1000)


class OperatorAssignmentInfo(BaseModel):
    """Информация об операторе в контексте источника"""
    operator_id: int
    operator_name: str
    weight: int
    is_active: bool
    current_load: int
    max_active_contacts: int
    
    model_config = ConfigDict(from_attributes=True)


class SourceAssignmentInfo(BaseModel):
    """Информация об источнике в контексте оператора"""
    source_id: int
    source_code: str
    source_name: str
    weight: int
    
    model_config = ConfigDict(from_attributes=True)


# ==================== Lead Schemas ====================

class LeadBase(BaseModel):
    external_id: str = Field(..., min_length=1, max_length=255)
    name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)


class LeadCreate(LeadBase):
    pass


class LeadResponse(LeadBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class LeadWithContacts(LeadResponse):
    """Лид со списком обращений"""
    contacts: List["ContactResponse"] = []


# ==================== Contact Schemas ====================

class ContactCreate(BaseModel):
    """Данные для создания обращения"""
    lead_external_id: str = Field(..., description="Внешний ID лида для идентификации")
    source_code: str = Field(..., description="Код источника (бота)")
    message: Optional[str] = None
    # Опциональные данные для создания/обновления лида
    lead_name: Optional[str] = None
    lead_phone: Optional[str] = None
    lead_email: Optional[str] = None


class ContactStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r'^(new|in_progress|closed)$')


class ContactResponse(BaseModel):
    id: int
    lead_id: int
    source_id: int
    source_code: str
    operator_id: Optional[int]
    operator_name: Optional[str]
    status: str
    message: Optional[str]
    created_at: datetime
    assigned_at: Optional[datetime]
    closed_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class ContactCreateResponse(ContactResponse):
    """Ответ на создание обращения"""
    lead: LeadResponse
    distribution_info: str  # Информация о том, как был выбран оператор


# ==================== Statistics Schemas ====================

class OperatorLoadStats(BaseModel):
    operator_id: int
    operator_name: str
    total_contacts: int
    active_contacts: int
    closed_contacts: int
    load_percentage: float


class SourceDistributionStats(BaseModel):
    source_code: str
    source_name: str
    total_contacts: int
    operators: List[OperatorLoadStats]


class SystemStats(BaseModel):
    total_operators: int
    active_operators: int
    total_sources: int
    total_leads: int
    total_contacts: int
    active_contacts: int


# Forward references
OperatorWithStats.model_rebuild()
SourceWithOperators.model_rebuild()
LeadWithContacts.model_rebuild()