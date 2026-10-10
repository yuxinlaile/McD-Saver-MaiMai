"""mcd_client 单元测试——全部用例不发起任何网络请求。"""
import json

import pytest

from mcd_client import (
    AuthError,
    McdMcpClient,
    _parse_sse,
    load_token,
    result_to_text,
)


# ---------------------------------------------------------------------------
# SSE 解析
# ---------------------------------------------------------------------------
class TestParseSse:
    def test_single_event(self):
        body = 'data: {"jsonrpc": "2.0", "id": 1}\n\n'
        assert _parse_sse(body) == [{"jsonrpc": "2.0", "id": 1}]

    def test_multiline_data_is_joined(self):
        # Streamable HTTP 规范：多行 data: 以换行拼接后再解析 JSON
        body = 'data: {"a":\ndata: 1}\n\n'
        assert _parse_sse(body) == [{"a": 1}]

    def test_comments_and_empty_blocks_ignored(self):
        body = ": ping\n\n: keep-alive\n\ndata: {\"id\": 2}\n\n"
        assert _parse_sse(body) == [{"id": 2}]

    def test_multiple_events_in_order(self):
        body = 'data: {"id": 1}\n\ndata: {"id": 2}\n\n'
        assert [e["id"] for e in _parse_sse(body)] == [1, 2]

    def test_invalid_json_skipped(self):
        body = 'data: not-json\n\ndata: {"ok": true}\n\n'
        assert _parse_sse(body) == [{"ok": True}]

    def test_empty_body(self):
        assert _parse_sse("") == []


# ---------------------------------------------------------------------------
# Token 解析优先级：CLI 参数 > 环境变量 > Token 文件
# ---------------------------------------------------------------------------
class TestLoadToken:
    def test_cli_token_wins(self, monkeypatch):
        monkeypatch.setenv("MCD_MCP_TOKEN", "env-token")
        assert load_token("cli-token") == "cli-token"

    def test_env_token_stripped(self, monkeypatch):
        monkeypatch.setenv("MCD_MCP_TOKEN", " env-token ")
        assert load_token(None) == "env-token"

    def test_token_file_fallback(self, monkeypatch, tmp_path):
        token_file = tmp_path / "token.txt"
        token_file.write_text("file-token\n", encoding="utf-8")
        monkeypatch.delenv("MCD_MCP_TOKEN", raising=False)
        monkeypatch.setenv("MCD_MCP_TOKEN_FILE", str(token_file))
        assert load_token(None) == "file-token"

    def test_missing_everything_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.delenv("MCD_MCP_TOKEN", raising=False)
        monkeypatch.setenv("MCD_MCP_TOKEN_FILE", str(tmp_path / "nope.txt"))
        assert load_token(None) is None


# ---------------------------------------------------------------------------
# 客户端（不联网）
# ---------------------------------------------------------------------------
class TestClient:
    def test_missing_token_raises_auth_error(self):
        with pytest.raises(AuthError) as exc_info:
            McdMcpClient(token=None)
        assert "open.mcd.cn" in str(exc_info.value)

    def test_headers_bearer_and_session(self):
        client = McdMcpClient(token="secret-token")
        client.session_id = "session-abc"
        headers = client._headers()
        assert headers["Authorization"] == "Bearer secret-token"
        assert headers["Mcp-Session-Id"] == "session-abc"
        assert "text/event-stream" in headers["Accept"]

    def test_no_session_header_before_initialize(self):
        headers = McdMcpClient(token="t")._headers()
        assert "Mcp-Session-Id" not in headers

    def test_decode_json_payload(self):
        client = McdMcpClient(token="t")
        raw = '{"jsonrpc": "2.0", "id": 1, "result": {}}'
        assert client._decode_payload(raw, "application/json")["id"] == 1

    def test_decode_sse_payload(self):
        client = McdMcpClient(token="t")
        assert client._decode_payload('data: {"id": 7}\n\n', "text/event-stream") == {"id": 7}

    def test_decode_empty_body_returns_none(self):
        client = McdMcpClient(token="t")
        assert client._decode_payload("", "application/json") is None

    def test_decode_unparseable_returns_none(self):
        client = McdMcpClient(token="t")
        assert client._decode_payload("hello", "text/plain") is None


# ---------------------------------------------------------------------------
# 结果转文本
# ---------------------------------------------------------------------------
class TestResultToText:
    def test_text_blocks_joined(self):
        result = {"content": [{"type": "text", "text": "A"}, {"type": "text", "text": "B"}]}
        assert result_to_text(result) == "A\nB"

    def test_non_text_blocks_serialized(self):
        result = {"content": [{"type": "image", "data": "x"}]}
        assert '"type": "image"' in result_to_text(result)

    def test_fallback_to_json(self):
        assert json.loads(result_to_text({"x": 1})) == {"x": 1}
