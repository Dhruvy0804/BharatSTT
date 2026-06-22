# BharatSTT

> **22 Indian Languages + English + Code-Switching — fully offline, no paid API**

BharatSTT is a production-ready Speech-to-Text pipeline that combines three open-source AI models to handle real-world Indian speech: pure Hindi/English, Hinglish, and everything in between.

**Models combined:**
- 🇮🇳 [AI4Bharat IndicConformer](https://github.com/AI4Bharat/NeMo) — Indian language transcription in native script
- 🌐 [OpenAI Whisper](https://github.com/openai/whisper) (via faster-whisper) — English + language detection
- 🔊 [Silero VAD](https://github.com/snakers4/silero-vad) — Voice activity detection

---

## The Idea — Why Combine 3 Models?

No single open-source model handles Indian languages + English + code-switching (Hinglish) well:

| Model alone | Problem |
|---|---|
| Whisper only | Translates Hindi to English instead of transcribing it |
| IndicConformer only | Phonetically writes English words in Devanagari (e.g. *office* → *ऑफिस*) |
| Any single model | Fails on Hinglish — switches language mid-sentence |

**The approach:** take the best model for each job and combine them intelligently.

```
IndicConformer  →  best at Indian languages (native script output)
Whisper         →  best at English + language detection
Silero VAD      →  best at splitting audio at silence boundaries
```

Instead of picking one model for everything, BharatSTT splits the audio into short chunks using VAD, detects the language of each chunk, and **routes each chunk to the right model** — or to both models with a word-level mixer when the language switches mid-chunk (Hinglish).

This phrase-level routing + word-level mixing is what makes it work for real Indian speech, where speakers switch between Hindi and English constantly.

---

## What it does

| You speak | BharatSTT outputs |
|---|---|
| Pure Hindi — *"आज मौसम बहुत अच्छा है"* | `आज मौसम बहुत अच्छा है` |
| Pure English — *"The meeting starts at nine"* | `The meeting starts at nine` |
| Hinglish — *"mujhe tomorrow office jana hai"* | `मुझे tomorrow office जाना है` |
| Mixed — *"Please send the report… बाकी काम कल होगा"* | `Please send the report बाकी काम कल होगा` |

---

## How it works

```
Audio Input
     │
     ▼
[1] Silero VAD  ──→  splits at silence →  Chunk 1 | Chunk 2 | Chunk 3 ...
                                                │
                                        For each chunk:
                                                │
                                           [2] Whisper
                                        detect_language()
                                        → lang, confidence
                                                │
                                          [3]  ROUTER
                          ┌─────────────────────┼──────────────────────┐
                          │                     │                      │
                    English ≥ 85%          Indian ≥ 90%         Mixed / Indian
                    confidence             confidence             < 85% conf
                          │                     │                      │
                     [Whisper]          [IndicConformer]           [MIXER]
                      direct                direct              both models
                          │                     │                      │
                          └─────────────────────┴──────────────────────┘
                                                │
                                          [4] Assembler
                                                │
                                       Final Transcript
```

### Routing logic

| Condition | Route | Reason |
|---|---|---|
| English ≥ 85% confidence | Whisper only | Best English model |
| Indian language ≥ 90% confidence | IndicConformer only | Whisper translates (not transcribes) at this level |
| Indian language 85–90% confidence | Both + Mixer | May contain English loanwords |
| Any language < 85% confidence | Both + Mixer | Code-switching detected |

### Mixer — two strategies

**Boundary strategy** — for audio that switches language once (e.g. English → Hindi):
- Finds the language switch point using Hindi grammar markers (`है`, `में`, `मैं`, `को`, `से` …)
- Takes Whisper-EN words for the English part + IndicConformer words for the Hindi part

**Word-level strategy** — for true Hinglish (mixed word by word):
- Keeps English words from Whisper
- Replaces romanised Indian words (hai, jana, mujhe…) with IndicConformer native script
- 1-to-1 word alignment maintained

---

## Installation

**Requirements:** Python 3.10+ · CUDA GPU recommended (CPU works, slower)

```bash
# 1. Clone
git clone https://github.com/Dhruvy0804/BharatSTT.git
cd BharatSTT

# 2. Virtual environment
python -m venv venv
source venv/bin/activate        # Linux / Mac
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install nemo_toolkit[asr]
pip install faster-whisper gradio soundfile scipy
```

**Download the IndicConformer model** from [AI4Bharat](https://github.com/AI4Bharat/NeMo) and set its path in `config.py`:

```python
INDIC_MODEL_PATH = "/path/to/hindi_asr.nemo"
WHISPER_MODEL_SIZE = "small"   # tiny | small | medium | large-v3
```

---

## Usage

### Web UI (Gradio)

```bash
python app.py
# Opens at http://localhost:7862
```

Upload audio → pick a language (or keep **Auto-detect**) → click **Transcribe**.

### CLI

```bash
# Set AUDIO path inside run_test.py, then:
python run_test.py
```

Prints per-chunk route, language, confidence, latency, RTF, and the final transcript.

---

## Latency

Tested on a 14.6 second mixed Hindi + English recording:

| Hardware | Processing Time | RTF |
|---|---|---|
| Intel i7 CPU (laptop) | ~33s | 2.3× |
| NVIDIA RTX 4060 Laptop GPU | ~10s | 0.7× |
| AWS A10G / A100 GPU | ~3–4s | 0.2× |

> **RTF** = processing time ÷ audio duration. RTF < 1.0 means faster than real-time.  
> No code changes needed for GPU — both models auto-detect CUDA on startup.

---

## Project structure

```
BharatSTT/
├── app.py                   # Gradio web UI
├── config.py                # Model paths, thresholds, language maps
├── run_test.py              # CLI test script with per-chunk latency
├── models/
│   ├── indic_model.py       # IndicConformer wrapper (NeMo)
│   └── whisper_model.py     # faster-whisper wrapper
└── pipeline/
    ├── vad.py               # Silero VAD — audio → speech chunks
    ├── lang_detect.py       # (lang, confidence) → route type
    ├── router.py            # Per-chunk routing + mixer invocation
    ├── mixer.py             # Boundary & word-level code-switch merger
    └── assembler.py         # Chunk transcripts → final output
```

---

## Supported languages

Hindi · Bengali · Tamil · Telugu · Marathi · Gujarati · Kannada · Malayalam · Punjabi · Urdu · Assamese · Odia · Sanskrit · Nepali · Maithili · Sindhi · Dogri · Konkani · Kashmiri · Santali · Bodo · Manipuri · **English**

> Current `.nemo` model covers **Hindi**. Swap to `ai4bharat/indic-conformer-600m-multilingual` for all 22 Indian languages (one line change in `config.py`).

---

## Upgrade path

| What | How | Effect |
|---|---|---|
| All 22 Indian languages | Set `INDIC_MODEL_PATH = "ai4bharat/indic-conformer-600m-multilingual"` | Full language coverage |
| Better English accuracy | Set `WHISPER_MODEL_SIZE = "large-v3"` | Improved mixed transcription |
| GPU / cloud deployment | AWS g5.2xlarge or better (CUDA auto-detected) | 8–10× faster than CPU |

---

## Known limitations

- Current model is Hindi-only (upgrade path above)
- English proper nouns in Hindi speech get phonetically transcribed (e.g. *Bluestem* → *ब्लोस्टैम*)
- Chunk inference is sequential — can be parallelised with threading for production

---

## Author

**Dhruv Garg**  
BML Munjal University · Intern @ Bluestem
