import threading
import torch
from aura.config import MODEL, CHECKPOINTS, TOKENIZER_PATH
from aura.models.transformer import AuraModel
from aura.tokenizer import AuraTokenizer
from aura.multimodal.preprocess import image_tensor, wav_spectrogram

class InferenceEngine:
    def __init__(self):
        self.lock = threading.Lock()
        self.model = None
        self.tokenizer = None
        self.step = 0

    def load(self, required=True):
        with self.lock:
            checkpoint = CHECKPOINTS / "latest.pt"
            if not checkpoint.exists():
                if required: raise RuntimeError("The from-scratch model has not produced a checkpoint yet.")
                return False
            saved = torch.load(checkpoint, map_location="cpu", weights_only=False)
            if self.model is None or int(saved.get("step", 0)) != self.step:
                self.model = AuraModel(MODEL).cpu()
                self.model.load_state_dict(saved["model"])
                self.model.eval()
                self.step = int(saved.get("step", 0))
                self.tokenizer = AuraTokenizer.load(TOKENIZER_PATH)
            return True

    def status(self):
        checkpoint = CHECKPOINTS / "latest.pt"
        trained_steps = self.step
        if checkpoint.exists() and not trained_steps:
            try:
                saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
                trained_steps = int(saved.get("step", 0))
            except Exception:
                pass
        return {"checkpoint_exists": checkpoint.exists(), "trained_steps": trained_steps, "tokenizer_ready": TOKENIZER_PATH.exists(), "model_parameters": 47895456}

    def generate(self, prompt, image_bytes=None, audio_bytes=None, max_new_tokens=160):
        self.load(required=True)
        with self.lock, torch.inference_mode():
            ids = torch.tensor([self.tokenizer.encode(prompt)[-MODEL.max_seq_len:]], dtype=torch.long)
            image = image_tensor(image_bytes) if image_bytes else None
            audio = wav_spectrogram(audio_bytes) if audio_bytes else None
            generated = self.model.generate(ids, max_new_tokens=max_new_tokens, image=image, audio=audio)
            output = generated[0].tolist()[len(ids[0]):]
            return self.tokenizer.decode(output), {"steps": self.step, "input_image": image is not None, "input_audio": audio is not None}
ENGINE = InferenceEngine()
