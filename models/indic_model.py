import torch
import nemo.collections.asr as nemo_asr


class IndicModel:
    def __init__(self, model_path):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading IndicConformer from {model_path} (device={device}) ...")
        self.model = nemo_asr.models.EncDecHybridRNNTCTCBPEModel.restore_from(
            model_path, map_location=device
        )
        self.model.eval()
        if device == "cuda":
            self.model = self.model.cuda()
        print("IndicConformer ready.")

    def transcribe(self, audio_path, language_id="hi"):
        result = self.model.transcribe([audio_path], language_id=language_id)
        if not result:
            return ""
        item = result[0]
        text = item[0] if isinstance(item, list) else item
        return text.strip() if text else ""
