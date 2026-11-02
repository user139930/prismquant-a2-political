# -*- coding: utf-8 -*-
"""A2 初始化：建表 + 種子人物（真實職務，不造假發言）。跑一次即可：python -m app.seed"""
from app import db

PEOPLE = [
    {"name_original": "Jerome Powell", "name_zh": "鮑威爾",
     "aliases": ["Powell", "鮑威爾"], "country_codes": ["US"]},
    {"name_original": "Christine Lagarde", "name_zh": "拉加德",
     "aliases": ["Lagarde", "拉加德"], "country_codes": ["EU"]},
    {"name_original": "中國人民銀行", "name_zh": "中國人民銀行",
     "aliases": ["人民銀行", "PBOC"], "country_codes": ["CN"]},
]


def seed():
    db.init_db()
    with db.SessionLocal() as s:
        existing = {p.name_original for p in s.query(db.Person).all()}
        for p in PEOPLE:
            if p["name_original"] not in existing:
                s.add(db.Person(**p))
        s.commit()
    print("種子人物已就緒（%d 位）" % len(PEOPLE))


if __name__ == "__main__":
    seed()
