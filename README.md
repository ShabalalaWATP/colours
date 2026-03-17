# Colour Invert for Dark Backgrounds

A Python tool that converts logos and images designed for light backgrounds into dark-theme-friendly versions. It generates **8 different colour variants** from a single input image and produces an interactive HTML comparison page so you can preview them all side-by-side on different dark backgrounds and pick the one that looks best.

## What it does

If you have a logo or graphic with:
- A **white background**
- **Black text/writing**
- **Coloured elements** (blue, yellow, red, etc.)

...and you need it to look good on a **dark webpage**, this tool will produce multiple versions with different treatments:

| Variant | Background | Text | Colours |
|---------|-----------|------|---------|
| `transparent_white` | Transparent | White | Unchanged |
| `transparent_bright` | Transparent | White | Brightened |
| `full_invert` | Black | White | Fully inverted |
| `invert_bw_only` | Black | White | Unchanged |
| `invert_bw_bright` | Black | White | Brightened |
| `dark_grey_bg` | Dark grey (#1e1e1e) | Off-white | Unchanged |
| `high_contrast` | Transparent | White | Saturated for max pop |
| `soft_glow` | Transparent | Warm white | Gently brightened |

It also creates an HTML page where you can click buttons to switch between different dark background colours (pure black, dark navy, VS Code dark, GitHub dark, etc.) and see how each variant looks.

## Requirements

- **Python 3.8** or newer
- **Pillow** (image processing library)
- **NumPy** (numerical operations)

That's it. No internet connection required once the packages are installed.

---

## Setup — Step by Step

### Step 1: Check you have Python installed

Open a terminal (Command Prompt, PowerShell, or your shell of choice) and run:

```
python --version
```

You should see something like `Python 3.10.12` or similar. If you get an error, install Python from [python.org](https://www.python.org/downloads/).

> **Note:** On some systems, the command may be `python3` instead of `python`. If `python` doesn't work, try `python3` and use that throughout.

### Step 2: Clone or download the repository

**Option A — Clone with Git:**

```
git clone https://github.com/ShabalalaWATP/colours.git
cd colours
```

**Option B — Download manually:**

1. Go to https://github.com/ShabalalaWATP/colours
2. Click the green **Code** button
3. Click **Download ZIP**
4. Extract the ZIP to a folder of your choice
5. Open a terminal and navigate to that folder:
   ```
   cd path\to\colours
   ```

### Step 3: (Optional) Create a virtual environment

This keeps the dependencies contained and avoids polluting your system Python. It's optional but recommended.

**Windows:**
```
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```
python3 -m venv venv
source venv/bin/activate
```

You'll see `(venv)` at the start of your terminal prompt when the virtual environment is active.

### Step 4: Install dependencies

```
pip install pillow numpy
```

That's it. Two packages, both lightweight, no internet needed after this point.

### Step 5: Verify the install

```
python -c "from PIL import Image; import numpy; print('Ready')"
```

If it prints `Ready`, you're good to go.

---

## Setup on an Air-Gapped Network

If the machine you want to run this on has **no internet access**, follow these steps:

### On the connected machine:

1. Download the Python wheel files:
   ```
   pip download pillow numpy -d ./wheels
   ```
   This creates a `wheels/` folder with `.whl` files inside.

2. Copy the following to your transfer media (USB, approved transfer process, etc.):
   - The `colour_invert.py` script
   - The entire `wheels/` folder

### On the air-gapped machine:

1. Copy the files to a working directory.

2. Install the packages from the local wheel files:
   ```
   pip install --no-index --find-links=./wheels pillow numpy
   ```

3. Run the script as normal (see usage below).

---

## Usage

### Basic usage — generate all variants

```
python colour_invert.py logo.png
```

This will:
1. Create a folder called `logo_variants/` next to your input image
2. Generate 8 different colour variants as PNG files
3. Save a copy of the original for reference
4. Create a `compare.html` file for side-by-side comparison

### Open the comparison page

After running the script, open the HTML file in any browser:

**Windows:**
```
start logo_variants\compare.html
```

**macOS:**
```
open logo_variants/compare.html
```

**Linux:**
```
xdg-open logo_variants/compare.html
```

The page shows all variants in a grid. Use the buttons at the top to switch between different dark background colours and see which variant looks best on your specific site colour.

### Generate only the recommended variant

If you don't need all 8 and just want the best default (transparent background, white text, colours preserved):

```
python colour_invert.py logo.png --single
```

### Specify a custom output directory

```
python colour_invert.py logo.png --output-dir ./my_output
```

### Set the default preview background colour

If your website uses a specific dark colour, set it as the default for the comparison page:

```
python colour_invert.py logo.png --bg "#1a1a2e"
```

---

## Fine-Tuning Detection Thresholds

The script classifies each pixel as white (background), black (text), grey (anti-aliased edges), or coloured. The thresholds control how that classification works. You can adjust them if the defaults don't suit your image.

### `--white-thresh` (default: 240)

Controls how "white" a pixel needs to be to count as background.

- **Lower value** (e.g. `220`): catches off-white and cream backgrounds
- **Higher value** (e.g. `250`): only pure white is treated as background

```
python colour_invert.py logo.png --white-thresh 220
```

**When to change it:** Your logo has a slightly off-white or cream background that isn't being removed.

### `--black-thresh` (default: 60)

Controls how "black" a pixel needs to be to count as text.

- **Lower value** (e.g. `30`): only very dark pixels are treated as text
- **Higher value** (e.g. `80`): catches dark grey text too

```
python colour_invert.py logo.png --black-thresh 80
```

**When to change it:** Your logo has dark grey text instead of pure black, and it's not being converted to white.

### `--grey-sat` (default: 0.12)

Controls the maximum colour saturation for a pixel to be classified as grey (anti-aliased edge). This is important for smooth text edges.

- **Lower value** (e.g. `0.05`): very strict — only truly grey pixels
- **Higher value** (e.g. `0.20`): more lenient — catches slightly tinted greys

```
python colour_invert.py logo.png --grey-sat 0.15
```

**When to change it:** Text edges look rough or jaggy in the output. Increasing this value usually helps because it catches more of the anti-aliased pixels between the text and background.

---

## Example Walkthrough

Here's a complete example from start to finish:

```
# 1. Navigate to the project folder
cd colours

# 2. Place your logo in the folder (or provide a path to it)
#    Let's say your logo is at C:\Images\company_logo.png

# 3. Run the script
python colour_invert.py C:\Images\company_logo.png

# 4. You'll see output like:
#    Processing: C:\Images\company_logo.png
#      Size: 800x400, Mode: RGB
#      Saved: C:\Images\company_logo_variants\company_logo_transparent_white.png
#      Saved: C:\Images\company_logo_variants\company_logo_transparent_bright.png
#      Saved: C:\Images\company_logo_variants\company_logo_full_invert.png
#      Saved: C:\Images\company_logo_variants\company_logo_invert_bw_only.png
#      Saved: C:\Images\company_logo_variants\company_logo_invert_bw_bright.png
#      Saved: C:\Images\company_logo_variants\company_logo_dark_grey_bg.png
#      Saved: C:\Images\company_logo_variants\company_logo_high_contrast.png
#      Saved: C:\Images\company_logo_variants\company_logo_soft_glow.png
#      Comparison page: C:\Images\company_logo_variants\compare.html
#
#    Done. 8 variants saved to C:\Images\company_logo_variants/
#    Open C:\Images\company_logo_variants\compare.html in a browser to compare them.

# 5. Open the comparison page
start C:\Images\company_logo_variants\compare.html

# 6. Browse the variants, click the background colour buttons to test
#    against different dark themes, and pick the one you like

# 7. Copy your chosen variant PNG into your web project
```

---

## Which Variant Should I Pick?

Here's a quick guide:

| Your situation | Recommended variant |
|---|---|
| Website has a pure black or very dark background | `transparent_white` or `transparent_bright` |
| Website has a dark grey background (#1e1e1e etc.) | `dark_grey_bg` |
| You want maximum visual punch | `high_contrast` |
| You want something subtle and professional | `soft_glow` |
| Your coloured elements look dull on dark | `transparent_bright` or `invert_bw_bright` |
| You want the image to have its own solid dark background | `invert_bw_only` |
| You just want a quick classic inversion | `full_invert` |

---

## Supported Image Formats

- **PNG** (recommended — supports transparency)
- **JPEG / JPG**
- **BMP**
- **GIF** (first frame only)
- **TIFF**
- **WebP**

All output is saved as **PNG** to preserve transparency in variants that use it.

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'PIL'"

Pillow isn't installed. Run:
```
pip install pillow
```

If you're using a virtual environment, make sure it's activated first.

### "ModuleNotFoundError: No module named 'numpy'"

```
pip install numpy
```

### The background isn't being removed properly

Your image's background may not be pure white. Try lowering the white threshold:
```
python colour_invert.py logo.png --white-thresh 220
```

### Text edges look rough or jaggy

The anti-aliasing isn't being caught. Increase the grey saturation threshold:
```
python colour_invert.py logo.png --grey-sat 0.20
```

### Dark grey text isn't being converted to white

Increase the black threshold to catch darker greys:
```
python colour_invert.py logo.png --black-thresh 100
```

### The script is slow on very large images

The script processes every pixel. For very large images (e.g. 5000x5000+), it may take a few seconds. This is normal. Consider resizing the image first if you only need a web-sized version.

---

## Licence

Do whatever you want with it.
