# -*- coding: utf-8 -*-
"""PostgreSQL 資料庫：人物、公開發言、影響分析三張表（用 a2_ 前綴避免與隊友表衝突）。"""
import datetime
import uuid

from sqlalchemy import (URL, Boolean, Column, DateTime, Float, ForeignKey,
                        String, Text, create_engine)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

Base = declarative_base()


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


class Person(Base):
    __tablename__ = "a2_people"

    person_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name_original = Column(String(255), nullable=False)
    name_zh = Column(String(255), nullable=True)
    aliases = Column(JSONB, default=list)
    country_codes = Column(JSONB, default=list)
    monitoring_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PublicRecord(Base):
    __tablename__ = "a2_public_records"

    record_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(UUID(as_uuid=True), ForeignKey("a2_people.person_id"), nullable=True)
    title = Column(Text, nullable=False)
    body_text = Column(Text, default="")
    source_name = Column(String(255), default="")
    publisher_name = Column(String(255), default="")
    original_url = Column(Text, default="")
    published_at = Column(DateTime(timezone=True), nullable=True)
    language = Column(String(20), nullable=True)
    verification_status = Column(String(50), default="needs_review")
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Analysis(Base):
    __tablename__ = "a2_analyses"

    analysis_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(UUID(as_uuid=True), ForeignKey("a2_public_records.record_id"), nullable=False)
    entities = Column(JSONB, default=list)
    markets = Column(JSONB, default=list)
    direction = Column(String(10), default="中性")
    confidence = Column(Float, nullable=True)
    summary = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)


def database_url():
    if not settings.db_password.get_secret_value():
        raise ValueError("請在 .env 設定 PQ_DB_PASSWORD")
    return URL.create(
        "postgresql+psycopg",
        username=settings.db_user,
        password=settings.db_password.get_secret_value(),
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
    )


engine = create_engine(database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    Base.metadata.create_all(engine)
