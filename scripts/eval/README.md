# Denoiser evaluation harness

Real numbers against a clean reference, not the vanity call-vs-gap SNR already
reported by the pipeline.

## What this does

1. **build_mixes.py** — picks the lowest-noise labelled rumbles from `data/` +
   `output/summary.json`, HPSS-extracts a clean-ish reference, grabs noise-only
   windows from vehicle / generator / airplane recordings, and mixes them at
   controlled input SNRs of `{-10, -5, 0, +5}` dB. Writes WAVs + `manifest.json`
   to `scripts/eval/mixes/`.
2. **run_eval.py** — runs `backend.pipeline.process.process_recording` on every
   mix and computes:
   - **SI-SDR** (Le Roux et al. 2018, arXiv:1811.02508) — scale-invariant SDR,
     improvement vs. input.
   - **Call-band cosine similarity** over 10–200 Hz (rumble preservation).
   - **Noise-band attenuation** over 200–1200 Hz (mechanical-noise removal).

   Writes `results.json` and a human-readable `REPORT.md`.

## How to run

From the repository root:

```bash
python scripts/eval/build_mixes.py     # creates scripts/eval/mixes/
python scripts/eval/run_eval.py        # creates scripts/eval/{results.json,REPORT.md}
```

## What you get

- `scripts/eval/mixes/*.wav` — noisy mixes fed to the pipeline.
- `scripts/eval/mixes/clean/*.wav` — per-mix clean references.
- `scripts/eval/mixes/noise/*.wav` — per-mix noise-only (diagnostic).
- `scripts/eval/mixes/manifest.json` — dataset manifest.
- `scripts/eval/_work/<mix_id>/cleaned.wav` — pipeline output for each mix.
- `scripts/eval/results.json` — one record per mix with every metric.
- `scripts/eval/REPORT.md` — grouped-by-SNR table and honest failure-mode notes.

## Caveats

- "Clean" here is HPSS-extracted from the least-noisy labelled windows; it is
  not truly clean audio (no such recording exists in the dataset). All metrics
  are *relative to that reference by construction*. The comparison across SNR
  tiers is still fair because the reference is identical for a given clean
  source.
- The pipeline is driven with an **empty** calls CSV for each mix so it falls
  into its no-labels branch (percentile-noise estimate + auto-detect). This is
  the right test: it mirrors how the pipeline would be used on unseen audio.
- SI-SDR can go DOWN at higher input SNR for aggressive denoisers; the report
  calls that out explicitly rather than hiding it.

## Dependencies

Only `numpy`, `scipy`, `pandas`, `librosa`, `soundfile` — already required by
the backend pipeline. No new pip installs.
