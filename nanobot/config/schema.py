from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = ""
    api_key: str = ""
    base_url: str | None = None
    model: str = ""
    api_version: str | None = None
    extra_headers: dict[str, str] = Field(default_factory=dict)
    extra_params: dict[str, Any] = Field(default_factory=dict)


class ShellConfig(BaseModel):
    timeout: int = 120
    allowed_commands: list[str] = Field(default_factory=list)


class FilesystemConfig(BaseModel):
    allowed_paths: list[str] = Field(default_factory=list)
    max_file_size: int = 10 * 1024 * 1024


class WebSearchConfig(BaseModel):
    provider: str = "ddgs"
    api_key: str | None = None
    base_url: str | None = None
    proxy: str | None = None


class ToolsConfig(BaseModel):
    shell: ShellConfig = Field(default_factory=ShellConfig)
    filesystem: FilesystemConfig = Field(default_factory=FilesystemConfig)
    web_search: WebSearchConfig = Field(default_factory=WebSearchConfig)


class GatewayConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 18790
    api_key: str | None = None


class TelegramConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    token: str = ""
    allow_from: list[str] = Field(default_factory=list)
    proxy: str | None = None
    group_policy: str = "mention"


class DiscordConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    token: str = ""
    allow_from: list[str] = Field(default_factory=list)
    command_prefix: str = "/"


class SlackConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    app_token: str = ""
    bot_token: str = ""
    allow_from: list[str] = Field(default_factory=list)


class FeishuConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    app_id: str = ""
    app_secret: str = ""
    allow_from: list[str] = Field(default_factory=list)
    encrypt_key: str | None = None
    verification_token: str | None = None


class DingTalkConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    client_id: str = ""
    client_secret: str = ""
    allow_from: list[str] = Field(default_factory=list)


class MatrixConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    homeserver: str = ""
    user_id: str = ""
    password: str | None = None
    access_token: str | None = None
    allow_from: list[str] = Field(default_factory=list)


class EmailConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    imap_server: str = ""
    smtp_server: str = ""
    username: str = ""
    password: str = ""
    allow_from: list[str] = Field(default_factory=list)
    poll_interval: int = 60


class WecomConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    corp_id: str = ""
    agent_id: str = ""
    secret: str = ""
    allow_from: list[str] = Field(default_factory=list)


class QQConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    app_id: str = ""
    secret: str = ""
    allow_from: list[str] = Field(default_factory=list)


class WhatsAppConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    bridge_url: str = ""
    allow_from: list[str] = Field(default_factory=list)


class MochatConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    server_url: str = ""
    token: str = ""
    allow_from: list[str] = Field(default_factory=list)


class ChannelsConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)
    feishu: FeishuConfig = Field(default_factory=FeishuConfig)
    dingtalk: DingTalkConfig = Field(default_factory=DingTalkConfig)
    matrix: MatrixConfig = Field(default_factory=MatrixConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    wecom: WecomConfig = Field(default_factory=WecomConfig)
    qq: QQConfig = Field(default_factory=QQConfig)
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)
    mochat: MochatConfig = Field(default_factory=MochatConfig)


class AgentConfig(BaseModel):
    name: str = "nanobot"
    model: str = ""
    max_iterations: int = 40
    max_tokens: int = 65536
    temperature: float | None = None
    prompt_cache: bool = True


class NanobotConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    mcp_servers: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_providers(self):
        if not self.providers:
            default_provider = ProviderConfig(name="openai", model="gpt-4o")
            self.providers = {"openai": default_provider}
        return self
