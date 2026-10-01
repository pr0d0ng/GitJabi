# Meeting Minutes Pipeline Dataflow

This document explains how data flows from input media to final meeting minutes.

## End-to-End

`meeting_test.mp4`
-> `whisperx-worker/whisperx_key_action_pipeline.py`
-> `whisperx-worker/out/meeting_test.key_action.json` + `.jsonl`
-> `meeting_minutes_pipeline.py` (optional Graph event metadata)
-> Databricks Llama (`LLAMA_ENDPOINT`)
-> `out/meeting_minutes/meeting_test.minutes.md` + `.meta.json`
-> Blob upload (`meeting-minutes/...`)

## Module I/O

### A) WhisperX + key/action classification

File: `whisperx-worker/whisperx_key_action_pipeline.py`

Input:
- `--audio` media path
- HF token and local classifier model dirs

Output:
- `<stem>.key_action.jsonl` (one utterance per line)
- `<stem>.key_action.json` (metadata + utterances)

Utterance fields used downstream:
- `utt_id`, `start`, `end`, `speaker`, `text`
- `key_prob`, `action_prob`, `line_class`

Class policy in this module:
- if `action_prob >= action_threshold` -> `action`
- elif `key_prob >= key_threshold` -> `key`
- else -> `other`

### B) Graph event metadata (optional)

File: `meeting_minutes_pipeline.py` -> `try_get_graph_event_info()`

Input (optional):
- `GRAPH_EVENT_USER_ID`
- `GRAPH_EVENT_ID`

Output:
- `meeting_name`, `start`, `end`, `attendees`, `is_online`

If missing/fail: returns empty dict and pipeline continues.

### C) Prompt builder (where key/action/other are consumed)

File: `meeting_minutes_pipeline.py` -> `build_llama_prompt()`

Source:
- `key_lines = utterances where line_class == 'key'`
- `action_lines = utterances where line_class == 'action'`
- `other_lines = utterances where line_class == 'other'`

Controls:
- `--key-limit` default `180`
- `--action-limit` default `120`
- `--other-sample-limit` default `20`
- `--max-prompt-chars` default `18000`

Important behavior:
- `other` is not fully dropped; sampled across timeline for context.
- If prompt is too long, context (`other`) is reduced first, then `key`.

### D) Databricks Llama call

File: `meeting_minutes_pipeline.py` -> `call_databricks_llama()`

Required env:
- `LLAMA_ENDPOINT`
- `DATABRICKS_TOKEN`

Output:
- minutes markdown text

### E) Save + Blob upload

Local output:
- `out/meeting_minutes/<stem>.minutes.md`
- `out/meeting_minutes/<stem>.minutes.meta.json`

Blob upload:
- container: `BLOB_CONTAINER_NAME` (default `meeting-videos`)
- prefix: `--blob-prefix` (default `meeting-minutes`)

## Why keep some `other`?

`key/action` alone often misses discourse context (who/what/exception/transition).
Small sampled `other` usually improves factual consistency and action ownership.

## Recommended settings for long meetings

- 1~2 hours:
  - `--key-limit 200 --action-limit 150 --other-sample-limit 25 --max-prompt-chars 22000`
- 3+ hours:
  - `--key-limit 160 --action-limit 120 --other-sample-limit 15 --max-prompt-chars 18000`

If quality still drops for very long meetings, use chunked map-reduce summarization as next step.
