"""Deepgram WebSocket service abstraction."""

import logging
import threading
import time
from typing import Callable, Optional

from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents


class DeepgramService:
    """Manage Deepgram's live transcription WebSocket.

    This service handles connection setup, streaming audio, finalizing and
    automatic reconnection with exponential backoff.
    """

    def __init__(
        self,
        client: DeepgramClient,
        on_transcript: Callable[[str, bool], None],
        on_reconnect: Optional[Callable[[int], None]] = None,
        max_retries: int = 5,
        punctuation_sensitivity: str = "balanced",
        endpointing_ms: int = 400,
        custom_keyterms: Optional[list] = None,
    ) -> None:
        self.client = client
        self.on_transcript = on_transcript
        self.on_reconnect = on_reconnect
        self.max_retries = max_retries
        self.punctuation_sensitivity = punctuation_sensitivity
        self.endpointing_ms = endpointing_ms
        self.custom_keyterms = custom_keyterms or []
        self.ws = None
        self._closing = threading.Event()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    def _validate_keyterms(self, keyterms) -> Optional[list]:
        """Validate keyterms list according to Deepgram constraints.

        Returns validated list of keyterms or None if invalid.
        """
        if not keyterms:
            return None

        if not isinstance(keyterms, list):
            logging.warning("Invalid keyterms type, expected list")
            return None

        # Deepgram limits - conservative estimates
        MAX_KEYTERMS = 100
        MAX_TERM_LENGTH = 100

        validated = []
        for term in keyterms[:MAX_KEYTERMS]:
            if not isinstance(term, str):
                logging.warning(f"Skipping non-string keyterm: {type(term)}")
                continue

            term = term.strip()
            if not term:
                continue

            if len(term) > MAX_TERM_LENGTH:
                logging.warning(f"Truncating keyterm longer than {MAX_TERM_LENGTH} chars: {term[:20]}...")
                term = term[:MAX_TERM_LENGTH]

            validated.append(term)

        if len(keyterms) > MAX_KEYTERMS:
            logging.warning(f"Too many keyterms ({len(keyterms)}), using first {MAX_KEYTERMS}")

        return validated if validated else None

    def _get_live_options(self) -> LiveOptions:
        """Generate Deepgram LiveOptions based on user preferences."""

        # Punctuation mapping
        punctuation_config = {
            "off": {"punctuate": False, "smart_format": False},
            "minimal": {"punctuate": True, "smart_format": False},
            "balanced": {"punctuate": True, "smart_format": True},
            "aggressive": {"punctuate": True, "smart_format": True, "diarize": True},
        }

        config = punctuation_config.get(self.punctuation_sensitivity, punctuation_config["balanced"])

        # Get and validate custom keyterms if available
        keyterms = self._validate_keyterms(getattr(self, "custom_keyterms", None))

        options = {
            "model": "nova-3",  # Keep nova-3 as recommended
            "language": "en-US",
            "endpointing": self.endpointing_ms,  # Key fix: increase from 10ms default
            "utterance_end_ms": 1000,  # Detect longer pauses
            "vad_events": True,  # Enable VAD
            "interim_results": True,  # Required for utterance detection
            "paragraphs": True,  # Better formatting for long transcripts
            **config,  # Apply punctuation settings
            "encoding": "linear16",
            "sample_rate": 16000,
            "channels": 1,
        }

        # Add keyterm if provided (Nova-3 specific)
        if keyterms:
            options["keyterm"] = keyterms

        return LiveOptions(**options)

    def start(self) -> None:
        """Start the WebSocket connection in a background thread."""

        threading.Thread(target=self._connect, daemon=True).start()

    def _connect(self) -> bool:
        attempt = 0
        delay = 1
        while attempt < self.max_retries:
            try:
                ws = self.client.listen.websocket.v("1")

                # Register all event handlers
                ws.on(LiveTranscriptionEvents.Transcript, self._handle_transcript)
                ws.on(LiveTranscriptionEvents.Close, self._handle_close)
                ws.on(LiveTranscriptionEvents.SpeechStarted, self._handle_speech_started)
                ws.on(LiveTranscriptionEvents.UtteranceEnd, self._handle_utterance_end)
                ws.on(LiveTranscriptionEvents.Metadata, self._handle_metadata)
                ws.on(LiveTranscriptionEvents.Error, self._handle_error)

                options = self._get_live_options()
                logging.debug("Starting WebSocket with options: %s", options)
                ws.start(options)
                self.ws = ws
                return True
            except Exception as exc:  # pragma: no cover - network errors
                # Don't show reconnect message if we're intentionally closing
                if self._closing.is_set():
                    return False
                attempt += 1
                if self.on_reconnect:
                    self.on_reconnect(attempt)
                logging.debug("WebSocket error: %s", exc)
                time.sleep(delay)
                delay *= 2

        self.ws = None
        return False

    def _handle_transcript(self, _client, result, **_kwargs) -> None:
        transcript = ""
        is_final = False
        try:
            if isinstance(result, dict):
                transcript = result.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "")
                is_final = result.get("is_final", False)
            else:
                transcript = result.channel.alternatives[0].transcript
                is_final = getattr(result, "is_final", False)
        except Exception as exc:  # pragma: no cover - defensive
            logging.debug("Transcript parse error: %s", exc)
            return

        if transcript:
            self.on_transcript(transcript.strip(), is_final)

    def _handle_close(self, _client, *_args, **_kwargs) -> None:
        """Handle WebSocket close events."""

        # If we've already cleared the socket reference, this close event has
        # been processed (or we purposely finalized), so ignore it to avoid
        # spawning duplicate connections.
        if self.ws is None:
            return

        self.ws = None

        if self._closing.is_set():
            # Expected close after a finalize; do not attempt to reconnect.
            self._closing.clear()
            return

        # Unexpected close – reconnect automatically.
        self.start()

    def _handle_speech_started(self, _client, *args, **kwargs) -> None:
        """Handle speech started events for visual feedback."""
        logging.debug("Speech started detected")
        # Could emit a signal here for UI feedback if needed
        # For now, just log for debugging

    def _handle_utterance_end(self, _client, *args, **kwargs) -> None:
        """Handle utterance end events to detect speech boundaries."""
        logging.debug("Utterance ended")
        # This helps segment natural speech boundaries
        # Could be used to trigger UI updates or finalization logic

    def _handle_metadata(self, _client, metadata, **kwargs) -> None:
        """Handle metadata events for debugging and monitoring."""
        try:
            # Check if metadata exists first
            if not metadata:
                return

            # Use getattr with defaults instead of hasattr
            request_id = getattr(metadata, "request_id", None)
            if request_id:
                logging.debug(f"Deepgram request ID: {request_id}")

            model_info = getattr(metadata, "model_info", None)
            if model_info:
                logging.debug(f"Model info: {model_info}")
        except Exception as exc:
            logging.debug(f"Metadata parse error: {exc}")

    def _handle_error(self, _client, error, **kwargs) -> None:
        """Handle error events with enhanced recovery."""
        logging.error(f"Deepgram error: {error}")
        # Enhanced error recovery could include:
        # - Retry logic with exponential backoff
        # - Fallback to alternative models
        # - User notification of issues
        # Note: Not calling on_reconnect here as it's for reconnection attempts only

    # ------------------------------------------------------------------
    # Streaming API
    # ------------------------------------------------------------------
    def send(self, chunk: bytes) -> bool:
        """Send an audio chunk to Deepgram."""

        if not self.ws:
            return False
        try:
            self.ws.send(chunk)
            return True
        except Exception:  # pragma: no cover - network errors
            self.ws = None
            self.start()
            return False

    def finalize(self) -> bool:
        """Finish the current stream and close the WebSocket."""

        if not self.ws:
            return False
        self._closing.set()
        try:
            self.ws.finish()
            return True
        except Exception:  # pragma: no cover - network errors
            self._closing.clear()
            # Treat as a hard failure; clear socket so future starts create a
            # fresh connection rather than trying to reuse a closed one.
            self.ws = None
            return False

    def is_connected(self) -> bool:
        """Return True if the WebSocket is currently connected."""

        return bool(self.ws)

    # ------------------------------------------------------------------
    # Context manager for resource cleanup
    # ------------------------------------------------------------------
    def __enter__(self):
        """Enter context manager - start the connection."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - ensure proper cleanup."""
        try:
            if self.ws:
                self.finalize()
        except Exception as e:
            logging.error(f"Error during context manager cleanup: {e}")
        finally:
            # Ensure cleanup even on error
            self.ws = None
        return False  # Don't suppress exceptions
