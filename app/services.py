import random
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from . import models, schemas


class OperatorService:
    """Сервис для работы с операторами"""
    
    @staticmethod
    def get_active_contacts_count(db: Session, operator_id: int) -> int:
        """Получить количество активных обращений оператора"""
        return db.query(models.Contact).filter(
            models.Contact.operator_id == operator_id,
            models.Contact.status.in_(["new", "in_progress"])
        ).count()
    
    @staticmethod
    def create(db: Session, data: schemas.OperatorCreate) -> models.Operator:
        operator = models.Operator(**data.model_dump())
        db.add(operator)
        db.commit()
        db.refresh(operator)
        return operator
    
    @staticmethod
    def get_all(db: Session) -> List[models.Operator]:
        return db.query(models.Operator).all()
    
    @staticmethod
    def get_by_id(db: Session, operator_id: int) -> Optional[models.Operator]:
        return db.query(models.Operator).filter(models.Operator.id == operator_id).first()
    
    @staticmethod
    def update(db: Session, operator_id: int, data: schemas.OperatorUpdate) -> Optional[models.Operator]:
        operator = db.query(models.Operator).filter(models.Operator.id == operator_id).first()
        if not operator:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(operator, field, value)
        
        db.commit()
        db.refresh(operator)
        return operator
    
    @staticmethod
    def delete(db: Session, operator_id: int) -> bool:
        operator = db.query(models.Operator).filter(models.Operator.id == operator_id).first()
        if not operator:
            return False
        db.delete(operator)
        db.commit()
        return True
    
    @staticmethod
    def get_with_stats(db: Session, operator_id: int) -> Optional[dict]:
        """Получить оператора с детальной статистикой"""
        operator = db.query(models.Operator).filter(models.Operator.id == operator_id).first()
        if not operator:
            return None
        
        current_load = OperatorService.get_active_contacts_count(db, operator_id)
        
        # Получаем назначения на источники
        sources = []
        for assignment in operator.source_assignments:
            sources.append({
                "source_id": assignment.source.id,
                "source_code": assignment.source.code,
                "source_name": assignment.source.name,
                "weight": assignment.weight
            })
        
        return {
            "id": operator.id,
            "name": operator.name,
            "is_active": operator.is_active,
            "max_active_contacts": operator.max_active_contacts,
            "created_at": operator.created_at,
            "current_load": current_load,
            "sources": sources
        }


class SourceService:
    """Сервис для работы с источниками"""
    
    @staticmethod
    def create(db: Session, data: schemas.SourceCreate) -> models.Source:
        source = models.Source(**data.model_dump())
        db.add(source)
        db.commit()
        db.refresh(source)
        return source
    
    @staticmethod
    def get_all(db: Session) -> List[models.Source]:
        return db.query(models.Source).all()
    
    @staticmethod
    def get_by_id(db: Session, source_id: int) -> Optional[models.Source]:
        return db.query(models.Source).filter(models.Source.id == source_id).first()
    
    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[models.Source]:
        return db.query(models.Source).filter(models.Source.code == code).first()
    
    @staticmethod
    def update(db: Session, source_id: int, data: schemas.SourceUpdate) -> Optional[models.Source]:
        source = db.query(models.Source).filter(models.Source.id == source_id).first()
        if not source:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(source, field, value)
        
        db.commit()
        db.refresh(source)
        return source
    
    @staticmethod
    def delete(db: Session, source_id: int) -> bool:
        source = db.query(models.Source).filter(models.Source.id == source_id).first()
        if not source:
            return False
        db.delete(source)
        db.commit()
        return True
    
    @staticmethod
    def get_with_operators(db: Session, source_id: int) -> Optional[dict]:
        """Получить источник со списком назначенных операторов"""
        source = db.query(models.Source).filter(models.Source.id == source_id).first()
        if not source:
            return None
        
        operators = []
        for assignment in source.operator_assignments:
            current_load = OperatorService.get_active_contacts_count(db, assignment.operator_id)
            operators.append({
                "operator_id": assignment.operator.id,
                "operator_name": assignment.operator.name,
                "weight": assignment.weight,
                "is_active": assignment.operator.is_active,
                "current_load": current_load,
                "max_active_contacts": assignment.operator.max_active_contacts
            })
        
        return {
            "id": source.id,
            "name": source.name,
            "code": source.code,
            "description": source.description,
            "is_active": source.is_active,
            "created_at": source.created_at,
            "operators": operators
        }


class AssignmentService:
    """Сервис для управления назначениями операторов на источники"""
    
    @staticmethod
    def create_or_update(db: Session, data: schemas.AssignmentCreate) -> models.OperatorSourceAssignment:
        """Создать или обновить назначение оператора на источник"""
        existing = db.query(models.OperatorSourceAssignment).filter(
            models.OperatorSourceAssignment.operator_id == data.operator_id,
            models.OperatorSourceAssignment.source_id == data.source_id
        ).first()
        
        if existing:
            existing.weight = data.weight
            db.commit()
            db.refresh(existing)
            return existing
        
        assignment = models.OperatorSourceAssignment(**data.model_dump())
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return assignment
    
    @staticmethod
    def delete(db: Session, operator_id: int, source_id: int) -> bool:
        """Удалить назначение оператора с источника"""
        assignment = db.query(models.OperatorSourceAssignment).filter(
            models.OperatorSourceAssignment.operator_id == operator_id,
            models.OperatorSourceAssignment.source_id == source_id
        ).first()
        
        if not assignment:
            return False
        
        db.delete(assignment)
        db.commit()
        return True
    
    @staticmethod
    def get_source_operators(db: Session, source_id: int) -> List[models.OperatorSourceAssignment]:
        """Получить всех операторов назначенных на источник"""
        return db.query(models.OperatorSourceAssignment).filter(
            models.OperatorSourceAssignment.source_id == source_id
        ).all()


class LeadService:
    """Сервис для работы с лидами"""
    
    @staticmethod
    def get_or_create(
        db: Session, 
        external_id: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None
    ) -> Tuple[models.Lead, bool]:
        """
        Найти лида по external_id или создать нового.
        Возвращает (лид, создан_новый).
        """
        lead = db.query(models.Lead).filter(models.Lead.external_id == external_id).first()
        
        if lead:
            # Обновляем данные, если они переданы
            updated = False
            if name and not lead.name:
                lead.name = name
                updated = True
            if phone and not lead.phone:
                lead.phone = phone
                updated = True
            if email and not lead.email:
                lead.email = email
                updated = True
            if updated:
                db.commit()
                db.refresh(lead)
            return lead, False
        
        # Создаём нового лида
        lead = models.Lead(
            external_id=external_id,
            name=name,
            phone=phone,
            email=email
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead, True
    
    @staticmethod
    def get_all(db: Session) -> List[models.Lead]:
        return db.query(models.Lead).all()
    
    @staticmethod
    def get_by_id(db: Session, lead_id: int) -> Optional[models.Lead]:
        return db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    
    @staticmethod
    def get_with_contacts(db: Session, lead_id: int) -> Optional[models.Lead]:
        """Получить лида со всеми обращениями"""
        return db.query(models.Lead).filter(models.Lead.id == lead_id).first()


class DistributionService:
    """
    Сервис распределения обращений между операторами.
    
    Алгоритм распределения:
    1. Находим всех операторов, назначенных на данный источник
    2. Фильтруем: оператор активен И текущая нагрузка < лимита
    3. Выбираем случайно с вероятностью пропорциональной весу:
       P(оператор) = вес_оператора / сумма_весов_всех_подходящих
    """
    
    @staticmethod
    def select_operator(
        db: Session, 
        source_id: int
    ) -> Tuple[Optional[models.Operator], str]:
        """
        Выбрать оператора для обращения из данного источника.
        
        Возвращает: (оператор или None, описание_выбора)
        """
        # 1. Получаем все назначения для источника
        assignments = db.query(models.OperatorSourceAssignment).filter(
            models.OperatorSourceAssignment.source_id == source_id
        ).all()
        
        if not assignments:
            return None, "Нет операторов, назначенных на данный источник"
        
        # 2. Фильтруем доступных операторов
        available_operators = []
        unavailable_reasons = []
        
        for assignment in assignments:
            operator = assignment.operator
            
            if not operator.is_active:
                unavailable_reasons.append(f"{operator.name}: неактивен")
                continue
            
            current_load = OperatorService.get_active_contacts_count(db, operator.id)
            
            if current_load >= operator.max_active_contacts:
                unavailable_reasons.append(
                    f"{operator.name}: достигнут лимит ({current_load}/{operator.max_active_contacts})"
                )
                continue
            
            available_operators.append({
                "operator": operator,
                "weight": assignment.weight,
                "current_load": current_load
            })
        
        if not available_operators:
            reasons = "; ".join(unavailable_reasons) if unavailable_reasons else "Неизвестная причина"
            return None, f"Нет доступных операторов. Причины: {reasons}"
        
        # 3. Взвешенный случайный выбор
        total_weight = sum(op["weight"] for op in available_operators)
        
        # Формируем список для выбора
        weighted_choices = []
        for op_data in available_operators:
            weighted_choices.extend([op_data["operator"]] * op_data["weight"])
        
        selected_operator = random.choice(weighted_choices)
        
        # Формируем описание выбора
        distribution_desc = ", ".join([
            f"{op['operator'].name}: вес {op['weight']} ({op['weight']*100//total_weight}%)"
            for op in available_operators
        ])
        info = f"Выбран {selected_operator.name} из [{distribution_desc}]"
        
        return selected_operator, info


class ContactService:
    """Сервис для работы с обращениями"""
    
    @staticmethod
    def create(db: Session, data: schemas.ContactCreate) -> Tuple[models.Contact, str]:
        """
        Создать обращение:
        1. Найти/создать лида
        2. Определить источник
        3. Выбрать оператора
        4. Создать обращение
        
        Возвращает: (обращение, информация_о_распределении)
        """
        # 1. Находим источник
        source = SourceService.get_by_code(db, data.source_code)
        if not source:
            raise ValueError(f"Источник с кодом '{data.source_code}' не найден")
        
        if not source.is_active:
            raise ValueError(f"Источник '{data.source_code}' неактивен")
        
        # 2. Находим или создаём лида
        lead, is_new_lead = LeadService.get_or_create(
            db,
            external_id=data.lead_external_id,
            name=data.lead_name,
            phone=data.lead_phone,
            email=data.lead_email
        )
        
        # 3. Выбираем оператора
        operator, distribution_info = DistributionService.select_operator(db, source.id)
        
        # 4. Создаём обращение
        contact = models.Contact(
            lead_id=lead.id,
            source_id=source.id,
            operator_id=operator.id if operator else None,
            message=data.message,
            status="new" if operator else "new",  # Можно добавить статус "pending" если нет оператора
            assigned_at=datetime.utcnow() if operator else None
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
        
        lead_info = "создан новый лид" if is_new_lead else "найден существующий лид"
        full_info = f"{lead_info}; {distribution_info}"
        
        return contact, full_info
    
    @staticmethod
    def get_all(db: Session, status: Optional[str] = None) -> List[models.Contact]:
        query = db.query(models.Contact)
        if status:
            query = query.filter(models.Contact.status == status)
        return query.order_by(models.Contact.created_at.desc()).all()
    
    @staticmethod
    def get_by_id(db: Session, contact_id: int) -> Optional[models.Contact]:
        return db.query(models.Contact).filter(models.Contact.id == contact_id).first()
    
    @staticmethod
    def update_status(
        db: Session, 
        contact_id: int, 
        new_status: str
    ) -> Optional[models.Contact]:
        """Обновить статус обращения"""
        contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
        if not contact:
            return None
        
        contact.status = new_status
        if new_status == "closed":
            contact.closed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(contact)
        return contact
    
    @staticmethod
    def reassign(db: Session, contact_id: int) -> Tuple[Optional[models.Contact], str]:
        """Переназначить обращение другому оператору"""
        contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
        if not contact:
            return None, "Обращение не найдено"
        
        if contact.status == "closed":
            return None, "Нельзя переназначить закрытое обращение"
        
        operator, info = DistributionService.select_operator(db, contact.source_id)
        
        contact.operator_id = operator.id if operator else None
        contact.assigned_at = datetime.utcnow() if operator else None
        db.commit()
        db.refresh(contact)
        
        return contact, info


class StatsService:
    """Сервис для получения статистики"""
    
    @staticmethod
    def get_system_stats(db: Session) -> dict:
        """Общая статистика системы"""
        return {
            "total_operators": db.query(models.Operator).count(),
            "active_operators": db.query(models.Operator).filter(
                models.Operator.is_active == True
            ).count(),
            "total_sources": db.query(models.Source).count(),
            "total_leads": db.query(models.Lead).count(),
            "total_contacts": db.query(models.Contact).count(),
            "active_contacts": db.query(models.Contact).filter(
                models.Contact.status.in_(["new", "in_progress"])
            ).count()
        }
    
    @staticmethod
    def get_source_distribution(db: Session, source_id: int) -> dict:
        """Статистика распределения обращений по операторам для источника"""
        source = db.query(models.Source).filter(models.Source.id == source_id).first()
        if not source:
            return None
        
        # Статистика по операторам
        operator_stats = db.query(
            models.Operator.id,
            models.Operator.name,
            func.count(models.Contact.id).label("total"),
            func.sum(
                func.cast(models.Contact.status.in_(["new", "in_progress"]), Integer)
            ).label("active")
        ).outerjoin(
            models.Contact,
            and_(
                models.Contact.operator_id == models.Operator.id,
                models.Contact.source_id == source_id
            )
        ).join(
            models.OperatorSourceAssignment,
            and_(
                models.OperatorSourceAssignment.operator_id == models.Operator.id,
                models.OperatorSourceAssignment.source_id == source_id
            )
        ).group_by(models.Operator.id).all()
        
        total_contacts = db.query(models.Contact).filter(
            models.Contact.source_id == source_id
        ).count()
        
        operators = []
        for stat in operator_stats:
            operators.append({
                "operator_id": stat.id,
                "operator_name": stat.name,
                "total_contacts": stat.total or 0,
                "active_contacts": stat.active or 0,
                "closed_contacts": (stat.total or 0) - (stat.active or 0),
                "load_percentage": round((stat.total or 0) / total_contacts * 100, 1) if total_contacts > 0 else 0
            })
        
        return {
            "source_code": source.code,
            "source_name": source.name,
            "total_contacts": total_contacts,
            "operators": operators
        }