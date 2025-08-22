# Deepgram Enhancement Sprint Ticket

## Overview

Upgrade Deepgram implementation with Nova-3 features to improve transcription accuracy, user experience, and formatting quality.

## Priority: High

**Estimated Effort:** 2-3 hours  
**Impact:** Significant improvements to transcription quality and UX

---

## Implementation Tasks

### 1. Upgrade to Nova-3-General Model

**File:** `deepgram_service.py:59-67`

**Current:**

```python
model="nova-3"
```

**Update to:**

```python
model="nova-3-general"  # Superior accuracy, 53.4% lower WER
```

**Benefits:**

- 53.4% better WER in streaming mode
- Enhanced background noise handling
- Better far-field audio processing

---

### 2. Add Event Handlers for Better UX

**File:** `deepgram_service.py`

**Add handlers for:**

- `SpeechStarted` - Visual feedback when user starts speaking
- `UtteranceEnd` - Detect when user stops speaking
- `Metadata` - Capture model info and request IDs for debugging
- `Error` - Improved error handling and recovery

**Implementation:**

```python
# In _setup_websocket_handlers()
self.ws_connection.on(LiveTranscriptionEvents.SpeechStarted, self._handle_speech_started)
self.ws_connection.on(LiveTranscriptionEvents.UtteranceEnd, self._handle_utterance_end)
self.ws_connection.on(LiveTranscriptionEvents.Metadata, self._handle_metadata)
self.ws_connection.on(LiveTranscriptionEvents.Error, self._handle_error)

# Add handler methods
def _handle_speech_started(self, *args, **kwargs):
    # Emit signal for UI feedback
    pass

def _handle_utterance_end(self, *args, **kwargs):
    # Handle end of speech segment
    pass

def _handle_metadata(self, metadata, **kwargs):
    # Log model info for debugging
    pass

def _handle_error(self, error, **kwargs):
    # Enhanced error recovery
    pass
```

---

### 3. Implement Filler Words Removal

**File:** `deepgram_service.py:59-67` in `_get_live_options()`

**Add:**

```python
filler_words=True,  # Removes "um", "uh", etc.
```

**Benefit:** Cleaner transcripts without manual post-processing

---

### 4. Add Domain-Specific Keywords Support

**File:** `deepgram_service.py` and `app_config.py`

**Config Addition:**

```python
# In app_config.py
self.custom_keywords = []  # User-configurable keywords
```

**Implementation:**

```python
# In _get_live_options()
keywords=self.custom_keywords if self.custom_keywords else None,
```

**Example keywords format:**

```python
keywords=["API:2", "WebSocket:2", "Deepgram:3"]  # boost weight 1-5
```

**UI Enhancement:** Consider adding text field for users to input custom terms

---

### 5. Enable Paragraph Formatting

**File:** `deepgram_service.py:59-67` in `_get_live_options()`

**Add:**

```python
paragraphs=True,  # Structure output with paragraphs
```

**Benefit:** Better formatted long-form transcripts with natural breaks

---

### 6. Add UtteranceEnd for Better Segmentation

**File:** `deepgram_service.py:59-67` in `_get_live_options()`

**Add:**

```python
utterance_end_ms=1000,  # Detect 1-second gaps between words
interim_results=True,    # Required for utterance_end
```

**Benefit:** More accurate sentence/thought boundaries, especially with background noise

---

## Complete Updated `_get_live_options()` Method

```python
def _get_live_options(self):
    return LiveOptions(
        model="nova-3-general",  # Upgraded model
        punctuate=True,
        interim_results=True,    # Required for utterance_end
        utterance_end_ms=1000,   # Better segmentation
        endpointing=self.endpointing_threshold,
        vad_events=True,
        smart_format=self.smart_format,
        filler_words=True,       # Remove filler words
        paragraphs=True,         # Better formatting
        keywords=self.custom_keywords if hasattr(self, 'custom_keywords') else None,
        language="en-US"         # Keep English-only
    )
```

---

## Testing Checklist

- [ ] Verify nova-3-general model loads correctly
- [ ] Test SpeechStarted event fires when speaking begins
- [ ] Confirm UtteranceEnd detects speech gaps properly
- [ ] Validate filler words are removed from transcripts
- [ ] Test custom keywords boost accuracy for technical terms
- [ ] Verify paragraph formatting improves readability
- [ ] Check error handler provides better recovery
- [ ] Ensure metadata events log useful debugging info

---

## Success Metrics

1. **Accuracy:** Noticeable improvement in transcription accuracy
2. **UX:** Visual feedback when speech is detected
3. **Formatting:** Cleaner transcripts without filler words
4. **Structure:** Natural paragraph breaks in long transcripts
5. **Customization:** Domain-specific terms recognized correctly

---

## Notes

- No profanity filter (user preference for uncensored transcription)
- No PII redaction (solo use only)
- No multilingual support (English-only requirement)
- Most changes are single-line additions to `_get_live_options()`
- Event handlers may require UI updates for visual feedback
