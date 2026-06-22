import os
import tempfile
from math import gcd

import numpy as np
import soundfile as sf
import torch
from scipy.signal import resample_poly

from config import VAD_THRESHOLD, MIN_SILENCE_MS, MIN_SPEECH_MS


class VADSplitter:
    TARGET_SR = 16000

    def __init__(self):
        print("Loading Silero VAD ...")
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
            trust_repo=True,
        )
        self.model = model
        self._get_ts = utils[0]   # get_speech_timestamps only — avoids broken read_audio
        print("Silero VAD ready.")

    def _load(self, audio_path):
        """Load any audio file as a float32 mono tensor at 16 kHz."""
        data, sr = sf.read(audio_path, dtype="float32")
        if data.ndim == 2:
            data = data.mean(axis=1)
        if sr != self.TARGET_SR:
            g = gcd(int(sr), self.TARGET_SR)
            data = resample_poly(data, self.TARGET_SR // g, sr // g).astype(np.float32)
        return torch.from_numpy(data)

    def _save(self, tensor, path):
        sf.write(path, tensor.numpy(), self.TARGET_SR)

    def split(self, audio_path):
        """
        Returns list of (start_sec, end_sec, chunk_wav_path).
        Chunk paths that differ from audio_path are temp files — caller must delete.
        """
        wav = self._load(audio_path)

        timestamps = self._get_ts(
            wav,
            self.model,
            threshold=VAD_THRESHOLD,
            sampling_rate=self.TARGET_SR,
            min_silence_duration_ms=MIN_SILENCE_MS,
            min_speech_duration_ms=MIN_SPEECH_MS,
        )

        if not timestamps:
            return [(0.0, len(wav) / self.TARGET_SR, audio_path)]

        chunks = []
        for ts in timestamps:
            chunk = wav[ts["start"]: ts["end"]]
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            self._save(chunk, tmp.name)
            chunks.append((
                ts["start"] / self.TARGET_SR,
                ts["end"] / self.TARGET_SR,
                tmp.name,
            ))
        return chunks
