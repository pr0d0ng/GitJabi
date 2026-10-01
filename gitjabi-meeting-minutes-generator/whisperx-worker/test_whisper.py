import os
import time
from pathlib import Path
from typing import Any

import torch
from omegaconf import DictConfig
from omegaconf.base import ContainerMetadata
from omegaconf.listconfig import ListConfig

# Allowlist objects required by some checkpoints when using PyTorch 2.6+
torch.serialization.add_safe_globals([
    Any,
    DictConfig,
    ListConfig,
    ContainerMetadata,
])

# PyTorch 2.6+ defaults torch.load(..., weights_only=True).
# WhisperX/pyannote checkpoints may require full checkpoint loading.
os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")

import whisperx


device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device)

base_dir = Path(__file__).resolve().parent
audio_file = base_dir / "test_5min.wav"
if not audio_file.exists():
    raise FileNotFoundError(
        f"Audio file not found: {audio_file}\n"
        f"Current working directory: {Path.cwd()}"
    )

start = time.time()

model = whisperx.load_model(
    "medium",
    device=device,
    compute_type="float16" if device == "cuda" else "int8",
)

result = model.transcribe(str(audio_file))

end = time.time()

print("Transcription sample:")
for seg in result["segments"][:3]:
    print(f"[{seg['start']:.2f} ~ {seg['end']:.2f}] {seg['text']}")

print("Elapsed:", round(end - start, 2), "seconds")
