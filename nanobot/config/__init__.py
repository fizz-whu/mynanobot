from nanobot.config.paths import ConfigPaths
from nanobot.config.schema import (
    AgentConfig,
    ChannelsConfig,
    DingTalkConfig,
    DiscordConfig,
    EmailConfig,
    FeishuConfig,
    FilesystemConfig,
    GatewayConfig,
    MatrixConfig,
    MochatConfig,
    NanobotConfig,
    ProviderConfig,
    QQConfig,
    ShellConfig,
    SlackConfig,
    TelegramConfig,
    ToolsConfig,
    WecomConfig,
    WhatsAppConfig,
    WebSearchConfig,
)
from nanobot.config.loader import (
    load_config,
    save_config,
    create_default_config,
    create_default_config_with_comments,
)

_config_instance: ConfigPaths | None = None


def get_config() -> ConfigPaths:
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigPaths()
    return _config_instance


__all__ = [
    "get_config",
    "ConfigPaths",
    "NanobotConfig",
    "ProviderConfig",
    "AgentConfig",
    "ChannelsConfig",
    "TelegramConfig",
    "DiscordConfig",
    "SlackConfig",
    "FeishuConfig",
    "DingTalkConfig",
    "MatrixConfig",
    "EmailConfig",
    "WecomConfig",
    "QQConfig",
    "WhatsAppConfig",
    "MochatConfig",
    "ToolsConfig",
    "ShellConfig",
    "FilesystemConfig",
    "WebSearchConfig",
    "GatewayConfig",
    "load_config",
    "save_config",
    "create_default_config",
    "create_default_config_with_comments",
]
