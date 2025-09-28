"""
Common constants for the Factorio Learning Environment.
"""

REWARD_OVERRIDE_KEY = "reward_override"

# Model Names for Different Providers (Updated September 2025)
# Based on actual API documentation and web search results
# ===========================================================

# OpenAI Models (Current as of Sept 2025)
# https://platform.openai.com/docs/models
GPT_5 = "gpt-5-2025-08-07"
GPT_5_MINI = "gpt-5-mini-2025-08-07"
GPT_5_NANO = "gpt-5-nano-2025-08-07"
O3 = "o3-2025-04-16"
O4_MINI = "o4-mini-2025-04-16"

# Anthropic Models (Current as of Sept 2025)
# https://docs.anthropic.com/en/docs/about-claude/models/overview
CLAUDE_OPUS_4_1 = "claude-opus-4-1-20250805"  # Latest as of Aug 2025
CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"
CLAUDE_3_7_SONNET = "claude-3-7-sonnet-20250219"  # Hybrid reasoning model

# Google Models (Current as of Sept 2025)
# https://ai.google.dev/gemini-api/docs/models
GEMINI_2_5_PRO = "gemini-2.5-pro"  # State-of-the-art thinking model
GEMINI_2_5_FLASH = "gemini-2.5-flash"  # Generally available
GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"  # Fast, low-cost
GEMINI_2_0_FLASH = "gemini-2.0-flash"

# xAI Models (Current as of Sept 2025)
# https://docs.x.ai/docs/models
GROK_4 = "grok-4-0709"  # Most intelligent model (July 2025)
GROK_3 = "grok-3"  # February 2025 flagship
GROK_CODE_FAST_1 = "grok-code-fast-1"  # Speedy coding model

# OpenRouter Models (Based on available models)
# Note: OpenRouter provides access to 400+ models through unified API
OR_GPT_5 = "openai/gpt-5"
OR_O4_MINI = "openai/o4-mini"
OR_CLAUDE_OPUS_4_1 = "anthropic/claude-opus-4.1"
OR_CLAUDE_SONNET_4 = "anthropic/claude-sonnet-4"
OR_CLAUDE_3_7_SONNET = "anthropic/claude-3.7-sonnet"
OR_GEMINI_2_5_PRO = "google/gemini-2.5-pro"
OR_GEMINI_2_5_FLASH = "google/gemini-2.5-flash"
OR_XAI_GROK_4 = "x-ai/grok-4"
OR_XAI_GROK_3 = "x-ai/grok-3"
OR_XAI_GROK_CODE_FAST_1 = "x-ai/grok-code-fast-1"
OR_DEEPSEEK_V3_1 = "deepseek/deepseek-chat-v3.1"
OR_DEEPSEEK_R1 = "deepseek/deepseek-r1-0528"
OR_LLAMA_4_MAVERICK = "meta-llama/llama-4-maverick"
OR_LLAMA_4_SCOUT = "meta-llama/llama-4-scout"
OR_QWEN3_235B_THINKING = "qwen/qwen3-235b-a22b-thinking-2507"
OR_GPT_OSS_120B = "openai/gpt-oss-120b"

# Model Lists for Easy Lookup
OPENAI_MODELS = [GPT_5, GPT_5_MINI, GPT_5_NANO, O3, O4_MINI]

ANTHROPIC_MODELS = [CLAUDE_OPUS_4_1, CLAUDE_SONNET_4, CLAUDE_3_7_SONNET]

GOOGLE_MODELS = [
    GEMINI_2_5_PRO,
    GEMINI_2_5_FLASH,
    GEMINI_2_5_FLASH_LITE,
    GEMINI_2_0_FLASH,
]

XAI_MODELS = [GROK_4, GROK_3, GROK_CODE_FAST_1]

OPENROUTER_MODELS = [
    OR_GPT_5,
    OR_O4_MINI,
    OR_CLAUDE_OPUS_4_1,
    OR_CLAUDE_SONNET_4,
    OR_CLAUDE_3_7_SONNET,
    OR_GEMINI_2_5_PRO,
    OR_GEMINI_2_5_FLASH,
    OR_XAI_GROK_4,
    OR_XAI_GROK_3,
    OR_XAI_GROK_CODE_FAST_1,
    OR_DEEPSEEK_V3_1,
    OR_DEEPSEEK_R1,
    OR_LLAMA_4_MAVERICK,
    OR_LLAMA_4_SCOUT,
    OR_QWEN3_235B_THINKING,
    OR_GPT_OSS_120B,
]

# Map normal model names to OpenRouter variants
OR_MODEL_MAP = {
    GPT_5: OR_GPT_5,
    O4_MINI: OR_O4_MINI,
    CLAUDE_OPUS_4_1: OR_CLAUDE_OPUS_4_1,
    CLAUDE_SONNET_4: OR_CLAUDE_SONNET_4,
    CLAUDE_3_7_SONNET: OR_CLAUDE_3_7_SONNET,
    GEMINI_2_5_PRO: OR_GEMINI_2_5_PRO,
    GEMINI_2_5_FLASH: OR_GEMINI_2_5_FLASH,
    GROK_4: OR_XAI_GROK_4,
    GROK_3: OR_XAI_GROK_3,
    GROK_CODE_FAST_1: OR_XAI_GROK_CODE_FAST_1,
}

# Model Categories for Evaluation Sweeps
FRONTIER_MODELS = [GPT_5, CLAUDE_OPUS_4_1, GROK_4, GEMINI_2_5_PRO]
FAST_MODELS = [GPT_5_MINI, GEMINI_2_5_FLASH_LITE]
REASONING_MODELS = [
    O4_MINI,
    O3,
    CLAUDE_3_7_SONNET,
    GEMINI_2_5_PRO,
    OR_QWEN3_235B_THINKING,
    OR_GPT_OSS_120B,
    OR_DEEPSEEK_V3_1,
]
OPENROUTER_FREE_MODELS = [OR_DEEPSEEK_R1, OR_LLAMA_4_MAVERICK, OR_LLAMA_4_SCOUT]
CODING_MODELS = [CLAUDE_OPUS_4_1, CLAUDE_SONNET_4, GROK_CODE_FAST_1]

MODEL_CATEGORIES = {
    "frontier": FRONTIER_MODELS,
    "fast": FAST_MODELS,
    "reasoning": REASONING_MODELS,
    "openrouter_free": OPENROUTER_FREE_MODELS,
    "coding": CODING_MODELS,
}
