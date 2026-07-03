from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Project(Base):
    __tablename__ = 'projects'

    id = Column(String, primary_key=True)  # lower-case slugified name
    name = Column(String, nullable=False)
    target_variable = Column(String, nullable=False)
    problem_type = Column(String, nullable=False)  # classification, regression
    description = Column(String, nullable=True)
    status = Column(String, default='Created')  # Created, EDA, Preprocessed, Training, Ready
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    decisions = relationship("DecisionMemory", back_populates="project", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="project", cascade="all, delete-orphan")
    knowledge_cards = relationship("KnowledgeCard", back_populates="project", cascade="all, delete-orphan")


class DecisionMemory(Base):
    __tablename__ = 'decision_memory'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey('projects.id'), nullable=False)
    feature_name = Column(String, nullable=False)
    decision = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    override_active = Column(Boolean, default=False)
    user_choice = Column(String, nullable=True)

    project = relationship("Project", back_populates="decisions")


class TimelineEvent(Base):
    __tablename__ = 'timeline_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey('projects.id'), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    event_type = Column(String, default='info')  # info, success, warning, error
    timestamp = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="timeline_events")


class KnowledgeCard(Base):
    __tablename__ = 'knowledge_cards'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey('projects.id'), nullable=False, unique=True)
    best_model = Column(String, nullable=True)
    best_f1 = Column(Float, nullable=True)
    best_accuracy = Column(Float, nullable=True)
    rows_count = Column(Integer, default=0)
    columns_count = Column(Integer, default=0)
    missing_values_pct = Column(Float, default=0.0)
    balancing_method = Column(String, nullable=True)
    models_tested_count = Column(Integer, default=0)
    top_features = Column(JSON, nullable=True)  # List of strings
    status = Column(String, nullable=False)

    project = relationship("Project", back_populates="knowledge_cards")
