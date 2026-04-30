# Journal Pulse Bootstrap Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 建立一個以 Python 為核心、MinIO 為儲存底層的期刊爬文系統基礎骨架，支援來源擴充、排程抓取、摘要產出與後續細節查閱。

**Architecture:** 以單一 Python 應用服務作為 orchestrator，分為 source adapters、storage、scheduler、summarizer、reporting 五層。所有來源都必須先轉成統一的 canonical article schema，再進入去重、索引與報表流程；storage layer 則以 interface 抽象化，讓 MinIO 只是第一個 backend implementation。MinIO 透過 Docker Compose 啟動並掛載到本機 `/home/amer-test/journal-pulse/data/`；初期以 CLI 與本地報告檔案驗證流程，同時避免 pipeline 與單一資料來源或單一儲存實作過度耦合。

**Tech Stack:** Python 3.11、Typer、Pydantic Settings、APScheduler、feedparser、httpx、MinIO SDK、pytest、Docker Compose。

---

### Task 1: 建立基礎專案骨架
**Objective:** 建立 Python package、Docker Compose、環境變數範本與 README。

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `src/journal_pulse/...`
- Create: `tests/...`

**Step 1: Write failing test**
建立設定載入測試與來源註冊測試。

**Step 2: Run test to verify failure**
Run: `pytest tests/ -q`
Expected: FAIL — package/config 尚未存在。

**Step 3: Write minimal implementation**
建立 config、registry、核心 domain model 與 CLI 入口。

**Step 4: Run test to verify pass**
Run: `pytest tests/ -q`
Expected: PASS。

### Task 2: 建立 MinIO 儲存抽象
**Objective:** 抽象出 storage layer，先支援把 article JSON 與 report JSON 寫入 MinIO 指定 bucket。

**Files:**
- Create: `src/journal_pulse/storage/minio_store.py`
- Create: `tests/test_storage.py`

### Task 3: 建立期刊來源介面與示範 adapter
**Objective:** 定義 `JournalSource` 介面，先以 RSS/Atom 示範來源（Nature/Science）完成 metadata 抓取。

**Files:**
- Create: `src/journal_pulse/sources/base.py`
- Create: `src/journal_pulse/sources/rss.py`
- Create: `src/journal_pulse/sources/defaults.py`
- Create: `tests/test_sources.py`

### Task 4: 建立摘要與每日報告骨架
**Objective:** 先用 rule-based summarizer 與 markdown/json reporter 形成可替換介面。

**Files:**
- Create: `src/journal_pulse/summarizer/...`
- Create: `src/journal_pulse/reporting/...`
- Create: `tests/test_reporting.py`

### Task 5: 建立排程與 CLI 工作流
**Objective:** 支援 `crawl-once`、`generate-report`、`schedule`、`show-article` 等指令。

**Files:**
- Modify: `src/journal_pulse/cli.py`
- Create: `src/journal_pulse/services/pipeline.py`
- Create: `src/journal_pulse/scheduler.py`
- Create: `tests/test_pipeline.py`

### Task 6: 驗證與交接
**Objective:** 提供啟動步驟、測試方式、未來擴充方向（LLM 摘要、Discord delivery、全文 parser、去重索引）。

**Files:**
- Modify: `README.md`
