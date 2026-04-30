# OpenRouter Agent + Failover Allocation Plan

> **For Hermes:** Follow strict TDD while implementing this plan.

**Goal:** Refactor Journal Pulse summary generation around an abstract LLM agent interface, with OpenRouter as the default provider and allocator-driven failover hooks for future providers.

**Architecture:** Use a Strategy interface for the LLM agent contract, a registry/factory to build provider-specific agents, and an allocator/orchestrator that selects an agent at startup and can re-allocate on runtime failure. Keep provider-specific details isolated from summarization flow.

**Tech Stack:** Python, httpx, pytest

---

1. Add failing tests for provider defaults, abstract agent allocation, and runtime re-allocation behavior.
2. Refactor `services/llm.py` into agent contract + OpenRouter implementation + allocator.
3. Refine prompt to enforce one-sentence Traditional Chinese broadcast style.
4. Wire CLI / Discord call sites through allocator-backed summarizer.
5. Run targeted tests, then full suite.
