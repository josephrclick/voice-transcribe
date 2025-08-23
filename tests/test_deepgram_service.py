import os
import sys
import types
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

deepgram_stub = types.SimpleNamespace(
    DeepgramClient=MagicMock,
    LiveOptions=MagicMock,
    LiveTranscriptionEvents=types.SimpleNamespace(Transcript="transcript", Close="close"),
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
    assert not service._closing.is_set()


def test_punctuation_levels():
    """Test all punctuation sensitivity levels"""
    client = MagicMock()

    test_cases = [
        ("off", {"punctuate": False, "smart_format": False}),
        ("minimal", {"punctuate": True, "smart_format": False}),
        ("balanced", {"punctuate": True, "smart_format": True}),
        ("aggressive", {"punctuate": True, "smart_format": True, "diarize": True}),
    ]

    for level, expected_config in test_cases:
        service = DeepgramService(client, dummy_callback, punctuation_sensitivity=level)
        options = service._get_live_options()

        assert options.punctuate == expected_config["punctuate"]
        assert options.smart_format == expected_config["smart_format"]
        if "diarize" in expected_config:
            assert options.diarize == expected_config["diarize"]


def test_endpointing_configuration():
    """Test endpointing parameter handling"""
    client = MagicMock()

    # Test default value
    service = DeepgramService(client, dummy_callback)
    options = service._get_live_options()
    assert options.endpointing == 400  # Default 400ms

    # Test custom values
    for endpointing_ms in [200, 500, 800, 1000]:
        service = DeepgramService(client, dummy_callback, endpointing_ms=endpointing_ms)
        options = service._get_live_options()
        assert options.endpointing == endpointing_ms


def test_vad_events_enabled():
    """Test Voice Activity Detection integration"""
    client = MagicMock()
    service = DeepgramService(client, dummy_callback)
    options = service._get_live_options()

    assert options.vad_events == True
    assert options.interim_results == True
    assert options.utterance_end_ms == 1000


def test_invalid_punctuation_level_fallback():
    """Test fallback behavior for invalid punctuation levels"""
    client = MagicMock()
    service = DeepgramService(client, dummy_callback, punctuation_sensitivity="invalid")
    options = service._get_live_options()

    # Should fallback to "balanced" defaults
    assert options.punctuate == True
    assert options.smart_format == True


def test_backward_compatibility():
    """Test that existing code without new parameters works"""
    client = MagicMock()

    # This should work exactly like before
    service = DeepgramService(client, dummy_callback)
    options = service._get_live_options()

    # Should have balanced defaults
    assert options.punctuate == True
    assert options.smart_format == True
    assert options.endpointing == 400
    assert options.vad_events == True
    assert options.interim_results == True


def test_get_live_options_structure():
    """Test that _get_live_options returns properly structured LiveOptions"""
    client = MagicMock()
    service = DeepgramService(client, dummy_callback)
    options = service._get_live_options()

    # Test all required parameters are set
    assert options.model == "nova-3"
    assert options.language == "en-US"
    assert options.encoding == "linear16"
    assert options.sample_rate == 16000
    assert options.channels == 1

    # Test new parameters
    assert hasattr(options, "endpointing")
    assert hasattr(options, "utterance_end_ms")
    assert hasattr(options, "vad_events")
    assert hasattr(options, "interim_results")


def test_thread_safety_closing_flag():
    """Test that _closing flag is thread-safe using threading.Event"""
    client = MagicMock()
    service = DeepgramService(client, dummy_callback)

    # Test initial state
    assert not service._closing.is_set()

    # Test setting and clearing
    service._closing.set()
    assert service._closing.is_set()

    service._closing.clear()
    assert not service._closing.is_set()


def test_context_manager_basic():
    """Test basic context manager functionality"""
    client = MagicMock()
    ws = MagicMock()
    client.listen.websocket.v.return_value = ws

    # Mock the start method to avoid threading complexities in tests
    with DeepgramService(client, dummy_callback) as service:
        # Service should be returned
        assert service is not None
        assert isinstance(service, DeepgramService)

    # After context exit, finalize should be called if ws exists
    # Note: In real usage, the WebSocket would be set during start()


def test_context_manager_cleanup_on_exception():
    """Test context manager cleans up even when exceptions occur"""
    client = MagicMock()
    ws = MagicMock()
    client.listen.websocket.v.return_value = ws

    try:
        with DeepgramService(client, dummy_callback) as service:
            service.ws = ws  # Simulate connected state
            raise ValueError("Test exception")
    except ValueError:
        pass  # Expected

    # Even with exception, finalize should be called
    ws.finish.assert_called_once()


def test_context_manager_no_finalize_if_not_connected():
    """Test context manager doesn't call finalize if not connected"""
    client = MagicMock()

    with DeepgramService(client, dummy_callback) as service:
        # Don't set ws - simulate no connection
        pass

    # Since ws is None, no finalize should be attempted
    # This just ensures no exceptions are raised


def test_finalize_thread_safety():
    """Test finalize method properly handles threading.Event"""
    client = MagicMock()
    ws = MagicMock()
    service = DeepgramService(client, dummy_callback)
    service.ws = ws

    # Initial state
    assert not service._closing.is_set()

    # Call finalize
    result = service.finalize()

    # Should set the closing event and call finish
    assert result is True
    ws.finish.assert_called_once()
    assert service._closing.is_set()


def test_finalize_exception_handling():
    """Test finalize properly clears _closing flag on exception"""
    client = MagicMock()
    ws = MagicMock()
    ws.finish.side_effect = Exception("Connection error")
    service = DeepgramService(client, dummy_callback)
    service.ws = ws

    # Call finalize - should handle exception
    result = service.finalize()

    # Should return False and clear the closing flag
    assert result is False
    assert not service._closing.is_set()
    assert service.ws is None
