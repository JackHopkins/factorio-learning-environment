# Together AI — API Reference

Quick-reference for all Together AI endpoints, parameters, models, and pricing. See `SKILL.md` for usage examples and best practices.

---

## REST API Endpoints

Base URL: `https://api.together.xyz/v1`

All requests require header: `Authorization: Bearer <TOGETHER_API_KEY>`

### Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/files` | Upload a file (multipart form: `file` + `purpose`) |
| `GET` | `/files` | List all files |
| `GET` | `/files/{id}` | Retrieve file metadata |
| `GET` | `/files/{id}/content` | Download file content |
| `DELETE` | `/files/{id}` | Delete a file |

File `purpose` values: `"fine-tune"`, `"batch-api"`

### Fine-Tuning

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/fine-tunes` | Create a fine-tuning job |
| `GET` | `/fine-tunes` | List all jobs |
| `GET` | `/fine-tunes/{id}` | Retrieve job details |
| `GET` | `/fine-tunes/{id}/events` | List training events (loss, metrics) |
| `POST` | `/fine-tunes/{id}/cancel` | Cancel a running job |
| `GET` | `/fine-tunes/{id}/download` | Download model weights |

Job statuses: `"pending"` → `"queued"` → `"running"` → `"completed"` | `"failed"` | `"cancelled"`

### Chat Completions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat/completions` | Chat completion (instruction-tuned models) |

### Completions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/completions` | Text completion (base models) |

### Embeddings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/embeddings` | Generate embeddings |

### Images

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/images/generations` | Generate images |

### Batch

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/batches` | Create batch job |
| `GET` | `/batches` | List batch jobs |
| `GET` | `/batches/{id}` | Retrieve batch status |
| `POST` | `/batches/{id}/cancel` | Cancel batch |

### Dedicated Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/endpoints` | Create dedicated endpoint |
| `GET` | `/endpoints` | List endpoints |
| `GET` | `/endpoints/{id}` | Retrieve endpoint |
| `DELETE` | `/endpoints/{id}` | Delete endpoint |

---

## Fine-Tuning: Full Parameter Reference

### `POST /fine-tunes` — Create Job

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | **required** | Base model ID (e.g. `"Qwen/Qwen3-8B"`) |
| `training_file` | string | **required** | File ID from upload |
| `validation_file` | string | null | Optional validation file ID |
| `n_epochs` | int | 1 | Number of training epochs (1–10) |
| `learning_rate` | float | 1e-5 | Learning rate |
| `lr_scheduler` | string | `"linear"` | `"linear"`, `"cosine"`, `"constant"` |
| `batch_size` | int | 16 | Training batch size (auto-adjusted to fit GPU) |
| `max_grad_norm` | float | 1.0 | Gradient clipping norm |
| `weight_decay` | float | 0.0 | L2 regularization weight |
| `warmup_ratio` | float | 0.0 | Fraction of total steps for LR warmup |
| `seed` | int | null | Random seed for reproducibility |
| `suffix` | string | null | Custom suffix for output model name |
| `wandb_api_key` | string | null | Weights & Biases API key for logging |
| `training_method` | string | `"sft"` | `"sft"` or `"dpo"` |
| `train_on_inputs` | bool/str | `"auto"` | Whether to compute loss on prompt tokens |
| **LoRA parameters** | | | |
| `lora` | bool | true | Enable LoRA (false = full fine-tune) |
| `lora_r` | int | 8 | LoRA rank (4, 8, 16, 32, 64) |
| `lora_alpha` | int | 8 | LoRA scaling factor |
| `lora_dropout` | float | 0.0 | Dropout on LoRA layers |
| `lora_trainable_modules` | string | `"all-linear"` | Which modules to apply LoRA to |
| **DPO parameters** | | | |
| `dpo_beta` | float | 0.1 | KL divergence penalty for DPO |

### Training Event Object

Returned by `GET /fine-tunes/{id}/events`:

```json
{
  "step": 100,
  "epoch": 1,
  "training_loss": 1.234,
  "validation_loss": 1.456,
  "learning_rate": 9.5e-6,
  "created_at": "2025-01-01T00:00:00Z"
}
```

---

## Chat Completions: Full Parameter Reference

### `POST /chat/completions`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | **required** | Model ID |
| `messages` | array | **required** | Array of `{role, content}` objects |
| `max_tokens` | int | model-dependent | Max tokens to generate |
| `temperature` | float | 0.7 | Sampling temperature (0–2) |
| `top_p` | float | 0.7 | Nucleus sampling threshold |
| `top_k` | int | 50 | Top-k sampling |
| `min_p` | float | — | Alternative to top_p/top_k filtering (0–1) |
| `repetition_penalty` | float | 1.0 | Penalize repeated tokens (>1 = more penalty) |
| `frequency_penalty` | float | 0.0 | Penalize frequent tokens (-2 to 2) |
| `presence_penalty` | float | 0.0 | Penalize present tokens (-2 to 2) |
| `logit_bias` | object | null | Adjust token likelihood (e.g. `{"105": 21.4}`) |
| `stop` | string/array | null | Stop sequence(s) |
| `stream` | bool | false | Stream response via SSE |
| `n` | int | 1 | Number of completions (1–128) |
| `logprobs` | int | null | Return log probabilities (0–20) |
| `echo` | bool | false | Echo back the prompt |
| `seed` | int | null | Random seed for reproducibility |
| `response_format` | object | null | See structured outputs below |
| `tools` | array | null | Function definitions for tool calling |
| `tool_choice` | string/object | `"auto"` | `"auto"`, `"none"`, `"required"`, or specific function |
| `safety_model` | string | null | Content safety model to apply |
| `reasoning_effort` | string | — | `"low"`, `"medium"`, `"high"` (reasoning models) |
| `reasoning` | object | — | `{"enabled": true/false}` toggle reasoning |
| `context_length_exceeded_behavior` | string | `"error"` | `"error"` or `"truncate"` |

### `response_format` Types

| Type | Description |
|------|-------------|
| `{"type": "text"}` | Plain text (default) |
| `{"type": "json_object"}` | Ensures valid JSON output |
| `{"type": "json_schema", "schema": {...}}` | Enforces specific JSON schema with `"strict": true` |
| `{"type": "regex", "pattern": "..."}` | Constrains output to match regex |

### Response Object

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "model": "...",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "...",
      "tool_calls": [...],
      "reasoning": "..."
    },
    "finish_reason": "stop",
    "index": 0,
    "logprobs": {...}
  }],
  "usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150}
}
```

`finish_reason` values: `"stop"`, `"eos"`, `"length"`, `"tool_calls"`

### Completions: `POST /completions`

Same parameters as chat completions but uses `prompt` (string) instead of `messages`.

---

## Embeddings: Parameter Reference

### `POST /embeddings`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | **required** | Embedding model ID |
| `input` | string/array | **required** | Text(s) to embed |

---

## Image Generation: Parameter Reference

### `POST /images/generations`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | **required** | Image model ID |
| `prompt` | string | **required** | Text prompt |
| `width` | int | 1024 | Image width in pixels |
| `height` | int | 1024 | Image height in pixels |
| `steps` | int | model-dependent | Diffusion steps (1–50) |
| `n` | int | 1 | Number of images (1–4) |
| `seed` | int | random | Random seed |
| `negative_prompt` | string | null | Content to avoid |
| `response_format` | string | `"url"` | `"url"` or `"base64"` |
| `image_url` | string | null | Reference image for guided generation |
| `aspect_ratio` | string | null | For Flux Schnell/Kontext (instead of width/height) |

---

## Supported Models for Fine-Tuning

### SFT & DPO — Model Families

| Model | Model ID | Max Context | FT Type |
|-------|----------|-------------|---------|
| Qwen3 0.6B | `Qwen/Qwen3-0.6B` | 32K | LoRA, Full |
| Qwen3 1.7B | `Qwen/Qwen3-1.7B` | 32K | LoRA, Full |
| Qwen3 4B | `Qwen/Qwen3-4B` | 32K | LoRA, Full |
| Qwen3 8B | `Qwen/Qwen3-8B` | 32K | LoRA, Full |
| Qwen3 14B | `Qwen/Qwen3-14B` | 32K | LoRA, Full |
| Qwen3 32B | `Qwen/Qwen3-32B` | 32K | LoRA, Full |
| Qwen 2.5 7B | `Qwen/Qwen2.5-7B-Instruct` | 32K | LoRA, Full |
| Qwen 2.5 72B | `Qwen/Qwen2.5-72B-Instruct` | 32K | LoRA |
| Llama 3.3 70B | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | 128K | LoRA |
| Llama 3.1 8B | `meta-llama/Meta-Llama-3.1-8B-Instruct-Reference` | 128K | LoRA, Full |
| Llama 3.1 70B | `meta-llama/Meta-Llama-3.1-70B-Instruct-Reference` | 128K | LoRA |
| Llama 3.1 405B | `meta-llama/Meta-Llama-3.1-405B-Instruct-Reference` | 128K | LoRA |
| Llama 3.2 3B | `meta-llama/Llama-3.2-3B-Instruct-Reference` | 128K | LoRA, Full |
| Llama 3.2 Vision 11B | `meta-llama/Llama-3.2-11B-Vision-Instruct-Reference` | 128K | LoRA |
| Llama 3.2 Vision 90B | `meta-llama/Llama-3.2-90B-Vision-Instruct-Reference` | 128K | LoRA |
| DeepSeek R1 8B | `deepseek-ai/DeepSeek-R1-Distill-Llama-8B-Reference` | 128K | LoRA, Full |
| DeepSeek R1 70B | `deepseek-ai/DeepSeek-R1-Distill-Llama-70B-Reference` | 128K | LoRA |
| DeepSeek V3 671B | `deepseek-ai/DeepSeek-V3` | 128K | LoRA |
| Gemma 2 9B | `google/gemma-2-9b-it` | 8K | LoRA, Full |
| Gemma 2 27B | `google/gemma-2-27b-it` | 8K | LoRA |
| Mistral 7B v0.3 | `mistralai/Mistral-7B-Instruct-v0.3` | 32K | LoRA, Full |

Note: Model IDs may change. Check https://docs.together.ai/docs/fine-tuning-models for the latest list.

---

## Serverless Inference — Model Catalog

### Chat / Instruct Models

| Model | ID | Context | Input $/1M | Output $/1M |
|-------|----|---------|-----------|------------|
| Qwen3.5 397B MoE | `Qwen/Qwen3.5-397B-A17B` | 262K | $0.60 | $3.60 |
| Qwen3 235B MoE (Thinking) | `Qwen/Qwen3-235B-A22B-Thinking-2507` | 262K | $0.65 | $3.00 |
| Qwen3 235B MoE (tput) | `Qwen/Qwen3-235B-A22B-Instruct-2507-tput` | 262K | $0.20 | $0.60 |
| Qwen3 Coder 480B MoE | `Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8` | 256K | $2.00 | $2.00 |
| Qwen3 Coder Next | `Qwen/Qwen3-Coder-Next-FP8` | 262K | $0.50 | $1.20 |
| Qwen3 Next 80B MoE | `Qwen/Qwen3-Next-80B-A3B-Instruct` | 262K | $0.15 | $1.50 |
| Qwen 2.5 7B Turbo | `Qwen/Qwen2.5-7B-Instruct-Turbo` | 32K | $0.30 | $0.30 |
| DeepSeek V3.1 | `deepseek-ai/DeepSeek-V3.1` | 128K | $0.60 | $1.70 |
| DeepSeek R1 | `deepseek-ai/DeepSeek-R1` | 163K | $3.00 | $7.00 |
| Llama 4 Maverick 17Bx128E | `meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8` | 1M | $0.27 | $0.85 |
| Llama 3.3 70B Turbo | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | 131K | $0.88 | $0.88 |
| Llama 3.1 8B Turbo | `meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo` | 131K | $0.18 | $0.18 |
| Llama 3.2 3B Turbo | `meta-llama/Llama-3.2-3B-Instruct-Turbo` | 131K | $0.06 | $0.06 |
| GPT-OSS 120B | `openai/gpt-oss-120b` | 128K | $0.15 | $0.60 |
| GPT-OSS 20B | `openai/gpt-oss-20b` | 128K | $0.05 | $0.20 |
| Kimi K2.5 | `moonshotai/Kimi-K2.5` | 262K | $0.50 | $2.80 |
| Kimi K2 Thinking | `moonshotai/Kimi-K2-Thinking` | 262K | $1.20 | $4.00 |
| GLM-5 | `zai-org/GLM-5` | 202K | $1.00 | $3.20 |
| MiniMax M2.5 | `MiniMaxAI/MiniMax-M2.5` | 228K | $0.30 | $1.20 |
| Mistral Small 24B | `mistralai/Mistral-Small-24B-Instruct-2501` | 32K | $0.10 | $0.30 |
| Gemma 2B (free) | `google/gemma-2b-it` | 8K | Free | Free |
| Gemma 3N E4B | `google/gemma-3n-E4B-it` | 32K | $0.02 | $0.04 |

### Vision Models

| Model | ID | Context | Input $/1M | Output $/1M |
|-------|----|---------|-----------|------------|
| Llama 4 Maverick | `meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8` | 1M | $0.27 | $0.85 |
| Qwen3-VL 32B | `Qwen/Qwen3-VL-32B-Instruct` | 262K | $0.50 | $1.50 |
| Qwen3-VL 8B | `Qwen/Qwen3-VL-8B-Instruct` | 262K | $0.18 | $0.68 |
| Qwen 2.5-VL 72B | `Qwen/Qwen2.5-VL-72B-Instruct` | 262K | $1.95 | $8.00 |

### Embedding Models

| Model | ID | Dimensions | Price $/1M |
|-------|----|-----------|-----------|
| M2-BERT 8K | `togethercomputer/m2-bert-80M-8k-retrieval` | 768 | — |
| M2-BERT 32K | `togethercomputer/m2-bert-80M-32k-retrieval` | 768 | — |
| E5 Large (multilingual) | `intfloat/multilingual-e5-large-instruct` | 1024 | $0.02 |
| UAE-Large | `WhereIsAI/UAE-Large-V1` | 1,024 | — |
| BGE-Large | `BAAI/bge-large-en-v1.5` | 1,024 | — |
| BGE-Base | `BAAI/bge-base-en-v1.5` | 768 | — |

### Reranking Models

| Model | ID | Price $/1M |
|-------|----|-----------|
| Mxbai Rerank Large V2 | `mixedbread-ai/Mxbai-Rerank-Large-V2` | $0.10 |

### Audio Models

| Model | ID | Type | Price |
|-------|----|------|-------|
| Orpheus 3B | `canopylabs/orpheus-3b-0.1-ft` | TTS | $0.27/$0.85 per 1M |
| Kokoro 82M | `hexgrad/Kokoro-82M` | TTS | $0.27/$0.85 per 1M |
| Cartesia Sonic 2 | `cartesia/sonic-2` | TTS | $65/1M chars |
| Whisper Large v3 | `openai/whisper-large-v3` | STT | $0.27/audio min |

### Moderation Models

| Model | ID | Context | Price $/1M |
|-------|----|---------|-----------|
| Llama Guard 4 12B | `meta-llama/Llama-Guard-4-12B` | 1M | $0.20 |
| VirtueGuard Lite | `VirtueAI/VirtueGuard-Text-Lite` | 32K | $0.20 |

### Image Generation Models

| Model | ID | Price |
|-------|----|-------|
| Imagen 4.0 Preview | `google/imagen-4.0-preview` | $0.04/MP |
| Imagen 4.0 Fast | `google/imagen-4.0-fast` | $0.02/MP |
| Imagen 4.0 Ultra | `google/imagen-4.0-ultra` | $0.06/MP |
| FLUX.1 Schnell | `black-forest-labs/FLUX.1-schnell` | $0.003/MP |
| FLUX.1.1 Pro | `black-forest-labs/FLUX.1.1-pro` | $0.04/MP |
| FLUX.1 Kontext Pro | `black-forest-labs/FLUX.1-kontext-pro` | $0.04/MP |
| FLUX.2 Pro | `black-forest-labs/FLUX.2-pro` | — |
| Seedream 4.0 | `ByteDance-Seed/Seedream-4.0` | $0.03/MP |
| Qwen Image | `Qwen/Qwen-Image` | $0.006/MP |
| SDXL 1.0 | `stabilityai/stable-diffusion-xl-base-1.0` | $0.002/MP |
| Ideogram 3.0 | `ideogram/ideogram-3.0` | $0.06/MP |

---

## Dedicated Endpoints

### GPU Options

| Hardware | GPU | VRAM | Approx $/hr | Use Case |
|----------|-----|------|-------------|----------|
| `gpu-1x-a100-80gb` | 1x A100 SXM | 80 GB | ~$1.42–$2.40 | Models up to ~30B (4-bit) |
| `gpu-2x-a100-80gb` | 2x A100 | 160 GB | ~$2.84–$4.80 | Models up to ~70B (4-bit) |
| `gpu-4x-a100-80gb` | 4x A100 | 320 GB | ~$5.68–$9.60 | Large models, high throughput |
| `gpu-8x-a100-80gb` | 8x A100 | 640 GB | ~$11.36–$19.20 | 405B+ models |
| `gpu-1x-h100-80gb` | 1x H100 | 80 GB | ~$2.56–$2.74 | Fastest single-GPU |
| `gpu-8x-h100-80gb` | 8x H100 | 640 GB | ~$20.48–$21.92 | Maximum performance |
| `gpu-1x-h200` | 1x H200 | 141 GB | ~$3.14 | Largest single-GPU VRAM |
| `gpu-1x-b200` | 1x B200 | 192 GB | ~$5.87 | Next-gen GPU |

### Create Endpoint Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | required | Model ID |
| `hardware` | string | required | GPU configuration (see above) |
| `min_replicas` | int | 1 | Minimum instances |
| `max_replicas` | int | 1 | Maximum instances (for autoscaling) |
| `autoscaling` | bool | false | Enable autoscaling |
| `idle_timeout` | int | 300 | Seconds before scaling down idle replicas |

Deployment time: up to 10 minutes. No rate limits on dedicated endpoints. Custom HuggingFace models can be deployed — no upload fees or storage costs.

---

## Rate Limits

Together uses **dynamic rate limiting** that adapts based on real-time model capacity and usage history.

### Dynamic Rate Limits

- **Formula**: `Dynamic Rate ≈ 2 × past_hour_successful_request_rate`
- **Bounds**: Between `base_rate` (60 RPM minimum) and `cap_rate`
- **Best practice**: Maintain steady, consistent traffic rather than bursts — sustained traffic increases your dynamic rate over time
- **Scale Plan**: Up to 9,000 RPM and 5M tokens/minute

### Rate Limit Headers

| Header | Description |
|--------|-------------|
| `x-ratelimit-limit` | Max requests per window |
| `x-ratelimit-remaining` | Remaining requests |
| `x-ratelimit-reset` | Time until limit resets |
| `x-tokenlimit-limit` | Max tokens per window |
| `x-tokenlimit-remaining` | Remaining tokens |
| `x-ratelimit-limit-dynamic` | Dynamic request limit |
| `x-ratelimit-remaining-dynamic` | Dynamic remaining requests |
| `x-tokenlimit-limit-dynamic` | Dynamic token limit |
| `x-tokenlimit-remaining-dynamic` | Dynamic remaining tokens |

### HTTP Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 400 | Bad request (invalid parameters, malformed JSON) | Fix request body |
| 401 | Invalid or missing API key | Check `TOGETHER_API_KEY` |
| 404 | Resource not found / invalid model name | Check endpoint URL and model ID |
| 422 | Validation error (e.g. safety checker violation) | Check parameter types/values |
| 429 | Rate limited (too many requests) | Back off, check rate limit headers |
| 500 | Server / validation error | Retry with backoff |
| 503 | Model loading / platform overloaded | Retry after ~30s |
| 504 | Request timeout | Reduce max_tokens or prompt length |
| 524 | Cloudflare timeout | Infrastructure-level timeout, retry |
| 529 | Internal server failure | Retry with backoff |

Error response format:
```json
{"error": {"message": "...", "type": "...", "param": null, "code": "..."}}
```

---

## Batch Inference Details

- **50% cost reduction** on supported models (DeepSeek, Llama, Qwen, Mistral families)
- **50,000 requests** per batch file max
- **100MB** max file size
- **30 billion tokens** enqueue limit per model
- Best-effort completion within **24 hours**
- Separate rate limit pool (does not consume standard API limits)
- Only supports `/v1/chat/completions` endpoint
- Output order may differ from input — match by `custom_id`

### Batch JSONL Input Format

```json
{"custom_id": "req-1", "body": {"model": "deepseek-ai/DeepSeek-V3", "messages": [{"role": "user", "content": "Hello!"}], "max_tokens": 200}}
```

### SDK v2 Methods

```python
client.files.upload(file="batch_input.jsonl", purpose="batch-api", check=False)
client.batches.create_batch(file_id, endpoint="/v1/chat/completions")
client.batches.get_batch(batch_id)
client.batches.list_batches()
client.batches.cancel_batch(batch_id)
client.files.retrieve_content(id=output_file_id, output="results.jsonl")
```

Batch statuses: `VALIDATING` → `IN_PROGRESS` → `COMPLETED` | `FAILED` | `CANCELLED`

---

## CLI Reference

```bash
# Authentication
export TOGETHER_API_KEY="your-key"

# Files
together files upload <path> [--purpose fine-tune]
together files list
together files retrieve <file-id>
together files delete <file-id>
together files check <file-id>          # validate file format

# Fine-Tuning
together fine-tuning create \
    --model "Qwen/Qwen3-8B" \
    --training-file <file-id> \
    --n-epochs 3 \
    --learning-rate 1e-5 \
    --batch-size 16 \
    --lora-r 16 \
    --suffix "my-model"
together fine-tuning list
together fine-tuning retrieve <job-id>
together fine-tuning list-events <job-id>
together fine-tuning cancel <job-id>
together fine-tuning download <job-id> [--output ./dir]

# Chat
together chat completions \
    --model "Qwen/Qwen3-8B" \
    --message "user:Hello"

# Completions
together completions \
    --model "Qwen/Qwen3-8B" \
    --prompt "Hello world"

# Images
together images generate \
    --model "black-forest-labs/FLUX.1-schnell" \
    --prompt "a clay tablet"

# Models
together models list
```

---

## Fine-Tuning Pricing

Pricing is per token processed during training (input tokens × epochs).

### SFT — LoRA

| Model Size | Price per M tokens |
|-----------|-------------------|
| ≤3B | ~$0.10 |
| 4B–8B | ~$0.30 |
| 9B–14B | ~$0.50 |
| 27B–32B | ~$0.80 |
| 70B | ~$1.20 |
| 405B | ~$5.00 |
| 671B (MoE) | ~$3.50 |

### SFT — Full Fine-Tune

Roughly 2x the LoRA price for the same model tier.

### DPO

~2.5x the SFT LoRA price. DPO processes both chosen and rejected examples.

### Serverless Inference

Fine-tuned LoRA models use the same per-token pricing as the base model.

---

## Python SDK v2 Methods Reference

```python
from together import Together, AsyncTogether

client = Together()

# Chat Completions
client.chat.completions.create(model=..., messages=..., **kwargs)
client.chat.completions.with_raw_response.create(...)  # access raw HTTP response

# Completions
client.completions.create(model=..., prompt=..., **kwargs)

# Images
client.images.generate(prompt=..., model=..., **kwargs)

# Embeddings
client.embeddings.create(model=..., input=..., **kwargs)

# Reranking
client.rerank.create(model=..., query=..., documents=..., top_n=...)

# Files
client.files.upload(file="path.jsonl", purpose="fine-tune")
client.files.list()
client.files.retrieve(id="file-xxx")
client.files.retrieve_content(id="file-xxx", output="output.jsonl")
client.files.delete(id="file-xxx")

# Fine-Tuning
client.fine_tuning.create(model=..., training_file=..., **kwargs)
client.fine_tuning.list()
client.fine_tuning.retrieve(job_id)
client.fine_tuning.list_events(job_id)
client.fine_tuning.cancel(job_id)
client.fine_tuning.download(job_id, output_dir="./checkpoint")

# Batches
client.batches.create_batch(file_id, endpoint="/v1/chat/completions")
client.batches.get_batch(batch_id)
client.batches.list_batches()
client.batches.cancel_batch(batch_id)

# Dedicated Endpoints
client.endpoints.create(model=..., hardware=..., **kwargs)
client.endpoints.list()
client.endpoints.retrieve(endpoint_id)
client.endpoints.delete(endpoint_id)
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TOGETHER_API_KEY` | API key (required) |
| `TOGETHER_BASE_URL` | Custom base URL (default: `https://api.together.xyz/v1`) |
| `TOGETHER_MAX_RETRIES` | Max retries on failure (default: 2) |
| `TOGETHER_TIMEOUT` | Request timeout in seconds (default: 300) |

---

## Links

- Python SDK: https://github.com/togethercomputer/together-python
- Docs: https://docs.together.ai
- Fine-Tuning Models: https://docs.together.ai/docs/fine-tuning-models
- Serverless Models: https://docs.together.ai/docs/serverless-models
- Batch Inference: https://docs.together.ai/docs/batch-inference
- Function Calling: https://docs.together.ai/docs/function-calling
- Structured Outputs: https://docs.together.ai/docs/json-mode
- Dedicated Endpoints: https://docs.together.ai/docs/dedicated-endpoints-ui
- Rate Limits: https://docs.together.ai/docs/rate-limits
- Pricing: https://www.together.ai/pricing
- Status: https://status.together.ai