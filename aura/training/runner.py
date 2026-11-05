import json
import os
import threading
import time
from pathlib import Path
import torch
from torch.utils.data import DataLoader, ConcatDataset
from aura.config import DATA, CHECKPOINTS, TOKENIZER_PATH, MODEL, TRAINING
from aura.tokenizer import AuraTokenizer
from aura.models.transformer import AuraModel
from aura.data import TextCorpus, PairCorpus

class TrainingRunner:
    def __init__(self):
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None
        self.state = {"status": "idle", "step": 0, "loss": None, "samples": 0, "error": None, "device": "cpu", "threads": 4}
        self.state_path = DATA / "training_state.json"

    def status(self):
        with self.lock:
            return dict(self.state)

    def start(self):
        with self.lock:
            if self.thread and self.thread.is_alive():
                return {"started": False, "reason": "already_running", **self.state}
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._run, name="aura-training", daemon=True)
            self.thread.start()
            self.state.update(status="starting", error=None)
            return {"started": True, **self.state}

    def stop(self):
        self.stop_event.set()
        with self.lock:
            self.state["status"] = "stopping"
        return {"stopping": True}

    def _limits(self):
        torch.set_num_threads(TRAINING["torch_threads"])
        torch.set_num_interop_threads(1)
        try:
            import psutil
            proc = psutil.Process()
            proc.cpu_affinity(list(range(TRAINING["cpu_affinity_logical_cpus"])))
            proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        except Exception:
            try:
                import ctypes
                kernel = ctypes.windll.kernel32
                kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), (1 << TRAINING["cpu_affinity_logical_cpus"]) - 1)
                kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x00004000)
            except Exception:
                pass
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        return "cpu"

    def _tokenizer(self):
        if TOKENIZER_PATH.exists():
            return AuraTokenizer.load(TOKENIZER_PATH)
        texts = []
        for path in (DATA / "text").rglob("*.txt"):
            texts.append(path.read_text(encoding="utf-8", errors="ignore"))
        for folder in ("image_text", "audio_text"):
            index = DATA / folder / "pairs.jsonl"
            if index.exists():
                for line in index.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        texts.append(json.loads(line)["text"])
        tokenizer = AuraTokenizer.train(texts, max_merges=2048)
        tokenizer.save(TOKENIZER_PATH)
        return tokenizer

    def _run(self):
        try:
            self._limits()
            tokenizer = self._tokenizer()
            datasets = [
                TextCorpus(tokenizer, TRAINING["sequence_length"]),
                PairCorpus("image", tokenizer, TRAINING["sequence_length"]),
                PairCorpus("audio", tokenizer, TRAINING["sequence_length"]),
            ]
            datasets = [ds for ds in datasets if len(ds)]
            if not datasets:
                raise RuntimeError("No training data found. Add UTF-8 .txt files or image/audio pairs under data/.")
            dataset = ConcatDataset(datasets)
            loader = DataLoader(dataset, batch_size=TRAINING["batch_size"], shuffle=True, num_workers=0)
            model = AuraModel(MODEL).cpu()
            optimizer = torch.optim.AdamW(model.parameters(), lr=TRAINING["learning_rate"], weight_decay=TRAINING["weight_decay"])
            start_step = 0
            latest = CHECKPOINTS / "latest.pt"
            if latest.exists():
                saved = torch.load(latest, map_location="cpu", weights_only=False)
                model.load_state_dict(saved["model"])
                optimizer.load_state_dict(saved["optimizer"])
                start_step = int(saved.get("step", 0))
            with self.lock:
                self.state.update(status="running", samples=len(dataset), step=start_step, device="cpu", threads=4)
            model.train()
            step = start_step
            running_loss = 0.0
            base_lr = TRAINING["learning_rate"]
            while not self.stop_event.is_set() and step < TRAINING["max_steps_per_session"]:
                for batch in loader:
                    if self.stop_event.is_set():
                        break
                    try:
                        import psutil
                        if psutil.Process().memory_info().rss > TRAINING["ram_budget_gb"] * (1024 ** 3):
                            time.sleep(5)
                            continue
                    except ImportError:
                        pass
                    input_ids = batch["input_ids"].cpu()
                    labels = batch["labels"].cpu()
                    image = batch.get("image")
                    audio = batch.get("audio")
                    if image is not None: image = image.cpu()
                    if audio is not None: audio = audio.cpu()
                    warmup = max(1, TRAINING["warmup_steps"])
                    lr = base_lr * min(1.0, (step + 1) / warmup)
                    for group in optimizer.param_groups:
                        group["lr"] = lr
                    _, loss = model(input_ids, image=image, audio=audio, labels=labels)
                    if not torch.isfinite(loss):
                        raise RuntimeError("Training loss became non-finite; check the dataset and tokenizer.")
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                    optimizer.step()
                    optimizer.zero_grad(set_to_none=True)
                    step += 1
                    running_loss = float(loss.detach())
                    if step % 10 == 0:
                        with self.lock:
                            self.state.update(step=step, loss=running_loss, status="running")
                        self.state_path.write_text(json.dumps(self.status(), ensure_ascii=False, indent=2), encoding="utf-8")
                    if step % TRAINING["checkpoint_every"] == 0:
                        CHECKPOINTS.mkdir(parents=True, exist_ok=True)
                        torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(), "step": step, "config": MODEL.__dict__}, latest)
                    time.sleep(TRAINING["sleep_seconds_per_step"])
                    if self.stop_event.is_set():
                        break
            CHECKPOINTS.mkdir(parents=True, exist_ok=True)
            torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(), "step": step, "config": MODEL.__dict__}, latest)
            with self.lock:
                self.state.update(status="stopped" if self.stop_event.is_set() else "completed", step=step, loss=running_loss)
        except Exception as exc:
            with self.lock:
                self.state.update(status="error", error=str(exc))
        finally:
            self.state_path.write_text(json.dumps(self.status(), ensure_ascii=False, indent=2), encoding="utf-8")

RUNNER = TrainingRunner()
