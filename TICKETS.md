# Nanobot Development Tickets

A step-by-step breakdown of the nanobot codebase into reviewable pull requests.
Each PR is sized for human review (~200-600 lines of production code, with occasional larger single-file PRs for self-contained features like channel implementations).

**Total: 33 PRs** | **Total codebase: ~14,000 lines Python + Node.js bridge**

---

## Phase 1: Foundation (PRs 1-5)

These PRs establish the project skeleton, configuration, and LLM provider infrastructure. Nothing runs yet, but all foundational abstractions are in place.

---

### TICKET-001: Project Scaffolding & Core Infrastructure

**PR Title:** `feat: project scaffolding, utils, message bus, and path resolution`
**Estimated Size:** ~350 lines | **Depends on:** None

**Goal:** Create the project skeleton so that `pip install -e .` works, the package is importable, and the internal message bus is ready.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `pyproject.toml` | ~60 | Package metadata, all dependencies (Python 3.11+), ruff config, pytest config |
| `nanobot/__init__.py` | ~40 | Package version (`__version__`), ASCII logo, `__all__` exports |
| `nanobot/__main__.py` | ~10 | Entry point: `from nanobot.cli.commands import app; app()` |
| `nanobot/utils/__init__.py` | ~5 | Module init |
| `nanobot/utils/helpers.py` | ~200 | Utility functions |
| `nanobot/config/__init__.py` | ~30 | Config module with `get_config()` singleton |
| `nanobot/config/paths.py` | ~55 | Path resolution for workspace, config, sessions |
| `nanobot/bus/__init__.py` | ~6 | Module init |
| `nanobot/bus/events.py` | ~38 | `InboundMessage` and `OutboundMessage` dataclasses |
| `nanobot/bus/queue.py` | ~44 | `MessageBus` class with async queues |

**Detailed instructions:**

1. **`pyproject.toml`**: Use `[build-system]` with hatchling. Define `[project]` with name="nanobot", version from `nanobot/__init__.py`, requires-python=">=3.11". List ALL dependencies (typer, litellm, pydantic, pydantic-settings, websockets, httpx, ddgs, loguru, croniter, mcp, json-repair, prompt_toolkit, rich, python-dotenv, etc.). Add `[project.scripts]` entry: `nanobot = "nanobot.cli.commands:app"`. Configure ruff with line-length=100.

2. **`nanobot/utils/helpers.py`**: Implement these utilities:
   - `ensure_dir(path)` - create directory if not exists
   - `safe_filename(name)` - sanitize strings for filenames
   - `estimate_tokens(text)` - rough token count (len/4 heuristic)
   - `estimate_messages_tokens(messages)` - sum token estimates for message list
   - `truncate_tool_result(text, max_tokens)` - truncate long tool outputs
   - `is_image_path(path)` - check if file is an image by extension
   - `format_timestamp()` - ISO timestamp helper
   - `merge_dicts(base, override)` - deep merge for configs
   - Platform detection helpers (is_windows, get_shell)

3. **`nanobot/config/paths.py`**: Implement `ConfigPaths` class:
   - `base_dir` → `~/.nanobot` (or `NANOBOT_HOME` env var)
   - `config_file` → `base_dir/config.yaml`
   - `workspace_dir` → configurable, default `base_dir/workspace`
   - `sessions_dir` → `workspace_dir/sessions`
   - `runtime_dir` → `base_dir/runtime`
   - `media_dir` → `runtime_dir/media`
   - Support multi-instance via `NANOBOT_INSTANCE` env var (appends suffix to base_dir)

4. **`nanobot/bus/events.py`**: Define dataclasses:
   - `InboundMessage`: fields `channel` (str), `sender_id` (str), `chat_id` (str), `content` (str), `media` (list[dict] | None), `metadata` (dict), `session_key_override` (str | None)
   - `OutboundMessage`: fields `channel` (str), `chat_id` (str), `content` (str), `reply_to` (str | None), `media` (list[dict] | None), `metadata` (dict)

5. **`nanobot/bus/queue.py`**: Implement `MessageBus`:
   - Two `asyncio.Queue` instances: `inbound` and `outbound`
   - `publish_inbound(msg)` / `consume_inbound()` async methods
   - `publish_outbound(msg)` / `consume_outbound()` async methods
   - Singleton pattern via module-level instance

**Acceptance criteria:**
- [ ] `pip install -e .` succeeds
- [ ] `python -c "import nanobot; print(nanobot.__version__)"` works
- [ ] `ConfigPaths` resolves all directories correctly
- [ ] `MessageBus` can publish and consume messages in an async test
- [ ] All utility functions have basic tests

---

### TICKET-002: Configuration Schema & Loader

**PR Title:** `feat: Pydantic configuration schema and YAML loader`
**Estimated Size:** ~540 lines | **Depends on:** TICKET-001

**Goal:** Define the entire configuration model using Pydantic v2 and implement YAML loading/saving, so the rest of the system has typed config access.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/config/schema.py` | ~463 | All Pydantic config models |
| `nanobot/config/loader.py` | ~75 | YAML load/save/create-default logic |
| `tests/test_config_paths.py` | ~50 | Path resolution tests |

**Detailed instructions:**

1. **`nanobot/config/schema.py`**: Define these Pydantic `BaseModel` classes:

   - **`ProviderConfig`**: `name` (str), `api_key` (str, default ""), `base_url` (str | None), `model` (str, default ""), `api_version` (str | None), `extra_headers` (dict), `extra_params` (dict)
   - **`AgentConfig`**: `name` (str, default "nanobot"), `model` (str, default ""), `max_iterations` (int, default 40), `max_tokens` (int, default 65536), `temperature` (float | None), `prompt_cache` (bool, default True)
   - **`ToolsConfig`**: `shell` (ShellConfig with `timeout`, `allowed_commands`), `filesystem` (FilesystemConfig with `allowed_paths`, `max_file_size`), `web_search` (WebSearchConfig)
   - **`WebSearchConfig`**: `provider` (str, default "ddgs"), `api_key` (str | None), `base_url` (str | None), `proxy` (str | None)
   - **`GatewayConfig`**: `host` (str, default "0.0.0.0"), `port` (int, default 18790), `api_key` (str | None)

   For each channel, define a config model:
   - **`TelegramConfig`**: `enabled` (bool), `token` (str), `allow_from` (list[str]), `proxy` (str | None), `group_policy` (str, default "mention")
   - **`DiscordConfig`**: `enabled`, `token`, `allow_from`, `command_prefix`
   - **`SlackConfig`**: `enabled`, `app_token`, `bot_token`, `allow_from`
   - **`FeishuConfig`**: `enabled`, `app_id`, `app_secret`, `allow_from`, `encrypt_key`, `verification_token`
   - **`DingTalkConfig`**: `enabled`, `client_id`, `client_secret`, `allow_from`
   - **`MatrixConfig`**: `enabled`, `homeserver`, `user_id`, `password`/`access_token`, `allow_from`
   - **`EmailConfig`**: `enabled`, `imap_server`, `smtp_server`, `username`, `password`, `allow_from`, `poll_interval`
   - **`WecomConfig`**: `enabled`, `corp_id`, `agent_id`, `secret`, `allow_from`
   - **`QQConfig`**: `enabled`, `app_id`, `secret`, `allow_from`
   - **`WhatsAppConfig`**: `enabled`, `bridge_url`, `allow_from`
   - **`MochatConfig`**: `enabled`, `server_url`, `token`, `allow_from`

   - **`ChannelsConfig`**: Contains all channel configs as optional fields
   - **`NanobotConfig`** (root): `providers` (dict[str, ProviderConfig]), `agent` (AgentConfig), `channels` (ChannelsConfig), `tools` (ToolsConfig), `gateway` (GatewayConfig), `mcp_servers` (dict)

   Use `model_validator` for cross-field validation. Add `model_config = ConfigDict(extra="allow")` where needed for forward compatibility.

2. **`nanobot/config/loader.py`**: Implement:
   - `load_config(path) -> NanobotConfig` - read YAML, parse with Pydantic, handle missing file gracefully
   - `save_config(config, path)` - serialize to YAML, write atomically (write to .tmp then rename)
   - `create_default_config(path)` - generate minimal starter config with comments
   - Use `pyyaml` or config already in dependencies for YAML support

3. **Tests**: Verify config loads from YAML string, defaults are applied, validation errors are raised for invalid values, and path resolution works correctly.

**Acceptance criteria:**
- [ ] `NanobotConfig` can be instantiated with defaults
- [ ] YAML config file round-trips (load → save → load produces same result)
- [ ] Missing optional fields get proper defaults
- [ ] Invalid config values raise clear validation errors
- [ ] `create_default_config` generates a working starter config

---

### TICKET-003: LLM Provider Base & Response Types

**PR Title:** `feat: LLM provider abstract base class and response types`
**Estimated Size:** ~270 lines | **Depends on:** TICKET-001

**Goal:** Define the provider interface that all LLM backends must implement, including response types, tool call parsing, and retry logic.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/providers/__init__.py` | ~8 | Module init |
| `nanobot/providers/base.py` | ~270 | `LLMProvider` ABC, `LLMResponse`, `ToolCallRequest` |

**Detailed instructions:**

1. **`nanobot/providers/base.py`**: Define:

   - **`ToolCallRequest`** dataclass: `id` (str), `name` (str), `arguments` (dict). Include a `from_openai_format(tool_call)` classmethod that parses OpenAI-style tool call objects (handling JSON parsing with json-repair for malformed arguments).

   - **`LLMResponse`** dataclass: `content` (str | None), `tool_calls` (list[ToolCallRequest]), `usage` (dict with `prompt_tokens`, `completion_tokens`, `total_tokens`), `raw_response` (Any), `reasoning_content` (str | None), `thinking_blocks` (list | None), `model` (str | None).

   - **`LLMProvider`** abstract class:
     - `__init__(self, config: ProviderConfig)` - store config, set up auth
     - `abstract async chat(self, messages, tools, **kwargs) -> LLMResponse` - single LLM call
     - `async chat_with_retry(self, messages, tools, max_retries=3, **kwargs) -> LLMResponse` - retry wrapper that catches transient errors (HTTP 429, 500, 502, 503, 504, connection errors). Use exponential backoff with jitter. Log retries with loguru.
     - `get_default_model(self) -> str` - return default model name
     - `_parse_tool_calls(self, response) -> list[ToolCallRequest]` - helper to extract tool calls from various response formats
     - `_build_auth_headers(self) -> dict` - construct auth headers from config

   - Error handling: Define `ProviderError`, `RateLimitError`, `AuthenticationError` exceptions.

   - The retry logic should:
     - Retry on `RateLimitError` and transient HTTP errors
     - NOT retry on `AuthenticationError` or validation errors
     - Use delays: 1s, 2s, 4s (exponential backoff)
     - Log each retry attempt with the error message

**Acceptance criteria:**
- [ ] `LLMProvider` cannot be instantiated directly (abstract)
- [ ] `ToolCallRequest.from_openai_format()` parses standard tool calls
- [ ] `chat_with_retry` retries on transient errors and gives up after max_retries
- [ ] `LLMResponse` correctly stores all response metadata
- [ ] Custom exceptions are defined and used properly

---

### TICKET-004: Provider Registry & Auto-Detection

**PR Title:** `feat: provider registry with model-based auto-detection`
**Estimated Size:** ~520 lines | **Depends on:** TICKET-003

**Goal:** Build the registry that maps model names to providers and contains specs for all supported LLM backends (OpenAI, Anthropic, Google, DeepSeek, Mistral, etc.).

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/providers/registry.py` | ~522 | Provider registry, ProviderSpec definitions |
| `tests/test_provider_retry.py` | ~60 | Retry logic tests |

**Detailed instructions:**

1. **`nanobot/providers/registry.py`**: Implement:

   - **`ProviderSpec`** dataclass for each known provider:
     - `name` (str) - e.g., "openai", "anthropic"
     - `keywords` (list[str]) - model name prefixes/keywords for auto-detection (e.g., ["gpt-", "o1-", "o3-", "o4-"] for OpenAI)
     - `default_model` (str) - e.g., "gpt-4o" for OpenAI
     - `env_key` (str) - environment variable for API key (e.g., "OPENAI_API_KEY")
     - `base_url` (str | None) - default API endpoint
     - `supports_tools` (bool, default True)
     - `supports_vision` (bool, default True)
     - `max_tokens` (int | None)
     - `provider_class` (str) - dotted path to the provider implementation class

   - **Define ProviderSpecs** for all supported providers:
     - **OpenAI**: keywords=["gpt-", "o1-", "o3-", "o4-", "chatgpt-"], env_key="OPENAI_API_KEY"
     - **Anthropic**: keywords=["claude-"], env_key="ANTHROPIC_API_KEY"
     - **Google/Gemini**: keywords=["gemini-"], env_key="GEMINI_API_KEY"
     - **DeepSeek**: keywords=["deepseek"], env_key="DEEPSEEK_API_KEY"
     - **Mistral**: keywords=["mistral", "codestral", "pixtral"], env_key="MISTRAL_API_KEY"
     - **OpenRouter**: keywords=["openrouter/"], env_key="OPENROUTER_API_KEY"
     - **MiniMax**: keywords=["minimax/"], env_key="MINIMAX_API_KEY"
     - **Volcano Engine**: keywords=["volc/", "doubao"], env_key="VOLC_API_KEY"
     - **Groq**: keywords=["groq/"], env_key="GROQ_API_KEY"
     - **Together**: keywords=["together/"], env_key="TOGETHER_API_KEY"

   - **`ProviderRegistry`** class:
     - `_specs: dict[str, ProviderSpec]` - name → spec mapping
     - `register(spec: ProviderSpec)` - add a provider spec
     - `detect_provider(model: str) -> ProviderSpec | None` - scan keywords to find matching provider
     - `get_spec(name: str) -> ProviderSpec | None` - lookup by name
     - `create_provider(config: ProviderConfig, model: str) -> LLMProvider` - instantiate provider class based on auto-detection or explicit config
     - `list_providers() -> list[str]` - return all registered provider names

   - **Auto-detection logic**: Given a model string like "deepseek-chat", iterate through all specs and check if any keyword is a substring of the model name. First match wins. If no match, fall back to the provider specified in config, or raise an error.

   - **Provider instantiation**: Use `importlib` to dynamically import the provider class from the dotted path in `provider_class`. This avoids importing all providers at startup.

2. **Tests**: Test that auto-detection works for various model names, that unknown models raise clear errors, and that provider instantiation works.

**Acceptance criteria:**
- [ ] `detect_provider("gpt-4o")` returns OpenAI spec
- [ ] `detect_provider("claude-3-opus")` returns Anthropic spec
- [ ] `detect_provider("unknown-model")` returns None
- [ ] `create_provider()` instantiates the correct provider class
- [ ] All 10+ providers are registered with correct keywords

---

### TICKET-005: LiteLLM Provider & Audio Transcription

**PR Title:** `feat: LiteLLM provider implementation and Groq Whisper transcription`
**Estimated Size:** ~420 lines | **Depends on:** TICKET-003, TICKET-004

**Goal:** Implement the primary LLM provider using LiteLLM (covers OpenAI, Anthropic, Google, DeepSeek, Mistral, etc.) and add audio transcription via Groq Whisper.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/providers/litellm_provider.py` | ~353 | LiteLLM-based provider |
| `nanobot/providers/transcription.py` | ~64 | Groq Whisper audio transcription |

**Detailed instructions:**

1. **`nanobot/providers/litellm_provider.py`**: Implement `LiteLLMProvider(LLMProvider)`:

   - **`__init__`**: Accept `ProviderConfig` + optional `ProviderSpec`. Set litellm config:
     - `litellm.drop_params = True` (ignore unsupported params)
     - Set API keys from config or environment
     - Configure base_url if provided
     - Set up extra headers (for providers like OpenRouter that need them)

   - **`async chat()`**:
     - Build kwargs: `model`, `messages`, `tools` (if any), `temperature`, `max_tokens`
     - Handle provider-specific params:
       - **Anthropic**: Add `extra_headers` for prompt caching, add `thinking` param for extended thinking models
       - **Google**: Handle `safety_settings` to disable content filters
       - **DeepSeek**: Handle reasoning content in response
     - Call `await litellm.acompletion(**kwargs)`
     - Parse response into `LLMResponse`:
       - Extract `content` from `choices[0].message.content`
       - Extract `tool_calls` using `ToolCallRequest.from_openai_format()`
       - Extract `usage` from response
       - Handle `reasoning_content` (DeepSeek) and `thinking` blocks (Anthropic)
     - Handle litellm exceptions and map to provider errors

   - **Tool call handling**: Some providers return tool arguments as strings, others as dicts. Normalize to dict using `json_repair.loads()` for robustness.

   - **Anthropic-specific**: Handle `content` being a list of blocks (text blocks + thinking blocks). Extract thinking blocks separately. Handle `prompt_caching` by adding `cache_control` to system messages.

   - **Vision support**: When messages contain image data, format as multimodal content blocks.

2. **`nanobot/providers/transcription.py`**: Implement `transcribe_audio(file_path, api_key=None) -> str`:
   - Use Groq's Whisper API via httpx
   - Send audio file as multipart form data
   - Return transcribed text
   - Handle errors (file not found, API errors, unsupported format)
   - Support GROQ_API_KEY from environment

**Acceptance criteria:**
- [ ] LiteLLM provider can complete a chat with OpenAI models
- [ ] Tool calls are correctly parsed from response
- [ ] Anthropic-specific features (prompt caching, thinking) work
- [ ] Audio transcription returns text for valid audio files
- [ ] Provider errors are properly wrapped and logged

---

## Phase 2: Agent Engine (PRs 6-11)

These PRs build the agent's brain: tools, context assembly, the processing loop, session persistence, and memory.

---

### TICKET-006: Tool System Foundation

**PR Title:** `feat: tool base class, registry, and shell execution tool`
**Estimated Size:** ~430 lines | **Depends on:** TICKET-001

**Goal:** Create the tool abstraction layer with JSON Schema validation, a registry for tool discovery, and the first tool (shell execution).

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/agent/__init__.py` | ~8 | Module init |
| `nanobot/agent/tools/__init__.py` | ~6 | Module init |
| `nanobot/agent/tools/base.py` | ~181 | `Tool` ABC with schema validation |
| `nanobot/agent/tools/registry.py` | ~70 | `ToolRegistry` |
| `nanobot/agent/tools/shell.py` | ~179 | `ExecTool` for shell commands |
| `tests/test_tool_validation.py` | ~80 | Tool parameter validation tests |

**Detailed instructions:**

1. **`nanobot/agent/tools/base.py`**: Define:

   - **`Tool`** abstract base class:
     - `name: str` - tool name (e.g., "exec")
     - `description: str` - human-readable description
     - `parameters: dict` - JSON Schema for parameters
     - `abstract async execute(self, **kwargs) -> str` - run the tool
     - `get_definition(self) -> dict` - return OpenAI-compatible function schema: `{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}`
     - `validate_and_cast(self, params: dict) -> dict` - validate params against JSON Schema, cast types (e.g., string "true" → bool True, string "42" → int 42). This is critical because some LLMs send all params as strings.

   - **Type casting logic** in `validate_and_cast`:
     - For `"type": "integer"` params: try `int(value)`
     - For `"type": "boolean"` params: handle "true"/"false" strings
     - For `"type": "number"` params: try `float(value)`
     - For `"type": "array"` params: try `json.loads(value)` if string
     - Apply `default` values for missing optional params
     - Raise clear error for missing required params

2. **`nanobot/agent/tools/registry.py`**: Implement:
   - `ToolRegistry`:
     - `_tools: dict[str, Tool]`
     - `register(tool: Tool)` - add tool by name
     - `get(name: str) -> Tool | None` - lookup
     - `execute(name: str, params: dict) -> str` - validate params, execute tool, return result
     - `get_definitions() -> list[dict]` - return all tool schemas for LLM
     - `list_tools() -> list[str]` - return tool names

3. **`nanobot/agent/tools/shell.py`**: Implement `ExecTool(Tool)`:
   - **name**: "exec"
   - **parameters**: `command` (string, required), `timeout` (integer, optional, default 120)
   - **execute**: Run shell command using `asyncio.create_subprocess_shell`
     - Capture stdout + stderr
     - Enforce timeout (kill process if exceeded)
     - Return combined output, truncated if too long
     - Handle process errors gracefully
     - Use platform-appropriate shell (bash on POSIX, cmd on Windows)
   - Security: Do NOT add command filtering here (the LLM decides what to run), but DO enforce timeout.

**Acceptance criteria:**
- [ ] Tools can be registered and discovered
- [ ] Parameter validation catches missing required params
- [ ] Type casting works (string → int, string → bool)
- [ ] Shell tool executes commands and returns output
- [ ] Shell tool respects timeout
- [ ] Tool definitions match OpenAI function calling schema

---

### TICKET-007: Filesystem Tools

**PR Title:** `feat: file read, write, edit, and directory listing tools`
**Estimated Size:** ~365 lines | **Depends on:** TICKET-006

**Goal:** Give the agent the ability to read, write, edit files, and list directories.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/agent/tools/filesystem.py` | ~365 | Four filesystem tools |
| `tests/test_filesystem_tools.py` | ~120 | Filesystem tool tests |

**Detailed instructions:**

1. **`ReadFileTool(Tool)`**:
   - **name**: "read_file"
   - **parameters**: `path` (string, required), `offset` (integer, optional), `limit` (integer, optional)
   - **execute**: Read file contents with optional line range. Return content with line numbers (like `cat -n`). Handle encoding errors (try utf-8, fall back to latin-1). For binary files, return a message saying "binary file". Limit output to prevent context overflow (default max ~2000 lines). Handle file-not-found gracefully.

2. **`WriteFileTool(Tool)`**:
   - **name**: "write_file"
   - **parameters**: `path` (string, required), `content` (string, required)
   - **execute**: Write content to file. Create parent directories if needed (`os.makedirs`). Return confirmation message with file path and line count. Handle permission errors.

3. **`EditFileTool(Tool)`**:
   - **name**: "edit_file"
   - **parameters**: `path` (string, required), `old_string` (string, required), `new_string` (string, required), `replace_all` (boolean, optional, default false)
   - **execute**: Read file, find `old_string`, replace with `new_string`. If `replace_all` is false, the `old_string` must appear exactly once (error if 0 or 2+ matches — ambiguity means the LLM needs to provide more context). If `replace_all` is true, replace all occurrences. Write the modified content back. Return a success message with the number of replacements made.

4. **`ListDirTool(Tool)`**:
   - **name**: "list_dir"
   - **parameters**: `path` (string, required)
   - **execute**: List directory contents. Show files and subdirectories with indicators (trailing `/` for dirs). Sort alphabetically. Limit to reasonable depth/count. Handle permission errors and non-existent paths.

**Acceptance criteria:**
- [ ] ReadFile reads files with line numbers
- [ ] ReadFile handles offset/limit for partial reads
- [ ] WriteFile creates files and parent directories
- [ ] EditFile replaces unique strings correctly
- [ ] EditFile errors when old_string is not found or is ambiguous
- [ ] ListDir shows directory contents
- [ ] All tools handle errors gracefully (missing files, permissions)

---

### TICKET-008: Context Builder

**PR Title:** `feat: context builder for LLM prompt construction`
**Estimated Size:** ~190 lines | **Depends on:** TICKET-006

**Goal:** Build the system prompt assembler that combines identity, memory, skills, and runtime context into the system message for the LLM.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/agent/context.py` | ~191 | `ContextBuilder` class |
| `tests/test_context_prompt_cache.py` | ~50 | Prompt caching tests |

**Detailed instructions:**

1. **`ContextBuilder`** class:

   - **`__init__(self, config, workspace_dir)`**: Store config and workspace path.

   - **`build_system_prompt(self, channel=None, skills_text="") -> str | list`**:
     Assemble the full system prompt in this order:
     1. **Identity section**: "You are {agent_name}." + current date/time + platform info
     2. **Bootstrap files**: Read and include these files from workspace if they exist:
        - `AGENTS.md` - agent behavior instructions
        - `SOUL.md` - personality/tone guidelines
        - `USER.md` - user context/preferences
        - `TOOLS.md` - tool usage instructions
     3. **Long-term memory**: Read `MEMORY.md` from workspace (if exists)
     4. **Skills**: Include the `skills_text` parameter (skill summaries/instructions)
     5. **Runtime context**: Channel name, available tools list, iteration limits

   - **`build_messages(self, history, user_message) -> list[dict]`**:
     Format conversation history into OpenAI-compatible message list:
     - Convert session history entries to `{"role": "user"|"assistant"|"tool", "content": ...}`
     - Append the current user message
     - Handle tool call messages (assistant with tool_calls + tool role responses)
     - Trim history if it exceeds token budget

   - **Prompt caching support**: For Anthropic models, return system prompt as a list of content blocks with `cache_control` markers on the largest static sections (bootstrap files, memory). This enables Anthropic's prompt caching to avoid re-processing the same system context on every turn.

   - **`_load_file(self, filename) -> str | None`**: Read a file from workspace, return content or None if not found.

**Acceptance criteria:**
- [ ] System prompt includes all sections in correct order
- [ ] Missing bootstrap files are silently skipped
- [ ] Message history is correctly formatted
- [ ] Prompt caching markers are added for Anthropic
- [ ] Token budget is respected when trimming history

---

### TICKET-009: Session Manager

**PR Title:** `feat: JSONL-based session persistence and management`
**Estimated Size:** ~215 lines | **Depends on:** TICKET-001

**Goal:** Implement conversation session storage using append-only JSONL files, with in-memory caching and history retrieval.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/session/__init__.py` | ~5 | Module init |
| `nanobot/session/manager.py` | ~213 | `Session` and `SessionManager` classes |

**Detailed instructions:**

1. **`Session`** class:
   - **Storage format**: Each session is a `.jsonl` file where each line is a JSON object: `{"role": "user"|"assistant"|"tool", "content": "...", "timestamp": "...", "tool_calls": [...], "tool_call_id": "...", "consolidated": false}`
   - **`__init__(self, session_key, sessions_dir)`**: Generate file path from session key (sanitize key for filesystem safety using `safe_filename`)
   - **`add_message(self, role, content, **kwargs)`**: Append a JSON line to the JSONL file. Include timestamp. Handle tool_calls and tool_call_id for tool messages.
   - **`get_history(self, max_messages=500) -> list[dict]`**: Read JSONL file and return last N messages. Parse each line as JSON. Handle corrupted lines gracefully (skip them, log warning).
   - **`get_unconsolidated_messages(self) -> list[dict]`**: Return messages where `consolidated` is not True.
   - **`mark_consolidated(self, up_to_index)`**: Re-write the file marking messages up to index as `consolidated: true`.
   - **`clear(self)`**: Delete the session file.

2. **`SessionManager`** class:
   - **`__init__(self, sessions_dir)`**: Store sessions dir, create if not exists.
   - **`_sessions: dict[str, Session]`**: In-memory cache of Session objects.
   - **`get_session(self, channel, chat_id, session_key_override=None) -> Session`**: Return cached session or create new one. Session key format: `{channel}:{chat_id}` (or use override).
   - **`list_sessions(self) -> list[str]`**: Return all session keys by scanning sessions dir.
   - **`delete_session(self, key)`**: Remove session file and cache entry.

**Acceptance criteria:**
- [ ] Messages are persisted to JSONL files
- [ ] History retrieval respects max_messages limit
- [ ] Corrupted JSONL lines are skipped with warning
- [ ] Sessions are cached in memory for performance
- [ ] Session keys are filesystem-safe
- [ ] Consolidated message marking works

---

### TICKET-010: Agent Loop

**PR Title:** `feat: core agent processing loop with tool execution`
**Estimated Size:** ~500 lines | **Depends on:** TICKET-005, TICKET-006, TICKET-008, TICKET-009

**Goal:** Implement the main agent loop that consumes messages from the bus, calls the LLM, executes tools, and produces responses.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/agent/loop.py` | ~497 | `AgentLoop` — the brain of nanobot |

**Detailed instructions:**

1. **`AgentLoop`** class:

   - **`__init__(self, config, bus, session_manager, provider, tool_registry, context_builder)`**:
     Store all dependencies. Initialize state: `_running` flag, `_current_task` (for cancellation), active sessions tracking.

   - **`async start(self)`**: Begin consuming from `bus.inbound` in a loop. For each `InboundMessage`:
     1. Check for special commands: `/stop` (cancel current task), `/new` (clear session), `/restart` (restart agent)
     2. Get or create session via `session_manager`
     3. Add user message to session
     4. Call `_process_message()`
     5. Publish result as `OutboundMessage` to bus

   - **`async _process_message(self, message, session) -> str`**:
     The core processing method:
     1. Build system prompt via `context_builder.build_system_prompt()`
     2. Get history from session
     3. Build messages list via `context_builder.build_messages()`
     4. Enter the **tool loop** (max `config.agent.max_iterations` iterations):
        a. Call `provider.chat_with_retry(messages, tools)`
        b. If response has no tool calls → return response content (done)
        c. If response has tool calls:
           - Add assistant message (with tool_calls) to messages
           - For each tool call: execute via `tool_registry.execute()`, add tool result message
           - Continue loop
     5. If max iterations reached, return a message saying the agent hit the iteration limit

   - **`async _execute_tool_call(self, tool_call) -> str`**:
     - Extract tool name and arguments from `ToolCallRequest`
     - Call `tool_registry.execute(name, arguments)`
     - Catch exceptions and return error message as tool result
     - Truncate very long tool results (use `truncate_tool_result` from helpers)
     - Log tool execution (name, duration)

   - **`async stop(self)`**: Set `_running = False`, cancel current task if any.

   - **Cancellation support**: When `/stop` is received, cancel the current `_process_message` task using `asyncio.Task.cancel()`. Clean up gracefully.

   - **Error handling**: Wrap the entire processing in try/except. On provider errors, return user-friendly error messages. On unexpected errors, log the traceback and return a generic error message.

   - **Session management**: After each complete turn (user message + assistant response), save both to the session. Save tool call messages as well for replay/debugging.

**Acceptance criteria:**
- [ ] Agent processes inbound messages and produces responses
- [ ] Tool calls are executed and results fed back to LLM
- [ ] Multi-turn tool usage works (LLM calls multiple tools in sequence)
- [ ] Max iterations limit prevents infinite loops
- [ ] `/stop` cancels in-progress processing
- [ ] `/new` clears the session
- [ ] Errors are caught and reported gracefully
- [ ] All messages (user, assistant, tool) are saved to session

---

### TICKET-011: Memory System

**PR Title:** `feat: long-term memory consolidation with MEMORY.md and HISTORY.md`
**Estimated Size:** ~360 lines | **Depends on:** TICKET-009, TICKET-010

**Goal:** Implement the memory consolidation system that summarizes conversation history into persistent MEMORY.md (facts) and HISTORY.md (searchable log) files.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/agent/memory.py` | ~357 | `MemoryStore` and `MemoryConsolidator` |
| `tests/test_memory_consolidation_types.py` | ~60 | Memory tests |
| `tests/test_consolidate_offset.py` | ~40 | Offset tracking tests |

**Detailed instructions:**

1. **`MemoryStore`** class:
   - **`__init__(self, workspace_dir)`**: Set paths for `MEMORY.md` and `HISTORY.md`.
   - **`read_memory(self) -> str`**: Read MEMORY.md content, return empty string if not found.
   - **`read_history(self) -> str`**: Read HISTORY.md content.
   - **`write_memory(self, content)`**: Write/overwrite MEMORY.md.
   - **`append_history(self, entry)`**: Append timestamped entry to HISTORY.md.
   - **`search_history(self, query) -> list[str]`**: Simple grep-like search through HISTORY.md, return matching lines with context.

2. **`MemoryConsolidator`** class:
   - **`__init__(self, provider, memory_store, config)`**: Store dependencies.

   - **`async consolidate(self, session, force=False)`**:
     Main consolidation method:
     1. Get unconsolidated messages from session
     2. If count < threshold (e.g., 10 messages) and not forced, skip
     3. Estimate token count of unconsolidated messages
     4. If tokens < budget and not forced, skip
     5. Call `_summarize_to_memory()` and `_summarize_to_history()`
     6. Mark messages as consolidated in session

   - **`async _summarize_to_memory(self, messages, existing_memory) -> str`**:
     Call LLM with a special prompt:
     - "Here is the existing memory: {existing_memory}"
     - "Here are new conversation messages: {messages}"
     - "Update the memory with new facts, preferences, and context. Remove outdated information. Keep it concise."
     - Return the updated memory text

   - **`async _summarize_to_history(self, messages) -> str`**:
     Call LLM with prompt:
     - "Summarize these conversation messages into a grep-friendly log format"
     - "Each entry should be: [YYYY-MM-DD HH:MM] topic: summary"
     - "Focus on: what was done, decisions made, problems solved"
     - Return formatted history entries

   - **Token boundary detection**: When deciding where to split consolidation batches, detect message boundaries (don't split in the middle of a tool call sequence). A tool call sequence is: assistant message with tool_calls → one or more tool result messages → next assistant message.

   - **`save_memory` tool integration**: The agent can call a `save_memory` tool (defined here or in the tool registry) that triggers consolidation on demand. The tool accepts `memory_text` parameter and writes it directly to MEMORY.md.

**Acceptance criteria:**
- [ ] MEMORY.md is created and updated with consolidated facts
- [ ] HISTORY.md receives grep-friendly timestamped entries
- [ ] Consolidation respects message boundaries (doesn't split tool call sequences)
- [ ] Token-based thresholds prevent unnecessary consolidation
- [ ] Existing memory is preserved and merged with new information
- [ ] `save_memory` tool works for on-demand memory updates

---

## Phase 3: User Interface (PRs 12-13)

---

### TICKET-012: CLI Core Commands & Onboarding

**PR Title:** `feat: CLI with onboard, status, and direct message commands`
**Estimated Size:** ~500 lines | **Depends on:** TICKET-010

**Goal:** Build the first half of the CLI using Typer: onboarding wizard, status display, and direct message mode (`nanobot agent -m "hello"`).

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/cli/__init__.py` | ~1 | Module init |
| `nanobot/cli/commands.py` (part 1) | ~500 | Typer app, core commands |
| `tests/test_commands.py` | ~80 | CLI command tests |

**Detailed instructions:**

1. **Typer app setup**: Create `app = typer.Typer()` with `help="nanobot - lightweight AI assistant"`. Add version callback for `--version`.

2. **`nanobot onboard` command**:
   - Interactive setup wizard that:
     1. Asks which LLM provider to use (list known providers)
     2. Asks for API key (with secure input)
     3. Asks for preferred model (show default for chosen provider)
     4. Optionally asks which channels to enable
     5. Creates config directory and config.yaml
     6. Creates workspace directory with template files (SOUL.md, USER.md, AGENTS.md, TOOLS.md)
     7. Prints success message with next steps
   - Use `typer.prompt()` for input and `rich` for formatted output

3. **`nanobot status` command**:
   - Load config and display:
     - Agent name and model
     - Provider status (which providers configured, API key set?)
     - Enabled channels
     - Workspace path
     - Memory file sizes
     - Session count
   - Use rich.table for formatted output

4. **`nanobot agent` command**:
   - **`-m` / `--message` option**: Direct message mode
     - Initialize provider, tool registry, session manager, context builder, agent loop
     - Process single message
     - Print response and exit
   - **Without `-m`**: Launch interactive shell (implemented in TICKET-013)

5. **`nanobot logs` command**:
   - Show recent log output from loguru
   - Support `--follow` flag for tail-like behavior
   - Support `--lines N` for number of lines

6. **`nanobot restart` command**:
   - Find running nanobot process
   - Send restart signal
   - Confirm restart

7. **Logging setup**: Configure loguru with:
   - File rotation (10MB per file, keep 5)
   - Console output (stderr) with colors
   - Log level from `NANOBOT_LOG_LEVEL` env var (default INFO)

**Acceptance criteria:**
- [ ] `nanobot onboard` creates config and workspace
- [ ] `nanobot status` shows current configuration
- [ ] `nanobot agent -m "hello"` returns an LLM response
- [ ] `nanobot --version` prints version
- [ ] Logging is configured with file rotation

---

### TICKET-013: CLI Interactive Shell & Gateway

**PR Title:** `feat: interactive shell with prompt_toolkit and gateway startup`
**Estimated Size:** ~470 lines | **Depends on:** TICKET-012

**Goal:** Add the interactive chat shell and the gateway command that starts the full agent with all channels.

**Files to modify/extend:**

| File | Lines Added | Purpose |
|------|-------------|---------|
| `nanobot/cli/commands.py` (part 2) | ~470 | Interactive shell, gateway command |
| `tests/test_cli_input.py` | ~50 | Input handling tests |

**Detailed instructions:**

1. **Interactive shell** (inside the `agent` command when no `-m` is given):
   - Use `prompt_toolkit` for rich line editing:
     - Command history (persisted to `~/.nanobot/history/cli_history`)
     - Multi-line input support (paste detection)
     - Auto-suggestions from history
   - Print welcome banner with agent name and model
   - Main loop:
     1. Read user input with prompt ">>> "
     2. Handle special inputs: `/stop`, `/new`, `/restart`, `/quit`, empty lines
     3. Create `InboundMessage` and publish to bus
     4. Await response from bus outbound queue
     5. Print response with rich Markdown rendering
     6. Handle Ctrl+C (cancel current) and Ctrl+D (exit)
   - **Streaming support** (optional in first version): Print tokens as they arrive rather than waiting for complete response
   - **Signal handling**: Register handlers for SIGINT, SIGTERM. Clean up on exit (restore terminal state).
   - **Windows compatibility**: Handle UTF-8 encoding issues on Windows, use appropriate terminal APIs

2. **`nanobot gateway` command**:
   - Initialize all components:
     1. Load config
     2. Create provider from config
     3. Create tool registry, register all tools
     4. Create session manager
     5. Create context builder
     6. Create agent loop
     7. Create channel manager
     8. Create cron service (if configured)
     9. Create heartbeat service (if configured)
   - Start all services concurrently with `asyncio.gather()`:
     - Agent loop
     - Channel manager (starts all enabled channels)
     - Cron service
     - Heartbeat service
   - Handle graceful shutdown on SIGINT/SIGTERM
   - Log startup status (which channels connected, which services running)

3. **Channel-specific CLI commands** (stubs for now):
   - `nanobot telegram` - Telegram-specific info
   - `nanobot discord` - Discord-specific info
   - etc. (these will be fleshed out when channels are added)

**Acceptance criteria:**
- [ ] Interactive shell works with history and multi-line input
- [ ] Rich Markdown rendering in terminal
- [ ] Ctrl+C cancels current processing
- [ ] Ctrl+D exits cleanly
- [ ] `nanobot gateway` starts agent with all configured services
- [ ] Graceful shutdown on SIGINT/SIGTERM
- [ ] Terminal state is properly restored on exit

---

## Phase 4: Channel Integrations (PRs 14-25)

Each channel PR is self-contained. They can be developed in parallel by different developers after the channel infrastructure (TICKET-014) is in place.

---

### TICKET-014: Channel Infrastructure

**PR Title:** `feat: channel base class, manager, and registry`
**Estimated Size:** ~330 lines | **Depends on:** TICKET-010

**Goal:** Build the channel abstraction layer: base class for all channels, a manager that coordinates them, and a registry for auto-discovery.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/channels/__init__.py` | ~6 | Module init |
| `nanobot/channels/base.py` | ~134 | `BaseChannel` ABC |
| `nanobot/channels/manager.py` | ~155 | `ChannelManager` |
| `nanobot/channels/registry.py` | ~35 | Channel auto-discovery |
| `tests/test_base_channel.py` | ~60 | Base channel tests |

**Detailed instructions:**

1. **`BaseChannel`** abstract class:
   - **`__init__(self, config, bus)`**: Store channel config and message bus reference.
   - **`abstract async start(self)`**: Begin listening for messages.
   - **`abstract async stop(self)`**: Clean up and disconnect.
   - **`abstract async send(self, message: OutboundMessage)`**: Send message to the platform.
   - **`async _handle_message(self, sender_id, chat_id, content, media=None, metadata=None)`**:
     Common inbound message processing:
     1. Check `is_allowed(sender_id)` against `allow_from` config
     2. If media contains audio, transcribe via Groq Whisper
     3. Create `InboundMessage` with channel name, sender_id, chat_id, content
     4. Publish to `bus.inbound`
   - **`is_allowed(self, sender_id) -> bool`**: Check if sender_id is in `allow_from` list. If `allow_from` is empty, deny all (secure by default).
   - **Properties**: `name` (str, channel identifier), `enabled` (bool from config)

2. **`ChannelManager`** class:
   - **`__init__(self, config, bus)`**: Store config and bus.
   - **`_channels: dict[str, BaseChannel]`**: Active channel instances.
   - **`async start(self)`**:
     1. Discover and instantiate enabled channels via registry
     2. Start each channel (with error handling — one channel failing shouldn't block others)
     3. Start outbound dispatch loop
   - **`async _dispatch_outbound(self)`**: Continuously consume from `bus.outbound` and route to the correct channel's `send()` method based on `OutboundMessage.channel`.
   - **`async stop(self)`**: Stop all channels gracefully.
   - **`get_channel(self, name) -> BaseChannel | None`**: Lookup by name.

3. **`registry.py`**: Use `pkgutil` to scan the `nanobot.channels` package for modules. For each module, check if it defines a class that extends `BaseChannel`. Return a mapping of channel name → channel class. This allows adding new channels by just dropping a new .py file.

**Acceptance criteria:**
- [ ] BaseChannel enforces start/stop/send contract
- [ ] is_allowed correctly filters by allow_from
- [ ] ChannelManager starts all enabled channels
- [ ] ChannelManager routes outbound messages to correct channel
- [ ] Registry auto-discovers channel modules
- [ ] One channel failing to start doesn't block others

---

### TICKET-015: Telegram Channel

**PR Title:** `feat: Telegram bot channel with groups, threads, and media support`
**Estimated Size:** ~780 lines | **Depends on:** TICKET-014

**Goal:** Implement full Telegram integration using python-telegram-bot library.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/channels/telegram.py` | ~776 | Telegram channel implementation |
| `tests/test_telegram_channel.py` | ~100 | Telegram tests |

**Detailed instructions:**

1. **`TelegramChannel(BaseChannel)`**:

   - **`start()`**: Initialize `Application` from python-telegram-bot:
     - Set bot token from config
     - Configure proxy if set (SOCKS5 support via `python-telegram-bot[socks]`)
     - Register message handlers for text, photos, documents, audio, voice
     - Register command handlers for `/start`
     - Start polling (or webhook if configured)

   - **`stop()`**: Shutdown the Application gracefully.

   - **`send(message)`**: Send message to Telegram:
     - Split long messages (Telegram limit: 4096 chars)
     - Support Markdown formatting (MarkdownV2 parse mode)
     - Handle reply_to (reply to specific message IDs)
     - Send media (photos, documents) if present in OutboundMessage
     - Support message threads (forum topics) via `message_thread_id`

   - **Message handling**:
     - **Text messages**: Extract text, handle `/commands`
     - **Photos**: Download photo, include as media in InboundMessage
     - **Documents**: Download document, include as media
     - **Audio/Voice**: Download audio, transcribe via Groq Whisper, include transcript
     - **Group messages**: Check `group_policy`:
       - `"mention"`: Only respond when bot is @mentioned
       - `"open"`: Respond to all messages
       - `"allowlist"`: Only respond in whitelisted groups

   - **Draft/streaming mode**: For long responses, send an initial "thinking..." message, then edit it with the final content. This provides better UX than waiting for the full response.

   - **Rate limiting**: Handle Telegram's rate limits (max 30 messages/second to different chats, 1 message/second to same chat). Queue messages and space them out.

   - **Thread isolation**: When a message comes from a forum topic, use the topic ID as part of the session key so each topic gets its own conversation history.

   - **Error handling**: Handle network errors, API errors (bot blocked by user, chat not found, etc.) gracefully with retries for transient errors.

**Acceptance criteria:**
- [ ] Bot responds to direct messages
- [ ] Bot handles group messages with mention detection
- [ ] Media (photos, audio) is received and processed
- [ ] Long messages are split correctly
- [ ] Markdown formatting is applied
- [ ] Proxy support works (SOCKS5)
- [ ] Thread/topic isolation works
- [ ] Rate limiting prevents API errors

---

### TICKET-016: Discord Channel

**PR Title:** `feat: Discord bot channel with gateway protocol and thread support`
**Estimated Size:** ~380 lines | **Depends on:** TICKET-014

**Goal:** Implement Discord bot integration using raw gateway WebSocket protocol (not discord.py library).

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/channels/discord.py` | ~377 | Discord channel implementation |

**Detailed instructions:**

1. **`DiscordChannel(BaseChannel)`**:

   - **Gateway connection**: Connect to Discord Gateway via WebSocket:
     - Identify with bot token and intents (MESSAGE_CONTENT, GUILDS, GUILD_MESSAGES, DIRECT_MESSAGES)
     - Handle heartbeat (OP 10 Hello → OP 1 Heartbeat at interval)
     - Handle reconnection (OP 7 Reconnect, OP 9 Invalid Session)
     - Resume sessions after disconnection

   - **Message handling**:
     - Listen for MESSAGE_CREATE events
     - Filter by `allow_from` (Discord user IDs)
     - Handle DMs and server messages differently
     - Detect @mentions of the bot
     - Extract message content, attachments, embeds

   - **Sending messages**:
     - Use Discord REST API (`POST /channels/{id}/messages`)
     - Split messages at 2000 chars (Discord limit)
     - Support Markdown formatting (Discord's subset)
     - Handle reply references (`message_reference` field)

   - **Thread support**: When messages come from threads, use thread ID in session key.

   - **Rate limiting**: Respect Discord's rate limit headers (X-RateLimit-Remaining, X-RateLimit-Reset).

   - **Intents**: Request `MESSAGE_CONTENT` privileged intent (must be enabled in Discord Developer Portal).

**Acceptance criteria:**
- [ ] Bot connects to Discord gateway and maintains heartbeat
- [ ] Bot receives and responds to DMs
- [ ] Bot handles server messages with mention detection
- [ ] Messages are split at 2000 chars
- [ ] Reconnection works after disconnection

---

### TICKET-017: Slack Channel

**PR Title:** `feat: Slack bot channel with Socket Mode`
**Estimated Size:** ~280 lines | **Depends on:** TICKET-014

**Goal:** Implement Slack bot integration using Socket Mode (no public URL needed).

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/channels/slack.py` | ~281 | Slack channel implementation |
| `tests/test_slack_channel.py` | ~60 | Slack tests |

**Detailed instructions:**

1. **`SlackChannel(BaseChannel)`**:

   - **Connection**: Use `slack_sdk.socket_mode.aio.AsyncSocketModeClient` for WebSocket connection:
     - Requires `app_token` (xapp-...) for Socket Mode
     - Requires `bot_token` (xoxb-...) for API calls

   - **Event handling**:
     - Listen for `message` events (type: events_api)
     - Filter out bot's own messages (check `bot_id`)
     - Handle DMs and channel messages
     - Detect @mentions using `<@BOT_USER_ID>` pattern
     - Acknowledge events to prevent retries

   - **Sending messages**:
     - Use `AsyncWebClient.chat_postMessage()`
     - Support thread replies via `thread_ts` parameter
     - Convert Markdown to Slack's mrkdwn format:
       - `**bold**` → `*bold*`
       - `*italic*` → `_italic_`
       - `` `code` `` stays the same
       - Code blocks stay the same
     - Split long messages (Slack limit: ~4000 chars per message)

   - **Thread isolation**: Use `thread_ts` as part of session key so each thread gets its own conversation.

   - **Error handling**: Handle disconnections, reconnect automatically via Socket Mode client.

**Acceptance criteria:**
- [ ] Bot connects via Socket Mode
- [ ] DMs are received and responded to
- [ ] Thread replies work correctly
- [ ] Markdown is converted to mrkdwn format
- [ ] Bot's own messages are filtered out

---

### TICKET-018: Feishu/Lark Channel

**PR Title:** `feat: Feishu/Lark bot channel with WebSocket and rich text`
**Estimated Size:** ~1005 lines | **Depends on:** TICKET-014

**Goal:** Implement Feishu (Lark) bot integration with WebSocket long connection, rich text support, and interactive cards.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/channels/feishu.py` | ~1005 | Feishu channel implementation |
| `tests/test_feishu_channel.py` | ~80 | Feishu tests (multiple test files exist) |

**Detailed instructions:**

This is the largest single channel implementation. Key areas:

1. **WebSocket connection**:
   - Get WebSocket endpoint URL via Feishu Open API
   - Maintain persistent WebSocket connection
   - Handle connection lifecycle (connect, ping/pong, reconnect)
   - Parse incoming events (message, mention, etc.)

2. **Authentication**:
   - Get tenant_access_token using app_id + app_secret
   - Auto-refresh token before expiry
   - Handle encrypted messages (AES decryption) if `encrypt_key` is set
   - Verify event signatures using `verification_token`

3. **Message handling**:
   - Parse Feishu message types: text, rich_text, image, audio, file
   - Handle mentions (`@bot` detection)
   - Support group chats and direct messages
   - Extract text from rich text format (nested tags structure)
   - Download media files via Feishu API

4. **Sending messages**:
   - Use Feishu API to send messages (`/im/v1/messages`)
   - Support text and rich text formats
   - Build interactive cards for structured responses
   - Handle message length limits
   - Support reply-to-message via `reply_message_id`

5. **Rich text building**:
   - Convert Markdown to Feishu rich text format
   - Handle bold, italic, code, links, lists
   - Build card messages for complex responses

**Acceptance criteria:**
- [ ] WebSocket connection establishes and maintains
- [ ] Messages are received from groups and DMs
- [ ] Rich text is parsed correctly
- [ ] Responses are sent in appropriate format
- [ ] Token refresh works automatically
- [ ] Encrypted messages are handled (if configured)

---

### TICKET-019: DingTalk Channel

**PR Title:** `feat: DingTalk bot channel with Stream mode`
**Estimated Size:** ~475 lines | **Depends on:** TICKET-014

**Goal:** Implement DingTalk bot integration using the Stream mode SDK.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/channels/dingtalk.py` | ~474 | DingTalk channel implementation |
| `tests/test_dingtalk_channel.py` | ~60 | DingTalk tests |

**Detailed instructions:**

1. **`DingTalkChannel(BaseChannel)`**:

   - **Connection**: Use `dingtalk_stream` SDK:
     - Configure with `client_id` and `client_secret`
     - Register callback handler for bot messages
     - Start stream client

   - **Message handling**:
     - Parse incoming bot messages (text, rich text, media)
     - Handle 1-on-1 chats and group chats
     - Detect @mentions in group messages
     - Extract sender info (`staffId` for access control)
     - Support webhook-style incoming messages as fallback

   - **Sending messages**:
     - Use DingTalk API to reply to messages
     - Support Markdown formatting
     - Handle message cards (ActionCard format)
     - Support @mentioning users in responses
     - Implement message splitting for long responses

   - **Group policy**: Handle group_policy config:
     - `"mention"`: Respond only when @mentioned
     - `"open"`: Respond to all group messages
     - Use `staffIds` for allow_from (not phone numbers)

   - **Webhook fallback**: Support outgoing webhook mode for simpler deployments (HTTP callback instead of Stream).

**Acceptance criteria:**
- [ ] Stream mode connects successfully
- [ ] Group and 1-on-1 messages are handled
- [ ] @mention detection works
- [ ] Markdown responses render correctly
- [ ] Staff ID-based access control works

---

### TICKET-020: Matrix Channel

**PR Title:** `feat: Matrix/Element channel with E2EE support`
**Estimated Size:** ~715 lines | **Depends on:** TICKET-014

**Goal:** Implement Matrix protocol integration with end-to-end encryption support using matrix-nio.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/channels/matrix.py` | ~714 | Matrix channel implementation |
| `tests/test_matrix_channel.py` | ~80 | Matrix tests |

**Detailed instructions:**

1. **`MatrixChannel(BaseChannel)`**:

   - **Connection**: Use `matrix-nio` (`AsyncClient`):
     - Login with user_id + password OR access_token
     - Set up E2EE key storage (SQLite-based via matrix-nio)
     - Perform initial sync
     - Start sync loop

   - **E2EE support**:
     - Auto-verify device keys (trust-on-first-use)
     - Handle key verification requests
     - Decrypt incoming encrypted messages
     - Encrypt outgoing messages (automatic in E2EE rooms)
     - Store encryption keys in persistent store

   - **Message handling**:
     - Listen for `RoomMessageText`, `RoomMessageImage`, `RoomMessageAudio` events
     - Filter by room membership (only respond in joined rooms)
     - Handle mentions (display name matching)
     - Track read receipts
     - Handle message edits and redactions

   - **Sending messages**:
     - Send text messages with HTML formatting
     - Convert Markdown to Matrix HTML format
     - Support media uploads (images, files)
     - Handle reply-to via `m.relates_to` event field
     - Split long messages

   - **Room management**:
     - Auto-join on invite
     - Track room membership
     - Use room_id as chat_id in session key

   - **Sync handling**:
     - Initial sync: catch up on missed messages
     - Incremental sync: process new messages only (use `since` token)
     - Handle sync errors and reconnection

**Acceptance criteria:**
- [ ] Bot logs in and syncs with homeserver
- [ ] Unencrypted messages are received and responded to
- [ ] E2EE works (encrypt/decrypt)
- [ ] Media messages are handled
- [ ] Auto-join on invite works
- [ ] Sync state persists across restarts

---

### TICKET-021: Email Channel

**PR Title:** `feat: email channel with IMAP polling and SMTP sending`
**Estimated Size:** ~410 lines | **Depends on:** TICKET-014

**Goal:** Implement email as a channel — poll for incoming emails via IMAP, respond via SMTP.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/channels/email.py` | ~409 | Email channel implementation |
| `tests/test_email_channel.py` | ~70 | Email tests |

**Detailed instructions:**

1. **`EmailChannel(BaseChannel)`**:

   - **IMAP polling**:
     - Connect to IMAP server with SSL
     - Authenticate with username/password
     - Poll INBOX at configurable interval (default: 60 seconds)
     - Fetch unread emails (UNSEEN flag)
     - Parse email content:
       - Prefer plain text part
       - Fall back to HTML (strip tags)
       - Handle multipart messages
       - Extract attachments as media
     - Mark processed emails as SEEN
     - Use email `Message-ID` as message identifier

   - **SMTP sending**:
     - Connect to SMTP server with TLS/STARTTLS
     - Send replies using `In-Reply-To` and `References` headers (proper threading)
     - Format response body:
       - Include original message as quoted text
       - Add bot response as plain text and HTML
     - Handle attachments in outgoing emails

   - **Consent mechanism**:
     - First-time senders get a consent request
     - Store consent status per email address
     - Only process messages from consented senders (in addition to `allow_from`)

   - **Session management**: Use sender's email address as chat_id for session key.

   - **Error handling**: Handle IMAP connection drops (reconnect), SMTP auth failures, malformed emails.

**Acceptance criteria:**
- [ ] IMAP polling fetches unread emails
- [ ] Email body is parsed correctly (plain text and HTML)
- [ ] SMTP replies maintain proper email threading
- [ ] Consent mechanism works for first-time senders
- [ ] allow_from filtering works with email addresses
- [ ] Connection drops are handled with auto-reconnect

---

### TICKET-022: WeChat Work (WeCom) Channel

**PR Title:** `feat: WeChat Work channel via wecom-aibot-sdk`
**Estimated Size:** ~355 lines | **Depends on:** TICKET-014

**Goal:** Implement WeChat Work (Enterprise WeChat) integration using the wecom-aibot-sdk.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/channels/wecom.py` | ~353 | WeChat Work channel implementation |

**Detailed instructions:**

1. **`WecomChannel(BaseChannel)`**:

   - **SDK integration**: Use `wecom-aibot-sdk-python`:
     - Initialize with corp_id, agent_id, secret
     - Register message callback handler
     - Start SDK client

   - **Message handling**:
     - Receive text, image, voice, video messages
     - Parse user info (user_id for access control)
     - Handle group chats and direct messages
     - Transcribe voice messages

   - **Sending messages**:
     - Reply via SDK API
     - Support text and Markdown formatting
     - Handle message length limits (WeChat Work: 2048 chars)
     - Support media sending (images)

   - **Access control**: Use WeChat Work user IDs for `allow_from` filtering.

**Acceptance criteria:**
- [ ] SDK connects successfully
- [ ] Messages are received and processed
- [ ] Replies are sent in proper format
- [ ] Voice messages are transcribed
- [ ] User ID-based access control works

---

### TICKET-023: QQ Channel

**PR Title:** `feat: QQ bot channel with botpy SDK`
**Estimated Size:** ~160 lines | **Depends on:** TICKET-014

**Goal:** Implement QQ bot integration using the official qq-botpy SDK.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/channels/qq.py` | ~161 | QQ channel implementation |
| `tests/test_qq_channel.py` | ~40 | QQ tests |

**Detailed instructions:**

1. **`QQChannel(BaseChannel)`**:

   - **Connection**: Use `qq-botpy`:
     - Configure with app_id and secret
     - Register intents (PUBLIC_GUILD_MESSAGES, DIRECT_MESSAGE)
     - Start bot client

   - **Message handling**:
     - Handle guild messages and direct messages
     - Detect @mentions
     - Extract message content
     - Handle message references (replies)

   - **Sending messages**:
     - Reply to messages via botpy API
     - Support Markdown (limited subset)
     - Handle message_reference for reply context
     - Message splitting if needed

   - **Access control**: Use QQ user IDs for filtering.

**Acceptance criteria:**
- [ ] Bot connects to QQ platform
- [ ] Guild and direct messages are handled
- [ ] @mention detection works
- [ ] Replies maintain message context

---

### TICKET-024: WhatsApp Channel & Node.js Bridge

**PR Title:** `feat: WhatsApp channel with Node.js Baileys bridge`
**Estimated Size:** ~170 lines Python + ~300 lines TypeScript | **Depends on:** TICKET-014

**Goal:** Implement WhatsApp integration via a separate Node.js bridge process using the Baileys library (WhatsApp Web reverse-engineered protocol).

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/channels/whatsapp.py` | ~171 | WhatsApp channel (Python side) |
| `bridge/package.json` | ~20 | Node.js dependencies |
| `bridge/tsconfig.json` | ~10 | TypeScript config |
| `bridge/src/whatsapp.ts` | ~200 | Baileys WhatsApp client |
| `bridge/src/server.ts` | ~80 | WebSocket server |
| `bridge/src/types.d.ts` | ~20 | TypeScript type definitions |

**Detailed instructions:**

1. **Node.js Bridge** (`bridge/`):

   - **`whatsapp.ts`**: Using `@whiskeysockets/baileys`:
     - Connect to WhatsApp Web (QR code authentication)
     - Store auth credentials in file-based store
     - Listen for incoming messages
     - Handle text, image, audio, document messages
     - Forward messages to Python via WebSocket

   - **`server.ts`**: WebSocket server on configurable port:
     - Accept connections from Python channel
     - Forward incoming WhatsApp messages as JSON
     - Accept outbound messages from Python and send via Baileys
     - Protocol: JSON messages with `type` field ("message", "send", "status")

   - **QR Code**: On first connection, display QR code in terminal for scanning

2. **Python Channel** (`whatsapp.py`):

   - **`WhatsAppChannel(BaseChannel)`**:
     - Connect to bridge via WebSocket
     - Parse incoming messages from bridge
     - Forward to message bus
     - Send outbound messages through bridge WebSocket
     - Handle bridge disconnection and reconnection
     - Optionally auto-start bridge process

   - **Bridge lifecycle**: Start bridge as subprocess if `auto_start_bridge` is configured. Monitor bridge process health.

**Acceptance criteria:**
- [ ] Bridge connects to WhatsApp Web via QR code
- [ ] Messages flow: WhatsApp → Bridge → Python channel → Bus
- [ ] Outbound messages are sent via bridge
- [ ] Bridge reconnects after disconnection
- [ ] Auth credentials persist (no QR re-scan)

---

### TICKET-025: Mochat Channel

**PR Title:** `feat: Mochat channel with Socket.IO and msgpack support`
**Estimated Size:** ~900 lines | **Depends on:** TICKET-014

**Goal:** Implement Mochat (Claw IM) integration with Socket.IO real-time communication.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/channels/mochat.py` | ~896 | Mochat channel implementation |

**Detailed instructions:**

1. **`MochatChannel(BaseChannel)`**:

   - **Socket.IO connection**:
     - Connect to Mochat server via Socket.IO
     - Authenticate with token
     - Handle connection events (connect, disconnect, reconnect)
     - Support msgpack binary protocol for efficiency

   - **Message handling**:
     - Parse incoming chat messages
     - Handle text, image, file, audio message types
     - Support group chats and direct messages
     - Handle @mentions in group chats
     - Process message metadata (sender info, timestamps)

   - **Sending messages**:
     - Emit messages via Socket.IO
     - Support text and rich text formats
     - Handle media attachments
     - Message splitting for long responses
     - Support reply-to-message

   - **Room/channel management**:
     - Join/leave rooms
     - Track room membership
     - Handle room events

   - **Claw integration features**:
     - Support Claw-specific message formats
     - Handle inline commands
     - Support reactions/emoji responses

**Acceptance criteria:**
- [ ] Socket.IO connection establishes and authenticates
- [ ] Messages are received from chats
- [ ] Responses are sent correctly
- [ ] Reconnection handles gracefully
- [ ] msgpack protocol works for efficiency

---

## Phase 5: Advanced Features (PRs 26-33)

---

### TICKET-026: Web Search & Fetch Tools

**PR Title:** `feat: multi-provider web search and URL content fetching tools`
**Estimated Size:** ~325 lines | **Depends on:** TICKET-006

**Goal:** Give the agent web search capability (DuckDuckGo, Jina, Bing, etc.) and the ability to fetch and parse web page content.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/agent/tools/web.py` | ~322 | `WebSearchTool` and `WebFetchTool` |
| `tests/test_web_search_tool.py` | ~60 | Web search tests |

**Detailed instructions:**

1. **`WebSearchTool(Tool)`**:
   - **name**: "web_search"
   - **parameters**: `query` (string, required), `max_results` (integer, optional, default 5)
   - **execute**: Search the web using configured provider:

     - **DuckDuckGo** (default, no API key needed):
       - Use `ddgs` library (`DDGS().text()`)
       - Return title, URL, and snippet for each result

     - **Jina Search**:
       - Call `https://s.jina.ai/{query}` with API key in header
       - Parse response for search results

     - **Bing**:
       - Call Bing Search API v7
       - Parse JSON response for web pages

     - **SearXNG** (self-hosted):
       - Call configured SearXNG instance
       - Parse JSON response

   - **Provider selection**: Read `config.tools.web_search.provider` to determine which search backend to use. Fall back to DuckDuckGo if not configured.

   - **Proxy support**: Route requests through `config.tools.web_search.proxy` if configured.

   - **Output format**: Return results as formatted text:
     ```
     1. [Title](URL)
        Snippet text...
     2. [Title](URL)
        Snippet text...
     ```

2. **`WebFetchTool(Tool)`**:
   - **name**: "web_fetch"
   - **parameters**: `url` (string, required)
   - **execute**: Fetch and parse a web page:
     - Use Jina Reader API: `https://r.jina.ai/{url}` (returns clean Markdown)
     - If Jina is not available, fall back to direct fetch with httpx + basic HTML stripping
     - Truncate output to prevent context overflow (max ~8000 tokens)
     - Handle errors (404, timeout, SSL errors)
     - Set reasonable timeout (30 seconds)

**Acceptance criteria:**
- [ ] DuckDuckGo search returns results without API key
- [ ] Multiple search providers are supported
- [ ] Web fetch returns clean, readable content
- [ ] Long pages are truncated appropriately
- [ ] Proxy support works
- [ ] Errors are handled gracefully

---

### TICKET-027: MCP, Message & Spawn Tools

**PR Title:** `feat: MCP integration, cross-channel messaging, and subagent spawn tools`
**Estimated Size:** ~320 lines | **Depends on:** TICKET-006, TICKET-014

**Goal:** Add three advanced tools: MCP server integration, cross-channel messaging, and background subagent spawning.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/agent/tools/mcp.py` | ~148 | `MCPTool` for MCP server integration |
| `nanobot/agent/tools/message.py` | ~109 | `MessageTool` for cross-channel messaging |
| `nanobot/agent/tools/spawn.py` | ~63 | `SpawnTool` for background tasks |
| `tests/test_mcp_tool.py` | ~50 | MCP tests |

**Detailed instructions:**

1. **`MCPTool`**: Model Context Protocol integration:
   - **Initialization**: Read MCP server configs from `config.mcp_servers`
   - **Server connection**: Support two transport types:
     - `stdio`: Launch MCP server as subprocess, communicate via stdin/stdout
     - `sse`/`http`: Connect to HTTP-based MCP server
   - **Tool discovery**: Call MCP server's `tools/list` to discover available tools
   - **Tool execution**: Forward tool calls to MCP server, return results
   - **Dynamic registration**: Register discovered MCP tools in the ToolRegistry so the LLM can use them
   - **Timeout**: Configurable timeout per server (default 30s)
   - **Auth**: Support custom headers per server for authentication

2. **`MessageTool`**: Let the agent send messages to any channel:
   - **name**: "send_message"
   - **parameters**: `channel` (string, required), `chat_id` (string, required), `content` (string, required)
   - **execute**: Create `OutboundMessage` and publish to bus. Validate that the target channel exists. Handle the case where agent wants to suppress the normal response (just send the message without also replying in the current chat).

3. **`SpawnTool`**: Spawn background subtasks:
   - **name**: "spawn"
   - **parameters**: `task` (string, required - description of what to do), `channel` (string, optional), `chat_id` (string, optional)
   - **execute**: Create a new asyncio Task that:
     1. Creates a fresh session
     2. Processes the task description through the agent loop
     3. Optionally sends the result to a specified channel/chat
   - Return immediately with a task ID

**Acceptance criteria:**
- [ ] MCP tools from configured servers appear in tool list
- [ ] MCP tool calls are forwarded and results returned
- [ ] Message tool sends to specified channel
- [ ] Spawn tool creates background tasks
- [ ] MCP supports both stdio and HTTP transports

---

### TICKET-028: Cron Scheduling System

**PR Title:** `feat: cron job scheduling with multiple schedule types`
**Estimated Size:** ~595 lines | **Depends on:** TICKET-010

**Goal:** Implement scheduled task execution supporting cron expressions, fixed intervals, and one-time schedules.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/cron/__init__.py` | ~6 | Module init |
| `nanobot/cron/types.py` | ~59 | `CronJob`, `CronSchedule` dataclasses |
| `nanobot/cron/service.py` | ~376 | `CronService` |
| `nanobot/agent/tools/cron.py` | ~158 | `CronTool` for agent to manage jobs |
| `tests/test_cron_service.py` | ~80 | Cron service tests |

**Detailed instructions:**

1. **`nanobot/cron/types.py`**: Define data structures:
   - **`CronSchedule`**: `kind` (literal "cron" | "every" | "at"), `value` (str - cron expression, interval like "5m", or ISO datetime), `timezone` (str, default "UTC")
   - **`CronJob`**: `id` (str, UUID), `name` (str), `schedule` (CronSchedule), `task` (str - the prompt to send to agent), `channel` (str), `chat_id` (str), `enabled` (bool, default True), `created_at` (str), `next_run_at` (str | None), `last_run_at` (str | None), `last_status` (str | None)

2. **`nanobot/cron/service.py`**: Implement `CronService`:
   - **Storage**: JSON files in `~/.nanobot/runtime/cron/` (one file per job)
   - **`async start(self)`**: Load all jobs, start the scheduling loop
   - **Scheduling loop**: Every 10 seconds, check all enabled jobs:
     - For `kind=cron`: Use `croniter` to check if current time has passed `next_run_at`
     - For `kind=every`: Check if elapsed time since `last_run_at` exceeds interval
     - For `kind=at`: Check if current time has passed scheduled time (then disable after running)
   - **Job execution**: When a job triggers:
     1. Create `InboundMessage` with the job's `task` as content
     2. Publish to message bus (targeting the specified channel/chat)
     3. Update `last_run_at` and `next_run_at`
     4. Save job state to disk
   - **CRUD operations**: `add_job()`, `remove_job()`, `enable_job()`, `disable_job()`, `list_jobs()`, `get_job()`
   - **File watching**: Detect changes to job files (for manual editing) using file modification time comparison
   - **Timezone support**: Use `croniter` with timezone-aware datetimes

3. **`nanobot/agent/tools/cron.py`**: Implement `CronTool(Tool)`:
   - **name**: "cron"
   - **parameters**: `action` (string: "list" | "add" | "remove" | "enable" | "disable"), plus action-specific params
   - **execute**: Dispatch to CronService methods based on action
   - For "add": validate schedule expression, create CronJob, save to disk
   - For "list": return formatted table of all jobs with status

**Acceptance criteria:**
- [ ] Cron expression jobs trigger at correct times
- [ ] "every" interval jobs run at fixed intervals
- [ ] "at" one-time jobs run once and auto-disable
- [ ] Jobs persist across restarts (JSON files)
- [ ] Agent can manage jobs via cron tool
- [ ] Timezone support works correctly
- [ ] Multiple concurrent jobs work

---

### TICKET-029: Heartbeat Service

**PR Title:** `feat: periodic heartbeat service for proactive agent tasks`
**Estimated Size:** ~175 lines | **Depends on:** TICKET-010

**Goal:** Implement a periodic wake-up service that reads a HEARTBEAT.md file and lets the LLM decide whether to take action.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/heartbeat/__init__.py` | ~5 | Module init |
| `nanobot/heartbeat/service.py` | ~173 | `HeartbeatService` |
| `tests/test_heartbeat_service.py` | ~50 | Heartbeat tests |

**Detailed instructions:**

1. **`HeartbeatService`** class:

   - **`__init__(self, config, provider, bus, workspace_dir)`**: Store dependencies. Set interval from config (default 30 minutes).

   - **`async start(self)`**: Run a loop:
     1. Sleep for `interval` seconds
     2. Read `HEARTBEAT.md` from workspace (if not exists, skip)
     3. Call `_check_and_execute()`
     4. Repeat

   - **`async _check_and_execute(self)`**:
     1. Read HEARTBEAT.md content (contains user-defined tasks/checks)
     2. Build a prompt: "Here are your periodic tasks: {heartbeat_content}. Current time: {now}. Decide if any tasks need to run right now. Respond with 'SKIP' if nothing to do, or describe what to do."
     3. Call LLM with this prompt
     4. Parse response:
        - If response contains "SKIP" (or similar), do nothing
        - Otherwise, create an InboundMessage with the LLM's decided action and publish to bus for full agent processing

   - **HEARTBEAT.md format**: Markdown file where users define periodic checks:
     ```markdown
     ## Periodic Tasks
     - Check if any GitHub issues need responses (every morning)
     - Summarize unread emails (every 2 hours)
     - Monitor server health dashboard
     ```

   - **`async stop(self)`**: Set running flag to False, cancel sleep task.

**Acceptance criteria:**
- [ ] Service wakes up at configured interval
- [ ] HEARTBEAT.md is read and sent to LLM
- [ ] LLM "SKIP" response prevents action
- [ ] LLM action response triggers agent processing
- [ ] Missing HEARTBEAT.md is handled gracefully
- [ ] Service stops cleanly

---

### TICKET-030: Skills System & Subagent Manager

**PR Title:** `feat: skills loader and background subagent execution`
**Estimated Size:** ~460 lines | **Depends on:** TICKET-010

**Goal:** Implement the skills system (load SKILL.md files with frontmatter) and the subagent manager for background task execution.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/agent/skills.py` | ~228 | `SkillsLoader` |
| `nanobot/agent/subagent.py` | ~232 | `SubagentManager` |

**Detailed instructions:**

1. **`SkillsLoader`** class:

   - **Skill format**: Each skill is a directory with a `SKILL.md` file containing YAML frontmatter:
     ```markdown
     ---
     name: github
     description: GitHub integration for issues, PRs, and repos
     version: 1.0
     requirements:
       - gh CLI installed
     always_load: false
     ---

     # GitHub Skill

     You can use the `gh` CLI tool to interact with GitHub...
     (full instructions for the agent)
     ```

   - **`__init__(self, workspace_dir, builtin_dir)`**: Set paths to user skills (`workspace_dir/skills/`) and built-in skills (`nanobot/skills/`).

   - **`load_skills(self) -> dict[str, Skill]`**:
     1. Scan both directories for `*/SKILL.md` files
     2. Parse YAML frontmatter to extract metadata
     3. Return dict of skill name → Skill object
     4. User skills override built-in skills with same name

   - **`get_skills_summary(self) -> str`**: Return a compact summary of all available skills (name + one-line description) for inclusion in the system prompt. This lets the LLM know what skills exist without loading full instructions.

   - **`get_skill_content(self, name) -> str`**: Return the full Markdown content of a skill (after frontmatter). Used when the agent needs the full instructions for a specific skill.

   - **`always_loaded_skills(self) -> list[str]`**: Return skills with `always_load: true` in frontmatter. These are always included in the system prompt.

   - **Progressive loading**: Don't load all skill content into context. Instead:
     1. Always include skill summaries in system prompt
     2. Only include full content for `always_load` skills
     3. Agent can request full skill content on-demand via a tool or instruction

2. **`SubagentManager`** class:

   - **`__init__(self, agent_loop)`**: Store reference to the main agent loop (for creating sub-loops).

   - **`async spawn(self, task, channel=None, chat_id=None) -> str`**:
     1. Create a unique task ID
     2. Create a new asyncio Task:
        - Build a fresh context with the task as user message
        - Call LLM with full tool access
        - Execute tools as needed
        - Collect final response
     3. If channel/chat_id provided, send result as OutboundMessage
     4. Return task ID immediately (don't wait for completion)

   - **`_tasks: dict[str, asyncio.Task]`**: Track running tasks.
   - **`cancel(self, task_id)`**: Cancel a running task.
   - **`list_tasks(self) -> list[dict]`**: Return status of all tasks.
   - **`get_result(self, task_id) -> str | None`**: Get result if task is complete.

**Acceptance criteria:**
- [ ] Skills are discovered from both workspace and built-in directories
- [ ] YAML frontmatter is parsed correctly
- [ ] Skill summaries are generated for system prompt
- [ ] always_load skills are included in context
- [ ] Subagents run in background and complete independently
- [ ] Subagent results can be delivered to channels
- [ ] Tasks can be cancelled

---

### TICKET-031: Additional LLM Providers

**PR Title:** `feat: Azure OpenAI, Custom, and OpenAI Codex providers`
**Estimated Size:** ~590 lines | **Depends on:** TICKET-003, TICKET-004

**Goal:** Add specialized provider implementations for Azure OpenAI, custom OpenAI-compatible endpoints, and OpenAI Codex with OAuth.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `nanobot/providers/azure_openai_provider.py` | ~212 | Azure OpenAI provider |
| `nanobot/providers/custom_provider.py` | ~62 | Custom endpoint provider |
| `nanobot/providers/openai_codex_provider.py` | ~317 | OpenAI Codex with OAuth |
| `tests/test_azure_openai_provider.py` | ~50 | Azure tests |

**Detailed instructions:**

1. **`AzureOpenAIProvider(LLMProvider)`**:
   - Uses Azure's OpenAI Service endpoints (different URL pattern from OpenAI)
   - **Config**: `base_url` (Azure resource URL), `api_key`, `api_version`, `deployment_name`
   - **URL construction**: `{base_url}/openai/deployments/{deployment}/chat/completions?api-version={version}`
   - **Auth**: `api-key` header (not `Authorization: Bearer`)
   - Use httpx for direct API calls (not litellm) for full control over Azure-specific parameters
   - Handle Azure-specific response format differences
   - Support Azure content filtering results in response

2. **`CustomProvider(LLMProvider)`**:
   - Simple OpenAI-compatible provider for:
     - Local models (LM Studio, llama.cpp, Ollama)
     - Self-hosted API proxies
   - **Config**: `base_url` (required), `api_key` (optional), `model` (required)
   - Use httpx to call `{base_url}/v1/chat/completions`
   - Minimal implementation — just format the request and parse the response
   - Don't require API key if not configured (local models often don't need one)

3. **`OpenAICodexProvider(LLMProvider)`**:
   - OAuth-based authentication for OpenAI's Codex service
   - **OAuth flow**:
     1. Open browser to authorization URL
     2. User grants access
     3. Receive callback with authorization code
     4. Exchange code for access token
     5. Store token for future use (with refresh)
   - **Token management**: Store tokens in config dir, auto-refresh when expired
   - **API calls**: Use access token in `Authorization: Bearer` header
   - Handle OAuth errors (expired tokens, revoked access)
   - CLI integration: `nanobot codex login` command for OAuth flow

**Acceptance criteria:**
- [ ] Azure provider works with deployment-based URLs
- [ ] Azure API key authentication works
- [ ] Custom provider connects to local models (e.g., Ollama)
- [ ] Codex OAuth login flow completes successfully
- [ ] Token refresh works for Codex
- [ ] All providers handle errors gracefully

---

### TICKET-032: Templates & Built-in Skills

**PR Title:** `feat: workspace templates and built-in skills (GitHub, weather, summarize, etc.)`
**Estimated Size:** ~400 lines Markdown + ~600 lines Python (scripts) | **Depends on:** TICKET-030

**Goal:** Create the workspace template files and built-in skill definitions.

**Files to create:**

| File | Purpose |
|------|---------|
| `nanobot/templates/SOUL.md` | Agent personality/tone template |
| `nanobot/templates/USER.md` | User context template |
| `nanobot/templates/AGENTS.md` | Agent behavior instructions template |
| `nanobot/templates/TOOLS.md` | Tool usage guidelines template |
| `nanobot/templates/memory/MEMORY.md` | Empty memory template |
| `nanobot/skills/README.md` | Skills documentation |
| `nanobot/skills/github/SKILL.md` | GitHub CLI skill |
| `nanobot/skills/weather/SKILL.md` | Weather lookup skill |
| `nanobot/skills/summarize/SKILL.md` | URL/file summarization skill |
| `nanobot/skills/tmux/SKILL.md` | Tmux remote control skill |
| `nanobot/skills/memory/SKILL.md` | Memory management skill |
| `nanobot/skills/cron/SKILL.md` | Cron scheduling skill |
| `nanobot/skills/clawhub/SKILL.md` | ClawHub skill discovery |
| `nanobot/skills/skill-creator/SKILL.md` | Create new skills |
| `nanobot/skills/skill-creator/scripts/init_skill.py` | Skill scaffolding script |
| `nanobot/skills/skill-creator/scripts/quick_validate.py` | Skill validation script |

**Detailed instructions:**

1. **Templates** (copied to workspace on `nanobot onboard`):

   - **SOUL.md**: Define agent personality:
     ```markdown
     # Personality
     You are a helpful, concise AI assistant. You prefer to:
     - Give direct answers without unnecessary caveats
     - Use tools proactively to accomplish tasks
     - Ask for clarification only when truly needed
     - Remember user preferences and context
     ```

   - **AGENTS.md**: Define agent behavior rules:
     ```markdown
     # Agent Behavior
     - Always check if a task can be done with available tools before saying you can't
     - For multi-step tasks, plan first, then execute
     - Save important findings to memory
     - When errors occur, try alternative approaches before giving up
     ```

   - **TOOLS.md**: Tool-specific instructions (how to use each tool effectively)

   - **USER.md**: Placeholder for user to fill in their context

2. **Built-in Skills**: Each SKILL.md should have:
   - YAML frontmatter with name, description, version, requirements
   - Detailed instructions for the agent on how to use the skill
   - Example commands/workflows

   - **GitHub skill**: Instructions for using `gh` CLI (issues, PRs, repos, actions)
   - **Weather skill**: Instructions for using wttr.in and Open-Meteo APIs via web_fetch
   - **Summarize skill**: Instructions for summarizing URLs, files, YouTube videos
   - **Tmux skill**: Instructions for managing remote tmux sessions via shell
   - **Memory skill**: Instructions for memory management best practices
   - **Cron skill**: Instructions for scheduling tasks
   - **ClawHub skill**: Instructions for discovering skills from clawhub.ai
   - **Skill-creator**: Tool + scripts for scaffolding new skills

3. **Skill-creator scripts** (Python):
   - `init_skill.py`: Create a new skill directory with SKILL.md template
   - `quick_validate.py`: Validate SKILL.md format (frontmatter, required fields)

**Acceptance criteria:**
- [ ] `nanobot onboard` copies templates to workspace
- [ ] All built-in skills have valid SKILL.md format
- [ ] Skills loader finds and parses all built-in skills
- [ ] Skill-creator scripts work
- [ ] Templates are sensible defaults for new users

---

### TICKET-033: Docker, Docker Compose & CI/CD

**PR Title:** `feat: Docker containerization and GitHub Actions CI pipeline`
**Estimated Size:** ~200 lines | **Depends on:** All previous PRs

**Goal:** Containerize the application and set up continuous integration.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `Dockerfile` | ~50 | Multi-stage Docker build |
| `docker-compose.yml` | ~60 | Service orchestration |
| `.github/workflows/ci.yml` | ~60 | CI pipeline |
| `.dockerignore` | ~15 | Docker build exclusions |
| `SECURITY.md` | ~20 | Security guidelines |
| `LICENSE` | ~20 | MIT License |

**Detailed instructions:**

1. **Dockerfile**:
   - **Base image**: `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` (fast Python package management)
   - **Stage 1** - Install dependencies:
     - Copy `pyproject.toml` and lock file
     - Run `uv pip install` to install Python dependencies
   - **Stage 2** - Install Node.js (for WhatsApp bridge):
     - Install Node.js 20 via nodesource
     - Copy bridge/ directory
     - Run `npm install` in bridge/
   - **Stage 3** - Copy application code:
     - Copy `nanobot/` directory
     - Set `PYTHONPATH`
     - Expose port 18790 (gateway)
     - Default command: `nanobot gateway`

2. **docker-compose.yml**: Define two services:
   - **nanobot-gateway**:
     - Build from Dockerfile
     - Port mapping: 18790:18790
     - Volume mounts: `~/.nanobot:/root/.nanobot` (config persistence)
     - Environment: pass through API keys
     - Resource limits: 1 CPU, 1GB memory
     - Restart policy: unless-stopped
   - **nanobot-cli**:
     - Same build, but `profiles: ["cli"]` (not started by default)
     - Command: `nanobot agent` (interactive mode)
     - `stdin_open: true`, `tty: true`
     - Same volume mounts

3. **`.github/workflows/ci.yml`**: GitHub Actions pipeline:
   - **Trigger**: Push to main, pull requests
   - **Jobs**:
     - **lint**: Run `ruff check nanobot/`
     - **test**: Run `pytest tests/ -v` with Python 3.11 and 3.12
     - **build**: Build Docker image (don't push)
   - Cache pip dependencies for speed

4. **`.dockerignore`**: Exclude tests, docs, .git, __pycache__, .env files

5. **SECURITY.md**: Document security considerations:
   - API key handling (never log, use env vars)
   - `allow_from` is deny-by-default
   - Shell tool risks and mitigations
   - Reporting vulnerabilities

**Acceptance criteria:**
- [ ] `docker build .` succeeds
- [ ] `docker-compose up` starts the gateway
- [ ] Config is persisted via volume mount
- [ ] CI pipeline runs lint and tests on PRs
- [ ] Docker image size is reasonable (< 1GB)

---

## Summary

| PR | Title | Est. Lines | Phase | Dependencies |
|----|-------|-----------|-------|--------------|
| 1 | Project Scaffolding & Core Infrastructure | ~350 | Foundation | None |
| 2 | Configuration Schema & Loader | ~540 | Foundation | PR 1 |
| 3 | LLM Provider Base & Response Types | ~270 | Foundation | PR 1 |
| 4 | Provider Registry & Auto-Detection | ~520 | Foundation | PR 3 |
| 5 | LiteLLM Provider & Transcription | ~420 | Foundation | PR 3, 4 |
| 6 | Tool System Foundation | ~430 | Agent | PR 1 |
| 7 | Filesystem Tools | ~365 | Agent | PR 6 |
| 8 | Context Builder | ~190 | Agent | PR 6 |
| 9 | Session Manager | ~215 | Agent | PR 1 |
| 10 | Agent Loop | ~500 | Agent | PR 5, 6, 8, 9 |
| 11 | Memory System | ~360 | Agent | PR 9, 10 |
| 12 | CLI Core Commands & Onboarding | ~500 | UI | PR 10 |
| 13 | CLI Interactive Shell & Gateway | ~470 | UI | PR 12 |
| 14 | Channel Infrastructure | ~330 | Channels | PR 10 |
| 15 | Telegram Channel | ~780 | Channels | PR 14 |
| 16 | Discord Channel | ~380 | Channels | PR 14 |
| 17 | Slack Channel | ~280 | Channels | PR 14 |
| 18 | Feishu/Lark Channel | ~1005 | Channels | PR 14 |
| 19 | DingTalk Channel | ~475 | Channels | PR 14 |
| 20 | Matrix Channel | ~715 | Channels | PR 14 |
| 21 | Email Channel | ~410 | Channels | PR 14 |
| 22 | WeChat Work Channel | ~355 | Channels | PR 14 |
| 23 | QQ Channel | ~160 | Channels | PR 14 |
| 24 | WhatsApp Channel + Bridge | ~470 | Channels | PR 14 |
| 25 | Mochat Channel | ~900 | Channels | PR 14 |
| 26 | Web Search & Fetch Tools | ~325 | Advanced | PR 6 |
| 27 | MCP, Message & Spawn Tools | ~320 | Advanced | PR 6, 14 |
| 28 | Cron Scheduling System | ~595 | Advanced | PR 10 |
| 29 | Heartbeat Service | ~175 | Advanced | PR 10 |
| 30 | Skills System & Subagent Manager | ~460 | Advanced | PR 10 |
| 31 | Additional LLM Providers | ~590 | Advanced | PR 3, 4 |
| 32 | Templates & Built-in Skills | ~1000 | Advanced | PR 30 |
| 33 | Docker, Compose & CI/CD | ~200 | Infra | All |

**Total estimated production code: ~13,500 lines**

---

## Development Order & Parallelism

```
Phase 1 (Sequential):   PR1 → PR2 → PR3 → PR4 → PR5
Phase 2 (Partial parallel):
  PR6 → PR7 (tools)          can start after PR1
  PR8 (context)              can start after PR6
  PR9 (session)              can start after PR1
  PR10 (agent loop)          needs PR5, PR6, PR8, PR9
  PR11 (memory)              needs PR9, PR10
Phase 3: PR12 → PR13        needs PR10
Phase 4 (Parallel):
  PR14 (channel infra)       needs PR10
  PR15-PR25 (channels)       all need PR14, can be done in parallel
Phase 5 (Parallel):
  PR26-PR27 (tools)          need PR6
  PR28-PR30 (services)       need PR10
  PR31 (providers)           needs PR3, PR4
  PR32 (skills/templates)    needs PR30
  PR33 (docker/CI)           needs all others
```

**Critical path:** PR1 → PR3 → PR4 → PR5 → PR10 → PR14 → [channels in parallel]

**Fastest completion with 3 developers:**
- Dev A: PRs 1, 2, 3, 4, 5, 10, 12, 13
- Dev B: PRs 6, 7, 8, 26, 27, 14, 15, 16, 17
- Dev C: PRs 9, 11, 28, 29, 30, 31, 32, 18-25, 33
