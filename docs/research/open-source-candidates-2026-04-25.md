# Open / Free Journal Source Probe — 2026-04-25

## 測試目標
先驗證有哪些**免費、可程式化存取**、而且適合拿來做「主流/頂級期刊爬文」的來源。

你的需求重點是：
- 先從開源 / 免費部分開始
- 重視**廣度**，先抓 metadata / 標題 / 摘要 / 連結
- 深度全文之後再處理

---

## A. 已確認可直接抓取的期刊 RSS / Feed
這類來源最適合做「高品質白名單期刊追蹤」。

| Source | 狀態 | 形式 | 觀察 |
|---|---:|---|---|
| Nature RSS | 200 | RSS 1.0 | 可抓到最新文章標題與 article URL |
| Science RSS | 200 | RSS 1.0 | 可抓到最新目錄與 DOI 頁面 |
| Cell RSS | 200 | RSS 1.0 | 可抓到最新文章標題與 Cell 文章頁 |
| PNAS RSS | 200 | RSS 1.0 | 可抓到最新 issue 內容 |
| The Lancet RSS | 200 | RSS 1.0 | 可抓到最新內容，含 fulltext/article link |
| NEJM RSS | 200 | RSS 1.0 | 可抓到最新文章與 DOI 頁 |
| eLife recent RSS | 200 | RSS 2.0 | 可抓到最新文章，對開放取得很友善 |
| BMJ RSS | 200 | RSS 2.0 | 可抓到最新內容，但目前看起來較多 rapid responses/commentary |

### 測試樣本
- **Nature**
  - Author Correction: Commensal yeast promotes *Salmonella* Typhimurium virulence
  - Cosmic-ray detection heralds era of mega-observatories for neutrinos
- **Science**
  - Dark discoveries
  - Mechanical load inhibits cancer growth in mouse and human hearts
- **Cell**
  - The Hallmarks of Cancer: 25 years guiding discovery and therapy
- **The Lancet**
  - The US CDC on the brink
  - Treatment of uncomplicated lower urinary tract infections in women
- **NEJM**
  - Transdermal Estradiol Patches in Locally Advanced Prostate Cancer
  - Ketamine or Etomidate for Tracheal Intubation of Critically Ill Adults
- **eLife**
  - The olfactory receptor SNIF-1 mediates foraging for leucine-enriched diets in *C. elegans*
- **BMJ**
  - 目前抓到的前幾筆偏向 rapid responses，不一定是你要的 primary research

---

## B. 已確認可用的免費聚合 / 檢索 API
這類來源更適合做你要的「廣度優先」。

| Source | 狀態 | 優勢 | 風險 / 注意 |
|---|---:|---|---|
| PubMed E-utilities | 200 | 生醫領域非常強，可直接用 journal filter、date filter、keyword filter | 偏生醫，不涵蓋所有自然科學領域 |
| Crossref Works API | 200 | 超廣 metadata 覆蓋，適合補 DOI / 標題 / 發表日期 / 出版社資訊 | 摘要不一定齊全，品質依出版社而異 |
| Europe PMC API | 200 | 生醫文獻與 open access 連動很好，對摘要與全文連結友善 | 偏生命科學 / 醫學 |
| OpenAlex API | 200 | 學科覆蓋面大，適合做廣域探索與 citation/source metadata | 搜尋要設計好 filter，否則容易抓太廣 |
| Semantic Scholar API | 200 | 適合做補充 ranking / citation / related papers | 免費額度與欄位可用性需後續確認 |
| DOAJ API | 200 | 適合純 OA 範圍探索 | 不等於「頂級期刊」，比較像 OA 補充池 |
| bioRxiv API | 200 | 生醫前沿很快，免費而且更新勤 | 這是 preprint，不是正式期刊 |
| arXiv API | 200 | 物理、數學、CS 很有價值，免費 | 也是 preprint，不是正式期刊 |

### 聚合 API 測試樣本
- **Crossref**
  - Lift off! Artemis II mission sends humans to the Moon — opening a new era of exploration
  - Giant cancer study reveals effectiveness of ‘off label’ treatments
  - AI models ‘subliminally’ transmit biases when training other systems
- **Europe PMC**
  - Severe obesity in human HFpEF alters contractile protein function and organization.
  - A single-cell multiomic analysis identifies molecular and gene-regulatory mechanisms dysregulated in developing Down syndrome neocortex.
- **PubMed**
  - 已成功用 journal filter 抓到頂級期刊集合的 PMID 結果
- **bioRxiv**
  - How and why ampliconic genes survive on the human Y chromosome
  - Candida albicans drives colorectal cancer progression by inducing hypoxia signaling

---

## C. 目前結論

### 最適合做第一版的來源組合
如果你要的是：
1. **先免費**
2. **先廣度**
3. **先能穩定每天吐新東西**

那我建議第一版來源分兩層：

#### Layer 1：白名單頂級期刊直抓
- Nature
- Science
- Cell
- PNAS
- The Lancet
- NEJM

> 註：依照目前專案決策，**eLife** 與 **BMJ** 雖然技術上可抓，但暫時不納入第一批預設來源。理由是目前要先維持高訊號、低例外處理成本，並把架構重點放在 pluggable source contract，而不是為個別來源客製過多判斷。

用途：
- 保證「頂級期刊」這條線不失焦
- 每天都有高信號來源

#### Layer 2：免費廣域聚合補強
- PubMed
- Crossref
- Europe PMC
- OpenAlex

用途：
- 補齊廣度
- 可以做 journal whitelist、keyword filter、date filter
- 對之後做主題追蹤很有幫助

---

## D. 實作建議

### 第一階段（我建議你下一步就做這個）
1. 先把 **8 個白名單期刊 feed** 做成 source adapters
2. 再加一個 **PubMed adapter** 當廣度入口
3. 儲存層先只存：
   - title
   - source
   - published_at
   - doi / article_url
   - abstract（若有）
   - tags / keyword hits
4. 日報先輸出：
   - 今日新增文章數
   - 各來源篇數
   - 每篇 1~2 句簡述
   - article_id 供後續查詢

### 第二階段
- 加入 Crossref / Europe PMC 補 metadata
- 加入去重（以 DOI / canonical URL 為主）
- 加入 relevance scoring / keyword filtering

---

## E. 不建議一開始就做的事
- 一開始就硬抓全文 PDF
- 一開始就做大型全文向量化
- 一開始就接太多 preprint 源而讓訊號品質失控
- 一開始就接付費 API 或 publisher login flow

---

## F. 實際檔案
- 原始測試輸出：`docs/research/free-source-probe-2026-04-25.json`
- 本整理文件：`docs/research/open-source-candidates-2026-04-25.md`
