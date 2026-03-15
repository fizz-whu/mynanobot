from nanobot.config.paths import ConfigPaths

_config_instance: ConfigPaths | None = None


def get_config() -> ConfigPaths:
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigPaths()
    return _config_instance


__all__ = ["get_config", "ConfigPaths"]
