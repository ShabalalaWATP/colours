"""
Colour Invert for Dark Backgrounds

Converts logos/images with white backgrounds and black text (plus coloured
elements) into dark-theme-friendly versions. Generates multiple variants
with different colour treatments so you can compare and pick the best one.

Produces a single HTML comparison page showing all variants side-by-side
on a dark background.

Requirements: pip install pillow numpy
Usage:
  python colour_invert.py logo.png                  # generate all variants + comparison page
  python colour_invert.py logo.png --single         # single best-guess output only
  python colour_invert.py logo.png --bg "#1a1a2e"   # preview against a specific background
"""

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import numpy as np


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def rgb_to_hsv_array(rgb: np.ndarray) -> np.ndarray:
    """Convert (H, W, 3) uint8 RGB to (H, W, 3) float HSV.
    H in [0, 360), S and V in [0, 1].
    """
    rgb_f = rgb.astype(np.float32) / 255.0
    r, g, b = rgb_f[..., 0], rgb_f[..., 1], rgb_f[..., 2]

    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    diff = maxc - minc

    hue = np.zeros_like(maxc)
    mask_r = (maxc == r) & (diff > 0)
    mask_g = (maxc == g) & (diff > 0)
    mask_b = (maxc == b) & (diff > 0)
    hue[mask_r] = (60.0 * ((g[mask_r] - b[mask_r]) / diff[mask_r])) % 360
    hue[mask_g] = (60.0 * ((b[mask_g] - r[mask_g]) / diff[mask_g]) + 120.0) % 360
    hue[mask_b] = (60.0 * ((r[mask_b] - g[mask_b]) / diff[mask_b]) + 240.0) % 360

    sat = np.where(maxc > 0, diff / maxc, 0.0)
    val = maxc
    return np.stack([hue, sat, val], axis=-1)


def classify_pixels(rgb: np.ndarray, hsv: np.ndarray,
                    white_thresh: int = 240,
                    black_thresh: int = 60,
                    grey_sat_max: float = 0.12) -> np.ndarray:
    """Classify each pixel: 0=white, 1=black, 2=coloured, 3=grey (anti-alias)."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    s, v = hsv[..., 1], hsv[..., 2]

    result = np.full(rgb.shape[:2], 2, dtype=np.int8)  # default: coloured

    is_white = (r > white_thresh) & (g > white_thresh) & (b > white_thresh)
    result[is_white] = 0

    is_black = (r < black_thresh) & (g < black_thresh) & (b < black_thresh)
    result[is_black] = 1

    is_grey = (~is_white) & (~is_black) & (s < grey_sat_max)
    result[is_grey] = 3

    return result


# ---------------------------------------------------------------------------
# Variant generators — each returns (name, description, RGBA Image)
# ---------------------------------------------------------------------------

def variant_transparent_white_text(img: Image.Image, classes: np.ndarray,
                                   hsv: np.ndarray, alpha: np.ndarray,
                                   rgb: np.ndarray) -> tuple:
    """Transparent background, white text, colours unchanged."""
    out = np.array(img.convert("RGBA"))

    out[classes == 0] = [255, 255, 255, 0]

    mask_black = classes == 1
    out[mask_black, :3] = 255
    out[mask_black, 3] = alpha[mask_black]

    mask_grey = classes == 3
    if np.any(mask_grey):
        out[mask_grey, :3] = 255
        out[mask_grey, 3] = ((1.0 - hsv[mask_grey, 2]) * 255).astype(np.uint8)

    return (
        "transparent_white",
        "Transparent bg, white text, original colours",
        Image.fromarray(out, "RGBA"),
    )


def variant_transparent_white_text_bright(img: Image.Image, classes: np.ndarray,
                                          hsv: np.ndarray, alpha: np.ndarray,
                                          rgb: np.ndarray) -> tuple:
    """Transparent background, white text, colours brightened for dark bg."""
    out = np.array(img.convert("RGBA"))

    out[classes == 0] = [255, 255, 255, 0]

    mask_black = classes == 1
    out[mask_black, :3] = 255
    out[mask_black, 3] = alpha[mask_black]

    mask_grey = classes == 3
    if np.any(mask_grey):
        out[mask_grey, :3] = 255
        out[mask_grey, 3] = ((1.0 - hsv[mask_grey, 2]) * 255).astype(np.uint8)

    mask_colour = classes == 2
    if np.any(mask_colour):
        out[mask_colour, :3] = np.clip(
            rgb[mask_colour].astype(np.int16) + 40, 0, 255
        ).astype(np.uint8)

    return (
        "transparent_bright",
        "Transparent bg, white text, colours brightened +40",
        Image.fromarray(out, "RGBA"),
    )


def variant_full_invert(img: Image.Image, classes: np.ndarray,
                        hsv: np.ndarray, alpha: np.ndarray,
                        rgb: np.ndarray) -> tuple:
    """Simple full colour inversion (the classic approach)."""
    rgba = img.convert("RGBA")
    r, g, b, a = rgba.split()
    inverted_rgb = ImageOps.invert(Image.merge("RGB", (r, g, b)))
    result = Image.merge("RGBA", (*inverted_rgb.split(), a))
    return (
        "full_invert",
        "Full colour inversion (all pixels inverted)",
        result,
    )


def variant_invert_bw_only(img: Image.Image, classes: np.ndarray,
                           hsv: np.ndarray, alpha: np.ndarray,
                           rgb: np.ndarray) -> tuple:
    """Invert only black/white/grey, keep colours untouched."""
    out = np.array(img.convert("RGBA"))

    mask_white = classes == 0
    out[mask_white, :3] = 0
    out[mask_white, 3] = 255

    mask_black = classes == 1
    out[mask_black, :3] = 255
    out[mask_black, 3] = alpha[mask_black]

    mask_grey = classes == 3
    if np.any(mask_grey):
        out[mask_grey, :3] = np.clip(
            255 - rgb[mask_grey].astype(np.int16), 0, 255
        ).astype(np.uint8)

    return (
        "invert_bw_only",
        "Black bg, white text, original colours preserved",
        Image.fromarray(out, "RGBA"),
    )


def variant_invert_bw_bright_colours(img: Image.Image, classes: np.ndarray,
                                     hsv: np.ndarray, alpha: np.ndarray,
                                     rgb: np.ndarray) -> tuple:
    """Invert black/white, brighten colours for contrast on dark bg."""
    out = np.array(img.convert("RGBA"))

    mask_white = classes == 0
    out[mask_white, :3] = 0
    out[mask_white, 3] = 255

    mask_black = classes == 1
    out[mask_black, :3] = 255
    out[mask_black, 3] = alpha[mask_black]

    mask_grey = classes == 3
    if np.any(mask_grey):
        out[mask_grey, :3] = np.clip(
            255 - rgb[mask_grey].astype(np.int16), 0, 255
        ).astype(np.uint8)

    mask_colour = classes == 2
    if np.any(mask_colour):
        out[mask_colour, :3] = np.clip(
            rgb[mask_colour].astype(np.int16) + 40, 0, 255
        ).astype(np.uint8)

    return (
        "invert_bw_bright",
        "Black bg, white text, colours brightened +40",
        Image.fromarray(out, "RGBA"),
    )


def variant_dark_grey_bg(img: Image.Image, classes: np.ndarray,
                         hsv: np.ndarray, alpha: np.ndarray,
                         rgb: np.ndarray) -> tuple:
    """Dark grey background instead of transparent — sometimes cleaner."""
    out = np.array(img.convert("RGBA"))

    out[classes == 0, :3] = 30  # dark grey
    out[classes == 0, 3] = 255

    mask_black = classes == 1
    out[mask_black, :3] = 240  # off-white text
    out[mask_black, 3] = alpha[mask_black]

    mask_grey = classes == 3
    if np.any(mask_grey):
        grey_v = hsv[mask_grey, 2]
        new_val = (30 + (1.0 - grey_v) * 210).astype(np.uint8)
        out[mask_grey, 0] = new_val
        out[mask_grey, 1] = new_val
        out[mask_grey, 2] = new_val
        out[mask_grey, 3] = 255

    return (
        "dark_grey_bg",
        "Dark grey (#1e1e1e) bg, off-white text, original colours",
        Image.fromarray(out, "RGBA"),
    )


def variant_high_contrast(img: Image.Image, classes: np.ndarray,
                          hsv: np.ndarray, alpha: np.ndarray,
                          rgb: np.ndarray) -> tuple:
    """Transparent bg, pure white text, colours saturated for max pop."""
    out = np.array(img.convert("RGBA"))

    out[classes == 0] = [0, 0, 0, 0]

    mask_black = classes == 1
    out[mask_black, :3] = 255
    out[mask_black, 3] = alpha[mask_black]

    mask_grey = classes == 3
    if np.any(mask_grey):
        out[mask_grey, :3] = 255
        out[mask_grey, 3] = ((1.0 - hsv[mask_grey, 2]) * 255).astype(np.uint8)

    # Boost saturation on coloured pixels
    mask_colour = classes == 2
    if np.any(mask_colour):
        colour_pixels = rgb[mask_colour].astype(np.float32) / 255.0
        # Push each channel away from the mean to increase saturation
        mean = colour_pixels.mean(axis=1, keepdims=True)
        boosted = mean + (colour_pixels - mean) * 1.4
        out[mask_colour, :3] = np.clip(boosted * 255, 0, 255).astype(np.uint8)

    return (
        "high_contrast",
        "Transparent bg, white text, colours saturated for max contrast",
        Image.fromarray(out, "RGBA"),
    )


def variant_soft_glow(img: Image.Image, classes: np.ndarray,
                      hsv: np.ndarray, alpha: np.ndarray,
                      rgb: np.ndarray) -> tuple:
    """Transparent bg, slightly warm white text, subtle colour boost."""
    out = np.array(img.convert("RGBA"))

    out[classes == 0] = [0, 0, 0, 0]

    mask_black = classes == 1
    out[mask_black, 0] = 255
    out[mask_black, 1] = 250
    out[mask_black, 2] = 245  # warm white
    out[mask_black, 3] = alpha[mask_black]

    mask_grey = classes == 3
    if np.any(mask_grey):
        out[mask_grey, 0] = 255
        out[mask_grey, 1] = 250
        out[mask_grey, 2] = 245
        out[mask_grey, 3] = ((1.0 - hsv[mask_grey, 2]) * 255).astype(np.uint8)

    mask_colour = classes == 2
    if np.any(mask_colour):
        out[mask_colour, :3] = np.clip(
            rgb[mask_colour].astype(np.int16) + 20, 0, 255
        ).astype(np.uint8)

    return (
        "soft_glow",
        "Transparent bg, warm white text, gently brightened colours",
        Image.fromarray(out, "RGBA"),
    )


ALL_VARIANTS = [
    variant_transparent_white_text,
    variant_transparent_white_text_bright,
    variant_full_invert,
    variant_invert_bw_only,
    variant_invert_bw_bright_colours,
    variant_dark_grey_bg,
    variant_high_contrast,
    variant_soft_glow,
]


# ---------------------------------------------------------------------------
# HTML comparison page
# ---------------------------------------------------------------------------

def build_comparison_html(variants: list, bg_colour: str, input_name: str) -> str:
    """Build an HTML page showing all variants side-by-side."""
    cards = []
    for filename, name, description in variants:
        cards.append(f"""
        <div class="card">
          <img src="{filename}" alt="{name}" />
          <div class="label">{name}</div>
          <div class="desc">{description}</div>
        </div>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Colour Variants — {input_name}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: {bg_colour};
    color: #ccc;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    padding: 2rem;
  }}
  h1 {{
    text-align: center;
    color: #fff;
    margin-bottom: 0.5rem;
    font-size: 1.4rem;
  }}
  .subtitle {{
    text-align: center;
    color: #888;
    margin-bottom: 2rem;
    font-size: 0.85rem;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.5rem;
    max-width: 1400px;
    margin: 0 auto;
  }}
  .card {{
    background: {bg_colour};
    border: 1px solid #333;
    border-radius: 8px;
    padding: 1.5rem;
    text-align: center;
    transition: border-color 0.2s;
  }}
  .card:hover {{ border-color: #666; }}
  .card img {{
    max-width: 100%;
    max-height: 280px;
    object-fit: contain;
    /* checkerboard for transparency */
    background-image:
      linear-gradient(45deg, #222 25%, transparent 25%),
      linear-gradient(-45deg, #222 25%, transparent 25%),
      linear-gradient(45deg, transparent 75%, #222 75%),
      linear-gradient(-45deg, transparent 75%, #222 75%);
    background-size: 16px 16px;
    background-position: 0 0, 0 8px, 8px -8px, -8px 0;
    border-radius: 4px;
    padding: 0.5rem;
  }}
  .label {{
    margin-top: 0.75rem;
    color: #fff;
    font-weight: 600;
    font-size: 0.95rem;
  }}
  .desc {{
    margin-top: 0.25rem;
    color: #999;
    font-size: 0.8rem;
  }}
  .bg-controls {{
    text-align: center;
    margin-bottom: 1.5rem;
  }}
  .bg-controls button {{
    background: #333;
    color: #ccc;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 0.3rem 0.8rem;
    margin: 0 0.25rem;
    cursor: pointer;
    font-size: 0.8rem;
  }}
  .bg-controls button:hover {{ background: #444; }}
  .bg-controls button.active {{ background: #555; color: #fff; border-color: #888; }}
</style>
</head>
<body>
  <h1>Colour Variants — {input_name}</h1>
  <p class="subtitle">Pick the version that looks best for your dark background</p>

  <div class="bg-controls">
    <span style="color:#777; font-size:0.8rem;">Preview background:</span>
    <button onclick="setBg('#000000')" id="bg-000000">Pure Black</button>
    <button onclick="setBg('#111111')" id="bg-111111">#111</button>
    <button onclick="setBg('#1a1a2e')" id="bg-1a1a2e">Dark Navy</button>
    <button onclick="setBg('#1e1e1e')" id="bg-1e1e1e">VS Code</button>
    <button onclick="setBg('#2d2d2d')" id="bg-2d2d2d">Charcoal</button>
    <button onclick="setBg('#0d1117')" id="bg-0d1117">GitHub Dark</button>
  </div>

  <div class="grid">
    {"".join(cards)}
  </div>

  <script>
    function setBg(colour) {{
      document.body.style.background = colour;
      document.querySelectorAll('.card').forEach(c => c.style.background = colour);
      document.querySelectorAll('.bg-controls button').forEach(b => b.classList.remove('active'));
      const btn = document.getElementById('bg-' + colour.replace('#', ''));
      if (btn) btn.classList.add('active');
    }}
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_variants(img: Image.Image,
                      white_thresh: int = 240,
                      black_thresh: int = 60,
                      grey_sat_max: float = 0.12) -> list:
    """Run all variant generators. Returns list of (name, description, Image)."""
    rgba = img.convert("RGBA")
    arr = np.array(rgba)
    rgb = arr[..., :3]
    alpha = arr[..., 3].copy()
    hsv = rgb_to_hsv_array(rgb)
    classes = classify_pixels(rgb, hsv, white_thresh, black_thresh, grey_sat_max)

    results = []
    for fn in ALL_VARIANTS:
        name, description, result_img = fn(img, classes, hsv, alpha, rgb)
        results.append((name, description, result_img))
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Convert a logo/image for dark webpage backgrounds. "
                    "Generates multiple colour variants and an HTML comparison page."
    )
    parser.add_argument("input", help="Input image path")
    parser.add_argument("--output-dir", default=None,
                        help="Output directory (default: <input>_variants/)")
    parser.add_argument("--single", action="store_true",
                        help="Only produce the recommended single output (transparent + white text)")
    parser.add_argument("--bg", default="#000000",
                        help="Background colour for HTML preview (default: #000000)")
    parser.add_argument("--white-thresh", type=int, default=240,
                        help="RGB threshold for white detection (default: 240)")
    parser.add_argument("--black-thresh", type=int, default=60,
                        help="RGB threshold for black detection (default: 60)")
    parser.add_argument("--grey-sat", type=float, default=0.12,
                        help="Max saturation for grey/anti-alias detection (default: 0.12)")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    if args.output_dir:
        out_dir = Path(args.output_dir)
    else:
        out_dir = input_path.parent / f"{input_path.stem}_variants"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing: {input_path}")
    img = Image.open(input_path)
    print(f"  Size: {img.size[0]}x{img.size[1]}, Mode: {img.mode}")

    if args.single:
        # Just produce the recommended variant
        variants = generate_variants(img, args.white_thresh, args.black_thresh, args.grey_sat)
        name, desc, result = variants[0]  # transparent_white_text
        out_path = out_dir / f"{input_path.stem}_{name}.png"
        result.save(out_path, "PNG")
        print(f"  Saved: {out_path}")
    else:
        variants = generate_variants(img, args.white_thresh, args.black_thresh, args.grey_sat)
        html_entries = []

        for name, description, result_img in variants:
            filename = f"{input_path.stem}_{name}.png"
            out_path = out_dir / filename
            result_img.save(out_path, "PNG")
            html_entries.append((filename, name, description))
            print(f"  Saved: {out_path}")

        # Also copy the original for reference
        orig_filename = f"{input_path.stem}_original.png"
        img.convert("RGBA").save(out_dir / orig_filename, "PNG")
        html_entries.insert(0, (orig_filename, "original", "Original image (unmodified)"))

        # Build comparison page
        html = build_comparison_html(html_entries, args.bg, input_path.name)
        html_path = out_dir / "compare.html"
        html_path.write_text(html, encoding="utf-8")
        print(f"  Comparison page: {html_path}")

    print(f"\nDone. {len(variants)} variants saved to {out_dir}/")
    if not args.single:
        print(f"Open {out_dir / 'compare.html'} in a browser to compare them.")


if __name__ == "__main__":
    main()
