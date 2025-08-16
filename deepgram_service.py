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
    ) -> None:
        self.client = client
        self.on_transcript = on_transcript
        self.on_reconnect = on_reconnect
        self.max_retries = max_retries
        self.ws = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the WebSocket connection in a background thread."""

        threading.Thread(target=self._connect, daemon=True).start()

    def _connect(self) -> bool:
        attempt = 0
        delay = 1
        while attempt < self.max_retries:
            try:
                ws = self.client.listen.websocket.v("1")
                ws.on(
                    LiveTranscriptionEvents.Transcript,
                    self._handle_transcript,
                )
                ws.on(LiveTranscriptionEvents.Close, self._handle_close)

                options = LiveOptions(
                    model="nova-3",
                    language="en",
                    punctuate=True,
                    smart_format=True,
                )
                logging.debug("Starting WebSocket with options: %s", options)
                ws.start(options)
                self.ws = ws
                return True
            except Exception as exc:  # pragma: no cover - network errors
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
                transcript = (
                    result.get("channel", {})
                    .get("alternatives", [{}])[0]
                    .get("transcript", "")
                )
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
        self.ws = None
        self.start()

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
        """Finalize the current stream."""

        if not self.ws:
            return False
        try:
            self.ws.finalize()
            self.ws.finish()
            return True
        except Exception:  # pragma: no cover - network errors
            return False
        finally:
            self.ws = None

    def is_connected(self) -> bool:
        """Return True if the WebSocket is currently connected."""

        return bool(self.ws)

