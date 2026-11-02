# -*- coding: utf-8 -*-
"""A2 採集：抓官方公開來源 → 大模型抽取實體與資產影響 → 結構化事件。"""
import datetime
from email.utils import parsedate_to_datetime

import urllib.request
import xml.etree.ElementTree as ET

from app.config import settings
from app.llm import chat_json

SYSTEM = (
    "你是政治風險分析員。對每一條公開發言，抽取："
    "實體關鍵詞（關稅、利率、監管、制裁、地緣等）、"
    "可能受影響的市場（美股、港股、原油、黃金、加密貨幣、外匯等）、"
    "影響方向（利多 / 利空 / 中性）、置信度。"
    "不要誇大，證據不足就標中性。"
)

SAMPLE = [
    ("示例：央行官員談通脹與貨幣政策前景",
     "（示例發言，非真實引述）通脹壓力正在緩和，貨幣政策仍有進一步調整空間。", "", ""),
    ("示例：貿易代表談關稅措施",
     "（示例發言，非真實引述）將重新評估對關鍵行業的關稅措施。", "", ""),
    ("示例：財政官員談金融監管",
     "（示例發言，非真實引述）計劃推出新一輪金融科技監管指引。", "", ""),
]


def parse_date(s: str):
    """把 RSS 的 pubDate 字串轉成 datetime，失敗回傳 None。"""
    if not s:
        return None
    try:
        return parsedate_to_datetime(s)
    except Exception:
        return None


def fetch_rss(url: str, timeout: int = 15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            xml = resp.read()
        root = ET.fromstring(xml)
        items = []
        for it in root.iter("item"):
            def g(tag):
                el = it.find(tag)
                return (el.text or "").strip() if el is not None and el.text else ""
            title = g("title")
            if title:
                items.append((title, g("description"), g("link"), g("pubDate")))
        return items
    except Exception:
        return []


def collect(limit: int = 6):
    """抓取公開來源 + 大模型分析，回傳 (records, analyses, sampled)。"""
    items = []
    for src in settings.political_rss_sources:
        items += fetch_rss(src)
    sampled = not items
    if sampled:
        items = list(SAMPLE)
    items = items[:limit]

    lines = []
    for i, (title, desc, _u, _d) in enumerate(items):
        lines.append("[%d] %s。%s" % (i, title, (desc or "")[:300]))
    prompt = (
        "請把下面每條發言逐條分析，輸出 JSON 陣列，每條格式：\n"
        '{"entities":["關稅","利率"],"markets":["美股","原油"],'
        '"direction":"利多|利空|中性","confidence":0.8,"summary":"一句中文摘要"}\n\n'
        + "\n\n".join(lines)
    )
    out = chat_json(SYSTEM, prompt)
    if isinstance(out, dict):
        out = out.get("items", out.get("events", [out]))

    records, analyses = [], []
    for i, it in enumerate(items):
        a = out[i] if isinstance(out, list) and i < len(out) else {}
        if not isinstance(a, dict):
            a = {}
        records.append({
            "title": it[0],
            "body_text": (it[0] + "。 " + it[1])[:2000],
            "source_name": "示例" if sampled else "官方來源",
            "publisher_name": "",
            "original_url": it[2],
            "published_at": parse_date(it[3]),
            "verification_status": "needs_review",
        })
        analyses.append({
            "entities": a.get("entities", []),
            "markets": a.get("markets", []),
            "direction": a.get("direction", "中性"),
            "confidence": a.get("confidence"),
            "summary": a.get("summary", ""),
        })
    return records, analyses, sampled
