from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, 
    DateTime, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class Operator(Base):
    """
    Оператор - сотрудник, который обрабатывает обращения.
    
    Атрибуты:
        - is_active: может ли получать новые обращения
        - max_active_contacts: лимит одновременных активных обращений
    """
    __tablename__ = "operators"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    max_active_contacts = Column(Integer, default=10, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    source_assignments = relationship(
        "OperatorSourceAssignment", 
        back_populates="operator",
        cascade="all, delete-orphan"
    )
    contacts = relationship("Contact", back_populates="operator")

    def __repr__(self):
        return f"<Operator(id={self.id}, name='{self.name}', active={self.is_active})>"


class Source(Base):
    """
    Источник (бот) - канал, откуда приходят обращения.
    
    Например: Telegram-бот, WhatsApp, сайт и т.д.
    """
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False)  # Уникальный код источника
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    operator_assignments = relationship(
        "OperatorSourceAssignment", 
        back_populates="source",
        cascade="all, delete-orphan"
    )
    contacts = relationship("Contact", back_populates="source")

    def __repr__(self):
        return f"<Source(id={self.id}, code='{self.code}')>"


class OperatorSourceAssignment(Base):
    """
    Назначение оператора на источник с указанием веса.
    
    Вес определяет долю трафика: если у оператора1 вес 10, а у оператора2 вес 30,
    то оператор2 получит примерно 75% обращений (30/(10+30)).
    """
    __tablename__ = "operator_source_assignments"

    id = Column(Integer, primary_key=True, index=True)
    operator_id = Column(Integer, ForeignKey("operators.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    weight = Column(Integer, default=1, nullable=False)  # Вес/компетенция >= 1

    # Связи
    operator = relationship("Operator", back_populates="source_assignments")
    source = relationship("Source", back_populates="operator_assignments")

    __table_args__ = (
        UniqueConstraint('operator_id', 'source_id', name='uq_operator_source'),
    )

    def __repr__(self):
        return f"<Assignment(operator={self.operator_id}, source={self.source_id}, weight={self.weight})>"


class Lead(Base):
    """
    Лид - потенциальный клиент.
    
    Идентификация: по полю external_id (например, номер телефона, 
    Telegram ID, email или UUID клиента из внешней системы).
    Один лид может обращаться через разные источники.
    """
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    contacts = relationship("Contact", back_populates="lead", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Lead(id={self.id}, external_id='{self.external_id}')>"


class Contact(Base):
    """
    Обращение - факт контакта лида через определённый источник.
    
    Статусы:
        - new: новое обращение
        - in_progress: в работе у оператора
        - closed: завершено
    
    Активными считаются обращения со статусом 'new' или 'in_progress'.
    Они учитываются при подсчёте нагрузки оператора.
    """
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False)
    operator_id = Column(Integer, ForeignKey("operators.id", ondelete="SET NULL"), nullable=True)
    
    status = Column(String(20), default="new", nullable=False)  # new, in_progress, closed
    message = Column(Text, nullable=True)  # Текст обращения
    created_at = Column(DateTime, default=datetime.utcnow)
    assigned_at = Column(DateTime, nullable=True)  # Когда назначен оператор
    closed_at = Column(DateTime, nullable=True)

    # Связи
    lead = relationship("Lead", back_populates="contacts")
    source = relationship("Source", back_populates="contacts")
    operator = relationship("Operator", back_populates="contacts")

    def __repr__(self):
        return f"<Contact(id={self.id}, lead={self.lead_id}, source={self.source_id}, status='{self.status}')>"