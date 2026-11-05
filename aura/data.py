import json
from pathlib import Path
import torch
from torch.utils.data import Dataset
from PIL import Image
from aura.config import DATA
from aura.multimodal.preprocess import wav_spectrogram

class TextCorpus(Dataset):
    def __init__(self, tokenizer, seq_len=256):
        self.items = []
        for path in (DATA / "text").rglob("*.txt"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            ids = tokenizer.encode(text)
            self.items.extend(chunk for i in range(0, max(0, len(ids) - 1), seq_len) if len(chunk := ids[i:i + seq_len]) > 1)
        self.seq_len = seq_len

    def __len__(self): return len(self.items)

    def __getitem__(self, idx):
        seq = self.items[idx]
        x = torch.full((self.seq_len,), 256, dtype=torch.long)
        labels = torch.full((self.seq_len,), -100, dtype=torch.long)
        n = min(len(seq), self.seq_len)
        x[:n] = torch.tensor(seq[:n])
        labels[:n] = torch.tensor(seq[:n])
        return {"input_ids": x, "labels": labels}

class PairCorpus(Dataset):
    def __init__(self, kind, tokenizer, seq_len=256):
        self.rows, self.kind, self.tokenizer, self.seq_len = [], kind, tokenizer, seq_len
        index = DATA / ("image_text" if kind == "image" else "audio_text") / "pairs.jsonl"
        if index.exists():
            for line in index.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    if (DATA / row["file"]).exists():
                        self.rows.append(row)

    def __len__(self): return len(self.rows)

    def __getitem__(self, idx):
        row = self.rows[idx]
        ids = self.tokenizer.encode(row["text"])[:self.seq_len]
        x = torch.full((self.seq_len,), 256, dtype=torch.long)
        labels = torch.full((self.seq_len,), -100, dtype=torch.long)
        n = min(len(ids), self.seq_len)
        x[:n] = torch.tensor(ids[:n])
        labels[:n] = torch.tensor(ids[:n])
        path = DATA / row["file"]
        if self.kind == "image":
            import numpy as np
            image = Image.open(path).convert("RGB").resize((224, 224))
            arr = np.asarray(image, dtype=np.float32) / 255.0
            image = torch.from_numpy((arr - 0.5) / 0.5).permute(2, 0, 1)
            return {"input_ids": x, "labels": labels, "image": image}
        return {"input_ids": x, "labels": labels, "audio": wav_spectrogram(path.read_bytes()).squeeze(0)}
