# PrismQuant A2 政要監控智能體（Political Monitoring Agent）

採集政治人物／機構的公開發言，並用大模型抽取**實體（關稅、利率、監管…）與資產影響**
（影響市場、利多／利空／中性），輸出「事件 → 資產影響」卡片。

架構與隊友的政治監控後端一致（FastAPI + SQLAlchemy + psycopg + PostgreSQL，`PQ_` 前綴設定），
並額外補上他還沒做的**大模型影響分析**。

## 技術棧

- FastAPI + SQLAlchemy + **PostgreSQL**（psycopg3）
- 大模型：OpenRouter（OpenAI 相容介面），預設 `deepseek/deepseek-chat`

## 快速開始

```bash
# 1. 建虛擬環境並安裝
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 2. 設定
copy .env.example .env
# 編輯 .env：填入 PQ_LLM_API_KEY 與 PQ_DB_PASSWORD（本機 PostgreSQL 密碼）

# 3. 建表＋種子人物（跑一次即可）
.venv\Scripts\python -m app.seed

# 4. 啟動
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8120
```

Windows 上也可雙擊 `start.cmd`（會先 seed 再啟動）。

## 接口

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/health` | 服務是否活著 |
| GET | `/api/v1/system-status` | 資料庫是否可用 |
| GET | `/api/v1/people?limit=20&cursor=` | 人物列表（items + next_cursor 分頁） |
| GET | `/api/v1/people/{person_id}` | 人物詳情 |
| GET | `/api/v1/public-records?person_id=&limit=&order=` | 發言列表（order=record_id / published_desc） |
| GET | `/api/v1/public-records/{record_id}` | 發言全文＋影響分析 |
| POST | `/api/v1/collect?limit=6` | 觸發採集＋LLM 分析 |
| GET | `/api/v1/analyses?limit=50` | 影響卡片列表 |

互動文件：`http://127.0.0.1:8120/docs`。

## 幾點說明

1. **與隊友後端共庫、不共表**：預設連 `prismquant_political` 資料庫，但表用 `a2_` 前綴
   （`a2_people` / `a2_public_records` / `a2_analyses`），不會動到隊友的資料。
2. **抓不到公開來源會退回示例**：`sampled=true` 會標示清楚，不造假。
3. **密鑰安全**：`.env`（含 key 與資料庫密碼）已被 `.gitignore` 擋住，不會被 push。
