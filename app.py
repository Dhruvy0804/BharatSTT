import os
import sys
import tempfile

import gradio as gr
import soundfile as sf

# Ensure local modules are importable
sys.path.insert(0, os.path.dirname(__file__))

from config import (
    INDIC_MODEL_PATH,
    WHISPER_MODEL_SIZE,
    SUPPORTED_LANGUAGES,
)
from models.indic_model import IndicModel
from models.whisper_model import WhisperModel
from pipeline.vad import VADSplitter
from pipeline.router import Router
from pipeline.assembler import Assembler

# ── Load all models once at startup ─────────────────────────────────────────
print("=" * 60)
indic_model   = IndicModel(INDIC_MODEL_PATH)
whisper_model = WhisperModel(WHISPER_MODEL_SIZE)
vad           = VADSplitter()
router        = Router(whisper_model, indic_model)
assembler     = Assembler()
print("=" * 60)
print("All models ready! Starting Gradio...")


def _to_wav(audio_path):
    """Normalise any audio format to a 16-bit mono WAV temp file."""
    audio, sr = sf.read(audio_path)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio, sr)
    tmp.close()
    return tmp.name


def transcribe(audio_path, language_label):
    if audio_path is None:
        return "Please upload an audio file."

    wav_path = _to_wav(audio_path)
    lang_code = SUPPORTED_LANGUAGES[language_label]
    forced = None if lang_code == "auto" else lang_code
    chunks = []

    try:
        chunks = vad.split(wav_path)

        results = []
        for start, end, chunk_path in chunks:
            text, info = router.process(chunk_path, forced_lang=forced)
            results.append((start, end, text, info))

        transcript, route_summary = assembler.assemble(results)
        header = f"[{language_label} | {route_summary}]\n\n"
        return header + (transcript if transcript else "(no speech detected)")

    except Exception as exc:
        return f"Error during transcription:\n{exc}"

    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass
        # Clean up VAD temp files (skip if chunk IS the original wav_path)
        for _, _, chunk_path in chunks:
            if chunk_path != wav_path:
                try:
                    os.unlink(chunk_path)
                except OSError:
                    pass


# ── Gradio UI ────────────────────────────────────────────────────────────────
with gr.Blocks(title="Multi-Language STT") as demo:
    gr.Markdown(
        "# Multi-Language Speech-to-Text\n"
        "**22 Indian languages** (IndicConformer · AI4Bharat) + "
        "**English** (Whisper · OpenAI) + "
        "**Code-switching** (phrase-level VAD routing + word-level mixer)\n\n"
        "Upload audio and pick a language, or leave on **Auto-detect**."
    )

    with gr.Row():
        with gr.Column():
            audio_input = gr.Audio(
                type="filepath",
                label="Upload Audio  (WAV / MP3 / OGG / FLAC)"
            )
            lang_dropdown = gr.Dropdown(
                choices=list(SUPPORTED_LANGUAGES.keys()),
                value="Auto-detect",
                label="Language  (Auto-detect = phrase-level routing)"
            )
            transcribe_btn = gr.Button("Transcribe", variant="primary")

        with gr.Column():
            output_text = gr.Textbox(
                label="Transcription",
                lines=12,
                placeholder="Transcript will appear here..."
            )

    transcribe_btn.click(
        fn=transcribe,
        inputs=[audio_input, lang_dropdown],
        outputs=output_text,
    )

    gr.Markdown(
        "---\n"
        "**Route labels in output header:**  "
        "`English×N` = N chunks via Whisper  |  "
        "`Indian×N` = N chunks via IndicConformer  |  "
        "`Mixed×N` = N chunks via word-level mixer"
    )

demo.launch(server_port=7862, inbrowser=True)
