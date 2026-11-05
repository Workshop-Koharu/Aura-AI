import json
from collections import Counter
from pathlib import Path

PAD, BOS, EOS, UNK = 256, 257, 258, 259
BASE_VOCAB = 260

class AuraTokenizer:
    def __init__(self, merges=None):
        self.merges = [tuple(x) for x in (merges or [])]
        self.ranks = {pair: i for i, pair in enumerate(self.merges)}
        self.vocab_size = BASE_VOCAB + len(self.merges)

    @classmethod
    def train(cls, texts, max_merges=2048, min_frequency=2):
        sequences = [list(text.encode("utf-8")) for text in texts if text]
        sequences = [seq for seq in sequences if seq]
        merges = []
        for _ in range(max_merges):
            counts = Counter()
            for seq in sequences:
                counts.update(zip(seq, seq[1:]))
            if not counts:
                break
            pair, freq = counts.most_common(1)[0]
            if freq < min_frequency:
                break
            merges.append(pair)
            merged_id = BASE_VOCAB + len(merges) - 1
            updated = []
            for seq in sequences:
                out, i = [], 0
                while i < len(seq):
                    if i + 1 < len(seq) and (seq[i], seq[i + 1]) == pair:
                        out.append(merged_id)
                        i += 2
                    else:
                        out.append(seq[i])
                        i += 1
                updated.append(out)
            sequences = updated
        return cls(merges)

    def encode(self, text, add_special=True):
        ids = list(text.encode("utf-8"))
        while len(ids) > 1:
            best, best_rank = None, None
            for pair in zip(ids, ids[1:]):
                rank = self.ranks.get(pair)
                if rank is not None and (best_rank is None or rank < best_rank):
                    best, best_rank = pair, rank
            if best is None:
                break
            merged_id = BASE_VOCAB + best_rank
            out, i = [], 0
            while i < len(ids):
                if i + 1 < len(ids) and (ids[i], ids[i + 1]) == best:
                    out.append(merged_id)
                    i += 2
                else:
                    out.append(ids[i])
                    i += 1
            ids = out
        return ([BOS] if add_special else []) + ids + ([EOS] if add_special else [])

    def decode(self, ids):
        def expand(token, out):
            if token < 256:
                out.append(token)
            elif token >= BASE_VOCAB:
                pair = self.merges[token - BASE_VOCAB]
                expand(pair[0], out)
                expand(pair[1], out)
        data = bytearray()
        for token in ids:
            if token < 256 or token >= BASE_VOCAB:
                expand(token, data)
        return data.decode("utf-8", errors="replace")

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps({"format": "aura-byte-bpe-v1", "merges": self.merges}, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(raw["merges"])
