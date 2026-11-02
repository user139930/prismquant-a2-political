# -*- coding: utf-8 -*-
"""A2 政要監控智能體：FastAPI 服務（PostgreSQL）。

接口（契約與隊友的政治監控後端一致）：
    GET  /health
    GET  /api/v1/system-status
    GET  /api/v1/people?limit=20&cursor=
    GET  /api/v1/people/{person_id}
    GET  /api/v1/public-records?person_id=&limit=&order=
    GET  /api/v1/public-records/{record_id}
    POST /api/v1/collect            （本服務新增：抓取 + LLM 影響分析）
    GET  /api/v1/analyses?limit=     （本服務新增：影響卡片）
"""
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import collector, db
from app.config import settings

app = FastAPI(
    title=settings.service_name,
    version="0.1.0",
    description="PrismQuant A2 政要監控智能體：採集公開發言，並用大模型抽取實體與資產影響。",
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )


def _person_dict(p: db.Person) -> dict:
    return {
        "person_id": str(p.person_id),
        "name_original": p.name_original,
        "name_zh": p.name_zh,
        "aliases": p.aliases or [],
        "country_codes": p.country_codes or [],
        "monitoring_enabled": p.monitoring_enabled,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


def _record_dict(r: db.PublicRecord, analysis: dict | None = None) -> dict:
    d = {
        "record_id": str(r.record_id),
        "person_id": str(r.person_id) if r.person_id else None,
        "title": r.title,
        "source_name": r.source_name,
        "publisher_name": r.publisher_name,
        "original_url": r.original_url,
        "published_at": r.published_at,
        "verification_status": r.verification_status,
        "language": r.language,
        "created_at": r.created_at,
    }
    if analysis is not None:
        d["body_text"] = r.body_text or ""
        d["analysis"] = analysis
    return d


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name, "version": app.version, "scope": "api_process"}


@app.get("/api/v1/system-status")
def system_status():
    db_status = "ok"
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "unavailable"
    return {"status": "ok" if db_status == "ok" else "degraded", "database": db_status, "collector": "on_demand"}


@app.get("/api/v1/people")
def list_people(limit: int = Query(20, ge=1, le=100), cursor: UUID | None = None):
    try:
        with db.SessionLocal() as s:
            q = s.query(db.Person).order_by(db.Person.person_id.asc())
            if cursor is not None:
                q = q.filter(db.Person.person_id > cursor)
            rows = q.limit(limit + 1).all()
    except SQLAlchemyError:
        raise HTTPException(503, detail={"code": "database_unavailable", "message": "数据库暂不可用"})
    items = [_person_dict(p) for p in rows[:limit]]
    return {"items": items, "next_cursor": items[-1]["person_id"] if len(rows) > limit else None}


@app.get("/api/v1/people/{person_id}")
def get_person(person_id: UUID):
    try:
        with db.SessionLocal() as s:
            p = s.get(db.Person, person_id)
    except SQLAlchemyError:
        raise HTTPException(503, detail={"code": "database_unavailable", "message": "数据库暂不可用"})
    if p is None:
        raise HTTPException(404, detail={"code": "person_not_found", "message": "未找到该人物"})
    return _person_dict(p)


@app.get("/api/v1/public-records")
def list_records(
    limit: int = Query(20, ge=1, le=100),
    cursor: UUID | None = None,
    person_id: UUID | None = None,
    order: str = Query("record_id", pattern="^(record_id|published_desc)$"),
):
    try:
        with db.SessionLocal() as s:
            q = s.query(db.PublicRecord)
            if person_id is not None:
                q = q.filter(db.PublicRecord.person_id == person_id)
            if order == "published_desc":
                q = q.order_by(db.PublicRecord.published_at.desc().nulls_last(), db.PublicRecord.record_id.desc())
                if cursor is not None:
                    q = q.filter(db.PublicRecord.record_id < cursor)
            else:
                q = q.order_by(db.PublicRecord.record_id.asc())
                if cursor is not None:
                    q = q.filter(db.PublicRecord.record_id > cursor)
            rows = q.limit(limit + 1).all()
    except SQLAlchemyError:
        raise HTTPException(503, detail={"code": "database_unavailable", "message": "数据库暂不可用"})
    items = [_record_dict(r) for r in rows[:limit]]
    return {"items": items, "next_cursor": items[-1]["record_id"] if len(rows) > limit else None}


@app.get("/api/v1/public-records/{record_id}")
def get_record(record_id: UUID):
    try:
        with db.SessionLocal() as s:
            r = s.get(db.PublicRecord, record_id)
            a = s.query(db.Analysis).filter(db.Analysis.record_id == record_id).order_by(db.Analysis.created_at.desc()).first()
    except SQLAlchemyError:
        raise HTTPException(503, detail={"code": "database_unavailable", "message": "数据库暂不可用"})
    if r is None:
        raise HTTPException(404, detail={"code": "public_record_not_found", "message": "未找到该内容记录"})
    analysis = {
        "entities": a.entities or [], "markets": a.markets or [], "direction": a.direction,
        "confidence": a.confidence, "summary": a.summary or "",
    } if a is not None else None
    return _record_dict(r, analysis)


@app.get("/api/v1/analyses")
def list_analyses(limit: int = Query(50, ge=1, le=200)):
    try:
        with db.SessionLocal() as s:
            rows = (s.query(db.Analysis, db.PublicRecord)
                    .join(db.PublicRecord, db.Analysis.record_id == db.PublicRecord.record_id)
                    .order_by(db.Analysis.created_at.desc()).limit(limit).all())
    except SQLAlchemyError:
        raise HTTPException(503, detail={"code": "database_unavailable", "message": "数据库暂不可用"})
    items = []
    for a, r in rows:
        items.append({
            "record_id": str(r.record_id),
            "title": r.title,
            "direction": a.direction,
            "entities": a.entities or [],
            "markets": a.markets or [],
            "confidence": a.confidence,
            "summary": a.summary or "",
        })
    return {"agent": "A2 政要監控", "count": len(items), "events": items}


@app.post("/api/v1/collect")
def collect(limit: int = Query(6, ge=1, le=20)):
    try:
        records, analyses, sampled = collector.collect(limit)
        with db.SessionLocal() as s:
            for rec, ana in zip(records, analyses):
                r = db.PublicRecord(**rec)
                s.add(r)
                s.flush()
                s.add(db.Analysis(record_id=r.record_id, **ana))
            s.commit()
    except Exception as exc:
        raise HTTPException(503, detail={"code": "collection_failed", "message": str(exc)})
    return {"collected": len(records), "sampled": sampled}
