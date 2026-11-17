"""Scenecraft Neural Watermark Cleaner (cross-platform, based on flow_clean_v3).

Removes visible corner watermarks from images and videos using the LaMa ONNX inpainting
model with grain matching, native 512x512 window fill, and temporal frame fill reuse.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from scenecraft.config import get_config

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VID_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
MODEL_URL = "https://huggingface.co/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx"
TILE = 512


def corner_box(w: int, h: int, corner: str, fw: float, fh: float, margin: float) -> Tuple[int, int, int, int]:
    bw, bh = int(w * fw), int(h * fh)
    m = int(min(w, h) * margin)
    x0 = w - bw - m if "right" in corner else m
    y0 = h - bh - m if "bottom" in corner else m
    x0, y0 = max(x0, 0), max(y0, 0)
    return x0, y0, min(x0 + bw + m, w), min(y0 + bh + m, h)


def raw_mask(img: np.ndarray, a: Any) -> np.ndarray:
    """0/1 map of pixels that stand out from their surroundings in the corner box."""
    h, w = img.shape[:2]
    x0, y0, x1, y1 = corner_box(w, h, a.corner, a.w, a.h, a.margin)
    roi = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    k = max(15, (min(roi.shape[:2]) // 3) | 1)
    m = (cv2.absdiff(roi, cv2.medianBlur(roi, k)) > a.sens).astype(np.uint8)
    full = np.zeros((h, w), np.uint8)
    full[y0:y1, x0:x1] = m
    return full


def get_mask(shape: Tuple[int, int], votes: np.ndarray, n: int, a: Any) -> np.ndarray:
    h, w = shape
    if getattr(a, "mask", None):
        m = cv2.imread(str(Path(a.mask).expanduser()), cv2.IMREAD_GRAYSCALE)
        if m is None:
            raise FileNotFoundError(f"Cannot read mask: {a.mask}")
        m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
        return (m > 127).astype(np.uint8) * 255
    m = (votes >= max(1, int(np.ceil(n * a.vote)))).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * a.grow + 1,) * 2))
    if m.sum() == 0:  # nothing detected -> whole search box
        x0, y0, x1, y1 = corner_box(w, h, a.corner, a.w, a.h, a.margin)
        m[y0:y1, x0:x1] = 255
    return m


def load_session(path: Optional[Path | str] = None, threads: int = 4) -> Any:
    try:
        import onnxruntime as ort
    except ImportError:
        return None

    if path is None:
        cfg = get_config()
        path = cfg.models_dir / cfg.cleaner_model_name
    else:
        path = Path(path).expanduser()

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading LaMa model to {path} (one time, ~200 MB)...")
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(MODEL_URL, tmp)
        tmp.rename(path)

    so = ort.SessionOptions()
    so.intra_op_num_threads = threads
    so.inter_op_num_threads = 1
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(str(path), sess_options=so, providers=["CPUExecutionProvider"])


class Cleaner:
    """Everything that depends only on the mask is computed once here."""

    def __init__(self, sess: Any, mask: np.ndarray, a: Any, video: bool = False):
        self.sess, self.a, self.video = sess, a, video
        h, w = mask.shape
        ys, xs = np.where(mask > 0)
        if len(xs) == 0 or len(ys) == 0:
            bx0, bx1, by0, by1 = 0, w, 0, h
        else:
            bx0, bx1, by0, by1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        bw, bh = bx1 - bx0, by1 - by0
        if bw <= TILE and bh <= TILE and w >= TILE and h >= TILE:
            cx0 = int(np.clip((bx0 + bx1) // 2 - TILE // 2, 0, w - TILE))
            cy0 = int(np.clip((by0 + by1) // 2 - TILE // 2, 0, h - TILE))
            self.win, self.native = (cx0, cy0, cx0 + TILE, cy0 + TILE), True
        else:
            pad = int(max(bw, bh) * getattr(a, "context", 1.0))
            self.win = (max(bx0 - pad, 0), max(by0 - pad, 0), min(bx1 + pad, w), min(by1 + pad, h))
            self.native = False
        cx0, cy0, cx1, cy1 = self.win
        self.cm = mask[cy0:cy1, cx0:cx1]
        self.inside = self.cm > 0
        big = cv2.dilate(self.cm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (51, 51)))
        self.ring = (big > 0) & ~self.inside
        alpha = cv2.GaussianBlur(self.cm.astype(np.float32) / 255.0, (0, 0), 2.0)
        self.alpha = np.clip(alpha * 1.3, 0, 1)[..., None]
        self.ref = self.last = None
        self.runs = self.reused = 0

    def _infer(self, crop: np.ndarray) -> np.ndarray:
        if self.sess is None:
            return cv2.inpaint(crop, self.cm, 5, cv2.INPAINT_TELEA)
        ch, cw = crop.shape[:2]
        if self.native:
            rimg, rmask = crop, self.cm > 127
        else:
            interp = cv2.INTER_AREA if max(ch, cw) > TILE else cv2.INTER_CUBIC
            rimg = cv2.resize(crop, (TILE, TILE), interpolation=interp)
            rmask = cv2.resize(self.cm, (TILE, TILE), interpolation=cv2.INTER_NEAREST) > 127
        inp = (cv2.cvtColor(rimg, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0).transpose(2, 0, 1)[None]
        mk = rmask.astype(np.float32)[None, None]
        names = [i.name for i in self.sess.get_inputs()]
        out = self.sess.run(None, {names[0]: inp, names[1]: mk})[0][0].transpose(1, 2, 0)
        if out.max() <= 1.5:
            out = out * 255.0
        out = cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
        if not self.native:
            out = cv2.resize(out, (cw, ch), interpolation=cv2.INTER_CUBIC)
        return out

    def _grain(self, crop: np.ndarray, out: np.ndarray) -> np.ndarray:
        if getattr(self.a, "no_grain", False) or self.ring.sum() < 50:
            return out

        def noise_level(img: np.ndarray, sel: np.ndarray) -> float:
            g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
            v = (g - cv2.GaussianBlur(g, (0, 0), 1.5))[sel]
            return float(1.4826 * np.median(np.abs(v - np.median(v))))

        s_ring, s_fill = noise_level(crop, self.ring), noise_level(out, self.inside)
        sigma = min(float(np.sqrt(max(s_ring ** 2 - s_fill ** 2, 0.0))), 8.0)
        if sigma < 0.3:
            return out
        n = cv2.GaussianBlur(np.random.normal(0, 1, out.shape[:2]).astype(np.float32), (0, 0), 0.7)
        n *= sigma / max(float(n.std()), 1e-6)
        return np.clip(out.astype(np.float32) + n[..., None], 0, 255).astype(np.uint8)

    def process(self, img: np.ndarray) -> np.ndarray:
        cx0, cy0, cx1, cy1 = self.win
        crop = img[cy0:cy1, cx0:cx1]
        out = None
        if self.video and self.ref is not None:
            if np.mean(np.abs(crop[self.ring].astype(np.int16) - self.ref)) < getattr(self.a, "static", 1.5):
                out, self.reused = self.last, self.reused + 1
        if out is None:
            out = self._infer(crop)
            self.runs += 1
            if self.video:
                self.ref, self.last = crop[self.ring].astype(np.int16), out
        out = self._grain(crop, out)
        blended = out.astype(np.float32) * self.alpha + crop.astype(np.float32) * (1 - self.alpha)
        res = img if self.video else img.copy()
        res[cy0:cy1, cx0:cx1] = np.clip(blended, 0, 255).astype(np.uint8)
        return res


class CleanerOptions:
    def __init__(
        self,
        corner: str = "bottom-right",
        w: float = 0.18,
        h: float = 0.08,
        margin: float = 0.01,
        sens: float = 10,
        grow: int = 4,
        vote: float = 0.5,
        vote_samples: int = 12,
        context: float = 1.0,
        no_grain: bool = False,
        threads: int = 4,
        nice: int = 10,
        static: float = 1.5,
        crf: int = 16,
        preset: str = "medium",
        mask: Optional[str] = None,
        save_mask: bool = False,
        force: bool = False,
    ):
        self.corner = corner
        self.w = w
        self.h = h
        self.margin = margin
        self.sens = sens
        self.grow = grow
        self.vote = vote
        self.vote_samples = vote_samples
        self.context = context
        self.no_grain = no_grain
        self.threads = threads
        self.nice = nice
        self.static = static
        self.crf = crf
        self.preset = preset
        self.mask = mask
        self.save_mask = save_mask
        self.force = force


def clean_image(image_path: Path | str, output_path: Path | str, sess: Any = None, opts: Optional[CleanerOptions] = None) -> Path:
    """Clean watermark from a single image."""
    img_p = Path(image_path).resolve()
    out_p = Path(output_path).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)
    opts = opts or CleanerOptions()

    img = cv2.imread(str(img_p), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Unreadable image: {img_p}")

    if sess is None:
        sess = load_session(threads=opts.threads)

    v = raw_mask(img, opts)
    mask = get_mask(img.shape[:2], v, 1, opts)
    cl = Cleaner(sess, mask, opts, video=False)
    cleaned = cl.process(img)

    ext = out_p.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        cv2.imwrite(str(out_p), cleaned, [cv2.IMWRITE_JPEG_QUALITY, 98])
    else:
        cv2.imwrite(str(out_p), cleaned)
    return out_p


def clean_directory(input_dir: Path | str, output_dir: Path | str, sess: Any = None, opts: Optional[CleanerOptions] = None) -> List[Path]:
    """Clean all images in a directory."""
    in_d = Path(input_dir).resolve()
    out_d = Path(output_dir).resolve()
    out_d.mkdir(parents=True, exist_ok=True)
    opts = opts or CleanerOptions()

    files = [f for f in sorted(in_d.iterdir()) if f.is_file() and f.suffix.lower() in IMG_EXTS]
    if not files:
        return []

    if sess is None:
        sess = load_session(threads=opts.threads)

    results: List[Path] = []
    for f in files:
        out_f = out_d / f.name
        clean_image(f, out_f, sess=sess, opts=opts)
        results.append(out_f)
    return results
