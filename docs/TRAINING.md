# Training guide

1. Gather a large, high-quality dataset with documented licenses and provenance.
2. Put plain text into data/text/.
3. Put image-caption pairs into data/image_text/pairs.jsonl.
4. Put 16-bit PCM WAV/transcript pairs into data/audio_text/pairs.jsonl.
5. Start training from the local UI.
6. Check loss, sample count and step count. Stop from the UI to save a checkpoint.
7. Add data incrementally and resume training from the latest checkpoint.

The initial random weights produce no useful knowledge. A few text files are only enough to test the training loop. Real capability requires extensive data cleaning, evaluation, deduplication, balanced sampling and many training steps.
