import os
import sys
import types
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

deepgram_stub = types.SimpleNamespace(
    DeepgramClient=MagicMock,
    LiveOptions=MagicMock,
    LiveTranscriptionEvents=types.SimpleNamespace(
        Transcript="transcript", Close="close"
    ),
)
sys.modules.setdefault("deepgram", deepgram_stub)

from deepgram_service import DeepgramService


def dummy_callback(text: str, is_final: bool) -> None:
    pass


def test_connect_start_sets_up_websocket():
    client = MagicMock()
    ws = MagicMock()
    client.listen.websocket.v.return_value = ws

    service = DeepgramService(client, on_transcript=dummy_callback)

    assert service._connect() is True
    client.listen.websocket.v.assert_called_once_with("1")
    ws.start.assert_called_once()


def test_send_and_finalize():
    client = MagicMock()
    ws = MagicMock()
    service = DeepgramService(client, on_transcript=dummy_callback)
    service.ws = ws

    chunk = b"data"
    assert service.send(chunk) is True
    ws.send.assert_called_once_with(chunk)

    assert service.finalize() is True
    ws.finish.assert_called_once()
    # Simulate the close event Deepgram emits after finalize so the service
    # can clean up its internal WebSocket reference.
    service._handle_close(None)
    assert service.ws is None


def test_send_failure_triggers_reconnect():
    client = MagicMock()
    ws = MagicMock()
    ws.send.side_effect = Exception("boom")
    service = DeepgramService(client, on_transcript=dummy_callback)
    service.ws = ws
    service.start = MagicMock()

    assert service.send(b"data") is False
    service.start.assert_called_once()


def test_handle_transcript_dict():
    cb = MagicMock()
    service = DeepgramService(MagicMock(), on_transcript=cb)
    result = {"channel": {"alternatives": [{"transcript": "hi"}]}, "is_final": True}
    service._handle_transcript(None, result)
    cb.assert_called_once_with("hi", True)


def test_finalize_does_not_reconnect():
    client = MagicMock()
    ws = MagicMock()
    service = DeepgramService(client, on_transcript=dummy_callback)
    service.ws = ws
    service.start = MagicMock()

    assert service.finalize() is True
    ws.finish.assert_called_once()
    service._handle_close(None)
    service.start.assert_not_called()
    assert service.ws is None
    assert service._closing is False

