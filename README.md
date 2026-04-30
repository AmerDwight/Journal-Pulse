# Journal Pulse

一個用 Python 建立的期刊爬文系統基礎骨架，底層以 MinIO 物件儲存為核心。

## 目前提供的能力
- Docker/MinIO 為首選物件儲存後端；若執行環境無法連上 MinIO，會自動 fallback 到本地持久化 `LocalObjectStore`
- 可擴充的來源定義與 registry，支援 `rss` / `api` 類型 adapter
- 預設來源採「白名單高品質期刊 + 廣域聚合器」雙層策略
- 已接上真實 RSS ingest、PubMed metadata ingest、Crossref metadata ingest
- 具備 canonical article schema、DOI/URL dedup key、digest 去重
- 已加入 quality gate：過濾低訊號 aggregator 項目（如 Crossref `book-chapter` / `proceedings-article`），並優先排序高品質期刊來源
- Markdown 日報產生器
- CLI：`crawl-once`、`monitor-once`、`monitor-discord-once`、`run-discord-bot`、`run-scheduler`、`generate-report`、`show-config`、`show-article`
- 後續可接 LLM summarizer、Discord 推播、全文 parser

## 目前預設來源
### Layer 1：白名單期刊
- Nature
- Science
- Cell
- PNAS
- The Lancet
- NEJM

### Layer 2：廣域聚合 / metadata 補強
- PubMed
- Crossref

> 依照目前需求，**eLife** 與 **BMJ** 已先排除，不列入預設來源。

## 架構原則
1. **Pluggable source adapters**：pipeline 只依賴 `SourceDefinition` 與 registry，不直接綁定特定 publisher。
2. **Storage abstraction first**：上層服務只面向 storage interface，不直接耦合 MinIO SDK 細節。
3. **Canonical article model**：不同來源先正規化成統一 article schema，再進入去重、索引、報表流程。
4. **Source-specific logic isolation**：每個來源自己的 query/filter/rate-limit 邏輯必須封裝在 adapter 內。
5. **Future breadth ready**：後續新增其他學科或非期刊來源時，只新增 adapter 與 mapping，不改核心 pipeline。

## 啟動方式
```bash
cp .env.example .env
python -m pip install -e .[dev]
python -m journal_pulse.cli show-config
python -m journal_pulse.cli crawl-once
python -m journal_pulse.cli monitor-once
python -m journal_pulse.cli monitor-discord-once
python -m journal_pulse.cli run-discord-bot
python -m journal_pulse.cli run-scheduler
python -m journal_pulse.cli show-article <article-storage-id>
```

> 若本機能啟動 MinIO，`crawl-once` 會優先寫進 MinIO bucket；否則會把 JSON 落在 `DATA_ROOT` 下的本地檔案系統。
>
> 目前此環境已完成 `docker compose` 安裝，並已驗證可用 `docker compose -f /home/amer-test/journal-pulse/docker-compose.yml up -d` 啟動 MinIO。
>
> 若要用 Discord bot 播報，請在 `.env` 設定 `DISCORD_BOT_TOKEN` 與 `DISCORD_CHANNEL_ID`；設定後 `run-scheduler` 會自動改用 Discord 播報工作。
>
> 若要讓 bot 能讀取你在 Discord 中 `@` 它的訊息，請執行 `python -m journal_pulse.cli run-discord-bot`，並確認 Discord Developer Portal 已開啟 **Message Content Intent**。

## 目錄
- `src/journal_pulse/`：主程式
- `tests/`：pytest 測試
- `docs/plans/`：規劃文件
- `docs/architecture/`：架構決策與 plug-in 契約
- `data/`：本地 fallback store 與 MinIO volume 掛載根目錄

## 下一步建議
1. 補上 Crossref / PubMed enrichment merge 規則，保留最完整 metadata
2. 強化中文摘要品質與詳細資訊回覆（例如 chunking、關鍵句抽取、更多 metadata）
3. 增加每篇 article 的摘要/重要性評分，讓定期回報更聚焦
4. 補 `show-article` 的全文/更多 metadata 呈現
