# 01 · Ingestion and Anchoring

The front of the pipeline, and the foundation of everything downstream. The timestamp and the fragment are the root of the entire trace: if a claim cannot be tied back to a `(speaker, start_ms, end_ms)` tuple or an image region, it cannot be grounded, attributed, or audited. Get this layer right and freeze it before building anything else.

The plane has two parallel tracks — audio and visual — that both terminate in one immutable evidence table.

---

## 1. Audio track — WhisperX

### What it is

WhisperX (BSD-licensed, `m-bain/whisperX`) is a three-stage speech-to-text pipeline that produces **word-level timestamps** and **per-word speaker labels** for long-form audio. Vanilla Whisper emits segment-level timestamps accurate to roughly ±500 ms; WhisperX uses forced phoneme alignment to tighten this to roughly ±50 ms at the word level. That tightening is what makes a transcript a usable anchor: you need to point at the exact phrase a requirement came from, not a thirty-second window.

### The three stages

1. **Transcription — faster-whisper.** The backend is `faster-whisper`, a CTranslate2 reimplementation of Whisper that runs batched inference at roughly 70× real-time on a capable GPU. It produces the raw transcript with coarse segment timestamps.
2. **Forced alignment — wav2vec2.** A `wav2vec2` phoneme model aligns the transcript text against the audio waveform, yielding a precise start and end time for every word. This is the step that produces the anchor precision.
3. **Diarization — pyannote.audio 3.1.** Speaker diarization segments the audio by speaker, and WhisperX assigns each aligned word to a speaker. The output is the canonical array of `(word, start, end, speaker)`.

### Outputs and the canonical anchor table

WhisperX can emit JSON, SRT, VTT, and TSV. The artifact you care about is the **word array**: a flat, ordered list of `(word, start_ms, end_ms, speaker)`. Persist this verbatim as the canonical anchor table. Every transcript fragment used downstream is a contiguous slice of this array, and every fragment carries the speaker and the start/end of its slice. Treat the word array as immutable once written.

### Operational notes and caveats

- WhisperX requires a Hugging Face token, and the pyannote models are gated. **Check the pyannote license terms for commercial use** before relying on it in production.
- faster-whisper benefits substantially from GPU; budget for it.
- Diarization quality degrades with heavy crosstalk and poor microphone separation. The diarization is a best-effort speaker label, not ground truth — record that uncertainty if a speaker label is shaky, because a misattributed requirement source is a real failure mode.

### Alternatives

- **faster-whisper directly** (use as the backend and bring your own diarization with pyannote) if you want a custom pipeline.
- **whisper.cpp** for CPU/edge deployment in C++.
- **NVIDIA NeMo** as an alternative ASR + diarization stack.
- **pyannote.audio** is the diarization workhorse regardless of which transcriber you pair it with.

---

## 2. Visual track — frames and OCR

Meetings are not only audio. Whiteboards, shared screens, and diagrams carry requirements that are never spoken aloud — and capturing them is one of the few ways to recover context that a pure transcript loses (see the tacit-knowledge limit in `08` §3). The visual track is a real expansion of what is anchorable.

### Frame extraction — ffmpeg

Use `ffmpeg` to extract frames, either on scene-change detection (capture when the shared screen changes materially) or on demand at specific timestamps. Each extracted frame gets a capture timestamp so it can be placed on the meeting timeline alongside the transcript.

### OCR and layout — PaddleOCR / PP-StructureV3

PaddleOCR (Apache-2.0, Baidu) is the recommended OCR engine for complex layouts:

- **PP-OCRv5** handles multilingual text recognition.
- **PP-StructureV3** does layout analysis, table recognition, and key-value extraction — important because a whiteboard or a shared spreadsheet is structured, not a flat paragraph.
- It runs offline, which matters for keeping client meeting data local (see the privacy obligations in `08` §6).

For simple, clean text, **Tesseract** (Apache-2.0) is adequate and lighter. EasyOCR and docTR are alternatives.

### Vision-language models for hard cases

For genuinely hard visual understanding — hand-drawn architecture diagrams, flowcharts, sketches where OCR alone misses the meaning — route the frame to an open-weight vision-language model (e.g., Qwen2.5-VL). This is optional and the tradeoff is GPU cost; reach for it only when OCR plus layout analysis demonstrably fails on your material.

### Image region records

The output of the visual track is the **image region record**: `(image_id, bbox, ocr_text, captured_at_ms)`. A bounding box on a captured frame, the text or interpretation extracted from it, and when it was captured. This is the visual analogue of a transcript fragment, and it is a first-class evidence entity.

---

## 3. The anchor contract

This is the contract the entire rest of the system depends on. Build it, freeze its shape, and treat it as the immutable root of every trace.

Every piece of evidence is exactly one of two record types, and each has a stable id:

```
transcript_fragment
    fragment_id   (stable, immutable)
    speaker
    start_ms
    end_ms
    text          (the slice of the canonical word array)

image_region
    region_id     (stable, immutable)
    image_id
    bbox
    ocr_text
    captured_at_ms
```

Every downstream claim — every hypothesis, every requirement, every conflict — references one or more of these evidence ids. That reference is what the backward walk terminates on and what the forward walk starts from (see `05` §7). In the W3C PROV model these records are the leaf `Entity` nodes of the lineage graph (`05` §5).

Two rules keep the contract sound:

1. **Stable ids before anything else.** The Stage 0 gate (`00` §4) is that every fragment has a stable id and a locator before any retrieval or agent work begins. An id that changes between runs breaks every link that points at it.
2. **Immutability.** Evidence rows are append-only and never edited. If transcription is re-run, it produces new rows with new ids; it does not mutate existing ones. This is what lets a months-old requirement still resolve to the exact fragment it was drawn from.

### Why chunking must respect these boundaries

The retrieval layer (`02`) chunks this evidence for embedding and search. The hard rule there — chunks never cross a speaker turn or a timestamp boundary — exists so that every retrievable chunk maps cleanly back to a single evidence record. The anchor contract is what that rule protects. If a chunk spanned two speakers, a requirement retrieved from it could not be attributed to one source, and the whole traceability chain would blur at its root.
