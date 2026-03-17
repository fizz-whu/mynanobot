import os
from pathlib import Path
from typing import Any

import yaml

from nanobot.config.schema import NanobotConfig


def load_config(path: str | Path) -> NanobotConfig:
    path = Path(path)
    if not path.exists():
        return NanobotConfig()
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    
    return NanobotConfig.model_validate(data)


def save_config(config: NanobotConfig, path: str | Path) -> None:
    path = Path(path)
    tmp_path = path.with_suffix(".yaml.tmp")
    
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.dump(
            config.model_dump(exclude_none=True),
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
    
    tmp_path.replace(path)


def create_default_config(path: str | Path) -> NanobotConfig:
    config = NanobotConfig()
    save_config(config, path)
    return config


DEFAULT_CONFIG_YAML = """\
# Nanobot Configuration
# ====================

# LLM Providers
# Add your API keys and configure models here
providers:
  openai:
    name: openai
    api_key: ${OPENAI_API_KEY:""}
    model: gpt-4o

# Agent Settings
agent:
  name: nanobot
  model: gpt-4o
  max_iterations: 40
  max_tokens: 65536
  temperature: null
  prompt_cache: true

# Gateway Settings
gateway:
  host: 0.0.0.0
  port: 18790
  api_key: null

# Tools Configuration
tools:
  shell:
    timeout: 120
    allowed_commands: []
  filesystem:
    allowed_paths: []
    max_file_size: 10485760
  web_search:
    provider: ddgs
    api_key: null
    base_url: null
    proxy: null

# Channel Configuration
channels:
  telegram:
    enabled: false
    token: ""
    allow_from: []
    proxy: null
    group_policy: mention
  discord:
    enabled: false
    token: ""
    allow_from: []
    command_prefix: "/"
  slack:
    enabled: false
    app_token: ""
    bot_token: ""
    allow_from: []
  # Add more channels as needed

# MCP Servers
mcp_servers: {}
"""


def create_default_config_with_comments(path: str | Path) -> NanobotConfig:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(DEFAULT_CONFIG_YAML)
    
    return load_config(path)
