# Dev History

> Last updated: 2026-04-29
> 
> This file records project progress in a sanitized form. Secrets, passwords, tokens, and raw credential values must never be written here.

## Project Direction

Journal Pulse is being evolved from a manually runnable prototype into a persistent journal monitoring system with:

- pluggable ingest adapters
- local/object storage support
- scheduled monitoring
- change detection between runs
- proactive Discord broadcasting
- interactive Discord bot queries by paper title

## Stable Product Decisions

### Data and architecture

- The project should prioritize scalability in the database/storage layer.
- Data sources should remain loosely coupled through pluggable adapters.
- Open/free sources are prioritized first.
- Breadth of paper coverage is preferred over deep full-text access.

### Discord UX

- Regular broadcasts should stay concise.
- Broadcast format should be:
  - English paper title
  - brief Chinese summary
- Detailed paper information should **not** be pushed in scheduled broadcasts.
- Detailed information should be returned only when a user mentions the bot and asks by paper title.
- Interactive bot behavior requires Discord Message Content Intent.

## Major Implementation Progress

### 1. Storage and runtime environment

- Docker daemon availability was verified during development.
- A previous Docker access issue was diagnosed as a session/group refresh problem rather than a daemon failure.
- MinIO was brought up through Docker Compose and confirmed healthy.
- Local development environment was prepared with editable install and development dependencies.

### 2. Monitoring and reporting flow

- Existing crawl/monitor/report flow was extended rather than replaced.
- Discord delivery path was confirmed to work in practice.
- Scheduled monitoring remains separate from interactive bot handling.
- This keeps periodic broadcast responsibilities decoupled from real-time chat interaction.

### 3. Chinese summarization support

A new summarization service was added to support:

- brief Chinese summary generation for broadcasts
- more detailed Chinese summary generation for detailed replies
- runtime translator construction for the MVP implementation

Current intent:

- broadcasts are short and lightweight
- mention replies can include richer detail

### 4. Query by paper title

Query capabilities were extended beyond article ID lookup.

Implemented direction:

- find article by title
- tolerate approximate title matching
- format richer detail output for interactive use

Approximate matching is important because users may type abbreviated or slightly different paper titles in Discord.

### 5. Discord interactive bot

A Discord gateway bot module was added to support:

- reading incoming messages
- detecting bot mentions
- extracting paper title queries
- looking up matching articles
- replying with detailed information

The architecture currently separates:

- scheduled broadcast path
- interactive gateway bot path

This separation is intentional and should be preserved unless a later operational reason justifies merging them.

### 6. CLI additions

The CLI was extended to support the interactive bot workflow.

Available commands now include:

- `crawl-once`
- `monitor-once`
- `monitor-discord-once`
- `run-discord-bot`
- `run-scheduler`
- `show-article`

## Test and Verification Status

Development followed a test-first / TDD-oriented workflow for the newer Discord interaction features.

### Added or updated tests

Coverage was added or updated for:

- summarization behavior
- concise Discord broadcast formatting
- title-based article lookup
- detailed article formatting
- Discord gateway bot mention parsing and reply construction
- CLI command integration
- config fields for Discord behavior
- scheduler CLI behavior under Discord/non-Discord settings

### Full-suite result

At the latest verified point, the full test suite passed:

- `43 passed`
- one non-blocking dependency warning from `discord.py` / `audioop` deprecation

## Files Added or Significantly Updated

### New or major files

- `src/journal_pulse/services/summarization.py`
- `src/journal_pulse/delivery/discord_gateway_bot.py`
- `tests/test_summarization.py`
- `tests/test_discord_gateway_bot.py`
- `dev-history.md`

### Updated files

- `src/journal_pulse/services/monitoring.py`
- `src/journal_pulse/services/query.py`
- `src/journal_pulse/delivery/__init__.py`
- `src/journal_pulse/config.py`
- `src/journal_pulse/cli.py`
- `pyproject.toml`
- `tests/test_monitoring.py`
- `tests/test_query.py`
- `tests/test_cli.py`
- `tests/test_config.py`
- `tests/test_scheduler_cli.py`
- `README.md`
- `.env.example`

## Current Runtime Status

At the latest known point during this development session:

- scheduled monitoring process was running
- Discord gateway bot process was running
- one-shot Discord broadcast succeeded in practice

These runtime facts should be re-verified if the environment, credentials, intents, or deployment method changes.

## Known Operational Notes

- If Docker permissions appear inconsistent, check whether the current shell session has refreshed group membership.
- Discord scheduled broadcasting can work even when interactive bot behavior still depends on intent or gateway-specific configuration.
- If interactive mention handling fails, first verify Message Content Intent in the Discord Developer Portal.

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

The main remaining validation work is real-environment interaction testing:

- verify the bot replies correctly when mentioned in Discord
- verify title lookup quality for realistic user-entered paper names
- refine detailed reply formatting if responses are too long
- consider chunking or candidate-list fallback if multiple similar titles match
- optionally convert scheduler and bot into managed services for auto-restart and boot-time startup

## Notes for Future Contributors

- Keep scheduled broadcasts concise.
- Do not overload passive broadcasts with detailed metadata.
- Put detailed paper information behind explicit user interaction.
- Preserve pluggable ingest boundaries and avoid tight coupling to a single journal source.
- Keep secrets in environment/config management, never in markdown history files.
