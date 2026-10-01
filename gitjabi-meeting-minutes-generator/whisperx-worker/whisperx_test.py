import argparse
import os
import time
from pathlib import Path
from typing import Any

import torch
from dotenv import load_dotenv
from huggingface_hub import HfApi
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


def parse_args(base_dir: Path):
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=str, default=str(base_dir / "test_5min.wav"))
    parser.add_argument("--num-speakers", type=int, default=None)
    parser.add_argument("--min-speakers", type=int, default=None)
    parser.add_argument("--max-speakers", type=int, default=None)
    args = parser.parse_args()

    if args.num_speakers is not None and (
        args.min_speakers is not None or args.max_speakers is not None
    ):
        raise ValueError("Use either --num-speakers or (--min-speakers/--max-speakers), not both.")
    if (
        args.min_speakers is not None
        and args.max_speakers is not None
        and args.min_speakers > args.max_speakers
    ):
        raise ValueError("--min-speakers must be <= --max-speakers.")
    return args


def verify_hf_access(token: str) -> None:
    api = HfApi(token=token)
    try:
        api.whoami()
    except Exception as e:
        raise RuntimeError(
            "Hugging Face token is invalid or expired. Reissue a token with Read access."
        ) from e

    required_models = [
        "pyannote/speaker-diarization-3.1",
        "pyannote/segmentation-3.0",
    ]
    for model_id in required_models:
        try:
            api.model_info(model_id)
        except Exception as e:
            raise RuntimeError(
                f"No access to '{model_id}'. Accept model terms on Hugging Face and ensure token has Read scope."
            ) from e


load_dotenv()
HF_TOKEN = (
    os.getenv("HF_TOKEN")
    or os.getenv("HUGGINGFACE_TOKEN")
    or os.getenv("HF_HUB_TOKEN")
)
if not HF_TOKEN:
    raise ValueError(
        "Hugging Face token not found. Set HF_TOKEN (or HUGGINGFACE_TOKEN / HF_HUB_TOKEN) in .env"
    )

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device)
verify_hf_access(HF_TOKEN)

base_dir = Path(__file__).resolve().parent
args = parse_args(base_dir)
audio_file = Path(args.audio).expanduser().resolve()
if not audio_file.exists():
    raise FileNotFoundError(
        f"Audio file not found: {audio_file}\n"
        f"Current working directory: {Path.cwd()}"
    )

audio_path = str(audio_file)
start = time.time()

# 1) Whisper ASR
model = whisperx.load_model(
    "medium",
    device=device,
    compute_type="float16" if device == "cuda" else "int8",
)
asr_result = model.transcribe(audio_path)

# 2) Alignment
model_a, metadata = whisperx.load_align_model(
    language_code=asr_result["language"],
    device=device,
)
aligned_result = whisperx.align(
    asr_result["segments"],
    model_a,
    metadata,
    audio_path,
    device,
)

# 3) Diarization
diar_model_name = "pyannote/speaker-diarization-3.1"
try:
    diarize_model = whisperx.diarize.DiarizationPipeline(
        use_auth_token=HF_TOKEN,
        device=device,
        model_name=diar_model_name,
    )
except AttributeError as e:
    # Common with pyannote/HF access issues in some whisperx/pyannote combos:
    # pipeline load returns None and then `.to(device)` crashes.
    if "'NoneType' object has no attribute 'to'" in str(e):
        raise RuntimeError(
            "Failed to initialize diarization pipeline. "
            "Check that your HF token can access "
            "'pyannote/speaker-diarization-3.1' and that you accepted model terms on Hugging Face."
        ) from e
    raise

diarize_kwargs = {}
if args.num_speakers is not None:
    diarize_kwargs["min_speakers"] = args.num_speakers
    diarize_kwargs["max_speakers"] = args.num_speakers
else:
    if args.min_speakers is not None:
        diarize_kwargs["min_speakers"] = args.min_speakers
    if args.max_speakers is not None:
        diarize_kwargs["max_speakers"] = args.max_speakers

if diarize_kwargs:
    print("Diarization speaker constraints:", diarize_kwargs)
else:
    print("Diarization speaker constraints: auto")

diarize_segments = diarize_model(audio_path, **diarize_kwargs)

# 4) Speaker assignment
final_result = whisperx.assign_word_speakers(
    diarize_segments,
    aligned_result,
)

end = time.time()

speaker_counts = {}
for seg in final_result["segments"]:
    spk = seg.get("speaker", "UNKNOWN")
    speaker_counts[spk] = speaker_counts.get(spk, 0) + 1
print("Speaker segment counts:", speaker_counts)

for seg in final_result["segments"][:10]:
    speaker = seg.get("speaker", "UNKNOWN")
    print(f"[{seg['start']:.1f}~{seg['end']:.1f}] {speaker}: {seg['text']}")

print("Elapsed:", round(end - start, 2), "sec")
