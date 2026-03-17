import pytest
import tempfile
import os

from nanobot.config import (
    NanobotConfig,
    ProviderConfig,
    AgentConfig,
    load_config,
    save_config,
    create_default_config,
    create_default_config_with_comments,
)


class TestNanobotConfig:
    def test_default_config(self):
        config = NanobotConfig()
        assert config.agent.name == "nanobot"
        assert config.agent.max_iterations == 40
        assert config.gateway.port == 18790
        assert "openai" in config.providers

    def test_provider_config(self):
        provider = ProviderConfig(
            name="openai",
            api_key="test-key",
            model="gpt-4o",
        )
        assert provider.name == "openai"
        assert provider.api_key == "test-key"
        assert provider.model == "gpt-4o"

    def test_agent_config(self):
        agent = AgentConfig(
            name="test-bot",
            model="gpt-4",
            max_iterations=20,
        )
        assert agent.name == "test-bot"
        assert agent.max_iterations == 20

    def test_extra_fields_allowed(self):
        config = NanobotConfig.model_validate({"custom_field": "value"})
        assert config.model_dump().get("custom_field") == "value"


class TestConfigLoader:
    def test_load_config_missing_file(self):
        config = load_config("/nonexistent/path.yaml")
        assert isinstance(config, NanobotConfig)
        assert config.agent.name == "nanobot"

    def test_save_and_load_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.yaml")
            config = NanobotConfig()
            config.agent.name = "test-bot"
            config.agent.model = "gpt-4o"
            
            save_config(config, path)
            loaded = load_config(path)
            
            assert loaded.agent.name == "test-bot"
            assert loaded.agent.model == "gpt-4o"

    def test_roundtrip_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.yaml")
            
            original = NanobotConfig()
            original.agent.name = "roundtrip-bot"
            original.providers["custom"] = ProviderConfig(
                name="custom",
                api_key="key123",
                model="custom-model",
            )
            
            save_config(original, path)
            loaded = load_config(path)
            
            assert loaded.agent.name == "roundtrip-bot"
            assert "custom" in loaded.providers
            assert loaded.providers["custom"].api_key == "key123"

    def test_create_default_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.yaml")
            config = create_default_config(path)
            
            assert os.path.exists(path)
            assert config.agent.name == "nanobot"

    def test_create_default_config_with_comments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.yaml")
            config = create_default_config_with_comments(path)
            
            assert os.path.exists(path)
            assert config.agent.name == "nanobot"
            
            with open(path, "r") as f:
                content = f.read()
                assert "# Nanobot Configuration" in content
