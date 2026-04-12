# Denoiser evaluation — synthetic mixes

Real metrics against a clean reference, not the vanity call-vs-gap SNR.

Metrics:

- **SI-SDR Δ (dB)**: improvement in scale-invariant SDR (est=cleaned vs est=mix), both referenced to the clean signal. Positive = pipeline helped.
- **Call-band cosine**: cosine similarity of |STFT(clean)| and |STFT(cleaned)| over 10–200 Hz. 1.0 = perfect rumble-shape preservation.
- **Noise-band attenuation (dB)**: energy reduction from mix → cleaned in 200–1200 Hz. Positive = mechanical noise removed.

## Aggregate by input SNR

| Target input SNR (dB) | N | SI-SDR in (dB) | SI-SDR out (dB) | SI-SDR Δ mean ± std (dB) | Call-band cosine | Noise-band attenuation (dB) |
|---:|---:|---:|---:|---:|---:|---:|
| -10 | 6 | -10.03 | -8.15 | +1.88 ± 4.01 | 0.547 | +1.82 |
| -5 | 6 | -5.01 | -2.95 | +2.07 ± 2.45 | 0.766 | +1.89 |
| +0 | 6 | -0.01 | -0.02 | -0.02 ± 1.57 | 0.906 | +2.09 |
| +5 | 6 | +5.00 | +1.24 | -3.75 ± 1.41 | 0.962 | +1.65 |

**Overall SI-SDR improvement across 24 mixes: +0.04 ± 3.48 dB**

## Honesty check

- At input SNR tiers **[0, 5] dB**, the pipeline REDUCED SI-SDR on average. This is the expected failure mode for aggressive denoisers at moderate/high input SNR: the spectral subtraction & bandpass steps distort the signal more than they remove noise when noise is already low. The pipeline's value is strongest at low input SNR (heavy noise).

## Per-mix detail

| mix_id | target SNR (dB) | measured SNR (dB) | SI-SDR in | SI-SDR out | Δ | call-cos | noise-atten (dB) | clean src | noise src |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| mix_000_c0_n0_snr-10dB | -10 | -10.00 | -9.85 | -10.48 | -0.62 | 0.378 | +3.27 | 04-040920-02_vehicle_1.wav | 090224-09_generator_01.wav |
| mix_001_c0_n0_snr-5dB | -5 | -5.00 | -4.92 | -4.09 | +0.82 | 0.640 | +2.68 | 04-040920-02_vehicle_1.wav | 090224-09_generator_01.wav |
| mix_002_c0_n0_snr+0dB | +0 | +0.00 | +0.05 | +0.36 | +0.31 | 0.851 | +3.08 | 04-040920-02_vehicle_1.wav | 090224-09_generator_01.wav |
| mix_003_c0_n0_snr+5dB | +5 | +5.00 | +5.03 | +2.65 | -2.38 | 0.943 | +1.48 | 04-040920-02_vehicle_1.wav | 090224-09_generator_01.wav |
| mix_004_c0_n1_snr-10dB | -10 | -10.00 | -10.09 | -3.19 | +6.91 | 0.739 | +0.11 | 04-040920-02_vehicle_1.wav | 99-45_vehicle_01.wav |
| mix_005_c0_n1_snr-5dB | -5 | -5.00 | -5.05 | +0.85 | +5.90 | 0.888 | -0.78 | 04-040920-02_vehicle_1.wav | 99-45_vehicle_01.wav |
| mix_006_c0_n1_snr+0dB | +0 | +0.00 | -0.03 | +2.89 | +2.92 | 0.952 | +0.00 | 04-040920-02_vehicle_1.wav | 99-45_vehicle_01.wav |
| mix_007_c0_n1_snr+5dB | +5 | +5.00 | +4.98 | +3.66 | -1.32 | 0.975 | +0.13 | 04-040920-02_vehicle_1.wav | 99-45_vehicle_01.wav |
| mix_008_c1_n0_snr-10dB | -10 | -10.00 | -10.11 | -13.19 | -3.08 | 0.306 | +3.25 | 2000-23_vehicle_noise_3.wav | 090224-09_generator_01.wav |
| mix_009_c1_n0_snr-5dB | -5 | -5.00 | -5.06 | -5.78 | -0.72 | 0.626 | +3.21 | 2000-23_vehicle_noise_3.wav | 090224-09_generator_01.wav |
| mix_010_c1_n0_snr+0dB | +0 | +0.00 | -0.03 | -1.71 | -1.68 | 0.859 | +2.57 | 2000-23_vehicle_noise_3.wav | 090224-09_generator_01.wav |
| mix_011_c1_n0_snr+5dB | +5 | +5.00 | +4.98 | -0.04 | -5.02 | 0.951 | +2.83 | 2000-23_vehicle_noise_3.wav | 090224-09_generator_01.wav |
| mix_012_c1_n1_snr-10dB | -10 | -10.00 | -10.06 | -4.87 | +5.20 | 0.761 | +1.12 | 2000-23_vehicle_noise_3.wav | 99-45_vehicle_01.wav |
| mix_013_c1_n1_snr-5dB | -5 | -5.00 | -5.04 | -1.45 | +3.59 | 0.903 | +2.04 | 2000-23_vehicle_noise_3.wav | 99-45_vehicle_01.wav |
| mix_014_c1_n1_snr+0dB | +0 | +0.00 | -0.02 | +0.11 | +0.13 | 0.961 | +2.37 | 2000-23_vehicle_noise_3.wav | 99-45_vehicle_01.wav |
| mix_015_c1_n1_snr+5dB | +5 | +5.00 | +4.99 | +0.64 | -4.35 | 0.980 | +1.15 | 2000-23_vehicle_noise_3.wav | 99-45_vehicle_01.wav |
| mix_016_c2_n0_snr-10dB | -10 | -10.00 | -10.06 | -12.44 | -2.38 | 0.335 | +3.29 | 2000-23_background_and_vehicle_noise_2.wav | 090224-09_generator_01.wav |
| mix_017_c2_n0_snr-5dB | -5 | -5.00 | -5.03 | -5.74 | -0.70 | 0.637 | +3.24 | 2000-23_background_and_vehicle_noise_2.wav | 090224-09_generator_01.wav |
| mix_018_c2_n0_snr+0dB | +0 | -0.00 | -0.02 | -1.84 | -1.82 | 0.857 | +2.79 | 2000-23_background_and_vehicle_noise_2.wav | 090224-09_generator_01.wav |
| mix_019_c2_n0_snr+5dB | +5 | +5.00 | +4.99 | -0.10 | -5.08 | 0.948 | +3.16 | 2000-23_background_and_vehicle_noise_2.wav | 090224-09_generator_01.wav |
| mix_020_c2_n1_snr-10dB | -10 | -10.00 | -9.99 | -4.74 | +5.25 | 0.761 | -0.11 | 2000-23_background_and_vehicle_noise_2.wav | 99-45_vehicle_01.wav |
| mix_021_c2_n1_snr-5dB | -5 | -5.00 | -4.99 | -1.49 | +3.51 | 0.900 | +0.96 | 2000-23_background_and_vehicle_noise_2.wav | 99-45_vehicle_01.wav |
| mix_022_c2_n1_snr+0dB | +0 | -0.00 | +0.00 | +0.03 | +0.03 | 0.957 | +1.72 | 2000-23_background_and_vehicle_noise_2.wav | 99-45_vehicle_01.wav |
| mix_023_c2_n1_snr+5dB | +5 | +5.00 | +5.00 | +0.63 | -4.37 | 0.978 | +1.17 | 2000-23_background_and_vehicle_noise_2.wav | 99-45_vehicle_01.wav |
