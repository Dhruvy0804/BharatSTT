import torch
from faster_whisper import WhisperModel as _FWModel


class WhisperModel:
    def __init__(self, model_size="small"):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        print(f"Loading Whisper {model_size} (faster-whisper · {device} · {compute_type}) ...")
        self.model = _FWModel(model_size, device=device, compute_type=compute_type)
        print("Whisper ready.")

    def detect_language(self, audio_path):
        """Returns (lang_code, confidence, all_probs)."""
        segments, info = self.model.transcribe(
            audio_path, language=None, beam_size=5, without_timestamps=True
        )
        list(segments)  # consume generator to finalise detection
        return info.language, info.language_probability, {info.language: info.language_probability}

    def transcribe(self, audio_path, language="en"):
        """Returns plain text string."""
        segments, _ = self.model.transcribe(audio_path, language=language, beam_size=5)
        return " ".join(seg.text.strip() for seg in segments).strip()

    def transcribe_words(self, audio_path, language=None):
        """Returns list of {word, start, end} dicts."""
        segments, _ = self.model.transcribe(
            audio_path, language=language, beam_size=5, word_timestamps=True
        )
        words = []
        for seg in segments:
            for w in (seg.words or []):
                words.append({"word": w.word, "start": w.start, "end": w.end})
        return words

    def detect_and_transcribe(self, audio_path):
        """
        Single-pass: detect language + word timestamps together.
        Returns (lang_code, confidence, text, words_list).
        Used by the router so English/IndicConformer chunks need only ONE Whisper pass
        instead of two (detect_language + transcribe separately).
        """
        segments, info = self.model.transcribe(
            audio_path, language=None, beam_size=5, word_timestamps=True
        )
        words = []
        for seg in segments:
            for w in (seg.words or []):
                words.append({"word": w.word, "start": w.start, "end": w.end})
        text = "".join(w["word"] for w in words).strip()
        return info.language, info.language_probability, text, words
