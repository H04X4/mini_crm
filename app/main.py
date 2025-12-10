from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from .database import get_db, init_db
from . import schemas, services


app = FastAPI(
    title="Mini-CRM: Lead Distribution",
    description="""
    Система распределения лидов между операторами по источникам.
    
    ## Основные возможности:
    - Управление операторами (создание, лимиты, активация)
    - Управление источниками (ботами)
    - Настройка весов распределения
    - Автоматическое распределение обращений
    - Статистика и отчёты
    """,
    version="1.0.0"
)


@app.on_event("startup")
def startup():
    init_db()


# ==================== Operators ====================

@app.post("/operators", response_model=schemas.OperatorResponse, tags=["Операторы"])
def create_operator(data: schemas.OperatorCreate, db: Session = Depends(get_db)):
    """Создать нового оператора"""
    operator = services.OperatorService.create(db, data)
    return {
        **operator.__dict__,
        "current_load": 0
    }


@app.get("/operators", response_model=List[schemas.OperatorResponse], tags=["Операторы"])
def list_operators(db: Session = Depends(get_db)):
    """Получить список всех операторов"""
    operators = services.OperatorService.get_all(db)
    result = []
    for op in operators:
        current_load = services.OperatorService.get_active_contacts_count(db, op.id)
        result.append({
            **op.__dict__,
            "current_load": current_load
        })
    return result


@app.get("/operators/{operator_id}", response_model=schemas.OperatorWithStats, tags=["Операторы"])
def get_operator(operator_id: int, db: Session = Depends(get_db)):
    """Получить оператора с детальной информацией"""
    result = services.OperatorService.get_with_stats(db, operator_id)
    if not result:
        raise HTTPException(status_code=404, detail="Оператор не найден")
    return result


@app.patch("/operators/{operator_id}", response_model=schemas.OperatorResponse, tags=["Операторы"])
def update_operator(operator_id: int, data: schemas.OperatorUpdate, db: Session = Depends(get_db)):
    """
    Обновить данные оператора.
    
    Можно изменить:
    - name: имя
    - is_active: активность (влияет на распределение)
    - max_active_contacts: лимит одновременных обращений
    """
    operator = services.OperatorService.update(db, operator_id, data)
    if not operator:
        raise HTTPException(status_code=404, detail="Оператор не найден")
    current_load = services.OperatorService.get_active_contacts_count(db, operator_id)
    return {
        **operator.__dict__,
        "current_load": current_load
    }


@app.delete("/operators/{operator_id}", tags=["Операторы"])
def delete_operator(operator_id: int, db: Session = Depends(get_db)):
    """Удалить оператора"""
    if not services.OperatorService.delete(db, operator_id):
        raise HTTPException(status_code=404, detail="Оператор не найден")
    return {"message": "Оператор удалён"}


# ==================== Sources ====================

@app.post("/sources", response_model=schemas.SourceResponse, tags=["Источники"])
def create_source(data: schemas.SourceCreate, db: Session = Depends(get_db)):
    """Создать новый источник (бота)"""
    existing = services.SourceService.get_by_code(db, data.code)
    if existing:
        raise HTTPException(status_code=400, detail=f"Источник с кодом '{data.code}' уже существует")
    return services.SourceService.create(db, data)


@app.get("/sources", response_model=List[schemas.SourceResponse], tags=["Источники"])
def list_sources(db: Session = Depends(get_db)):
    """Получить список всех источников"""
    return services.SourceService.get_all(db)


@app.get("/sources/{source_id}", response_model=schemas.SourceWithOperators, tags=["Источники"])
def get_source(source_id: int, db: Session = Depends(get_db)):
    """Получить источник с назначенными операторами и их весами"""
    result = services.SourceService.get_with_operators(db, source_id)
    if not result:
        raise HTTPException(status_code=404, detail="Источник не найден")
    return result


@app.patch("/sources/{source_id}", response_model=schemas.SourceResponse, tags=["Источники"])
def update_source(source_id: int, data: schemas.SourceUpdate, db: Session = Depends(get_db)):
    """Обновить данные источника"""
    source = services.SourceService.update(db, source_id, data)
    if not source:
        raise HTTPException(status_code=404, detail="Источник не найден")
    return source


@app.delete("/sources/{source_id}", tags=["Источники"])
def delete_source(source_id: int, db: Session = Depends(get_db)):
    """Удалить источник"""
    if not services.SourceService.delete(db, source_id):
        raise HTTPException(status_code=404, detail="Источник не найден")
    return {"message": "Источник удалён"}


# ==================== Assignments (распределение по источникам) ====================

@app.post("/assignments", tags=["Настройка распределения"])
def assign_operator_to_source(data: schemas.AssignmentCreate, db: Session = Depends(get_db)):
    """
    Назначить оператора на источник с указанием веса.
    
    Вес определяет долю трафика. Например:
    - Оператор1 с весом 10 и Оператор2 с весом 30 → 25% и 75% соответственно
    
    Если назначение уже существует, обновляется вес.
    """
    # Проверяем существование оператора и источника
    operator = services.OperatorService.get_by_id(db, data.operator_id)
    if not operator:
        raise HTTPException(status_code=404, detail="Оператор не найден")
    
    source = services.SourceService.get_by_id(db, data.source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Источник не найден")
    
    assignment = services.AssignmentService.create_or_update(db, data)
    
    return {
        "message": "Назначение создано/обновлено",
        "operator_id": assignment.operator_id,
        "source_id": assignment.source_id,
        "weight": assignment.weight
    }


@app.delete("/assignments/{operator_id}/{source_id}", tags=["Настройка распределения"])
def remove_operator_from_source(operator_id: int, source_id: int, db: Session = Depends(get_db)):
    """Удалить назначение оператора с источника"""
    if not services.AssignmentService.delete(db, operator_id, source_id):
        raise HTTPException(status_code=404, detail="Назначение не найдено")
    return {"message": "Назначение удалено"}


# ==================== Contacts (обращения) ====================

@app.post("/contacts", response_model=schemas.ContactCreateResponse, tags=["Обращения"])
def create_contact(data: schemas.ContactCreate, db: Session = Depends(get_db)):
    """
    Зарегистрировать новое обращение.
    
    Система автоматически:
    1. Найдёт существующего лида по external_id или создаст нового
    2. Выберет оператора по весам с учётом лимитов нагрузки
    3. Создаст обращение и вернёт результат
    
    Если подходящих операторов нет, обращение создаётся без оператора.
    """
    try:
        contact, distribution_info = services.ContactService.create(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "id": contact.id,
        "lead_id": contact.lead_id,
        "source_id": contact.source_id,
        "source_code": contact.source.code,
        "operator_id": contact.operator_id,
        "operator_name": contact.operator.name if contact.operator else None,
        "status": contact.status,
        "message": contact.message,
        "created_at": contact.created_at,
        "assigned_at": contact.assigned_at,
        "closed_at": contact.closed_at,
        "lead": {
            "id": contact.lead.id,
            "external_id": contact.lead.external_id,
            "name": contact.lead.name,
            "phone": contact.lead.phone,
            "email": contact.lead.email,
            "created_at": contact.lead.created_at
        },
        "distribution_info": distribution_info
    }


@app.get("/contacts", response_model=List[schemas.ContactResponse], tags=["Обращения"])
def list_contacts(
    status: Optional[str] = Query(None, pattern=r'^(new|in_progress|closed)$'),
    db: Session = Depends(get_db)
):
    """Получить список обращений (можно фильтровать по статусу)"""
    contacts = services.ContactService.get_all(db, status)
    result = []
    for contact in contacts:
        result.append({
            "id": contact.id,
            "lead_id": contact.lead_id,
            "source_id": contact.source_id,
            "source_code": contact.source.code,
            "operator_id": contact.operator_id,
            "operator_name": contact.operator.name if contact.operator else None,
            "status": contact.status,
            "message": contact.message,
            "created_at": contact.created_at,
            "assigned_at": contact.assigned_at,
            "closed_at": contact.closed_at
        })
    return result


@app.patch("/contacts/{contact_id}/status", response_model=schemas.ContactResponse, tags=["Обращения"])
def update_contact_status(
    contact_id: int, 
    data: schemas.ContactStatusUpdate, 
    db: Session = Depends(get_db)
):
    """
    Обновить статус обращения.
    
    Доступные статусы:
    - new: новое обращение
    - in_progress: в работе
    - closed: завершено (освобождает нагрузку оператора)
    """
    contact = services.ContactService.update_status(db, contact_id, data.status)
    if not contact:
        raise HTTPException(status_code=404, detail="Обращение не найдено")
    return {
        "id": contact.id,
        "lead_id": contact.lead_id,
        "source_id": contact.source_id,
        "source_code": contact.source.code,
        "operator_id": contact.operator_id,
        "operator_name": contact.operator.name if contact.operator else None,
        "status": contact.status,
        "message": contact.message,
        "created_at": contact.created_at,
        "assigned_at": contact.assigned_at,
        "closed_at": contact.closed_at
    }


@app.post("/contacts/{contact_id}/reassign", tags=["Обращения"])
def reassign_contact(contact_id: int, db: Session = Depends(get_db)):
    """Переназначить обращение другому оператору"""
    contact, info = services.ContactService.reassign(db, contact_id)
    if not contact:
        raise HTTPException(status_code=400, detail=info)
    return {
        "message": "Обращение переназначено",
        "new_operator_id": contact.operator_id,
        "new_operator_name": contact.operator.name if contact.operator else None,
        "distribution_info": info
    }


# ==================== Leads ====================

@app.get("/leads", response_model=List[schemas.LeadResponse], tags=["Лиды"])
def list_leads(db: Session = Depends(get_db)):
    """Получить список всех лидов"""
    return services.LeadService.get_all(db)


@app.get("/leads/{lead_id}", response_model=schemas.LeadWithContacts, tags=["Лиды"])
def get_lead_with_contacts(lead_id: int, db: Session = Depends(get_db)):
    """Получить лида со всеми его обращениями из разных источников"""
    lead = services.LeadService.get_with_contacts(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Лид не найден")
    
    contacts = []
    for contact in lead.contacts:
        contacts.append({
            "id": contact.id,
            "lead_id": contact.lead_id,
            "source_id": contact.source_id,
            "source_code": contact.source.code,
            "operator_id": contact.operator_id,
            "operator_name": contact.operator.name if contact.operator else None,
            "status": contact.status,
            "message": contact.message,
            "created_at": contact.created_at,
            "assigned_at": contact.assigned_at,
            "closed_at": contact.closed_at
        })
    
    return {
        "id": lead.id,
        "external_id": lead.external_id,
        "name": lead.name,
        "phone": lead.phone,
        "email": lead.email,
        "created_at": lead.created_at,
        "contacts": contacts
    }


# ==================== Statistics ====================

@app.get("/stats", response_model=schemas.SystemStats, tags=["Статистика"])
def get_system_stats(db: Session = Depends(get_db)):
    """Общая статистика системы"""
    return services.StatsService.get_system_stats(db)


@app.get("/stats/sources/{source_id}", response_model=schemas.SourceDistributionStats, tags=["Статистика"])
def get_source_distribution(source_id: int, db: Session = Depends(get_db)):
    """Статистика распределения обращений по операторам для конкретного источника"""
    result = services.StatsService.get_source_distribution(db, source_id)
    if not result:
        raise HTTPException(status_code=404, detail="Источник не найден")
    return result


# ==================== Health Check ====================

@app.get("/health", tags=["Системные"])
def health_check():
    """Проверка работоспособности сервиса"""
    return {"status": "ok"}