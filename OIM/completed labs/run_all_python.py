"""MATLAB-free runner for OIM laboratories 1-4.

Requires: numpy, Pillow, scipy, scikit-image, matplotlib.
All generated artifacts are written into each Lab_XX/results_python folder.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
DEPS = ROOT.parent.parent / "tmp" / "oim" / "deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage
from skimage import exposure, feature, filters, transform, color, util
from skimage.draw import line as draw_line


def save_gray(a, path):
    a = np.asarray(a)
    if a.dtype == bool:
        out = (a * 255).astype(np.uint8)
    elif np.issubdtype(a.dtype, np.floating):
        out = np.clip(a * 255 if a.max(initial=0) <= 1 else a, 0, 255).astype(np.uint8)
    else:
        out = np.clip(a, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(path)


def lab1():
    out = ROOT / "Lab_01" / "results_python"; out.mkdir(exist_ok=True)
    A = np.array([[22, 5], [4, 11], [13, 2]])
    B = np.array([[17, 9, 2, 1, 3], [6, 4, 11, 9, 16]])
    C = np.eye(3, dtype=int)
    D = A - np.array([[0, 0], [3, 0], [0, 0]])
    E = 3 * D; F = D.T
    G = B.copy(); G[:, 2] += [1, -8]; H = G[:, 4::-2]
    I = C[:2, :2]; J = I @ np.diag([1, -1]); K = D @ J
    with (out / "matrix_results.txt").open("w", encoding="utf-8") as f:
        for name, value in {"A": A, "B": B, "C": C, "D": D, "E": E, "F": F,
                            "G": G, "H": H, "I": I, "J": J, "K": K}.items():
            f.write(f"{name} =\n{value}\n\n")
    image = np.loadtxt(ROOT / "Lab_01" / "data" / "image.dat")
    low, high, mean = image.min(), image.max(), image.mean()
    shifted = image - low
    stretched = shifted * (255 / (high - low)) if high > low else shifted
    save_gray(image, out / "original.png"); save_gray(shifted, out / "shifted.png"); save_gray(stretched, out / "autocontrast.png")
    (out / "measurements.txt").write_text(f"i_low={low}\ni_high={high}\ni_mean={mean}\nk={255/(high-low)}\n", encoding="utf-8")


def lab2():
    out = ROOT / "Lab_02" / "results_python"; out.mkdir(exist_ok=True)
    data = ROOT / "Lab_02" / "data"
    lifting = np.asarray(Image.open(data / "liftingbody.jpg"))
    save_gray(lifting, out / "lifting_original.png")
    save_gray(lifting[158:488, 32:362], out / "lifting_sub1.png")
    save_gray(lifting[109:209, 359:459], out / "lifting_sub2.png")
    flood = np.asarray(Image.open(data / "flood.jpg").convert("L"))
    eq = exposure.equalize_hist(flood, nbins=256)
    matched = exposure.match_histograms(flood, np.asarray(Image.open(data / "flood_reference_from_pdf.png").convert("L")))
    save_gray(flood, out / "flood_original.png"); save_gray(eq, out / "flood_equalized.png"); save_gray(matched, out / "flood_matched.png")
    np.savetxt(out / "histogram_original.txt", np.bincount(flood.ravel(), minlength=256), fmt="%d")
    np.savetxt(out / "histogram_equalized.txt", np.histogram(eq, bins=256, range=(0, 1))[0], fmt="%d")


def lab3():
    out = ROOT / "Lab_03" / "results_python"; out.mkdir(exist_ok=True)
    data = ROOT / "Lab_03" / "data"
    f = np.asarray(Image.open(data / "liftingbody_r0.png"))
    d = f.astype(float) / 255
    transforms = [1-d, 1/(1+(d.mean()/(d+np.finfo(float).eps))**10), 2*np.log1p(d), d**3]
    checks=[]
    for i, result in enumerate(transforms, 1):
        result = np.clip(result, 0, 1)
        ref = np.asarray(Image.open(data / f"liftingbody_r{i}.png"))
        actual = np.rint(result*255).astype(np.uint8)
        checks.append(f"r{i}: different={np.count_nonzero(actual != ref)}, MAE={np.abs(actual.astype(float)-ref).mean():.12g}")
        save_gray(result, out / f"reproduced_r{i}.png")
    (out / "transform_checks.txt").write_text("\n".join(checks)+"\n", encoding="utf-8")
    cats = np.asarray(Image.open(data / "two_cats.jpg").convert("L"))
    sobel_h = ndimage.sobel(cats, axis=0, mode="constant")
    sobel_v = ndimage.sobel(cats, axis=1, mode="constant")
    save_gray(np.abs(sobel_h)/np.max(np.abs(sobel_h)), out / "horizontal_edges.png")
    save_gray(np.abs(sobel_v)/np.max(np.abs(sobel_v)), out / "vertical_edges.png")
    save_gray((np.abs(sobel_h)+np.abs(sobel_v))/np.max(np.abs(sobel_h)+np.abs(sobel_v)), out / "combined_edges.png")


def lab4():
    out = ROOT / "Lab_04" / "results_python"; out.mkdir(exist_ok=True)
    data = ROOT / "Lab_04" / "data"
    building = np.asarray(Image.open(data / "building.jpg").convert("L")) / 255
    canny = feature.canny(building, sigma=2, low_threshold=.04, high_threshold=.10)
    zero = ndimage.gaussian_laplace(building, sigma=2)
    zero = (zero * ndimage.maximum_filter(zero, 3) <= 0) & (zero * ndimage.minimum_filter(zero, 3) <= 0)
    save_gray(canny, out / "canny.png"); save_gray(zero, out / "zerocross.png")
    text = np.asarray(Image.open(data / "text.jpg").convert("L"))
    t = .5 * (float(text.min()) + float(text.max())); history=[t]
    for _ in range(1000):
        g = text >= t
        if g.all() or (~g).all(): break
        tn = .5 * (text[g].mean() + text[~g].mean()); history.append(tn)
        if abs(tn-t) < .5: t=tn; break
        t=tn
    otsu = filters.threshold_otsu(text)
    save_gray(text >= t, out / "text_iterative.png"); save_gray(text >= otsu, out / "text_otsu.png")
    lines = transform.probabilistic_hough_line(canny, threshold=10, line_length=40, line_gap=15)
    overlay = np.dstack([canny, canny, canny]).astype(float)
    for (p0, p1) in lines:
        rr, cc = draw_line(p0[1], p0[0], p1[1], p1[0]); valid=(rr<overlay.shape[0])&(cc<overlay.shape[1])
        overlay[rr[valid],cc[valid]]=[1,0,0]
    save_gray(overlay, out / "hough_lines.png")
    (out / "thresholds.txt").write_text(f"iterative={t}\notsu={otsu}\niterations={len(history)-1}\nlines={len(lines)}\n", encoding="utf-8")


if __name__ == "__main__":
    lab1(); lab2(); lab3(); lab4()
    print("All four laboratories completed with Python equivalents.")
