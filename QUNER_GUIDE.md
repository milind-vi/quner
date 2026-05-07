# Quner — Complete Project Walkthrough

> Companion notes for the Major Project II final presentation.
> Reads top-to-bottom; sections 1–4 give the story arc, sections 5–7 are the deep dive, sections 8–11 are the "questions you might get asked" cheat sheet.

---

## 0. Table of Contents

1. [The 30-second pitch](#1-the-30-second-pitch)
2. [What problem does it solve?](#2-what-problem-does-it-solve)
3. [High-level architecture](#3-high-level-architecture)
4. [Tech stack & frameworks](#4-tech-stack--frameworks)
5. [File-by-file walkthrough](#5-file-by-file-walkthrough)
   - [Repository root](#51-repository-root)
   - [Backend — `central_backend_server/`](#52-backend--central_backend_server)
   - [Dashboard — `client_dashboard/`](#53-dashboard--client_dashboard)
6. [WebSocket protocol](#6-websocket-protocol)
7. [The three agents in depth](#7-the-three-agents-in-depth)
8. [Pipeline modes (OpenAI / Groq / Full)](#8-pipeline-modes-openai--groq--full)
9. [Three runtime stories (data flow walkthroughs)](#9-three-runtime-stories-data-flow-walkthroughs)
10. [Where to extend Quner](#10-where-to-extend-quner)
11. [Presentation talking points & likely questions](#11-presentation-talking-points--likely-questions)
12. [Glossary](#12-glossary)

---

## 1. The 30-second pitch

Quner is a **multi-agent AI framework that lets medical students practise clinical interviewing on demand** with structured, rubric-aligned feedback at the end. It replaces the scarce human "standardised patient" actor with an LLM-driven virtual patient, plus an LLM-driven examiner that grades the student against the **Master Interview Rating Scale (MIRS)** plus a separate **clinical-reasoning rubric**.

The system has **three cooperating agents**:

- **Generator** — programmatically builds an EBM-grounded vignette with a configurable difficulty (1–10) and Big Five personality.
- **Virtual Simulated Patient (VSP)** — holds a persona-consistent dialogue, routed through 6 different system prompts depending on the conversation case.
- **Critic** — gives a one-line "quick tip" after each turn, on-demand "hint" mid-session, and a structured **MIRS + clinical** report on session pause.

A **NiceGUI browser dashboard** is the primary client. It supports text chat, push-to-talk speech, optional auto-submit, system-default text-to-speech for patient replies, an on-demand hint button, and a slide-out vignette drawer.

---

## 2. What problem does it solve?

Medical schools rely on **standardised patient (SP) actors** for interviewing practice — humans paid to portray a specific case. They are scarce, expensive, hard to schedule, and you can only run as many concurrent sessions as you have actors and rooms. The result: **students get a small number of high-stakes practice sessions**, mostly clustered around exam time.

LLM-driven simulated patients are a credible alternative, but the first generation has three recurring failure modes:

1. **Persona drift** — the model breaks character when challenged.
2. **Knowledge leakage** — the patient cites diagnostic detail a real patient wouldn't know.
3. **Weak feedback** — at best a free-text summary; no per-criterion rubric, no transcript evidence.

Quner's **multi-agent design directly attacks each failure mode**:

| Failure | Quner's mitigation |
|---|---|
| Persona drift | VSP runs a **routing pre-processor** + **post-processing filter** that strips doctor-vocabulary and tightens persona |
| Knowledge leakage | Same post-processing filter removes any fact the patient couldn't plausibly know |
| Weak feedback | Critic emits **per-MIRS-criterion** scores + a **7-criterion clinical** evaluation, each with transcript evidence |

---

## 3. High-level architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Browser (Chrome/Safari)                     │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ NiceGUI Dashboard  (client_dashboard/, port 8501)            │    │
│  │   • chat input + messages                                    │    │
│  │   • Web Speech API STT/TTS  (browser-native)                 │    │
│  │   • view-vignette drawer, hint button, restart button        │    │
│  │   • feedback dialog (MIRS + clinical tabs)                   │    │
│  └────────────────┬─────────────────────────────────────────────┘    │
└───────────────────┼──────────────────────────────────────────────────┘
                    │ WebSocket (ws://localhost:8085)
                    │ JSON actions/events
                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│             central_backend_server/  (port 8085, asyncio)            │
│                                                                      │
│   ┌──────────────────────────────────────────────────┐               │
│   │  Orchestrator  ws_server.py                      │               │
│   │  routes JSON action → agent function             │               │
│   └──────────┬─────────────┬────────────┬────────────┘               │
│              ▼             ▼            ▼                            │
│   ┌──────────────┐  ┌────────────┐  ┌─────────────┐                  │
│   │ Generator    │  │   VSP      │  │  Critic     │                  │
│   │ agent        │  │  agent     │  │  agent      │                  │
│   └──────┬───────┘  └─────┬──────┘  └──────┬──────┘                  │
│          │                │                │                         │
│          └────────────────┴────────────────┘                         │
│                           │                                          │
│              ┌────────────▼─────────────┐                            │
│              │  llm/clients.py          │  ← single dispatcher       │
│              │   model_for(stage)       │                            │
│              └────────────┬─────────────┘                            │
└───────────────────────────┼──────────────────────────────────────────┘
                            ▼
              ┌─────────────────────────────────────┐
              │  External LLM provider              │
              │   • OpenAI         (default)        │
              │   • Groq           (free tier)      │
              │   • Cerebras       (full mode)      │
              └─────────────────────────────────────┘
              ┌─────────────────────────────────────┐
              │  (optional, USE_RAG=1)              │
              │   • Pinecone vector index           │
              │   • LlamaIndex + HF embeddings      │
              └─────────────────────────────────────┘
```

**Two processes**, communicating over **one WebSocket**. Either side can be restarted without bringing the other down.

---

## 4. Tech stack & frameworks

### Backend (Python 3.10+)

| Library | What it does in Quner | Why this choice |
|---|---|---|
| `asyncio` | Concurrency — the WebSocket server, every agent function, broadcast helper, and history queries are all async | Standard library, lets one process serve many clients without threads |
| `websockets` | The `ws_server.py` gateway server | Pure-asyncio WebSocket implementation, no extra dependencies |
| `openai` (Python SDK) | Single OpenAI-compatible client class — used to talk to OpenAI, Groq, **and** Cerebras (because all three expose OpenAI-compatible APIs) | One SDK, three providers — switching is a `base_url` change |
| `python-dotenv` | Loads `.env` at startup so `os.environ` is populated | Industry-standard secret management; no hard-coded keys |
| `mdextractor` | Pulls the first `# heading…` Markdown block out of a noisy LLM response | Generator's vignette steps return Markdown wrapped in commentary; this strips the wrapper |
| `llama-index`, `pinecone-client`, `sentence-transformers` (HuggingFace) | **Optional** — only loaded if `USE_RAG=1` | RAG layer for grounding patient answers in evidence-based-medicine corpus |

### Dashboard (browser via Python)

| Library | What it does | Why this choice |
|---|---|---|
| `nicegui` (pinned `<2.0`) | Python web-UI framework that renders Quasar/Vue components and bridges Python ↔ browser through WebSockets | Lets you write the dashboard in Python — no JS build chain. Pinned to 1.x because 2.x changes the page-lifecycle model |
| `aiohttp` | The dashboard's WebSocket *client* (it connects out to the backend) | Async HTTP/WS client; pairs well with NiceGUI's async event loop |
| FastAPI + Uvicorn | Hidden under NiceGUI; serves the page on port 8501 | Default NiceGUI runtime |

### Browser (no Python, no extra dependency)

| API | What it does |
|---|---|
| `SpeechRecognition` / `webkitSpeechRecognition` | Push-to-talk speech-to-text. On-device. Chrome/Edge/Safari only — Firefox is missing it |
| `SpeechSynthesis` | Text-to-speech for patient replies. System default voice |

These run **entirely client-side** — no server-side audio pipeline, no extra API keys.

### LLM providers (configurable via `.env`)

| Provider | Purpose | Cost |
|---|---|---|
| **OpenAI** (`gpt-4o-mini`) | Default for everything in OpenAI-only mode; for post-processing + feedback in full mode | ~$0.02 per typical session |
| **Groq** (`llama-3.3-70b-versatile`) | Default for vignette + answer generation in full mode; everything in groq-only mode | Free tier with daily token cap |
| **Cerebras** (`llama-4-scout-17b-16e-instruct`) | VSP preprocessing in full mode | Free tier |
| **Pinecone** | Vector store for RAG (only if `USE_RAG=1`) | Free tier |

---

## 5. File-by-file walkthrough

### 5.1 Repository root

```
quner/
├── .env                         # Secrets + pipeline flags (gitignored)
├── .env.example                 # Template — committed to git
├── .gitignore                   # ignores .env, venvs, __pycache__, generated_patients/
├── README.md                    # Quick-start + architecture overview
├── LICENSE.md                   # GPL-3.0
├── create_rag_storage.py        # OPTIONAL: build the Pinecone EBM index
├── central_backend_server/      # backend (port 8085)
└── client_dashboard/            # dashboard (port 8501)
```

#### `.env` and `.env.example`

The `.env` file is the **single source of secrets and pipeline flags**:

```bash
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
CEREBRAS_API_KEY=csk-...
PINECONE_API_KEY=pcsk_...

PIPELINE_MODE=openai-only   # or groq-only, or full
USE_RAG=0                   # 1 to enable Pinecone grounding
PINECONE_INDEX_NAME=quner2
```

**Why this matters in your presentation:** the original prototype hard-coded all four keys directly in `config.py`. That's a serious operational problem (keys leak the moment you push). Major II externalised every secret to `.env`, gitignores it, and ships an `.env.example` template.

#### `create_rag_storage.py`

Operational script (not part of the runtime). Reads a folder of `.md` evidence-based-medicine documents, embeds them with `sentence-transformers/all-MiniLM-L6-v2`, and pushes them into a Pinecone index. **Run once** to build the index, then enable `USE_RAG=1` in `.env`. Skip it entirely if you don't want RAG.

---

### 5.2 Backend — `central_backend_server/`

Tree:

```
central_backend_server/
├── ws_server.py                 # Orchestrator (async WebSocket gateway)
├── config.py                    # .env loader + pipeline flags + model names
├── globals_server.py            # Connected-clients registry + broadcast helper
├── globals_conversation_logic.py # Per-session state (Patient, history, debug log…)
├── conversion_tables.py         # Disease library + Big-Five → text + Furhat catalogs
├── predefined_patients.py       # Eleanor, Cassian, Marcus
├── utils.py                     # Backwards-compatibility facade (re-exports)
├── minimal_generate_client.py   # CLI test harness
├── prompts/                     # All prompt templates
│   ├── __init__.py
│   ├── generation.py
│   ├── vsp.py
│   ├── feedback.py
│   ├── post_processing.py
│   └── hint.py
├── llm/                         # Client wiring + RAG + parsers
│   ├── __init__.py
│   ├── clients.py
│   ├── rag.py
│   └── parsers.py
├── agents/                      # Three agents + glue
│   ├── __init__.py
│   ├── generator.py
│   ├── vsp.py
│   ├── critic.py
│   ├── predefined.py
│   └── lifecycle.py
└── generated_patients/          # auto-created — saved vignettes
```

#### `ws_server.py` — the orchestrator

The **entry point** for the backend. Its `handler(websocket)` coroutine is what `websockets.serve()` runs for every client connection.

What it does, in order:

1. Registers the client in `globals_server._connected_clients`.
2. Reads JSON messages in a loop. Each message has an `action` field.
3. Dispatches the action to the right place — most actions go to a function in `agents/`, a few read state from `globals_conversation_logic`.
4. The full action list (~16 actions): `setRole`, `addPatientResponse`, `addDoctorResponse`, `getPatientResponse`, `checkFurhatConnected`, `getFurhatStatusUpdate`, `furhatStatusUpdate`, `checkPatient`, `getHistory`, `getDebugLog`, `getPatientInformation`, `getQuickFeedback`, `generatePatient`, `launchPredefinedPatient`, `stopAndGetFinalFeedback`, `recallFinalFeedback`, `resumePatient`, `getConversationId`, `getHint`.
5. On disconnect: removes the client. If it was a `furhat` client, also broadcasts `furhatDisconnected`.

**Talking point:** This is a giant `if/elif` ladder, intentionally simple. Could be refactored into a dispatcher dict; works fine as-is.

#### `config.py` — environment loader + model dispatcher inputs

Lines 1–40 (approx) load `.env` via `python-dotenv` into `os.environ`.
Then it exposes Python-side constants:

- **Secrets**: `OPENAI_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `PINECONE_API_KEY`.
- **Pipeline flags**: `PIPELINE_MODE` (`"openai-only"`, `"groq-only"`, `"full"`), plus boolean shortcuts `OPENAI_ONLY` and `GROQ_ONLY`. `USE_RAG` is auto-disabled outside of full mode.
- **Model names**: per-stage names for OpenAI mode (`VSP_model_openai`, `quick_feedback_api_model`, `full_feedback_api_model`, etc.) and full-mode names (`vignette_generation_groq_model`, `VSP_model_preprocessing`, `VSP_model_answergeneration`).
- **Other**: `EBM_path`, `pinecone_index_name`, `GENERATED_PATIENT_OUTPUT_DIR`, `RAG_EMBEDDING_MODEL`, `RAG_EMBEDDING_DIMENSION`.

**Talking point:** every single decision about how the system runs is in this one file. Want to add a fourth pipeline mode? Add a flag here, add a branch in `llm/clients.py::model_for()`. That's it.

#### `globals_server.py` — connections + broadcast

Three tiny things:

- `_connected_clients` (a `set`)
- `_connected_client_roles` (a dict mapping websocket → role string like `"dashboard"` or `"furhat"`)
- `broadcast_message(json_dict)` — sends the JSON to every connected websocket simultaneously via `asyncio.gather`

Plus accessors: `add_client`, `remove_client`, `set_client_role`, `is_furhat_connected`, etc.

**Talking point:** this is the "message bus" of the system. Every agent posts its results through `broadcast_message`. Decoupling = every connected client sees every event regardless of which client triggered it.

#### `globals_conversation_logic.py` — per-session state

Holds the **actual data** for the current simulation:

- `_patient` — the current `Patient` (a small dataclass with `disease`, `vignette`, `face`, `voice`, and 5 personality strings)
- `_conversation_history` — list of `{"origin": "doctor"|"patient", "message": str, "time": "HH:MM"}`
- `_debug_log` — list of strings, one per step of the generation pipeline
- `_quick_feedback` — the latest one-liner from the Critic agent
- `_final_feedback` — list of `feedbackResponse` + `clinicalFeedbackResponse` JSON objects, accumulated when the session is paused
- `_is_patient_running` — bool, gates whether the chat is "live"
- `_conversation_id` — random 16-hex-char ID generated on each session start

Plus the orchestration helpers:

- `start_patient(patient, new=True)` — sets state, broadcasts `startPatient` and `patientInformation` (now including `fullVignette` for the side drawer), broadcasts `generationStop` success
- `stop_patient()` — flips the running flag
- `reset_patient()` — wipes everything (used when a new generation starts)

**Talking point:** this is module-level global state. Known design weakness — flagged in the original README's "Future Work". A real production version would wrap this in a `Session` class keyed by conversation ID.

#### `conversion_tables.py` — three lookup dictionaries

1. `diseases` — `{"acute pancreatitis": [[], 7], "chronic obstructive pulmonary disease": [[], 7.5], …}`. Each value is `[list_of_EBM_filenames, baseline_difficulty_1_to_10]`. EBM lists are empty in the current build (the generator falls back to general medical knowledge).
2. `neuroticism_score_conversion_table` — for each Big Five dimension (neuroticism, extraversion, openness, agreeableness, conscientiousness) and each integer score 0–5, a sentence describing how that score manifests in patient behavior. Used by `translate_score()` to turn the slider values into prompt-friendly English.
3. `furhat_faces_list` and `furhat_elevenlabs_voices_list` — multi-line strings that catalog every available Furhat avatar face and ElevenLabs voice. Fed to the Generator's step 7 so the LLM can pick a matching avatar.

#### `predefined_patients.py` — three hard-coded patients

`mapping[1]` = Eleanor Vance (acute simple cystitis), `mapping[2]` = Cassian Bellwether, `mapping[3]` = Marcus Williams (norovirus). Each is a fully-formed `Patient` instance with a long, hand-authored vignette. Useful for repeatable demos and for testing without spending tokens on generation.

#### `utils.py` — backwards-compatibility facade (50 lines)

After the refactor, `utils.py` is a thin re-exporter. It does:

```python
from llm.clients import client, cerebras_client, groq_client, model_for, ...
from agents.generator import generate_patient
from agents.vsp import generate_patient_response, post_process
from agents.critic import ask_quick_feedback, final_feedback, generate_hint
from agents.predefined import launch_predefined_patient
from agents.lifecycle import stop_patient, save_patient_artifact
```

So any existing call site that does `import utils; utils.generate_patient(...)` keeps working unchanged. The module is documented as a facade — implementation lives in `agents/` and `llm/`.

#### `minimal_generate_client.py` — CLI test harness

Standalone script. Connects to `ws_server.py` as a `dashboard` role, fires either a `generatePatient` or `launchPredefinedPatient` action, and prints every server response to stdout. Useful for verifying the Generator works without booting the NiceGUI dashboard. Has a `--debug-only` flag that prints just the generation log.

#### `prompts/` package — every LLM prompt template

After the refactor, this is a package (folder with `__init__.py`) instead of one 879-line file.

- **`prompts/__init__.py`** — re-exports every public template name from the submodules so `import prompts; prompts.vignette_template` keeps working unchanged.

- **`prompts/generation.py`** — the Generator agent's prompts:
  - `vignette_template` — a multi-section Markdown template (Basic patient info, Chief complaint, History of present illness using OPQRST, Past medical history, Current medications, Family history, Social history, Allergies, etc.). The LLM fills this in.
  - `generate_prompt_1_part1a` / `1_part1b` / `1_part2` — the disease-difficulty preamble.
  - `generate_prompt_2` — "fill in this vignette template at difficulty X."
  - `generate_prompt_3` — "scan the vignette for inconsistencies."
  - `generate_prompt_4` — "reason about post-process changes."
  - `generate_prompt_5` — "rewrite with the corrections."
  - `generate_prompt_6` — "pick a face and voice from these catalogs."

- **`prompts/vsp.py`** — the Virtual Simulated Patient's prompts:
  - `conversation_new_firstmessage` — used for the patient's very first greeting (when `len(history) == 0`).
  - `conversation_new_preprocessing` — the routing prompt sent to the preprocessing model. Asks the model to classify the doctor's last utterance into one of 6 cases and (for case 6) emit a database query.
  - `conversation_new_1` … `conversation_new_6` — the system prompt to use when each case fires.
  - `conversation_system_prompt` — fallback default.

- **`prompts/feedback.py`** — the Critic's prompts and rubrics:
  - `quick_feedback_prompt` — the one-liner per-turn coaching prompt.
  - `final_feedback_system_prompt` — the system prompt for the per-MIRS-criterion scoring.
  - `final_feedback_criteria` — a Python list of `{"title": str, "content": str}` dicts, one per MIRS criterion. **This is the actual MIRS rubric**, encoded in the codebase. Each entry's `content` is the criterion's instruction text given to the model.
  - `final_feedback_diagnostic` — the system prompt for the 7-criterion clinical evaluation.

- **`prompts/post_processing.py`** — the patient-reply filter prompts. Run as a second LLM pass after the VSP generates its raw answer. Strips doctor-vocabulary, removes diagnostic guesses, tightens to fit the patient's Big Five profile, removes anything the patient couldn't plausibly know.

- **`prompts/hint.py`** — the on-demand coaching prompt. Carefully engineered to refuse to name the diagnosis and to start every suggestion with an action verb (Ask…, Explore…, Consider…).

#### `llm/` package — provider wiring + RAG bootstrap + parsers

- **`llm/clients.py`** — the **single source of truth** for which LLM provider you talk to. At import time, depending on `config.PIPELINE_MODE`:

  - `groq-only` → `client = OpenAI(base_url="https://api.groq.com/openai/v1/", api_key=GROQ_API_KEY)`. `cerebras_client = groq_client = client` (aliases).
  - `openai-only` → `client = OpenAI(api_key=OPENAI_API_KEY)`. `cerebras_client = groq_client = client`.
  - `full` → three real clients pointed at three real providers.

  Then exposes:
  - `model_for(stage)` — given a stage name (`"vignette"`, `"preprocessing"`, `"answergeneration"`, `"postprocessing"`, `"quick_feedback"`, `"full_feedback"`), returns the right model name. In groq-only mode it returns `vignette_generation_groq_model` for everything; in openai-only mode it picks per-stage names from `config`; in full mode it splits across providers.
  - `structured_response_format(schema_dict)` — returns OpenAI's strict `json_schema` response_format on OpenAI, or `json_object` on Groq (which doesn't support strict mode).

- **`llm/rag.py`** — **lazy** RAG bootstrap. Sets `medical_knowledge_tool = None` if `USE_RAG=0` and skips every heavy import. Only when `USE_RAG=1` does it import LlamaIndex, Pinecone, and HuggingFace embeddings, build the vector store, and create the `medical_knowledge_tool` query engine that the VSP's case-6 path consults.

- **`llm/parsers.py`** — three small helper functions:
  - `extract_markdown_or_fail(response)` — pull the first Markdown block out of a noisy LLM response. Used after vignette-generation steps where the model wraps the vignette in commentary.
  - `parse_face_voice_or_default(response)` — robust JSON parser for the `{"face": ..., "voice": ...}` reply at step 7. Strips ``` fences if present, falls back to regex extraction if `json.loads` fails.
  - `sanitize_filename(s)` — turns a disease name into a safe filename for the persisted patient artifact.

#### `agents/` package — three agents + lifecycle glue

- **`agents/generator.py`** — `generate_patient(...)`. The 8-step pipeline (detailed in section 7).
- **`agents/vsp.py`** — `generate_patient_response()` and `post_process(...)`. The dialogue agent (detailed in section 7).
- **`agents/critic.py`** — `ask_quick_feedback()`, `final_feedback()`, `generate_hint()`. The evaluation agent (detailed in section 7).
- **`agents/predefined.py`** — `launch_predefined_patient(nr)`. Loads patient #N from the mapping in `predefined_patients.py`, posts a single debug-log entry summarising the patient, calls `start_patient()`, and persists the artifact. **No LLM calls** — predefined patients skip the entire 8-step generation pipeline.
- **`agents/lifecycle.py`** — `stop_patient()` (pauses the conversation and broadcasts `stopPatient`) and `save_patient_artifact(patient, source)` (writes a timestamped Markdown file to `generated_patients/` with the metadata table + full vignette).

---

### 5.3 Dashboard — `client_dashboard/`

Tree:

```
client_dashboard/
├── main.py                  # NiceGUI entry point — page layout + injected JS
├── config.py                # WebSocket URL + retry delay
├── utils.py                 # WS consumer (receive loop) + senders
├── ui_utils.py              # Backwards-compat facade (60 lines)
└── ui/                      # UI components (the post-refactor split)
    ├── __init__.py          # re-exports
    ├── state.py             # all module-level mutable state
    ├── dialogs.py           # lazy modal dialogs
    ├── form.py              # sliders + Generate / Restart / predefined buttons
    ├── chat.py              # chat input + messages container
    ├── sidebar.py           # control buttons + furhat status + vignette drawer
    ├── feedback_view.py     # immediate feedback + final-feedback rows
    └── notifications.py     # progress + connection + show_hint
```

#### `main.py` — NiceGUI entry point

This file does three things:

1. **Build the page layout.** A sticky dark header (project name + avatar status), a flex row with two columns: left has the conversation log (flex-1 chat scroll, then chat input row, then patient control buttons, then immediate-feedback card capped at 130px); right has the scenario-settings card and the View-vignette button. Everything is wrapped in `100vh; overflow:hidden` so the page itself never scrolls — only the chat area does.

2. **Inject the JavaScript speech bridge.** A 100-line `<script>` block via `ui.add_body_html()` that defines:
   - `coworkSpeak(text)` — gated on `coworkTtsEnabled`; uses `SpeechSynthesisUtterance` with the system default voice.
   - `coworkSetAutoSubmit(bool)` — flips the auto-submit mode flag.
   - `coworkToggleMic()` — starts or stops `webkitSpeechRecognition`.
   - `buildRecognition()` — constructs a fresh `SpeechRecognition` object with `continuous=false` (push-to-talk only), `interimResults=true`, `lang='en-US'`. On result it streams the transcript into the input. On `onend` it auto-submits if the toggle is on and the stop wasn't manual.
   - `clickSend()` — programmatic click on the Send button (used by auto-submit).
   - `findChatInput()` — robustly locates the real `<input>` element inside Quasar's q-input wrapper by querying inside `#cowork-chat-input-wrap`.

3. **Register startup hooks.** `app.on_startup(utils.consumer)` boots the WebSocket consumer task; `app.on_startup(ui_utils.fresh_*_dialog)` lazily creates the modal dialogs.

#### `config.py`

Two lines: `WS_CONN = "ws://localhost:8085/"` and `RETRY_DELAY = 5`.

#### `utils.py` — WebSocket consumer + senders

Two halves:

**Senders.** Synchronous functions that push a JSON action over the WebSocket:
- `generate_patient(...)`, `launch_predefined_patient(nr)`, `send_doctor_message(text)`, `request_initial_patient_message()`, `request_hint()`, `stop_and_get_final_feedback()`, `resume_patient()`.
- `send_message(message_str)` is the underlying primitive that does `_websocket.send_str(message)`.

**Consumer.** `async def consumer():` is the long-running coroutine NiceGUI starts via `app.on_startup`. It:
1. Opens an `aiohttp` WebSocket connection to `config.WS_CONN`.
2. Sends `setRole role=dashboard`.
3. Replays a fixed sequence of state-query actions (`checkPatient`, `getHistory`, `getQuickFeedback`, `recallFinalFeedback`, `checkFurhatConnected`, `getDebugLog`, `getPatientInformation`, `getConversationId`) so the UI repopulates from the backend's current state on every (re)connect.
4. Enters an `async for message in websocket:` loop — for every server message, dispatches to the right `ui_utils.X` handler based on the `action` field.
5. On any error, sleeps `RETRY_DELAY` and reconnects.

This is the **only** module in the dashboard that touches the WebSocket. Everything else is UI.

#### `ui_utils.py` — backwards-compatibility facade (60 lines)

After the refactor this is a thin re-exporter that forwards every public symbol from `ui/`. Plus a module-level `__getattr__` that forwards reads to `ui.state` so `ui_utils.conversation_id` keeps working.

#### `ui/` package — the components

- **`ui/state.py`** — every module-level mutable variable lives here:
  - dialog references (`dialog_dialog`, `debug_dialog`, `patientinfo_dialog`, `vignette_drawer_dialog` and their content elements)
  - notifications (`generation_progress_notification`, `server_connection_notification`, `furhat_connection_notification`)
  - the messages container + scroll area
  - launch tracking (`last_form_values`, `last_launch_kind`, `last_predefined_nr`)
  - cached vignette text (`full_vignette_text`)
  - speech flags (`tts_enabled`, `auto_submit`)
  - `conversation_id`
  
  Other `ui/*` submodules read and write these via `from . import state` then `state.foo = ...`. This avoids the `global` keyword scattered everywhere.

- **`ui/dialogs.py`** — three `fresh_*_dialog()` functions:
  - `fresh_feedback_dialog()` — final-feedback modal with two tabs (MIRS conversation / clinical).
  - `fresh_debug_dialog()` — generation-log modal.
  - `fresh_patient_dialog()` — legacy patient-info modal (kept for backwards compat).
  
  Each is **lazy** — the underlying `ui.dialog()` is created only on first call (NiceGUI 2.x rule).

- **`ui/form.py`** — the patient-generation form (six sliders) plus the buttons:
  - `Generate patient` — calls `_do_generate()` which records `_last_launch_kind = "generated"` and calls `utils.generate_patient(...)`.
  - `Launch predef. patient` dropdown — three items, each calls `_do_predefined(N)` which records `_last_launch_kind = "predefined"` and calls `utils.launch_predefined_patient(N)`.
  - `Restart` button — appears only after the first launch; replays the last form values or the last predefined number.
  - `Generation log` button — opens the debug dialog.

- **`ui/chat.py`** — the conversation log + input row:
  - `messages()` — the `ui.scroll_area` that holds the chat. Set to `flex-1` so it fills the remaining vertical space.
  - `add_doctor_message(text, time)` and `add_patient_message(text, time)` — append a `ui.chat_message` bubble. The patient version also calls `ui.run_javascript("window.coworkSpeak(...)")` so TTS plays if enabled.
  - `chat_input()` — the input row with text box, mic button, hint button, Send button, plus the toggle row underneath ("Speak responses" + "Auto-submit after speaking").

- **`ui/sidebar.py`** — control widgets:
  - `patient_control_buttons()` — Pause / Feedback / Resume row.
  - `furhat_status(status)` — the avatar status icon in the header.
  - `vignette_drawer()` — builds the right-slide drawer (a `ui.dialog().props("position=right")` that overlays a 480-px panel).
  - `vignette_panel()` — the small "View patient vignette" button in the right column that opens the drawer.
  - `set_full_vignette(text)` — caches the text and refreshes the drawer's content.
  - Plus the old debug-log and patient-info button wrappers.

- **`ui/feedback_view.py`** — feedback display widgets:
  - `feedback(message)` — the inline immediate-feedback card under the chat.
  - `add_conversation_feedback_item(criterium, mark, i, message, evidence)` — appends a row to the MIRS tab. Includes a colour-coded score circle (red 1–2, yellow 3, green 4–5).
  - `add_clinical_feedback_item(fb)` — appends rows to the clinical tab, one per criterion.

- **`ui/notifications.py`** — progress + connection UI:
  - `_start_notification`, `progress_message`, `progress_step`, `progress_end` — the top-right ongoing notification driven by `generationStart` / `generationUpdate` / `generationStop` events.
  - `server_connection_lost_ui` / `server_connection_restored_ui` — bottom-left "connecting…" notification + UI reset.
  - `furhat_connection_lost_ui` / `furhat_connection_restored_ui` — same pattern for Furhat.
  - `show_hint(hint)` — top notification with the lightbulb prefix and a dismiss button.
  - `update_form_fields_running_patient()` — central refresh helper that updates the form, the control buttons, the chat input, and the side-panel buttons whenever patient state changes.

---

## 6. WebSocket protocol

The hub speaks one direction in JSON: every message has an `action` string and zero or more extra fields. **Both** clients send actions; the server broadcasts events back to **all** connected clients.

### Actions sent by the dashboard

| Action | Extra fields | Purpose |
|---|---|---|
| `setRole` | `role: "dashboard"` | First message — declares this client's role |
| `generatePatient` | `diseaseDifficulty`, `neuroticism`, `extraversion`, `openness`, `agreeableness`, `conscientiousness` (all 0–5 ints, except difficulty 1–10) | Triggers the 8-step Generator |
| `launchPredefinedPatient` | `patient_nr` (1–3) | Loads a hard-coded patient |
| `getPatientResponse` | (optional) `doctorResponse: str` | Asks for next patient utterance. With doctorResponse: also adds it to history first. Without: bootstraps the first patient turn |
| `stopAndGetFinalFeedback` | none | Pauses the session and triggers the Critic's final feedback |
| `resumePatient` | none | Un-pauses the same patient |
| `getHint` | none | Asks the Critic for a one-line next-step suggestion |
| `checkPatient`, `getHistory`, `getDebugLog`, `getPatientInformation`, `getQuickFeedback`, `recallFinalFeedback`, `getConversationId`, `checkFurhatConnected`, `getFurhatStatusUpdate` | varies | State-query / repopulation actions |

### Events broadcast by the server

| Action | Fields | Purpose |
|---|---|---|
| `startPatient` | `face`, `voice`, `new` | Patient is loaded; UI switches into chat mode |
| `stopPatient` | none | Session paused |
| `patientInformation` | `information`, `fullVignette` | Basic info for header + full vignette for the side drawer |
| `generationStart` | none | Generator pipeline started |
| `generationUpdate` | `text`, `step`, `totalSteps` | Progress tick (step/8) |
| `generationStop` | `state` (`success` / `error` / `warning`), `text` | Pipeline ended |
| `updateDebugLog` | `debugLog: str` | One step's prompt or answer |
| `doctorResponse` | `response`, `time` | Echo of a doctor utterance |
| `patientGeneratedResponse` | `response`, `time` | A patient reply |
| `quickFeedbackResponse` | `response: str` | The one-liner under the chat |
| `feedbackResponse` | `i`, `criterium`, `mark`, `explanation`, `evidence` | One MIRS-criterion row |
| `clinicalFeedbackResponse` | `feedback: [{criterium, feedback}, ...]` | The 7-criterion clinical evaluation, all in one event |
| `hintResponse` | `hint: str` | The lightbulb's reply |
| `conversationId` | `conversationId: str` | Random 16-hex ID |
| `furhatStatusUpdate` | `status: str` | Avatar status icon |
| `furhatDisconnected` | none | A Furhat client just left |
| `checkFurhatConnectedResponse`, `checkPatientResponse` | varies | Replies to the matching state queries |

### Roles

| Role | Set by | Behavior |
|---|---|---|
| `dashboard` | The browser dashboard | Receives every event |
| `furhat` | A Furhat skill (optional) | Same as dashboard, plus the backend will auto-`startPatient` for it on connect if a session is already running |

---

## 7. The three agents in depth

### The Generator agent (`agents/generator.py`)

`generate_patient(disease_difficulty, neuroticism, extraversion, openness, agreeableness, conscientiousness)` runs an **eight-step prompt chain** on the configured "vignette" model. Each step appends both its prompt and its answer to the debug log so educators can audit the chain.

| Step | What happens | What the dashboard sees |
|---|---|---|
| 1 | Pick a disease at random from `conversion_tables.diseases`. Log `"1. Picked the disease: X with difficulty Y/10."` | `generationUpdate` "Picking a disease…" |
| 2 | Build the EBM-context prompt (or no-EBM fallback if no documents are attached) and ask the model to reason about adapting the disease to the requested difficulty | "Reasoning about changing difficulty to X/10" |
| 3 | Ask the model to fill in `vignette_template` at the target difficulty. Extract the resulting Markdown block via `extract_markdown_or_fail` | "Generating the first version of the patient…" |
| 4 | Ask the model to scan the draft vignette for inconsistencies | "Scanning the generated patient's parameters…" |
| 5 | Ask the model to *plan* what to change | "Reasoning about post-process changes…" |
| 6 | Ask the model to actually rewrite the vignette with the corrections. Extract Markdown | "Generating the final version of the patient…" |
| 7 | Ask the model to pick a face from `furhat_faces_list` and a voice from `furhat_elevenlabs_voices_list`. Parse JSON via `parse_face_voice_or_default` | "Choosing an avatar…" |
| 8 | Construct the `Patient` object with the markdown vignette + face + voice + 5 personality strings (translated from int 0–5 to text via `conversion_tables.translate_score`). Call `start_patient()`. Save artifact to `generated_patients/<ts>_<disease>.md` | "Sending generated details to the robot head…", then `startPatient`, then `generationStop success` |

**Talking points:**
- Why eight steps and not one big prompt? Because each step keeps the context window small, lets you tune each step independently, and produces an auditable trail in the debug log.
- Why pick a random disease and *then* adapt difficulty? Because forcing a specific disease is more brittle than letting the model pick from the catalog and then dialing it. The disease catalog itself is curated.

### The Virtual Simulated Patient agent (`agents/vsp.py`)

`generate_patient_response()` is called after every doctor turn. Two paths:

**Path A: first turn (history is empty).** Use `conversation_new_firstmessage` directly — the patient greets the doctor in 5 words or less, in their personality.

**Path B: subsequent turns.** Run a **routing pre-processor** that classifies the situation into one of six cases:

| Case | Meaning | System prompt selected |
|---|---|---|
| 1 | Doctor's last utterance might try to throw the patient off — be cautious | `conversation_new_1` (with a `WARNING:` decoration around the last user turn) |
| 2 | Routine clinical question | `conversation_new_2` |
| 3 | Non-clinical small talk | `conversation_new_3` (this is the only one that excludes the vignette to keep it light) |
| 4 | Empathy / emotional moment | `conversation_new_4` |
| 5 | Test / exam / procedure question | `conversation_new_5` |
| 6 | Clinical knowledge needed (RAG path) | `conversation_new_6` with `medical_information` injected from the Pinecone query — but **only if `USE_RAG=1`**, otherwise fall back to the default `conversation_system_prompt` |

After generating the raw answer on the configured "answergeneration" model, the answer goes through `post_process()` — a **second LLM pass** on the configured "postprocessing" model (always OpenAI-compatible) that:

- strips any doctor vocabulary the patient wouldn't use
- removes diagnostic guesses
- removes anything the patient couldn't plausibly know (e.g., specific lab values they were never told)
- tightens the tone to match the patient's Big Five profile
- enforces "patient says only their words, no actions or thoughts in asterisks/parens"

The post-processed answer is then added to `_conversation_history` and broadcast as `patientGeneratedResponse`.

**Talking point:** the routing + post-processing combo is what makes Quner robust against persona drift and knowledge leakage. A naive "you are a 45-year-old patient" prompt fails on both counts within a few turns.

### The Critic agent (`agents/critic.py`)

Three functions, three triggers:

**`ask_quick_feedback()`** — runs after every doctor turn (called immediately after `generate_patient_response()` finishes). Takes the conversation history, formats it with the doctor's last utterance highlighted, sends it to the "quick_feedback" model with `quick_feedback_prompt`. Result: a few-words coaching tip that gets broadcast as `quickFeedbackResponse` and shown under the chat.

**`final_feedback()`** — runs on `stopAndGetFinalFeedback`. Two sub-evaluations:

- *Clinical* — one LLM call. Takes the vignette + dialog + EBM corpus (or fallback), asks for seven feedback strings (diagnosis, treatment_planning, follow_up_and_monitoring, adherence_to_guidelines, risk_assessment, test_and_investigation_ordering, preventive_care). Uses `structured_response_format(clinical_schema)` so the output is strict JSON. Broadcast as `clinicalFeedbackResponse`.

- *Communication* — one LLM call **per MIRS criterion** (so ~25 calls). Each call uses the same conversation as system prompt but a different criterion's instruction text as the user prompt. Returns `{mark, explanation, evidence}`. Each result is broadcast as `feedbackResponse` with the criterion index `i`, so the dashboard can render them one row at a time as they arrive.

**`generate_hint()`** — runs on `getHint`. Takes the vignette + current conversation, sends to the "quick_feedback" model with `hint_prompt`. The prompt is engineered to refuse to name the diagnosis, refuse to disclose anything the patient hasn't volunteered, and start the suggestion with an action verb. Result is broadcast as `hintResponse`.

**Talking point:** the per-MIRS-criterion design is intentional. A single LLM call asked to score 25 criteria at once tends to blur its reasoning. Splitting into 25 short calls keeps each evaluation tight and gives you parallel-friendly broadcasts.

---

## 8. Pipeline modes (OpenAI / Groq / Full)

A single `PIPELINE_MODE` variable drives all of this:

### `openai-only` (default, recommended for demos)

- All LLM calls go to OpenAI.
- `gpt-4o-mini` is used for *everything* (vignette, preprocessing, answer generation, post-processing, both feedback paths, hints).
- Strict `json_schema` response format used for feedback.
- RAG is **forced off** even if `USE_RAG=1`.
- Cost: ~$0.02 per typical session.
- Latency: ~2–5 s per turn.

### `groq-only` (free tier, for cost-free demos)

- All LLM calls go to Groq's OpenAI-compatible endpoint.
- `llama-3.3-70b-versatile` for everything.
- Falls back to `json_object` mode (Groq doesn't support strict schemas) — prompts get a "return only this JSON shape" instruction appended.
- Daily token cap on the free tier (~100k tokens/day).
- RAG forced off.

### `full` (paper-faithful)

- **Preprocessing** → Cerebras (`llama-4-scout-17b-16e-instruct`) — fast classifier.
- **Vignette + answer generation** → Groq (`llama-3.3-70b-versatile`).
- **Post-processing + feedback + hint** → OpenAI (`gpt-4o-mini`).
- RAG can be enabled.
- Best quality / cost tradeoff but requires keys for all three providers.

**The key abstraction**: every agent calls `client.chat.completions.create(model=model_for(stage), ...)`. The `client` reference and the `model_for()` function are configured **once** in `llm/clients.py` based on `PIPELINE_MODE`. No agent ever asks "what mode am I in" — they just get the right client and model from the dispatcher.

---

## 9. Three runtime stories (data flow walkthroughs)

### Story A: "The student clicks Generate patient with difficulty=7, neuroticism=2"

1. Dashboard `_do_generate()` records the launch as "generated" and sends `{"action": "generatePatient", "diseaseDifficulty": 7, ...}`.
2. `ws_server.py` receives, calls `await globals_conversation_logic.reset_patient()` (wipes any previous state), then `await utils.generate_patient(7, 2, 4, 4, 4, 4)`.
3. The Generator broadcasts `generationStart`, then runs the 8 steps (each step makes a `groq_client.chat.completions.create` call — but in openai-only mode `groq_client` is just an alias for the OpenAI client).
4. Each step broadcasts a `generationUpdate` (the dashboard's progress notification ticks: 1/8, 2/8, …) and an `updateDebugLog` (the Generation log dialog gets a new entry).
5. After step 8, the `Patient` object is constructed and `start_patient()` is called.
6. `start_patient` broadcasts:
   - `startPatient {face, voice, new: true}` → dashboard sets `is_patient_running=True`, clears messages, and sends a follow-up `getPatientResponse` (without doctorResponse) to bootstrap the first patient utterance.
   - `patientInformation {information, fullVignette}` → dashboard caches the full vignette in `state.full_vignette_text`, ready for the side drawer.
   - `generationStop success` → dashboard turns the progress notification green and dismisses it.
7. Backend handles the bootstrap `getPatientResponse`. The VSP agent sees `len(history) == 0` and uses `conversation_new_firstmessage`. The patient says "Hello, doctor." or similar in 5 words.
8. Result is broadcast as `patientGeneratedResponse`. The dashboard adds the bubble. If TTS is on, `coworkSpeak()` is fired.

### Story B: "The student types 'What brings you in today?' and clicks Send"

1. Dashboard's `_send()` calls `utils.send_doctor_message("What brings you in today?")`.
2. Sender pushes `{"action": "getPatientResponse", "doctorResponse": "What brings you in today?"}`.
3. `ws_server.py` adds the doctor message to history, broadcasts `doctorResponse {response, time}` (so the dashboard echoes it). Then runs `await utils.generate_patient_response()`.
4. The VSP agent sees `len(history) > 0`, runs the preprocessing call on `cerebras_client` (which is OpenAI in openai-only mode). Result: routing case = 2 (routine clinical question).
5. Builds `conversation_new_2` system prompt with the vignette and personality strings. Sends the system prompt + the conversation history (mapped to alternating user/assistant turns) to `groq_client` (still OpenAI in openai-only).
6. Raw answer comes back. Runs `post_process(was_doctor_utterance=True, answer, history, patient)` — a second OpenAI call that strips doctor-vocabulary etc.
7. Post-processed answer added to history; `patientGeneratedResponse` broadcast.
8. After the response, `await utils.ask_quick_feedback()` runs — yet another LLM call that produces the one-line tip under the chat. Broadcast as `quickFeedbackResponse`.

### Story C: "The student clicks Pause"

1. Dashboard sends `{"action": "stopAndGetFinalFeedback"}`.
2. Backend calls `await utils.stop_patient()` (sets `is_patient_running=False`, broadcasts `stopPatient`).
3. Calls `await utils.final_feedback()`.
4. Final feedback first does the *clinical* evaluation: builds the prompt with vignette + dialog + (optional) EBM corpus, calls `client.chat.completions.create(...)` with `structured_response_format(clinical_schema)`. Parses the JSON, builds `clinicalFeedbackResponse {feedback: [...]}`, broadcasts.
5. Then loops over `prompts.final_feedback_criteria` (the MIRS list, ~25 entries). For each one, calls `_eval_criterion(criterium["content"])`. Each call returns `{mark, explanation, evidence}`. Each result is broadcast as `feedbackResponse {i, criterium, mark, explanation, evidence}`.
6. Dashboard renders each event as a row in the feedback dialog as it arrives.
7. After about 30–60 s, the dialog is fully populated. The dashboard's "Feedback" button (which appeared when `stopPatient` arrived) opens it on demand.

---

## 10. Where to extend Quner

| You want to… | Touch this |
|---|---|
| Add a 4th pipeline mode (e.g., Anthropic) | `config.py` (add a flag), `llm/clients.py` (add the branch), maybe a new model-name override |
| Add a new agent (e.g., a "Devil's advocate" critic) | New file in `agents/`, register a new action in `ws_server.py`, add a button in `ui/chat.py` or `ui/sidebar.py` |
| Add a new prompt | New file in `prompts/`, re-export it from `prompts/__init__.py` |
| Add a new disease | One line in `conversion_tables.py::diseases` |
| Add a 4th predefined patient | `predefined_patients.py` — add a `Patient(...)`, then `mapping[4] = it`, then add a dropdown item in `ui/form.py` |
| Add EBM grounding | Drop `.md` files in `EBM_path`, run `create_rag_storage.py`, set `USE_RAG=1` |
| Persist transcripts | `agents/lifecycle.py` already has the shape; extend `save_patient_artifact` or write a sibling function that dumps the conversation on `stop_patient` |
| Replace NiceGUI with React | The dashboard talks to the backend over WebSocket, so writing a new client in any framework is a self-contained job — no backend changes |

---

## 11. Presentation talking points & likely questions

### Pitch slides

- **Problem**: SP actors are scarce and expensive; existing AI patients drift and give weak feedback.
- **Solution**: a multi-agent framework where each agent owns one capability, with browser-native multimodal I/O.
- **Three agents**: Generator (programmatic vignettes), VSP (routed + post-processed dialogue), Critic (per-MIRS-criterion + 7-criterion clinical feedback).
- **Architecture win**: pluggable LLM backends — switch from $5 OpenAI deployment to free-tier Groq with one env-var change.
- **Pedagogical win**: every score has transcript evidence and a textual explanation.
- **Cost**: ~$0.02 per session on `gpt-4o-mini`, free on Groq.

### Likely questions and short answers

| Question | Answer |
|---|---|
| *"Why three agents and not one big prompt?"* | Smaller context per call, independent tuning, narrower failure surface, easier auditability. The same prompt asked to do everything tends to blur its reasoning. |
| *"How do you stop the patient from breaking character?"* | Routing pre-processor classifies the doctor's last turn into one of six cases, each with its own system prompt. Plus a separate post-processing LLM pass that strips doctor-vocabulary and removes anything the patient couldn't plausibly know. |
| *"What if the LLM hallucinates a symptom?"* | Two mitigations. (1) The vignette is the source of truth — the system prompt embeds it on every turn. (2) Optional RAG layer grounds case-6 answers in an EBM corpus when enabled. |
| *"How is your feedback better than ChatGPT giving feedback?"* | We go through MIRS criterion-by-criterion, one LLM call per criterion, with a structured JSON output that gives `{mark, explanation, evidence}`. The student gets a 1–5 score plus the exact transcript lines that justify it, not a vague free-text summary. |
| *"What about Web Speech API support?"* | Push-to-talk STT works in Chrome, Edge, and Safari. Firefox doesn't ship `webkitSpeechRecognition`, so it falls back to typing. TTS works everywhere. Both are on-device, no extra service needed. |
| *"Can you swap LLM providers?"* | Yes — one env var. The whole codebase routes through a single `model_for(stage)` dispatcher in `llm/clients.py`. Adding a fourth provider is one branch in that function. |
| *"What's the Furhat thing?"* | A robotic head from Furhat Robotics. The original prototype was tightly coupled to it. Major II decoupled the dashboard from Furhat — text chat works without any robot. If a Furhat client connects with `role=furhat` it gets the same broadcast events and can render speech + facial animation, but it's purely optional. |
| *"Is the data secure?"* | All vignettes are synthetic (no real PHI). Secrets live in `.env` (gitignored). Transport is local-only WebSocket; for production you'd put TLS in front. We don't store transcripts to disk by default — only the generated vignette is persisted. |
| *"How big is the codebase?"* | About 4,500 lines of Python, every file under 250 lines. Backend has 23 Python files; dashboard has 13. The original prototype had 3 files over 600 lines each — Major II's refactor was a major code-quality win. |
| *"Why pin NiceGUI to <2.0?"* | NiceGUI 2.x changed the page lifecycle so module-level UI element creation no longer works. The original codebase was written for 1.x, so we pinned `nicegui<2.0` and made the dialog setup lazy — that way the dashboard works on either generation. |
| *"How does auto-submit work?"* | The mic button starts `webkitSpeechRecognition` in push-to-talk mode. The recognition fires `onend` either when the user clicks the mic again (manual stop, suppressed) or when there's a long enough silence (natural end). On natural end, if `coworkAutoSubmit` is true and the input has text, JS programmatically clicks the Send button after a 150 ms delay. |
| *"Why is the page locked to 100vh?"* | UX. With a normal flowing layout, the immediate-feedback card gets pushed below the fold and you need to scroll to see it during a session. Locking the page to viewport height means only the chat area scrolls — the feedback card is always visible. |

### Demo script (15 minutes)

1. **Boot** — `python ws_server.py` in one terminal, `python main.py` in another. Open `http://localhost:8501`. (1 min)
2. **Header tour** — point out the project name, the avatar status icon. (30 s)
3. **Pick a predefined patient** — Eleanor Vance. Show the patient's first greeting appearing in the chat. (1 min)
4. **Conversation** — type a few questions. Show the patient replies, the immediate-feedback card updating. (3 min)
5. **Hint** — click the lightbulb. Show the notification appearing. (1 min)
6. **Right-slide drawer** — click "View patient vignette." Show the slide-in panel. (1 min)
7. **Speech** — toggle "Speak responses" on. Type another question. The patient's reply is read aloud. (1 min)
8. **STT** — click the mic, say a question, watch the transcript stream into the input. Toggle auto-submit on, do it again — watch it auto-fire. (2 min)
9. **Pause** — click Pause. Click "Feedback" when it appears. Open the modal. Show the MIRS tab and the Clinical tab. (3 min)
10. **Generation log** — click "Generation log" (it's there even after a predefined launch). Walk through one or two of the generation steps. (1 min)
11. **Restart** — click "Restart predef. #1" to demo the same-settings replay. (30 s)
12. **Generated patient** — click "Generate patient" with custom slider values. Watch the progress notification tick through 8 steps. New patient. (1 min)
13. **`.env` and pipeline modes** — show the `.env`, switch `PIPELINE_MODE=groq-only`, restart backend. Same demo, different provider. (45 s)

---

## 12. Glossary

| Term | Meaning |
|---|---|
| **Agent** | A single-responsibility module with its own prompts and LLM-call patterns. Quner has three: Generator, VSP, Critic |
| **Big Five** | Personality model with five dimensions: Neuroticism, Extraversion, Openness, Agreeableness, Conscientiousness. Quner exposes all five as 0–5 sliders |
| **Cerebras** | LLM inference provider known for very-low-latency inference. Used in Quner's full mode for VSP preprocessing |
| **EBM** | Evidence-Based Medicine. A canonical medical-knowledge corpus that grounds the patient's responses (only used if RAG is enabled) |
| **Facade module** | A thin file that re-exports symbols from a sub-package, used for backwards compatibility. `utils.py`, `prompts/__init__.py`, `ui_utils.py`, `ui/__init__.py` are all facades |
| **Furhat** | A robotic head from Furhat Robotics. Optional client for Quner — drives ElevenLabs speech and facial animation if connected |
| **Generator agent** | The agent that builds vignettes via the 8-step prompt pipeline |
| **Groq** | LLM inference provider with an OpenAI-compatible API. Free tier with daily token cap |
| **MIRS** | Master Interview Rating Scale. The standard rubric for medical-interview communication assessment. Quner's Critic produces a per-criterion MIRS score with transcript evidence |
| **NiceGUI** | Python web-UI framework (pinned to <2.0 in Quner). Dashboard is built with it |
| **OSCE** | Objective Structured Clinical Examination. The standardized assessment format Quner is designed to support practice for |
| **Pinecone** | Hosted vector database used for the optional RAG layer |
| **Pipeline mode** | One of `openai-only`, `groq-only`, or `full`. Determines which LLM provider each stage of the system talks to |
| **Quasar** | Vue-based UI framework that NiceGUI uses under the hood. The chat input element is a `q-input` (Quasar's input component) |
| **RAG** | Retrieval-Augmented Generation. Couples an LLM with a vector index so factual answers come from retrieved documents, not the model's parametric memory |
| **Standardized Patient (SP)** | A human actor trained to portray a specific patient case. The scarce resource Quner is designed to multiply |
| **Vignette** | The structured Markdown document that defines a patient case (chief complaint, history of present illness, past medical history, etc.) |
| **VSP agent** | Virtual Simulated Patient agent. The agent that holds the dialogue with the doctor in character |
| **Web Speech API** | The browser's native `SpeechRecognition` (STT) and `SpeechSynthesis` (TTS) APIs. Quner uses both with no server-side audio pipeline |
| **WebSocket** | The single bidirectional channel between the dashboard and the backend. Carries JSON action/event messages on port 8085 |

---

## 13. Quick command cheat sheet

```bash
# Boot (in two terminals)
cd central_backend_server && python ws_server.py
cd client_dashboard && python main.py

# Then open http://localhost:8501

# Switch to Groq
sed -i '' 's/^PIPELINE_MODE=.*/PIPELINE_MODE=groq-only/' .env
# (restart the backend)

# Kill leftover processes
lsof -ti:8085 | xargs kill -9
lsof -ti:8501 | xargs kill -9

# Run only the Generator from the CLI (no dashboard)
cd central_backend_server
python ws_server.py &
python minimal_generate_client.py --difficulty 7 --neuroticism 2

# Re-build the RAG index (only if you have an EBM corpus)
python create_rag_storage.py
```

---

*Last updated for Major Project II final submission (Quner v2 — modular architecture, pluggable LLM backends, browser multimodal I/O).*
