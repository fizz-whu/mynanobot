import pytest
import asyncio
import tempfile
import os

from nanobot.bus import InboundMessage, OutboundMessage, message_bus
from nanobot.config import ConfigPaths
from nanobot.utils import (
    ensure_dir, safe_filename, estimate_tokens, estimate_messages_tokens,
    truncate_tool_result, is_image_path, format_timestamp, merge_dicts,
    is_windows, get_shell
)


class TestUtils:
    def test_ensure_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = ensure_dir(os.path.join(tmpdir, 'test', 'nested'))
            assert path.exists()

    def test_safe_filename(self):
        assert safe_filename('test@file#name.txt') == 'testfilenametxt'
        assert safe_filename('hello world') == 'hello-world'

    def test_estimate_tokens(self):
        assert estimate_tokens('hello world') == 2

    def test_estimate_messages_tokens(self):
        msgs = [{'content': 'hello'}, {'content': 'world'}]
        assert estimate_messages_tokens(msgs) == 2

    def test_truncate_tool_result(self):
        long_text = 'a' * 10000
        truncated = truncate_tool_result(long_text, max_tokens=1)
        assert 'truncated' in truncated
        assert len(truncated) < 10000

    def test_is_image_path(self):
        assert is_image_path('test.png') == True
        assert is_image_path('test.jpg') == True
        assert is_image_path('test.txt') == False

    def test_format_timestamp(self):
        ts = format_timestamp()
        assert 'T' in ts
        assert '+' in ts or 'Z' in ts

    def test_merge_dicts(self):
        base = {'a': 1, 'b': {'c': 2}}
        override = {'b': {'d': 3}, 'e': 4}
        merged = merge_dicts(base, override)
        assert merged == {'a': 1, 'b': {'c': 2, 'd': 3}, 'e': 4}

    def test_platform_helpers(self):
        assert is_windows() == False
        assert get_shell() == '/bin/bash'


class TestConfigPaths:
    def test_default_paths(self):
        cp = ConfigPaths()
        assert cp.base_dir == os.path.expanduser('~/.nanobot')
        assert cp.config_file == os.path.expanduser('~/.nanobot/config.yaml')
        assert cp.workspace_dir == os.path.expanduser('~/.nanobot/workspace')
        assert cp.sessions_dir == os.path.expanduser('~/.nanobot/workspace/sessions')
        assert cp.runtime_dir == os.path.expanduser('~/.nanobot/runtime')
        assert cp.media_dir == os.path.expanduser('~/.nanobot/runtime/media')

    def test_custom_nanobot_home(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cp = ConfigPaths(nanobot_home=tmpdir)
            assert cp.base_dir == tmpdir

    def test_instance_suffix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cp = ConfigPaths(nanobot_home=tmpdir, instance='test')
            assert str(cp.base_dir).endswith('.nanobot_test')

    def test_ensure_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cp = ConfigPaths(nanobot_home=tmpdir)
            cp.ensure_directories()
            assert cp.base_dir.exists()
            assert cp.workspace_dir.exists()
            assert cp.sessions_dir.exists()
            assert cp.runtime_dir.exists()
            assert cp.media_dir.exists()


class TestMessageBus:
    @pytest.mark.asyncio
    async def test_publish_consume_inbound(self):
        bus = message_bus
        msg = InboundMessage(channel='test', sender_id='user1', chat_id='chat1', content='hello')
        await bus.publish_inbound(msg)
        received = await bus.consume_inbound()
        assert received.content == 'hello'
        assert received.channel == 'test'

    @pytest.mark.asyncio
    async def test_publish_consume_outbound(self):
        bus = message_bus
        msg = OutboundMessage(channel='test', chat_id='chat1', content='response')
        await bus.publish_outbound(msg)
        received = await bus.consume_outbound()
        assert received.content == 'response'
        assert received.channel == 'test'
