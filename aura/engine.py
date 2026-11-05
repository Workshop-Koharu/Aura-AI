import os
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
        self.device = "cuda" if os.getenv("AURA_DEVICE", "auto") in ("auto", "cuda") and torch.cuda.is_available() else "cpu"
        if self.device == "cuda":
            fraction = min(max(float(os.getenv("AURA_GPU_MEMORY_FRACTION", "0.33")), 0.1), 0.9)
            torch.cuda.set_per_process_memory_fraction(fraction, 0)

    def load(self, required=True):
        with self.lock:
            checkpoint = CHECKPOINTS / "latest.pt"
            if not checkpoint.exists():
                if required:
                    from aura.training.runner import RUNNER
                    training = RUNNER.status()
                    if training.get("status") in ("starting", "running", "stopping"):
                        raise RuntimeError("Aura 자체 모델이 아직 학습 중입니다. 첫 체크포인트가 저장된 뒤 다시 요청하세요. 현재 학습 단계: {}".format(training.get("step", 0)))
                    raise RuntimeError("Aura 자체 모델의 체크포인트가 없습니다. Colab에서 자체 학습 데이터 준비와 학습을 완료한 뒤 다시 요청하세요.")
                return False
            saved = torch.load(checkpoint, map_location=self.device, weights_only=False)
            if self.model is None or int(saved.get("step", 0)) != self.step:
                self.model = AuraModel(MODEL).to(self.device)
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
        return {"checkpoint_exists": checkpoint.exists(), "trained_steps": trained_steps, "tokenizer_ready": TOKENIZER_PATH.exists(), "model_parameters": 47895456, "device": self.device}

    def generate(self, prompt, image_bytes=None, audio_bytes=None, max_new_tokens=160):
        self.load(required=True)
        with self.lock, torch.inference_mode():
            encoded = [257] + self.tokenizer.encode(prompt, add_special=False)[-(MODEL.max_seq_len - 1):]
            ids = torch.tensor([encoded], dtype=torch.long, device=self.device)
            image = image_tensor(image_bytes).to(self.device) if image_bytes else None
            audio = wav_spectrogram(audio_bytes).to(self.device) if audio_bytes else None
            generated = self.model.generate(ids, max_new_tokens=max_new_tokens, image=image, audio=audio)
            output = generated[0].tolist()[len(ids[0]):]
            return self.tokenizer.decode(output), {"steps": self.step, "input_image": image is not None, "input_audio": audio is not None, "device": self.device}

ENGINE = InferenceEngine()
