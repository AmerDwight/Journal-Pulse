# Dev History

> Last updated: 2026-04-30
>
> This file records project progress in a sanitized form. Secrets, passwords, tokens, and raw credential values must never be written here.

## Project Direction

Journal Pulse is being evolved from a manually runnable prototype into a persistent journal monitoring system with:

- pluggable ingest adapters
- local/object storage support
- scheduled monitoring
- change detection between runs
- proactive Discord broadcasting
- interactive Discord bot queries by paper title and recent-history range
- provider-agnostic external Chinese summarization

## Stable Product Decisions

### Data and architecture

- The project should prioritize scalability in the database/storage layer.
- Data sources should remain loosely coupled through pluggable adapters.
- Open/free sources are prioritized first.
- Breadth of paper coverage is preferred over deep full-text access.
- External LLM integration should stay behind an OpenAI-compatible / provider-agnostic boundary rather than binding the project to a single SDK.

### Discord UX

- Regular broadcasts should stay concise.
- Broadcast format should be:
  - English paper title
  - brief Chinese summary
- Detailed paper information should **not** be pushed in scheduled broadcasts.
- Detailed information should be returned only when a user mentions the bot and asks by paper title.
- Interactive bot behavior requires Discord Message Content Intent.
- History queries should return quickly and should not block on per-article LLM calls.
- Time-window history views should not include future-dated records.

## Major Implementation Progress

### 1. Storage and runtime environment

- Docker daemon availability was verified during development.
- A previous Docker access issue was diagnosed as a session/group refresh problem rather than a daemon failure.
- MinIO was brought up through Docker Compose and confirmed healthy.
- Local development environment was prepared with editable install and development dependencies.
- Runtime storage fallback behavior remains important so the project can still operate when MinIO is unavailable.

### 2. Monitoring and reporting flow

- Existing crawl/monitor/report flow was extended rather than replaced.
- Discord delivery path was confirmed to work in practice.
- Scheduled monitoring remains separate from interactive bot handling.
- This keeps periodic broadcast responsibilities decoupled from real-time chat interaction.

### 3. Chinese summarization support

The summarization path was extended from the earlier MVP translator-oriented shape into an external LLM-backed flow.

Implemented direction:

- brief Chinese summary generation for broadcasts
- more detailed Chinese summary generation for mention replies
- OpenRouter-compatible chat-completions backend
- runtime summarizer construction behind a shared service boundary
- provider-order / failover-oriented wiring at the service layer
- output normalization so summaries stay concise and do not repeat the English title

Current intent:

- broadcasts are short and lightweight
- mention replies can include richer detail
- backend selection should stay configurable through runtime settings rather than hard-coded provider coupling

### 4. Query by paper title

Query capabilities were extended beyond article ID lookup.

Implemented direction:

- find article by title
- tolerate approximate title matching
- format richer detail output for interactive use
- clean raw HTML/metadata noise from stored English summary or abstract fields before presenting detail replies

Approximate matching is important because users may type abbreviated or slightly different paper titles in Discord.

### 5. Discord interactive bot

A Discord gateway bot module was added and expanded to support:

- reading incoming messages
- detecting bot mentions
- extracting paper title queries
- looking up matching articles
- replying with detailed information
- a two-step history interaction (`history` → choose `1周 / 2周 / 1個月 / All Time`)
- chunked history replies sized for Discord message limits

The architecture currently separates:

- scheduled broadcast path
- interactive gateway bot path

This separation is intentional and should be preserved unless a later operational reason justifies merging them.

### 6. History-range performance fix

A production issue was investigated where replying `1周` in Discord appeared to hang for a very long time.

Root cause established during debugging:

- history replies were generating a Chinese summary for every listed paper
- those summaries were produced through serial external LLM calls
- a one-week window contained many records, so response time scaled linearly with article count
- some PubMed records carried future publication dates and were incorrectly included in recent-history windows because the query had a lower bound but no upper bound

Initial fix direction:

- recent-history queries now apply an upper time bound (`until=now`)
- future-dated records are excluded from `1周` / `2周` / `1個月` history windows
- the interactive path was temporarily kept lightweight to stop per-request timeout behavior

Observed result during verification:

- the history reply path dropped from timeout-scale behavior to near-instant local generation
- one-week history count dropped from an inflated value that included future-dated PubMed items to a bounded non-future set

### 7. Ingest-time Chinese summary caching

The next step was to preserve concise history replies **without** reintroducing live per-article LLM latency during Discord interaction.

Implemented direction:

- article records now support persisted Chinese summary fields:
  - `summary_zh`
  - `brief_summary_zh`
- the ingest flow now accepts an optional summarizer and precomputes Chinese summaries before article JSON is stored
- cached summaries are derived once per stored article and then reused by downstream readers
- history replies now reuse the cached brief Chinese summary from storage instead of issuing live LLM calls
- mention-detail replies prefer the cached detailed Chinese summary when present
- broadcast formatting can also reuse the cached brief summary instead of depending on fresh runtime generation

Important architecture notes:

- ingest-time enrichment stays optional; if no summarizer is configured, articles are still stored normally
- placeholder fallback text is **not** persisted into storage as if it were a real Chinese summary
- history interaction no longer constructs a runtime summarizer, so the `history` path remains bounded by local storage reads and formatting work only

Observed result during verification:

- history replies can include concise Chinese summaries again while remaining local/cache-backed at read time
- ingest-time LLM work shifts the latency cost to the crawl phase instead of the interactive Discord history path
- detail and broadcast paths can reuse the same persisted Chinese summary fields, reducing repeated summarization work across features

### 8. CLI additions

The CLI was extended to support the interactive bot workflow.

Available commands now include:

- `crawl-once`
- `monitor-once`
- `monitor-discord-once`
- `run-discord-bot`
- `run-scheduler`
- `show-article`

## Test and Verification Status

Development continued to follow a test-first / regression-test-oriented workflow for the Discord interaction and summarization changes.

### Added or updated tests

Coverage was added or updated for:

- OpenRouter-compatible summarizer behavior
- provider selection / failover-oriented summarizer wiring
- concise Discord broadcast formatting
- title-based article lookup
- detailed article formatting
- Discord gateway bot mention parsing and reply construction
- history prompt / range parsing behavior
- history reply formatting and chunking
- reuse of cached Chinese summaries in history replies
- ingest-time persistence of generated Chinese summaries
- exclusion of future-dated records from bounded history windows
- CLI command integration
- config fields for Discord and LLM behavior
- scheduler CLI behavior under Discord/non-Discord settings

### Full-suite result

At the latest verified point, the full test suite passed:

- `63 passed`
- one non-blocking dependency warning from `discord.py` / `audioop` deprecation

## Files Added or Significantly Updated

### New or major files

- `src/journal_pulse/services/llm.py`
- `src/journal_pulse/services/summarization.py`
- `src/journal_pulse/delivery/discord_gateway_bot.py`
- `tests/test_llm.py`
- `tests/test_summarization.py`
- `tests/test_discord_gateway_bot.py`
- `dev-history.md`

### Updated files

- `src/journal_pulse/models.py`
- `src/journal_pulse/services/ingest.py`
- `src/journal_pulse/services/summarization.py`
- `src/journal_pulse/services/query.py`
- `src/journal_pulse/services/monitoring.py`
- `src/journal_pulse/config.py`
- `src/journal_pulse/cli.py`
- `src/journal_pulse/delivery/discord_gateway_bot.py`
- `pyproject.toml`
- `tests/test_query.py`
- `tests/test_ingest.py`
- `tests/test_summarization.py`
- `tests/test_discord_gateway_bot.py`
- `tests/test_cli.py`
- `tests/test_config.py`
- `tests/test_scheduler_cli.py`
- `.env.example`
- `README.md`

## Current Runtime Status

At the latest known point during this development session:

- scheduled monitoring process was running
- Discord gateway bot process was running
- one-shot Discord broadcast had previously succeeded in practice
- interactive history replies were locally verified after the speed fix

These runtime facts should be re-verified if the environment, credentials, intents, source mix, or deployment method changes.

## Known Operational Notes

- If Docker permissions appear inconsistent, check whether the current shell session has refreshed group membership.
- Discord scheduled broadcasting can work even when interactive bot behavior still depends on intent or gateway-specific configuration.
- If interactive mention handling fails, first verify Message Content Intent in the Discord Developer Portal.
- If history results look unexpectedly large, inspect whether upstream source metadata includes future dates or low-signal aggregator content.
- Avoid reintroducing heavy inline LLM work into bulk history replies unless a capped / async / cached design is added.

## Security / Sanitization Notes

The following categories must never be committed into this file:

- sudo passwords
- bot tokens
- API keys
- raw `.env` secrets
- full chat IDs unless explicitly needed for public, non-sensitive documentation
- copied credential values from screenshots or messages

When documenting sensitive configuration, use placeholders such as:

- `[REDACTED]`
- `<set in .env>`
- `<configured externally>`

## Remaining Work

The main remaining validation work is real-environment interaction testing and release hardening:

- verify the bot replies correctly when mentioned in Discord using realistic paper-title queries
- verify the new history flow in the live Discord environment
- consider whether history replies should later support capped summaries, pagination, or follow-up detail selection
- refine detail formatting if mention replies are too long
- consider chunking or candidate-list fallback if multiple similar titles match
- optionally convert scheduler and bot into managed services for auto-restart and boot-time startup
