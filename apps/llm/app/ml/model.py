# -*- coding: utf-8 -*-
from __future__ import annotations

import threading
from urllib.parse import urlparse

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download

_REPO_ID = "pirocheto/phishing-url-detection"
_FILENAME = "model.onnx"

_WHITELIST_SUFFIXES: tuple[str, ...] = (
    ".go.kr",
    ".or.kr",
    ".ac.kr",
    ".edu.kr",
    ".re.kr",
    ".mil.kr",
)

_session_lock = threading.Lock()
_session: ort.InferenceSession | None = None


def _hostname(url: str) -> str | None:
    if not url or not url.strip():
        return None
    u = url.strip()
    if not urlparse(u).scheme:
        u = "http://" + u
    host = urlparse(u).hostname
    return host.lower() if host else None


def _is_whitelisted_domain(host: str | None) -> bool:
    if not host:
        return False
    h = host.lower()
    return any(h.endswith(s) for s in _WHITELIST_SUFFIXES)


def _get_session() -> ort.InferenceSession:
    global _session
    with _session_lock:
        if _session is None:
            model_path = hf_hub_download(repo_id=_REPO_ID, filename=_FILENAME)
            _session = ort.InferenceSession(
                model_path,
                providers=["CPUExecutionProvider"],
            )
        return _session


def _probability_to_percent(prob: float) -> float:
    if prob <= 1.0 + 1e-6:
        return float(np.clip(prob * 100.0, 0.0, 100.0))
    return float(np.clip(prob, 0.0, 100.0))


def predict_phishing_score(url: str) -> float:
    """피싱 추정 점수 0~100. 화이트리스트면 0.0, 모델 오류 시 -1.0."""
    try:
        host = _hostname(url)
        if _is_whitelisted_domain(host):
            return 0.0

        sess = _get_session()
        input_meta = sess.get_inputs()[0]
        input_name = input_meta.name
        arr = np.array([url.strip()], dtype=object)

        outputs = sess.run(None, {input_name: arr})

        if len(outputs) >= 2:
            raw = outputs[1]
        else:
            raw = outputs[0]

        row = np.asarray(raw).reshape(-1)
        if row.size >= 2:
            p = float(row[1])
        else:
            p = float(row[0])

        return _probability_to_percent(p)
    except Exception:
        return -1.0
