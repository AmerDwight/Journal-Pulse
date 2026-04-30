# Free / low-cost external LLM options for Journal Pulse summaries

## Goal
Use an external LLM for Traditional Chinese paper-summary generation without coupling Journal Pulse to a single provider SDK.

## Chosen integration shape
Journal Pulse now uses a generic **OpenAI-compatible chat completions backend**:
- configurable base URL
- configurable model
- configurable auth key
- configurable extra headers JSON

This keeps provider switching in `.env` rather than code.

## Candidate providers

### 1. OpenRouter
Observed from OpenRouter docs (`/docs/quickstart`):
- unified API over many models
- standard `/api/v1/chat/completions` endpoint
- OpenAI SDK compatibility
- OpenRouter-specific attribution headers are optional

Why it fits:
- easiest way to swap among many hosted models
- useful when a previously free model disappears or rate limits change
- one integration can target multiple upstream providers

Example config:
```env
LLM_BACKEND=openai-compatible
LLM_API_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your_openrouter_key
LLM_MODEL=deepseek/deepseek-chat-v3-0324:free
LLM_EXTRA_HEADERS_JSON={"HTTP-Referer":"https://github.com/your-org/journal-pulse","X-Title":"Journal Pulse"}
```

### 2. Hugging Face Inference Providers
Observed from Hugging Face pricing/docs:
- routed provider API across many providers
- monthly free credits for free users (`$0.10`, subject to change)
- can switch providers behind one Hugging Face token
- docs show OpenAI-compatible client usage for chat completions

Why it fits:
- low commitment experimentation path
- many backend providers available behind one account
- can act as a fallback when OpenRouter free models are unstable

Example config:
```env
LLM_BACKEND=openai-compatible
LLM_API_BASE_URL=https://router.huggingface.co/v1
LLM_API_KEY=your_hf_token
LLM_MODEL=deepseek-ai/DeepSeek-V3-0324
LLM_EXTRA_HEADERS_JSON={}
```

## Recommendation
1. Start with **OpenRouter** because model swapping is the cleanest.
2. Keep **Hugging Face** as a second configured option when free-model availability changes.
3. Do not add provider-specific SDKs unless a provider offers a must-have capability unavailable through OpenAI-compatible chat completions.

## Operational note
Free external LLM capacity changes frequently:
- free models can disappear
- rate limits can tighten
- model names can change

So the right strategy is **provider agility**, not deep provider-specific integration.
