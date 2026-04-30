# Pluggable Source & Storage Architecture

## 目標
讓 Journal Pulse 能在不重寫核心 pipeline 的前提下：
- 新增新的期刊來源
- 納入不同學科或其他文獻型態
- 替換或並存不同儲存 backend
- 逐步增加 metadata enrichment、dedup、ranking 能力

## 核心原則
1. **Source plugin contract 固定**：每個來源只需要遵守共同 adapter 介面。
2. **Canonical schema 先行**：來源回來的資料先正規化，再交給後續流程。
3. **Pipeline 不認識 publisher 細節**：publisher-specific parser/filter 不得散落在 service layer。
4. **Storage backend 可替換**：MinIO 是預設實作，不是唯一實作。
5. **Metadata enrichment 與 crawling 分離**：像 Crossref、OpenAlex 這種來源可作為 enrichment plugin，而不是硬綁在 ingest 流程。

## SourceDefinition 最小契約
目前 `SourceDefinition` 至少包含：
- `name`
- `source_type`
- `endpoint`
- `category`
- `enabled`
- `metadata`

設計意圖：
- `source_type`：讓 registry 用型別決定要建哪一種 adapter。
- `endpoint`：統一 feed/API 入口，不讓上層綁定 `feed_url` 這種單一來源命名。
- `metadata`：容納每個來源的額外設定，例如 journal whitelist、query template、rate limit hint。

## Registry 規則
`SourceRegistry` 負責：
- 註冊 `source_type -> adapter factory`
- 依 `SourceDefinition` 建立對應 adapter

這表示：
- 上層只需要知道 `build(definition)`
- 不需要在 pipeline 中寫 `if source.name == "nature"` 這類硬編碼分支

## 建議中的 adapter 分類
- `rss`：期刊 RSS / Atom 來源
- `api`：聚合檢索 API，例如 PubMed、Crossref、OpenAlex
- `enrichment`：只補 metadata，不主動當 primary ingest
- `fulltext`：未來若要抓 HTML / PDF / XML，可作為另一種 plugin 類型

## Storage abstraction 建議
下一步應抽成類似：
- `ObjectStore.put_json()`
- `ObjectStore.get_json()`
- `ObjectStore.list(prefix=...)`
- `ObjectStore.exists(key=...)`

第一個 implementation 是：
- `MinIOStore`

後續可擴充：
- local filesystem store
- S3-compatible cloud store
- test double / in-memory store

## 對未來擴充的直接好處
- 新增其他面向論文時，不必重寫 digest pipeline
- 可混用 publisher feed 與 aggregator API
- 可把 dedup / ranking / summarization 做成獨立 stage
- 若之後 MinIO 不夠或部署環境改變，storage backend 可替換而不影響來源層
