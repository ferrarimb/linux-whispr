"""Download, list, and delete Whisper models."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from linux_whispr.constants import MODELS_DIR, SUPPORTED_WHISPER_MODELS

logger = logging.getLogger(__name__)

# Approximate model sizes in MB (for display purposes)
MODEL_SIZES: dict[str, int] = {
    "tiny": 75,
    "base": 150,
    "small": 500,
    "medium": 1500,
    "large-v3": 3100,
    "large-v3-turbo": 1600,
    "distil-large-v3": 1500,
}


@dataclass
class ModelInfo:
    """Information about a Whisper model."""

    name: str
    size_mb: int
    downloaded: bool
    path: Path | None = None


class ModelManager:
    """Manages Whisper model downloads, listing, and deletion."""

    def __init__(self, models_dir: Path | None = None) -> None:
        self._models_dir = models_dir or MODELS_DIR

    def list_models(self) -> list[ModelInfo]:
        """List all supported models and their download status."""
        models: list[ModelInfo] = []
        for name in SUPPORTED_WHISPER_MODELS:
            model_path = self._get_model_path(name)
            downloaded = model_path is not None and model_path.exists()
            models.append(
                ModelInfo(
                    name=name,
                    size_mb=MODEL_SIZES.get(name, 0),
                    downloaded=downloaded,
                    path=model_path if downloaded else None,
                )
            )
        return models

    def is_downloaded(self, model_name: str) -> bool:
        """Check if a model is already downloaded."""
        path = self._get_model_path(model_name)
        return path is not None and path.exists()

    def download(
        self,
        model_name: str,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        """Download a Whisper model via huggingface_hub.

        faster-whisper models are hosted on HuggingFace as CTranslate2 conversions.

        Args:
            model_name: Name of the model (e.g., "base", "large-v3-turbo").
            progress_callback: Optional callback with progress 0.0-1.0.

        Returns:
            Path to the downloaded model directory.
        """
        if model_name not in SUPPORTED_WHISPER_MODELS:
            raise ValueError(f"Unsupported model: {model_name}")

        self._models_dir.mkdir(parents=True, exist_ok=True)

        # faster-whisper downloads models from HuggingFace automatically
        # We just need to trigger a load, which will cache the model
        logger.info("Downloading model '%s' (this may take a while)...", model_name)

        try:
            from faster_whisper import WhisperModel

            # This will download the model to the cache directory
            model = WhisperModel(
                model_name,
                device="cpu",
                compute_type="int8",
                download_root=str(self._models_dir),
            )
            # Immediately delete the loaded model to free memory
            del model

            logger.info("Model '%s' downloaded successfully", model_name)
            return self._models_dir / model_name

        except Exception:
            logger.exception("Failed to download model '%s'", model_name)
            raise

    def delete(self, model_name: str) -> bool:
        """Delete a downloaded model. Returns True if deleted."""
        path = self._get_model_path(model_name)
        if path is None or not path.exists():
            logger.warning("Model '%s' not found", model_name)
            return False

        shutil.rmtree(path)
        logger.info("Deleted model '%s' at %s", model_name, path)
        return True

    def get_disk_usage(self) -> int:
        """Get total disk usage of all downloaded models in bytes."""
        if not self._models_dir.exists():
            return 0

        total = 0
        for path in self._models_dir.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        return total

    def _get_model_path(self, model_name: str) -> Path | None:
        """Get the expected path for a model. Returns None if unknown."""
        if model_name not in SUPPORTED_WHISPER_MODELS:
            return None

        # faster-whisper stores models in subdirectories
        # Check various possible directory names
        candidates = [
            self._models_dir / model_name,
            self._models_dir / f"faster-whisper-{model_name}",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        # HuggingFace hub caches models as models--{org}--faster-whisper-{name}
        # Different models may come from different orgs (Systran, mobiuslabsgmbh, etc.)
        if self._models_dir.exists():
            pattern = f"*faster-whisper-{model_name}"
            for child in self._models_dir.iterdir():
                if child.is_dir() and child.name.endswith(f"faster-whisper-{model_name}"):
                    return child

        return self._models_dir / model_name
