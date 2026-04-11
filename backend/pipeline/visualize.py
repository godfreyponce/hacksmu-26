"""
Visualization utilities for the elephant audio pipeline.
=========================================================

Generates presentation-quality images for the pitch deck and demo:
1. Side-by-side spectrogram comparison (before | after)
2. Waveform overlay with call regions highlighted
3. Standalone HTML A/B demo page
"""

import os
import json
import base64

import numpy as np
import librosa
import librosa.display
import soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


BG_COLOR = "#0d1117"
TEXT_COLOR = "white"
ACCENT_COLOR = "#58a6ff"
CALL_COLOR = "#3fb950"     # green highlight for call regions
NOISE_COLOR = "#f85149"    # red for noise regions


# ---------------------------------------------------------------------------
# 1. Side-by-side spectrogram comparison
# ---------------------------------------------------------------------------

def save_comparison_spectrogram(original: np.ndarray, cleaned: np.ndarray,
                                 sr: int, path: str,
                                 title: str = "Noise Removal: Before vs After",
                                 n_fft: int = 4096) -> str:
    """
    Generate a single side-by-side image showing original (left) and cleaned (right).
    Perfect for pitch decks — judges see the difference at a glance.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 6), facecolor=BG_COLOR)

    for ax, audio, subtitle in [(ax1, original, "Original (Noisy)"),
                                 (ax2, cleaned, "Cleaned (HPSS + Spectral Gate)")]:
        ax.set_facecolor(BG_COLOR)
        D = librosa.stft(audio, n_fft=n_fft)
        S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)

        img = librosa.display.specshow(
            S_db, sr=sr, x_axis="time", y_axis="hz",
            fmin=0, fmax=2000, ax=ax, cmap="magma",
        )

        cbar = fig.colorbar(img, ax=ax, format="%+2.0f dB")
        cbar.ax.yaxis.set_tick_params(color=TEXT_COLOR)
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color=TEXT_COLOR)

        ax.set_title(subtitle, color=TEXT_COLOR, fontsize=13, pad=8)
        ax.tick_params(colors=TEXT_COLOR)
        ax.xaxis.label.set_color(TEXT_COLOR)
        ax.yaxis.label.set_color(TEXT_COLOR)
        for spine in ax.spines.values():
            spine.set_color("#444444")

    fig.suptitle(title, color=ACCENT_COLOR, fontsize=16, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)
    print(f"  Saved comparison spectrogram: {path}")
    return path


# ---------------------------------------------------------------------------
# 2. Waveform overlay with call regions highlighted
# ---------------------------------------------------------------------------

def save_waveform_overlay(audio: np.ndarray, sr: int, calls: list,
                           path: str, title: str = "Audio Waveform with Elephant Calls",
                           cleaned: np.ndarray = None) -> str:
    """
    Plot the waveform with call regions highlighted in green.
    If `cleaned` is provided, shows both original (faded) and cleaned (solid) overlaid.
    """
    n_plots = 2 if cleaned is not None else 1
    fig, axes = plt.subplots(n_plots, 1, figsize=(16, 4 * n_plots),
                              facecolor=BG_COLOR, sharex=True)
    if n_plots == 1:
        axes = [axes]

    time = np.arange(len(audio)) / sr

    for idx, (ax, wav, label) in enumerate([
        (axes[0], audio, "Original"),
    ] + ([(axes[1], cleaned, "Cleaned")] if cleaned is not None else [])):

        ax.set_facecolor(BG_COLOR)

        # Plot waveform
        ax.plot(time[:len(wav)], wav, color="#8b949e", linewidth=0.3, alpha=0.7)

        # Highlight call regions in green
        for start, end in calls:
            ax.axvspan(start, end, alpha=0.25, color=CALL_COLOR, zorder=0)
            # Draw a stronger border at call boundaries
            ax.axvline(start, color=CALL_COLOR, linewidth=0.5, alpha=0.5)
            ax.axvline(end, color=CALL_COLOR, linewidth=0.5, alpha=0.5)

        ax.set_ylabel("Amplitude", color=TEXT_COLOR)
        ax.set_title(label, color=TEXT_COLOR, fontsize=12, loc="left", pad=5)
        ax.tick_params(colors=TEXT_COLOR)
        for spine in ax.spines.values():
            spine.set_color("#444444")

        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=CALL_COLOR, alpha=0.25, label="Elephant Call")]
        ax.legend(handles=legend_elements, loc="upper right",
                  facecolor="#161b22", edgecolor="#444", labelcolor=TEXT_COLOR, fontsize=9)

    axes[-1].set_xlabel("Time (seconds)", color=TEXT_COLOR)
    fig.suptitle(title, color=ACCENT_COLOR, fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)
    print(f"  Saved waveform overlay: {path}")
    return path


# ---------------------------------------------------------------------------
# 3. Standalone HTML A/B demo page
# ---------------------------------------------------------------------------

def generate_demo_html(output_dir: str, html_path: str, top_n: int = 5) -> str:
    """
    Build a standalone HTML page that lets judges toggle between noisy/clean
    audio with spectrograms. No server needed — everything is embedded or
    uses relative file paths.

    Picks the top N recordings by SNR improvement to showcase the best results.
    """
    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path) as f:
        all_results = json.load(f)

    # Pick top N by SNR improvement, skip errors and zero-call files
    ranked = [r for r in all_results if "error" not in r and r.get("snr_improvement_db", 0) > 0]
    ranked.sort(key=lambda x: x["snr_improvement_db"], reverse=True)
    top = ranked[:top_n]

    cards_html = ""
    for r in top:
        stem = os.path.splitext(r["filename"])[0]
        rec_dir = os.path.join(output_dir, stem)

        # Read spectrogram images as base64 for embedding
        before_b64 = _img_to_base64(os.path.join(rec_dir, "spectrogram_before.png"))
        after_b64 = _img_to_base64(os.path.join(rec_dir, "spectrogram_after.png"))

        noise_type = stem.split("_", 1)[1] if "_" in stem else "unknown"
        noise_type = noise_type.rsplit("_", 1)[0]  # remove trailing number

        cards_html += f"""
    <div class="card">
      <h2>{r['filename']}</h2>
      <div class="stats">
        <span class="stat">SNR Before: <b>{r['snr_before_db']:.1f} dB</b></span>
        <span class="stat">SNR After: <b>{r['snr_after_db']:.1f} dB</b></span>
        <span class="stat improvement">Improvement: <b>+{r['snr_improvement_db']:.1f} dB</b></span>
        <span class="stat">Calls: <b>{len(r.get('calls_detected', []))}</b></span>
        <span class="stat">Duration: <b>{r['duration_seconds']:.1f}s</b></span>
      </div>

      <div class="toggle-row">
        <button class="toggle-btn active" onclick="toggleView(this, 'noisy')">Original (Noisy)</button>
        <button class="toggle-btn" onclick="toggleView(this, 'clean')">Cleaned</button>
      </div>

      <div class="spectrograms">
        <img class="spec noisy active" src="data:image/png;base64,{before_b64}" alt="Before">
        <img class="spec clean" src="data:image/png;base64,{after_b64}" alt="After">
      </div>

      <div class="audio-row">
        <div>
          <label>Original</label>
          <audio controls src="{stem}/original.wav"></audio>
        </div>
        <div>
          <label>Cleaned</label>
          <audio controls src="{stem}/cleaned.wav"></audio>
        </div>
      </div>
    </div>
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EchoMap — Elephant Audio Noise Removal Demo</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: {BG_COLOR};
    color: {TEXT_COLOR};
    padding: 2rem;
    max-width: 1200px;
    margin: 0 auto;
  }}
  h1 {{
    color: {ACCENT_COLOR};
    font-size: 2rem;
    margin-bottom: 0.5rem;
  }}
  .subtitle {{
    color: #8b949e;
    font-size: 1rem;
    margin-bottom: 2rem;
  }}
  .card {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 2rem;
  }}
  .card h2 {{
    font-size: 1.1rem;
    color: #e6edf3;
    margin-bottom: 0.75rem;
    font-family: monospace;
  }}
  .stats {{
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 1rem;
  }}
  .stat {{
    background: #21262d;
    padding: 0.4rem 0.8rem;
    border-radius: 6px;
    font-size: 0.85rem;
    color: #8b949e;
  }}
  .stat b {{ color: #e6edf3; }}
  .improvement b {{ color: {CALL_COLOR}; }}
  .toggle-row {{
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }}
  .toggle-btn {{
    padding: 0.5rem 1.2rem;
    border: 1px solid #30363d;
    border-radius: 8px;
    background: #21262d;
    color: #8b949e;
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.2s;
  }}
  .toggle-btn.active {{
    background: {ACCENT_COLOR};
    color: white;
    border-color: {ACCENT_COLOR};
  }}
  .spectrograms {{ position: relative; margin-bottom: 1rem; }}
  .spec {{
    width: 100%;
    border-radius: 8px;
    display: none;
  }}
  .spec.active {{ display: block; }}
  .audio-row {{
    display: flex;
    gap: 2rem;
    flex-wrap: wrap;
  }}
  .audio-row div {{ flex: 1; min-width: 250px; }}
  .audio-row label {{
    display: block;
    font-size: 0.85rem;
    color: #8b949e;
    margin-bottom: 0.4rem;
  }}
  audio {{ width: 100%; }}
  .header-stats {{
    display: flex;
    gap: 2rem;
    margin-bottom: 2rem;
    flex-wrap: wrap;
  }}
  .header-stat {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 1rem 1.5rem;
    text-align: center;
  }}
  .header-stat .value {{
    font-size: 1.8rem;
    font-weight: bold;
    color: {CALL_COLOR};
  }}
  .header-stat .label {{
    font-size: 0.85rem;
    color: #8b949e;
    margin-top: 0.25rem;
  }}
</style>
</head>
<body>
  <h1>EchoMap</h1>
  <p class="subtitle">AI-powered elephant call extraction — removing mechanical noise using Harmonic-Percussive Source Separation</p>

  <div class="header-stats">
    <div class="header-stat">
      <div class="value">44</div>
      <div class="label">Recordings Processed</div>
    </div>
    <div class="header-stat">
      <div class="value">+{ranked[0]['snr_improvement_db']:.1f} dB</div>
      <div class="label">Best SNR Improvement</div>
    </div>
    <div class="header-stat">
      <div class="value">{sum(1 for r in all_results if r.get('snr_improvement_db',0)>0)}/44</div>
      <div class="label">Files Improved</div>
    </div>
    <div class="header-stat">
      <div class="value">HPSS</div>
      <div class="label">No ML Models</div>
    </div>
  </div>

  {cards_html}

<script>
function toggleView(btn, variant) {{
  const card = btn.closest('.card');
  card.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  card.querySelectorAll('.spec').forEach(s => s.classList.remove('active'));
  card.querySelector('.spec.' + variant).classList.add('active');
}}
</script>
</body>
</html>"""

    with open(html_path, "w") as f:
        f.write(html)
    print(f"  Saved demo page: {html_path}")
    return html_path


def _img_to_base64(path: str) -> str:
    """Read an image file and return its base64 encoding."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


# ---------------------------------------------------------------------------
# Generate all visualizations for a single recording
# ---------------------------------------------------------------------------

def generate_all_visuals(output_dir: str, recording_stem: str, n_fft: int = 4096):
    """Generate comparison spectrogram + waveform overlay for one recording."""
    rec_dir = os.path.join(output_dir, recording_stem)
    results_path = os.path.join(rec_dir, "results.json")

    with open(results_path) as f:
        results = json.load(f)

    original, sr = sf.read(os.path.join(rec_dir, "original.wav"))
    cleaned, _ = sf.read(os.path.join(rec_dir, "cleaned.wav"))

    calls = [(c["start_time"], c["end_time"]) for c in results.get("calls_detected", [])]

    # Side-by-side spectrogram
    save_comparison_spectrogram(
        original, cleaned, sr,
        os.path.join(rec_dir, "comparison.png"),
        title=f"{results['filename']} — SNR: {results['snr_before_db']:.1f} → {results['snr_after_db']:.1f} dB (+{results['snr_improvement_db']:.1f})",
        n_fft=n_fft,
    )

    # Waveform with call highlights
    if calls:
        save_waveform_overlay(
            original, sr, calls,
            os.path.join(rec_dir, "waveform.png"),
            title=f"Call Regions — {results['filename']}",
            cleaned=cleaned,
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"

    # Generate comparison + waveform for top 5 recordings
    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path) as f:
        all_results = json.load(f)

    ranked = [r for r in all_results if "error" not in r and r.get("snr_improvement_db", 0) > 0]
    ranked.sort(key=lambda x: x["snr_improvement_db"], reverse=True)

    print("Generating visuals for top 5 recordings...\n")
    for r in ranked[:5]:
        stem = os.path.splitext(r["filename"])[0]
        print(f"  {r['filename']} (+{r['snr_improvement_db']:.1f} dB)")
        generate_all_visuals(output_dir, stem)
        print()

    # Generate the standalone demo HTML
    print("Generating demo HTML page...")
    generate_demo_html(output_dir, os.path.join(output_dir, "demo.html"), top_n=5)

    print("\nDone! Open output/demo.html in a browser.")
