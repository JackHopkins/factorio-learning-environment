---
name: together-ai
description: Use this skill when asked to fine-tune models on Together AI, create LoRA or DPO training jobs, format training data for Together, upload files to Together, use the Together inference API, set up serverless or dedicated endpoints, run batch inference, or use the Together CLI. Triggers include mentions of "Together AI", "together fine-tune", "together API", "LoRA training on Together", "DPO training", "serverless LoRA", "together batch", or references to the together Python package.
---

# Together AI — Fine-Tuning & Inference

Together AI provides fine-tuning (SFT, DPO, full & LoRA), serverless inference, and dedicated GPU endpoints. This skill covers the Python SDK, REST API, data formatting, and best practices.

- SDK docs: https://docs.together.ai/docs/quickstart
- Fine-tuning guide: https://docs.together.ai/docs/fine-tuning-overview
- API reference: https://docs.together.ai/reference

See `REFERENCE.md` for complete API parameter tables, model lists, and pricing.

---

## Setup

```bash
pip install together
```

```python
# Sync client
from together import Together
client = Together()  # reads TOGETHER_API_KEY from env

# Async client
from together import AsyncTogether
async_client = AsyncTogether()
```

```bash
# CLI authentication
export TOGETHER_API_KEY="your-key"
together --help
```

**Note**: The `together` package (SDK v2) uses keyword-only arguments, `NOT_GIVEN` sentinel instead of `None`, and httpx instead of requests.

---

## Part 1: Fine-Tuning Data Formats

Together accepts JSONL files. Every line is a JSON object. The format depends on the task type.

### SFT — Chat Format (recommended for instruction tuning)

Each line has a `"messages"` array with `role` and `content` fields:

```jsonl
{"messages": [{"role": "system", "content": "You are a helpful translator."}, {"role": "user", "content": "Translate: ta-ad-na-ú"}, {"role": "assistant", "content": "they gave"}]}
{"messages": [{"role": "user", "content": "Translate: i-di-nam"}, {"role": "assistant", "content": "he gave me"}]}
```

System messages are optional. Multi-turn conversations are supported — just alternate user/assistant roles.

### SFT — Completion Format (legacy, for base models)

Each line has a `"text"` field with the full prompt + completion:

```jsonl
{"text": "Translate Akkadian to English:\nta-ad-na-ú\nAnswer: they gave"}
{"text": "Translate Akkadian to English:\ni-di-nam\nAnswer: he gave me"}
```

### SFT — Chat with Reasoning / Chain-of-Thought

For models that support `<think>` blocks (Qwen3, DeepSeek-R1), include reasoning in the assistant content:

```jsonl
{"messages": [{"role": "user", "content": "Translate: 1 MA.NA KÙ.BABBAR"}, {"role": "assistant", "content": "<think>\nMA.NA is the Sumerian logogram for mina (unit of weight).\nKÙ.BABBAR is the logogram for silver.\n1 MA.NA KÙ.BABBAR = 1 mina of silver.\n</think>\n\n1 mina of silver"}]}
```

### SFT — Tool Calling Format

```jsonl
{"messages": [{"role": "system", "content": "You have access to functions."}, {"role": "user", "content": "What is the weather?"}, {"role": "assistant", "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "get_weather", "arguments": "{\"location\": \"NYC\"}"}}]}, {"role": "tool", "tool_call_id": "call_1", "content": "{\"temp\": 72}"}, {"role": "assistant", "content": "It's 72F in NYC."}]}
```

### SFT — Vision / VLM Format

For vision-language models (Llama-Vision, Qwen3-VL, etc.):

```jsonl
{"messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}, {"type": "text", "text": "What is in this image?"}]}, {"role": "assistant", "content": "A clay tablet with cuneiform writing."}]}
```

Image URLs must be publicly accessible during training. Base64 is also supported via `data:image/jpeg;base64,...`.

### DPO — Preference Format

Each line has `prompt`, `chosen`, and `rejected`:

```jsonl
{"prompt": "Translate: a-na a-bi-a", "chosen": "to my father", "rejected": "for father"}
{"prompt": "Translate: um-ma A-šur-ma", "chosen": "thus says Aššur:", "rejected": "Aššur said"}
```

For chat-style DPO:

```jsonl
{"prompt": [{"role": "user", "content": "Translate: a-na a-bi-a"}], "chosen": [{"role": "assistant", "content": "to my father"}], "rejected": [{"role": "assistant", "content": "for father"}]}
```

---

## Part 2: File Upload & Validation

### Upload a training file

```python
# Upload for fine-tuning
response = client.files.upload(file="data/train.jsonl", purpose="fine-tune")
file_id = response.id
print(f"File ID: {file_id}")  # e.g. "file-abc123"

# Check file status (processing can take a few minutes)
file_info = client.files.retrieve(file_id)
print(f"Status: {file_info.status}")  # "uploaded", "processed", "error"
print(f"Rows: {file_info.num_lines}")
```

### List and delete files

```python
# List all files
files = client.files.list()
for f in files.data:
    print(f"{f.id} | {f.filename} | {f.status} | {f.num_lines} rows")

# Delete a file
client.files.delete(file_id)

# Download file content
client.files.retrieve_content(id=file_id, output="downloaded.jsonl")
```

### CLI upload

```bash
together files upload data/train.jsonl
together files list
together files check <file-id>
```

### Validation

Together validates files on upload. Common issues:
- Missing `messages` or `text` key
- Empty messages array
- Role must be `system`, `user`, `assistant`, or `tool`
- First non-system message must be `user` role
- Max file size: 5GB (4.8GB recommended)
- DPO: `chosen` and `rejected` must have the same prompt

---

## Part 3: Creating Fine-Tuning Jobs

### LoRA Fine-Tune (default, recommended)

```python
response = client.fine_tuning.create(
    model="Qwen/Qwen3-8B",
    training_file=file_id,
    # Hyperparameters
    n_epochs=3,
    learning_rate=1e-5,
    batch_size=16,
    # LoRA-specific
    lora=True,                    # default is True
    lora_r=16,                    # rank (8, 16, 32, 64)
    lora_alpha=16,                # scaling factor
    lora_dropout=0.05,
    lora_trainable_modules="all-linear",
    # Training
    warmup_ratio=0.1,
    weight_decay=0.01,
    max_grad_norm=1.0,
    # Data
    train_on_inputs=False,        # mask user/system tokens from loss
    # Optional
    suffix="akkadian-v1",         # custom model name suffix
    wandb_api_key="your-key",     # optional W&B logging
)

job_id = response.id
print(f"Job ID: {job_id}")
```

### Full Fine-Tune

```python
response = client.fine_tuning.create(
    model="Qwen/Qwen3-8B",
    training_file=file_id,
    n_epochs=2,
    learning_rate=2e-6,           # lower LR for full FT
    batch_size=8,
    lora=False,                   # full fine-tune
    warmup_ratio=0.1,
    suffix="akkadian-full-v1",
)
```

### DPO Fine-Tune

```python
response = client.fine_tuning.create(
    model="Qwen/Qwen3-8B",
    training_file=file_id,
    training_method="dpo",
    dpo_beta=0.1,                 # KL penalty (0.1–0.5 typical)
    n_epochs=1,
    learning_rate=5e-7,           # very low LR for DPO
    batch_size=8,
    lora=True,
    lora_r=16,
)
```

### Hyperparameter Reference (Quick)

| Parameter | Default | Range | Notes |
|-----------|---------|-------|-------|
| `n_epochs` | 1 | 1–10 | More epochs for small datasets |
| `learning_rate` | 1e-5 | 1e-7 to 1e-4 | Lower for full FT, higher for LoRA |
| `batch_size` | 16 | 1–512 | Auto-adjusted to fit GPU memory |
| `lora_r` | 8 | 4–64 | Higher = more capacity, more VRAM |
| `lora_alpha` | 8 | 8–128 | Scaling; often set equal to `lora_r` |
| `lora_dropout` | 0 | 0–0.1 | Small dropout helps generalization |
| `warmup_ratio` | 0.0 | 0–0.2 | Fraction of steps for LR warmup |
| `weight_decay` | 0.0 | 0–0.1 | L2 regularization |
| `max_grad_norm` | 1.0 | 0.1–10 | Gradient clipping |
| `train_on_inputs` | `"auto"` | bool | `False` = mask prompt tokens from loss |
| `dpo_beta` | 0.1 | 0.01–1.0 | DPO KL divergence penalty |

See `REFERENCE.md` for the complete parameter table.

---

## Part 4: Monitoring & Managing Jobs

### Check job status

```python
job = client.fine_tuning.retrieve(job_id)
print(f"Status: {job.status}")     # "pending", "queued", "running", "completed", "failed", "cancelled"
print(f"Model: {job.output_name}") # final model name once completed
```

### List jobs

```python
jobs = client.fine_tuning.list()
for j in jobs.data:
    print(f"{j.id} | {j.status} | {j.model} | {j.output_name}")
```

### Monitor training events

```python
events = client.fine_tuning.list_events(job_id)
for event in events.data:
    print(f"Step {event.step}: loss={event.training_loss:.4f}")
```

### Cancel a job

```python
client.fine_tuning.cancel(job_id)
```

### Download weights (LoRA adapter or full model)

```python
# After job completes, download checkpoint
client.fine_tuning.download(
    job_id,
    output_dir="./outputs/together_checkpoint"
)
```

### CLI monitoring

```bash
together fine-tuning list
together fine-tuning retrieve <job-id>
together fine-tuning list-events <job-id>
together fine-tuning cancel <job-id>
together fine-tuning download <job-id> --output ./checkpoint
```

---

## Part 5: Inference API

### Chat Completions (main API)

```python
response = client.chat.completions.create(
    model="Qwen/Qwen3-8B",   # or your fine-tuned model name
    messages=[
        {"role": "system", "content": "Translate Akkadian to English."},
        {"role": "user", "content": "ta-ad-na-ú"},
    ],
    max_tokens=512,
    temperature=0.7,
    top_p=0.7,
    top_k=50,
    repetition_penalty=1.1,
    stop=["<|im_end|>"],
)
print(response.choices[0].message.content)
```

### Streaming

```python
stream = client.chat.completions.create(
    model="Qwen/Qwen3-8B",
    messages=[{"role": "user", "content": "Translate: a-na a-bi-a"}],
    max_tokens=256,
    stream=True,
)
for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
```

### Async Parallel Requests

```python
import asyncio
from together import AsyncTogether

async def translate_batch(texts):
    async_client = AsyncTogether()
    tasks = [
        async_client.chat.completions.create(
            model="Qwen/Qwen3-8B",
            messages=[{"role": "user", "content": f"Translate: {t}"}],
        )
        for t in texts
    ]
    responses = await asyncio.gather(*tasks)
    return [r.choices[0].message.content for r in responses]
```

### JSON Mode / Structured Outputs

Four `response_format` types are available:

```python
# 1. Simple JSON mode — ensures valid JSON
response = client.chat.completions.create(
    model="Qwen/Qwen3-8B",
    messages=[
        {"role": "system", "content": "Respond in JSON with keys: amount, unit, commodity"},
        {"role": "user", "content": "Parse: 5 GÍN KÙ.BABBAR"},
    ],
    response_format={"type": "json_object"},
)

# 2. JSON Schema — enforces specific structure
response = client.chat.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    messages=[
        {"role": "system", "content": "Parse commodity amounts into structured JSON."},
        {"role": "user", "content": "Parse: 5 GÍN KÙ.BABBAR"},
    ],
    response_format={
        "type": "json_schema",
        "schema": {
            "name": "CommodityAmount",
            "schema": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "unit": {"type": "string"},
                    "commodity": {"type": "string"},
                },
                "required": ["amount", "unit", "commodity"],
            },
            "strict": True,
        },
    },
)

# 3. Regex — constrained to regex pattern
response = client.chat.completions.create(
    model="Qwen/Qwen3-8B",
    messages=[{"role": "user", "content": "Classify sentiment: positive, neutral, or negative"}],
    response_format={"type": "regex", "pattern": "(positive|neutral|negative)"},
)
```

**Important**: Always also include a textual instruction in the prompt telling the model to respond in JSON — the `response_format` parameter alone is not sufficient for best results.

### Structured Output with Pydantic

```python
import json
from pydantic import BaseModel, Field

class Translation(BaseModel):
    source: str = Field(description="Original Akkadian text")
    translation: str = Field(description="English translation")
    confidence: float = Field(description="Confidence score 0-1")

response = client.chat.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    messages=[
        {"role": "system", "content": f"Respond in JSON: {json.dumps(Translation.model_json_schema())}"},
        {"role": "user", "content": "Translate: a-na a-bi-a"},
    ],
    response_format={
        "type": "json_schema",
        "schema": Translation.model_json_schema(),
    },
)
result = Translation.model_validate_json(response.choices[0].message.content)
```

### Function Calling

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "lookup_word",
            "description": "Look up an Akkadian word in the lexicon",
            "parameters": {
                "type": "object",
                "properties": {
                    "word": {"type": "string", "description": "The word to look up"},
                },
                "required": ["word"],
            },
        },
    }
]

response = client.chat.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    messages=[{"role": "user", "content": "What does kaspum mean?"}],
    tools=tools,
    tool_choice="auto",  # "auto", "none", "required", or {"type": "function", "function": {"name": "..."}}
)

# Check if the model wants to call a tool
choice = response.choices[0]
if choice.finish_reason == "tool_calls":
    for tc in choice.message.tool_calls:
        args = json.loads(tc.function.arguments)
        result = lookup_word(**args)  # your function

        # Multi-turn: append assistant + tool messages, then call again
        messages.append(choice.message)
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "name": tc.function.name,
            "content": json.dumps(result),
        })

    final = client.chat.completions.create(
        model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        messages=messages,
    )
```

Supported patterns: single tool, multiple tools, parallel calls, parallel + multiple, multi-step, multi-turn.

### Reasoning Models

For models with reasoning capability (DeepSeek-R1, Qwen3-thinking):

```python
response = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-R1",
    messages=[{"role": "user", "content": "Translate: ta-ad-na-ú"}],
    reasoning_effort="medium",  # "low", "medium", "high"
    # Or toggle: reasoning={"enabled": True}
)
# Reasoning content in: response.choices[0].message.reasoning
# Final answer in: response.choices[0].message.content
```

### Completions (legacy, for base models)

```python
response = client.completions.create(
    model="Qwen/Qwen3-8B",
    prompt="Translate Akkadian to English:\nta-ad-na-ú\nAnswer:",
    max_tokens=128,
    temperature=0.0,
    stop=["\n"],
)
print(response.choices[0].text)
```

### Embeddings

```python
response = client.embeddings.create(
    model="togethercomputer/m2-bert-80M-8k-retrieval",
    input=["silver traded in Kaneš"],
)
embedding = response.data[0].embedding  # list of floats
```

### Reranking

```python
response = client.rerank.create(
    model="mixedbread-ai/Mxbai-Rerank-Large-V2",
    query="silver trade",
    documents=["5 shekels of silver", "tin shipment to Kaneš", "silver debt record"],
    top_n=2,
)
```

---

## Part 6: Batch Inference

For large-scale offline inference at **50% cost reduction** (on supported models). Separate rate limit pool. Up to 50,000 requests per batch, 100MB max file size.

```python
# 1. Prepare a JSONL file with requests
import json

requests = []
for i, text in enumerate(akkadian_texts):
    requests.append({
        "custom_id": f"req-{i}",
        "body": {
            "model": "Qwen/Qwen3-8B",
            "messages": [
                {"role": "system", "content": "Translate Akkadian to English."},
                {"role": "user", "content": text},
            ],
            "max_tokens": 512,
        },
    })

with open("batch_input.jsonl", "w") as f:
    for r in requests:
        f.write(json.dumps(r) + "\n")

# 2. Upload the batch file (purpose="batch-api")
batch_file = client.files.upload(file="batch_input.jsonl", purpose="batch-api", check=False)

# 3. Create the batch job
batch = client.batches.create_batch(batch_file.id, endpoint="/v1/chat/completions")
print(f"Batch ID: {batch.id}")

# 4. Check status
batch_status = client.batches.get_batch(batch.id)
print(f"Status: {batch_status.status}")  # VALIDATING, IN_PROGRESS, COMPLETED, FAILED, CANCELLED

# 5. Download results when complete
if batch_status.status == "COMPLETED":
    client.files.retrieve_content(
        id=batch_status.output_file_id,
        output="batch_output.jsonl",
    )

# 6. List / cancel batches
all_batches = client.batches.list_batches()
client.batches.cancel_batch(batch.id)
```

**Important**: Output line order may not match input — use `custom_id` for mapping. Cancelled batches still incur charges for already-processed responses.

---

## Part 7: OpenAI Compatibility

Together's API is OpenAI-compatible. You can use the OpenAI SDK as a drop-in:

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_TOGETHER_API_KEY",
    base_url="https://api.together.xyz/v1",
)

# Use exactly like OpenAI
response = client.chat.completions.create(
    model="Qwen/Qwen3-8B",
    messages=[{"role": "user", "content": "Hello"}],
)
```

Compatible endpoints: chat completions, completions, embeddings, images, vision, structured outputs, function calling. Works with LangChain, LlamaIndex, LiteLLM, Vercel AI SDK, Instructor, etc.

---

## Part 8: Using Fine-Tuned Models

### Serverless inference (LoRA)

After a LoRA job completes, the model is available for serverless inference:

```python
# The model name is: <your-username>/<base-model-suffix>
# e.g., "jackhopkins/Qwen3-8B-akkadian-v1"
model_name = job.output_name

response = client.chat.completions.create(
    model=model_name,
    messages=[{"role": "user", "content": "Translate: ta-ad-na-ú"}],
    max_tokens=256,
)
```

Serverless LoRA models are loaded on-demand. First request may have cold-start latency (~30s). Subsequent requests are fast.

### Dedicated endpoints (for production)

For consistent latency, create a dedicated endpoint:

```python
endpoint = client.endpoints.create(
    model=model_name,
    hardware="gpu-1x-h100-80gb",  # see REFERENCE.md for all GPU options
    min_replicas=1,
    max_replicas=3,
    autoscaling=True,
    idle_timeout=300,             # seconds before scaling down
)
```

Dedicated endpoints: single-tenant, no rate limits, consistent latency. Custom fine-tuned models from HuggingFace can be uploaded and deployed — no upload fees or storage costs.

---

## Part 9: Best Practices

### Data Quality

- **Minimum**: 10 examples (but 100+ recommended for good results)
- **Sweet spot**: 1,000–10,000 examples for most tasks
- **Diminishing returns** past ~50K unless highly diverse
- **Validate format** before upload: all JSON must parse, messages must alternate roles correctly
- **`train_on_inputs=False`** (default for chat): prevents the model from memorizing prompts, only learns to generate completions
- **Shuffle** your data before upload

### Choosing LoRA vs Full Fine-Tune

| Factor | LoRA | Full FT |
|--------|------|---------|
| Speed | Faster (2-5x) | Slower |
| Cost | Lower | ~2x LoRA |
| Quality | Great for most tasks | Slightly better for complex tasks |
| Serverless inference | Yes (on-demand) | Need dedicated endpoint |
| Typical use case | Adapting to a domain/style | Deep knowledge injection |

### Hyperparameter Tips

- **Small datasets (<500 rows)**: Higher `n_epochs` (3-5), lower `learning_rate` (5e-6)
- **Large datasets (>5K rows)**: Fewer `n_epochs` (1-2), standard `learning_rate` (1e-5)
- **LoRA rank**: Start with `lora_r=16`. Increase to 32/64 if underfitting
- **`lora_alpha`**: Often set equal to `lora_r` for a scaling factor of 1.0
- **DPO beta**: 0.1 is standard. Increase to 0.3-0.5 if model diverges too far from base
- **Batch size**: Together auto-adjusts to fit GPU. Larger batch = more stable gradients

### Common Pitfalls

1. **Wrong data format**: Chat models need `messages` format, not `text` format
2. **Forgetting `train_on_inputs=False`**: Without this, model trains on prompts too (usually wasteful)
3. **Too many epochs on small data**: Leads to overfitting. Watch validation loss
4. **DPO without SFT first**: DPO works best as a refinement after SFT
5. **Not stripping `<think>` at inference**: If you trained with CoT, strip reasoning blocks from final output
6. **Model name format**: Fine-tuned models are `<username>/<base-suffix>`, not the base model name
7. **Batch file purpose**: Use `purpose="batch-api"` for batch files, `purpose="fine-tune"` for training data
8. **Batch output order**: Results may not be in input order — always match by `custom_id`

### Pricing Overview

Fine-tuning is priced per token processed during training. LoRA is cheaper than full FT. DPO costs ~2.5x SFT. See `REFERENCE.md` for detailed pricing tables.

| Model Tier | SFT (LoRA) | SFT (Full) | DPO |
|------------|-----------|-----------|-----|
| 1-8B | ~$0.30/M tokens | ~$0.60/M tokens | ~$0.75/M tokens |
| 8-70B | ~$1.20/M tokens | ~$3.00/M tokens | ~$3.00/M tokens |

Serverless inference pricing varies by model. Fine-tuned LoRA models use the same pricing as the base model.