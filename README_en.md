# File Match Tool

[中文](README.md) | English

> A photographer's workflow tool for matching selected photos with their RAW files

---

## Table of Contents

- [0. Author's Note](#0-authors-note)
- [1. Application Scenarios](#1-application-scenarios)
- [2. Core Features](#2-core-features)
- [3. Supported Formats](#3-supported-formats)
- [4. Usage Guide](#4-usage-guide)
- [5. Version Comparison](#5-version-comparison-lite-vs-verified)
- [6. How to Run](#6-how-to-run)
- [7. Technical Principles](#7-technical-principles)
- [8. Project Structure](#8-project-structure)
- [9. Version History](#9-version-history)
- [10. Notes](#10-notes)

---

## 0. Author's Note

This program was first developed in February 2025, initially just for my own Sony RAW export workflow.

Recently I've been learning a lot, and felt compelled to share this tool with the community — hopefully it can help more people.

Before releasing it, I searched on Bilibili and found that someone else had already developed a similar tool and published it, sooner or later.

Maybe my release won't be useful, maybe nobody will search for it — but that doesn't matter, everyone has their own workflow. In any case: do your own thing, let others talk.

---

## 1. Application Scenarios

### Typical Workflow

```
Shoot → Camera outputs JPG + RAW → Select photos → Find matching RAW files → Post-process
```

### Pain Points

- Hundreds of photos per shoot, camera saves both JPG + ARW(RAW)
- You selected 10 JPGs for editing
- Need to find the corresponding RAW files
- Manual search is slow and error-prone

### Solution

**File Match**: Drop selected photos on the left, all originals on the right, one-click export.

---

## 2. Core Features

```
┌─────────────────────────────────────────────────────┐
│  Left Panel                Right Panel              │
│  (Selected photos)         (All JPG + RAW)          │
│  1.jpg  ─────┐                                      │
│  5.jpg  ─────┼──→ Filename match ──→ Export matches │
│ 12.jpg  ─────┘                                      │
└─────────────────────────────────────────────────────┘
```

**Matching Logic**: Match by filename stem. Left `1.jpg` matches right `1.arw` + `1.jpg`, both exported.

---

## 3. Supported Formats

### Left Side (Reference Files) — 23 Image Formats

| Category  | Extensions                         |
| --------- | ---------------------------------- |
| JPEG      | .jpg, .jpeg, .jpe                  |
| PNG       | .png                               |
| WebP      | .webp                              |
| HEIC/HEIF | .heic, .heif, .hif                 |
| TIFF      | .tiff, .tif                        |
| BMP       | .bmp                               |
| GIF       | .gif                               |
| AVIF      | .avif                              |
| JPEG 2000 | .jp2, .j2k, .jpx                   |
| Others    | .ico, .tga, .pcx, .ppm, .pgm, .pbm |

### Right Side (Match Files) — 30 RAW Formats

| Brand      | Extensions       |
| ---------- | ---------------- |
| Sony       | .arw, .sr2, .srf |
| Canon      | .cr2, .cr3, .crw |
| Nikon      | .nef, .nrw       |
| Olympus    | .orf             |
| Fujifilm   | .raf             |
| Panasonic  | .rw2, .raw       |
| Adobe/Generic | .dng          |
| Pentax     | .pef, .ptx       |
| Samsung    | .srw             |
| Sigma      | .x3f             |
| Epson      | .erf             |
| Leaf       | .mos             |
| Phase One  | .iiq             |
| Hasselblad | .3fr, .fff       |
| Leica      | .rwl             |
| Kodak      | .kdc, .dcr, .k25 |
| Mamiya     | .mef             |
| Minolta    | .mrw             |
| Casio      | .bay             |
| Sinar      | .cs1             |

> Right side also supports all left-side image formats (for JPG+RAW same-folder scenarios)

---

## 4. Usage Guide

### Steps

```
1. Double-click to open the exe

2. Drag left: Selected photos folder (only JPGs)
   → Auto-recognizes 23 image formats

3. Drag right: All originals folder (JPG + RAW together)
   → Auto-recognizes 30 RAW + 22 image formats

4. Click [Export All Matching Files]

5. Choose export directory → Done
```

### Example

```
Left (Selected):      Right (All):          Export Result:
├── 1.jpg             ├── 1.jpg             ├── 1.jpg
├── 5.jpg             ├── 1.arw             ├── 1.arw
└── 12.jpg            ├── 2.jpg             ├── 5.jpg
                      ├── 2.arw             ├── 5.arw
                      ├── 3.jpg             ├── 12.jpg
                      ├── 3.arw             └── 12.arw
                      ├── 5.jpg
                      ├── 5.arw
                      ├── 12.jpg
                      └── 12.arw
```

### Right-Click Menu

| Function       | Description                    |
| -------------- | ------------------------------ |
| Clear this list| Clear all files on current side|
| Delete selected| Remove only selected items     |

---

## 5. Version Comparison: Lite vs Verified

### Quick Comparison

| Item         | Lite Version            | Verified Version               |
| ------------ | ----------------------- | ------------------------------ |
| File         | 文件匹配.exe (10 MB)    | 文件匹配终版.exe (61 MB)       |
| Source       | 文件匹配.py             | 文件匹配终版.py                |
| Matching     | Filename only           | Filename + **Image fingerprint verification** |
| Tamper-proof | ❌ No                   | ✅ Yes (pHash perceptual hash) |

> Both versions support the same formats: 23 left-side images, 30 right-side RAW + 22 images

### When to use Lite?

- Right folder is your own photos, RAW files are genuine
- Want lightweight, easy to share
- Fast operation, no need for double verification
- Many files (thousands), speed priority

### When to use Verified?

- Right folder from untrusted source (from others, used hard drive)
- Someone may have renamed RAW files (e.g., 2.arw → 1.arw)
- Better to miss than to mismatch
- Highest accuracy required

### Difference Demo

```
Scenario: Right 1.arw was renamed (actually 2.arw)

Lite (filename match):
  Left 1.jpg → Match → Export 1.arw ✗(wrong! exports someone else's RAW)

Verified (pHash check):
  Left 1.jpg → Match → pHash compare → Distance=136(>10) → Skip ✓(not exported)
```

### Recommendation

**Use Lite daily, Verified for important projects.**

---

## 6. How to Run

### Method 1: Run exe directly (Recommended)

Double-click the exe, no dependencies needed.

Download exe files from [Releases](https://github.com/your-username/raw-match/releases).

### Method 2: Run from Python source

**For**: Developers, code modification, or exe blocked by system.

#### 1. Requirements

- Python 3.9+
- pip package manager

#### 2. Install Dependencies

**Lite Version**:

```bash
pip install tkinterdnd2
```

**Verified Version**:

```bash
pip install tkinterdnd2 pillow imagehash rawpy scipy
```

#### 3. Run

**Lite:**

```bash
python 文件匹配.py
```

**Verified:**

```bash
python 文件匹配终版.py
```

#### 4. Package to exe (Optional)

**Lite:**

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "文件匹配" 文件匹配.py
```

**Verified:**

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "文件匹配终版" \
  --hidden-import=tkinterdnd2 \
  --hidden-import=rawpy \
  --hidden-import=imagehash \
  --hidden-import=PIL \
  --hidden-import=numpy \
  文件匹配终版.py
```

Output in `dist/` directory.

---

## 7. Technical Principles

### Lite: Filename Stem Matching

```
File: DSC00001.JPG
      ─────── ────
      stem    ext

stem = Filename without extension
```

**Process**:

```
1. Scan left folder, extract stems of all image files
   → base_names = {"DSC00001", "DSC00005", "DSC00012"}

2. Scan right folder, group by stem
   → match_files = {
       "DSC00001": {"jpg": "D:/xxx/DSC00001.JPG", "arw": "D:/xxx/DSC00001.ARW"},
       "DSC00002": {"jpg": "...", "arw": "..."},
       ...
     }

3. Export: For each base_name in match_files, copy all right-side files
```

**Time Complexity**: O(n + m), where n and m are file counts on each side.

### Verified: pHash Perceptual Hash

Verified adds **image content verification** on top of filename matching.

#### pHash Algorithm

```
Original image
   ↓
1. Scale to 32×32 (remove high-frequency details)
   ↓
2. Convert to grayscale
   ↓
3. 2D DCT (extract frequency features)
   ↓
4. Take top-left 8×8 low-frequency coefficients
   ↓
5. Calculate average of 64 coefficients
   ↓
6. Each coefficient > average → 1, else → 0
   ↓
7. Concatenate into 64-bit integer = pHash value
```

#### Comparison

```
Image A → pHash → 0b10110011...
Image B → pHash → 0b10110100...

Hamming distance = Number of different bits
                 = Count 1s after XOR

Distance = 0    → Same image
Distance ≤ 10  → Match (tolerates minor compression/scaling)
Distance > 10  → Different images
```

#### RAW File Handling

RAW files cannot be opened directly, but **most camera RAWs contain an embedded preview JPG** (the one you see on camera screen).

```
RAW file
   ↓
rawpy.extract_thumb()  ← Extract embedded preview JPG
   ↓
PIL.Image.open()       ← Open as normal image
   ↓
pHash compare           ← Compare with left JPG
```

**Key Finding**: The camera JPG and RAW embedded preview from the same photo are **nearly byte-identical**, pHash distance is usually 0.

#### Anti-Tampering

```
Scenario: Someone renamed DSC00002.ARW to DSC00001.ARW

Lite: DSC00001.JPG → stem match → Export DSC00001.ARW(fake)  ✗

Verified: DSC00001.JPG → stem match → Extract DSC00001.ARW preview
          → pHash(left JPG) vs pHash(right RAW preview)
          → Distance = 136(>10)
          → Decision: Not same image → Skip                ✓
```

### Technical Differences

| Aspect       | Lite              | Verified                          |
| ------------ | ----------------- | --------------------------------- |
| Algorithm    | String stem match | stem match + pHash                |
| Libraries    | None              | Pillow + rawpy + imagehash + scipy|
| Hash         | None              | pHash (DCT-based)                 |
| Threshold    | None              | Hamming distance ≤ 10             |
| Dependencies | 1 (tkinterdnd2)   | 5                                 |
| Size         | 10 MB             | 61 MB                             |

---

## 8. Project Structure

```
raw-match/
├── README.md                    ← This file (Chinese)
├── README_en.md                 ← English version
├── 文件匹配.py                   ← Lite version source
├── 文件匹配终版.py               ← Verified version source
└── Releases page:
    ├── 文件匹配.exe              ← Lite executable (10 MB)
    └── 文件匹配终版.exe          ← Verified executable (61 MB)
```

---

## 9. Version History

| Version  | Date       | Changes                                                      |
| -------- | ---------- | ------------------------------------------------------------ |
| Lite     | 2026-07-03 | Extended format support (23 left + 30 right RAW), removed verification deps, only 10 MB |
| Verified | 2026-07-03 | Added pHash image fingerprint verification, anti-tamper, 61 MB |

---

## 10. Notes

Please do not resell this tool. If you find someone doing so, please report it.

**We all benefit from each other's contributions.**

---

## License

MIT License
