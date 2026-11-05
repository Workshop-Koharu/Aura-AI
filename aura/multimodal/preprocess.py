import io
import wave
import numpy as np
import torch
from PIL import Image

def image_tensor(raw: bytes, size=224):
    image = Image.open(io.BytesIO(raw)).convert("RGB").resize((size, size))
    array = np.asarray(image, dtype=np.float32) / 255.0
    array = (array - 0.5) / 0.5
    return torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)

def wav_spectrogram(raw: bytes, n_mels=80, max_frames=1000):
    with wave.open(io.BytesIO(raw), "rb") as wf:
        channels, rate, width, count = wf.getnchannels(), wf.getframerate(), wf.getsampwidth(), wf.getnframes()
        frames = wf.readframes(count)
    if width != 2:
        raise ValueError("Only 16-bit PCM WAV is supported in the first audio pipeline.")
    audio = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    waveform = torch.from_numpy(audio)
    spec = torch.stft(waveform, n_fft=400, hop_length=160, win_length=400, return_complex=True).abs()
    # Log-frequency bins are grouped into 80 bands; this is learned-free signal preprocessing.
    bins = torch.tensor_split(spec, n_mels, dim=0)
    mel = torch.stack([part.mean(0) if part.numel() else torch.zeros(spec.shape[1]) for part in bins])
    mel = torch.log1p(mel * 10.0)
    if mel.shape[-1] > max_frames:
        mel = mel[:, :max_frames]
    return mel.unsqueeze(0).unsqueeze(0)
