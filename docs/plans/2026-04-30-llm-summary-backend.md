# LLM Summary Backend Implementation Plan

> **For Hermes:** Follow strict TDD while implementing this plan.

**Goal:** Replace the current translator-specific summary path with a low-coupling external LLM summary backend that can be swapped between providers without changing pipeline code.

**Architecture:** Introduce a lightweight summary backend protocol plus an OpenAI-compatible HTTP backend, then route CLI and Discord bot summary generation through a runtime builder driven by settings. Keep summarization logic provider-agnostic and fall back cleanly when no backend is configured.

**Tech Stack:** Python 3.11, httpx, pydantic-settings, pytest.

---

## Tasks
1. Add failing tests for config/env keys and provider-agnostic summary backend behavior.
2. Add failing tests for OpenAI-compatible backend request/response parsing.
3. Implement the backend protocol and runtime builder with low coupling.
4. Refactor summarization/CLI/Discord bot call sites to use the new backend.
5. Update env example and rerun targeted plus full tests.
