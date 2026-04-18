"""ArUco-based gate angle detector with zero-position calibration.

Camera is mounted in front of the gate face. The ArUco marker (4x4 cm) sits
on the flat end-cap of the gate.

Without calibration: returns raw tilt from camera axis (unreliable as absolute angle).
With calibration:    stores the rotation matrix at gate-closed (0°) position,
                     then reports the relative rotation from that reference.
                     Formula: arccos((trace(R_rel) - 1) / 2)
                     This works for any hinge axis direction without needing to
                     know which physical axis the gate rotates about.
"""
from __future__ import annotations

import json
import logging
import math
import os

import cv2
import numpy as np

log = logging.getLogger("riglab.angle_detector")

MARKER_SIZE_M = float(os.getenv("ARUCO_MARKER_SIZE_M", "0.04"))
EXPECTED_MARKER_ID = int(os.getenv("ARUCO_MARKER_ID", "-1"))

_DICT_MAP: dict[str, int] = {
    "DICT_4X4_50": cv2.aruco.DICT_4X4_50,
    "DICT_4X4_100": cv2.aruco.DICT_4X4_100,
    "DICT_4X4_250": cv2.aruco.DICT_4X4_250,
    "DICT_4X4_1000": cv2.aruco.DICT_4X4_1000,
    "DICT_5X5_50": cv2.aruco.DICT_5X5_50,
    "DICT_6X6_50": cv2.aruco.DICT_6X6_50,
}
_dict_name = os.getenv("ARUCO_DICT", "DICT_4X4_50")
_aruco_dict = cv2.aruco.getPredefinedDictionary(
    _DICT_MAP.get(_dict_name, cv2.aruco.DICT_4X4_50)
)
_aruco_params = cv2.aruco.DetectorParameters()
_detector = cv2.aruco.ArucoDetector(_aruco_dict, _aruco_params)

_half = MARKER_SIZE_M / 2.0
_OBJ_POINTS = np.array(
    [
        [-_half,  _half, 0.0],
        [ _half,  _half, 0.0],
        [ _half, -_half, 0.0],
        [-_half, -_half, 0.0],
    ],
    dtype=np.float64,
)

# ── Calibration state ────────────────────────────────────────────────────────

_CALIB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "angle_calibration.json")
_R_zero: np.ndarray | None = None


def _load_calibration() -> None:
    global _R_zero
    if not os.path.exists(_CALIB_PATH):
        return
    try:
        with open(_CALIB_PATH) as f:
            data = json.load(f)
        _R_zero = np.array(data["R_zero"], dtype=np.float64).reshape(3, 3)
        log.info("Loaded zero calibration from %s", _CALIB_PATH)
    except Exception as exc:
        log.warning("Could not load calibration file: %s", exc)


def is_calibrated() -> bool:
    return _R_zero is not None


def calibrate_zero(image_bytes: bytes) -> tuple[bool, str]:
    """Store the current marker pose as the zero (gate fully closed) reference."""
    global _R_zero
    try:
        pose = _extract_pose(image_bytes)
        if pose is None:
            return False, "No ArUco marker detected — make sure the marker is visible"
        R, _, _, _, _ = pose
        _R_zero = R.copy()
        with open(_CALIB_PATH, "w") as f:
            json.dump({"R_zero": _R_zero.tolist()}, f, indent=2)
        log.info("Zero calibration saved to %s", _CALIB_PATH)
        return True, "Zero calibrated successfully"
    except Exception as exc:
        log.error("Calibration error: %s", exc, exc_info=True)
        return False, f"Calibration error: {exc}"


def clear_calibration() -> None:
    global _R_zero
    _R_zero = None
    if os.path.exists(_CALIB_PATH):
        os.remove(_CALIB_PATH)
    log.info("Zero calibration cleared")


# ── Pose extraction ──────────────────────────────────────────────────────────

def _extract_pose(
    image_bytes: bytes,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, tuple[int, int]] | None:
    """Detect the ArUco marker and return (R, rvec, tvec, img_points, (w, h)).

    Returns None when no valid marker is found.
    """
    img_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        log.warning("Failed to decode image bytes")
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    f = float(max(w, h))
    camera_matrix = np.array(
        [[f, 0.0, w / 2.0], [0.0, f, h / 2.0], [0.0, 0.0, 1.0]], dtype=np.float64
    )
    dist_coeffs = np.zeros((5, 1), dtype=np.float64)

    corners, ids, _ = _detector.detectMarkers(gray)
    if ids is None or len(ids) == 0:
        log.debug("No ArUco markers detected")
        return None

    idx = 0
    if EXPECTED_MARKER_ID >= 0:
        matches = [i for i, mid in enumerate(ids) if int(mid[0]) == EXPECTED_MARKER_ID]
        if not matches:
            log.debug("Expected marker ID %d not found", EXPECTED_MARKER_ID)
            return None
        idx = matches[0]

    img_points = corners[idx][0].astype(np.float64)

    success, rvec, tvec = cv2.solvePnP(
        _OBJ_POINTS, img_points, camera_matrix, dist_coeffs,
        flags=cv2.SOLVEPNP_IPPE_SQUARE,
    )
    if not success or rvec is None:
        log.debug("solvePnP failed")
        return None

    R, _ = cv2.Rodrigues(rvec)

    # Reproject to compute confidence
    projected, _ = cv2.projectPoints(_OBJ_POINTS, rvec, tvec, camera_matrix, dist_coeffs)
    reproj_error = float(
        np.mean(np.linalg.norm(projected.reshape(4, 2) - img_points, axis=1))
    )
    marker_area = float(cv2.contourArea(img_points.astype(np.float32)))
    conf_reproj = max(0.0, 1.0 - reproj_error / 5.0)
    conf_size = min(1.0, math.sqrt(marker_area) / (min(w, h) * 0.10))
    confidence = round((conf_reproj + conf_size) / 2.0, 4)

    return R, rvec, tvec, img_points, confidence  # type: ignore[return-value]


def _rotation_angle_deg(R: np.ndarray) -> float:
    """Total rotation angle of a rotation matrix (axis-angle magnitude, 0–180°)."""
    cos_a = (np.trace(R) - 1.0) / 2.0
    cos_a = max(-1.0, min(1.0, float(cos_a)))
    return abs(math.degrees(math.acos(cos_a)))


# ── Public API ───────────────────────────────────────────────────────────────

def detect_angle(image_bytes: bytes) -> tuple[float | None, float]:
    """Detect gate angle from a JPEG/PNG image.

    Returns (angle_degrees, confidence).
    - If calibrated: angle is relative to the stored zero position (0–90°).
    - If not calibrated: raw tilt from camera axis (useful only for comparison).
    Returns (None, 0.0) when no marker is detected or an error occurs.
    """
    try:
        return _detect_impl(image_bytes)
    except Exception as exc:
        log.error("Angle detection failed: %s", exc, exc_info=True)
        return None, 0.0


def _detect_impl(image_bytes: bytes) -> tuple[float | None, float]:
    result = _extract_pose(image_bytes)
    if result is None:
        return None, 0.0

    R, _, _, _, confidence = result

    if _R_zero is not None:
        # Relative rotation from the calibrated zero position.
        # arccos((trace(R_rel)-1)/2) gives the actual rotation angle around
        # whatever axis the gate hinge is — no need to know the axis direction.
        R_rel = R @ _R_zero.T
        angle_deg = _rotation_angle_deg(R_rel)
    else:
        # Uncalibrated fallback: tilt of marker face from camera axis.
        cos_val = max(-1.0, min(1.0, float(abs(R[2, 2]))))
        angle_deg = math.degrees(math.acos(cos_val))

    angle_deg = round(max(0.0, min(90.0, angle_deg)), 2)
    log.debug("angle=%.2f deg  confidence=%.4f  calibrated=%s", angle_deg, confidence, _R_zero is not None)
    return angle_deg, confidence


# Load persisted calibration on module import
_load_calibration()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    blank = np.ones((480, 480, 3), dtype=np.uint8) * 255
    _, enc = cv2.imencode(".jpg", blank)
    result = detect_angle(enc.tobytes())
    assert result == (None, 0.0), f"Expected (None, 0.0) for blank image, got {result}"
    print("Smoke test passed: blank image → (None, 0.0)")
