"""ArUco-based gate angle detector with zero-position and camera calibration.

This module supports two operating modes:

- ``mounted``: primary production path for a fixed external camera. Relative
  angle is measured against a stored zero-pose calibration.
- ``handheld``: best-effort debug path for manual uploads. The detector checks
  viewpoint drift against the zero-pose reference and degrades or rejects the
  reading when the camera moved too far.

The marker is expected to be mounted on the moving gate end-cap. Because only a
single moving marker is available, handheld uploads can be improved but cannot
match the accuracy of the fixed-camera path without an additional fixed
reference in the scene.
"""
from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

import cv2
import numpy as np

log = logging.getLogger("riglab.angle_detector")

AngleMode = Literal["mounted", "handheld"]

MARKER_SIZE_M = float(os.getenv("ARUCO_MARKER_SIZE_M", "0.04"))
EXPECTED_MARKER_ID = int(os.getenv("ARUCO_MARKER_ID", "-1"))
MAX_REPROJECTION_ERROR_PX = float(os.getenv("ARUCO_MAX_REPROJECTION_ERROR_PX", "8.0"))
AMBIGUITY_SCORE_MARGIN = float(os.getenv("ARUCO_AMBIGUITY_SCORE_MARGIN", "0.2"))
HANDHELD_APPROX_ANGLE_DEG = float(os.getenv("ARUCO_HANDHELD_APPROX_ANGLE_DEG", "15.0"))
HANDHELD_APPROX_DEPTH_RATIO = float(os.getenv("ARUCO_HANDHELD_APPROX_DEPTH_RATIO", "0.18"))
HANDHELD_REJECT_ANGLE_DEG = float(os.getenv("ARUCO_HANDHELD_REJECT_ANGLE_DEG", "25.0"))
HANDHELD_REJECT_DEPTH_RATIO = float(os.getenv("ARUCO_HANDHELD_REJECT_DEPTH_RATIO", "0.35"))

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
if hasattr(cv2.aruco, "CORNER_REFINE_SUBPIX"):
    _aruco_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
_detector = cv2.aruco.ArucoDetector(_aruco_dict, _aruco_params)

_half = MARKER_SIZE_M / 2.0
_OBJ_POINTS = np.array(
    [
        [-_half, _half, 0.0],
        [_half, _half, 0.0],
        [_half, -_half, 0.0],
        [-_half, -_half, 0.0],
    ],
    dtype=np.float64,
)

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ZERO_CALIB_PATH = os.path.join(_BACKEND_ROOT, "angle_calibration.json")
_CAMERA_CALIB_PATH = os.getenv(
    "ARUCO_CAMERA_CALIBRATION_PATH",
    os.path.join(_BACKEND_ROOT, "camera_calibration.json"),
)


@dataclass
class CameraCalibrationProfile:
    camera_matrix: np.ndarray
    dist_coeffs: np.ndarray
    calibrated: bool
    source: str
    image_size: tuple[int, int] | None = None


@dataclass
class ZeroCalibrationProfile:
    R_zero: np.ndarray
    tvec_zero: np.ndarray
    normal_sign: int
    view_direction_zero: np.ndarray
    depth_zero: float
    samples_used: int
    mean_reprojection_error: float
    camera_calibrated: bool
    camera_source: str
    created_at: str


@dataclass
class PoseCandidate:
    R: np.ndarray
    rvec: np.ndarray
    tvec: np.ndarray
    reprojection_error: float
    marker_area: float
    normal_z: float


@dataclass
class DetectionFrame:
    image_size: tuple[int, int]
    img_points: np.ndarray
    candidates: list[PoseCandidate]
    camera_profile: CameraCalibrationProfile
    marker_area: float


@dataclass
class DetectionResult:
    angle: float | None
    confidence: float
    detected: bool
    calibrated: bool
    mode: AngleMode
    warning: str | None = None
    viewpoint_consistent: bool | None = None
    camera_calibrated: bool = False
    reprojection_error: float | None = None
    used_fallback_intrinsics: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_angle": self.angle,
            "detected": self.detected,
            "calibrated": self.calibrated,
            "confidence": round(float(self.confidence), 4),
            "mode": self.mode,
            "warning": self.warning,
            "viewpoint_consistent": self.viewpoint_consistent,
            "camera_calibrated": self.camera_calibrated,
            "reprojection_error": None
            if self.reprojection_error is None
            else round(float(self.reprojection_error), 4),
            "used_fallback_intrinsics": self.used_fallback_intrinsics,
        }


_camera_profile: CameraCalibrationProfile | None = None
_zero_profile: ZeroCalibrationProfile | None = None
_last_pose_by_mode: dict[AngleMode, np.ndarray | None] = {"mounted": None, "handheld": None}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_mode(value: str | None) -> AngleMode:
    if str(value or "").strip().lower() == "handheld":
        return "handheld"
    return "mounted"


def normalize_mode(value: str | None) -> AngleMode:
    return _normalize_mode(value)


def _ensure_rotation_matrix(matrix: np.ndarray) -> np.ndarray:
    u, _, vt = np.linalg.svd(matrix)
    R = u @ vt
    if np.linalg.det(R) < 0:
        u[:, -1] *= -1
        R = u @ vt
    return R


def _rotation_angle_deg(R: np.ndarray) -> float:
    cos_a = (np.trace(R) - 1.0) / 2.0
    cos_a = max(-1.0, min(1.0, float(cos_a)))
    return abs(math.degrees(math.acos(cos_a)))


def _rotation_delta_deg(a: np.ndarray, b: np.ndarray) -> float:
    return _rotation_angle_deg(a @ b.T)


def _unit(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm <= 1e-9:
        return np.zeros_like(vec, dtype=np.float64)
    return np.asarray(vec, dtype=np.float64).reshape(-1) / norm


def _angle_between_vectors_deg(a: np.ndarray, b: np.ndarray) -> float:
    ua = _unit(a)
    ub = _unit(b)
    if not np.any(ua) or not np.any(ub):
        return 180.0
    dot = max(-1.0, min(1.0, float(np.dot(ua, ub))))
    return math.degrees(math.acos(dot))


def _average_rotation_matrices(rotations: list[np.ndarray]) -> np.ndarray:
    return _ensure_rotation_matrix(np.mean(rotations, axis=0))


def _average_tvecs(vectors: list[np.ndarray]) -> np.ndarray:
    return np.mean(np.stack([np.asarray(vec, dtype=np.float64).reshape(3, 1) for vec in vectors]), axis=0)


def _camera_profile_to_json(profile: CameraCalibrationProfile) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "camera_matrix": profile.camera_matrix.tolist(),
        "dist_coeffs": profile.dist_coeffs.reshape(-1).tolist(),
        "source": profile.source,
    }
    if profile.image_size is not None:
        payload["image_size"] = {"width": int(profile.image_size[0]), "height": int(profile.image_size[1])}
    return payload


def _camera_profile_summary() -> dict[str, Any]:
    return {
        "configured": _camera_profile is not None,
        "calibrated": bool(_camera_profile and _camera_profile.calibrated),
        "source": _camera_profile.source if _camera_profile is not None else None,
        "image_size": None
        if _camera_profile is None or _camera_profile.image_size is None
        else {"width": _camera_profile.image_size[0], "height": _camera_profile.image_size[1]},
    }


def get_camera_calibration_status() -> dict[str, Any]:
    return _camera_profile_summary()


def get_zero_calibration_status() -> dict[str, Any]:
    if _zero_profile is None:
        return {"configured": False}
    return {
        "configured": True,
        "samples_used": _zero_profile.samples_used,
        "mean_reprojection_error": round(float(_zero_profile.mean_reprojection_error), 4),
        "camera_calibrated": _zero_profile.camera_calibrated,
        "camera_source": _zero_profile.camera_source,
        "created_at": _zero_profile.created_at,
    }


def is_calibrated() -> bool:
    return _zero_profile is not None


def _synthetic_camera_profile(width: int, height: int) -> CameraCalibrationProfile:
    f = float(max(width, height))
    matrix = np.array(
        [[f, 0.0, width / 2.0], [0.0, f, height / 2.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    return CameraCalibrationProfile(
        camera_matrix=matrix,
        dist_coeffs=np.zeros((5, 1), dtype=np.float64),
        calibrated=False,
        source="synthetic",
        image_size=(width, height),
    )


def _parse_camera_profile(data: dict[str, Any]) -> CameraCalibrationProfile:
    camera_matrix_raw = data.get("camera_matrix") or data.get("cameraMatrix")
    dist_coeffs_raw = data.get("dist_coeffs") or data.get("distCoeffs")
    if camera_matrix_raw is None or dist_coeffs_raw is None:
        raise ValueError("Camera calibration JSON must include camera_matrix and dist_coeffs")

    camera_matrix = np.array(camera_matrix_raw, dtype=np.float64).reshape(3, 3)
    dist_coeffs = np.array(dist_coeffs_raw, dtype=np.float64).reshape(-1, 1)

    image_size = None
    image_size_raw = data.get("image_size")
    if isinstance(image_size_raw, dict):
        image_size = (int(image_size_raw["width"]), int(image_size_raw["height"]))
    elif "image_width" in data and "image_height" in data:
        image_size = (int(data["image_width"]), int(data["image_height"]))

    return CameraCalibrationProfile(
        camera_matrix=camera_matrix,
        dist_coeffs=dist_coeffs,
        calibrated=True,
        source=str(data.get("source") or "file"),
        image_size=image_size,
    )


def _load_camera_calibration() -> None:
    global _camera_profile
    if not os.path.exists(_CAMERA_CALIB_PATH):
        return
    try:
        with open(_CAMERA_CALIB_PATH, encoding="utf-8") as handle:
            data = json.load(handle)
        _camera_profile = _parse_camera_profile(data)
        log.info("Loaded camera calibration from %s", _CAMERA_CALIB_PATH)
    except Exception as exc:
        _camera_profile = None
        log.warning("Could not load camera calibration: %s", exc)


def set_camera_calibration_from_bytes(raw: bytes) -> tuple[bool, str]:
    global _camera_profile
    try:
        data = json.loads(raw.decode("utf-8"))
        profile = _parse_camera_profile(data)
        with open(_CAMERA_CALIB_PATH, "w", encoding="utf-8") as handle:
            json.dump(_camera_profile_to_json(profile), handle, indent=2)
        _camera_profile = profile
        log.info("Camera calibration saved to %s", _CAMERA_CALIB_PATH)
        return True, "Camera calibration saved"
    except Exception as exc:
        log.error("Camera calibration error: %s", exc, exc_info=True)
        return False, f"Camera calibration error: {exc}"


def clear_camera_calibration() -> None:
    global _camera_profile
    _camera_profile = None
    if os.path.exists(_CAMERA_CALIB_PATH):
        os.remove(_CAMERA_CALIB_PATH)
    log.info("Camera calibration cleared")


def _zero_profile_to_json(profile: ZeroCalibrationProfile) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "marker_size_m": MARKER_SIZE_M,
        "expected_marker_id": EXPECTED_MARKER_ID,
        "R_zero": profile.R_zero.tolist(),
        "tvec_zero": profile.tvec_zero.reshape(-1).tolist(),
        "normal_sign": int(profile.normal_sign),
        "view_direction_zero": profile.view_direction_zero.reshape(-1).tolist(),
        "depth_zero": float(profile.depth_zero),
        "samples_used": int(profile.samples_used),
        "mean_reprojection_error": float(profile.mean_reprojection_error),
        "camera_calibrated": bool(profile.camera_calibrated),
        "camera_source": profile.camera_source,
        "created_at": profile.created_at,
    }


def _parse_zero_profile(data: dict[str, Any]) -> ZeroCalibrationProfile:
    R_zero = np.array(data["R_zero"], dtype=np.float64).reshape(3, 3)
    tvec_zero = np.array(data.get("tvec_zero", [0.0, 0.0, 1.0]), dtype=np.float64).reshape(3, 1)
    view_direction_zero = np.array(
        data.get("view_direction_zero", _unit(tvec_zero.reshape(3))),
        dtype=np.float64,
    ).reshape(3)
    return ZeroCalibrationProfile(
        R_zero=_ensure_rotation_matrix(R_zero),
        tvec_zero=tvec_zero,
        normal_sign=int(data.get("normal_sign", 1)) or 1,
        view_direction_zero=_unit(view_direction_zero),
        depth_zero=float(data.get("depth_zero", float(tvec_zero[2][0]))),
        samples_used=int(data.get("samples_used", 1)),
        mean_reprojection_error=float(data.get("mean_reprojection_error", 0.0)),
        camera_calibrated=bool(data.get("camera_calibrated", False)),
        camera_source=str(data.get("camera_source", "unknown")),
        created_at=str(data.get("created_at") or _utc_now_iso()),
    )


def _load_zero_calibration() -> None:
    global _zero_profile
    if not os.path.exists(_ZERO_CALIB_PATH):
        return
    try:
        with open(_ZERO_CALIB_PATH, encoding="utf-8") as handle:
            data = json.load(handle)
        _zero_profile = _parse_zero_profile(data)
        log.info("Loaded zero calibration from %s", _ZERO_CALIB_PATH)
    except Exception as exc:
        _zero_profile = None
        log.warning("Could not load zero calibration: %s", exc)


def clear_calibration() -> None:
    global _zero_profile
    _zero_profile = None
    _last_pose_by_mode["mounted"] = None
    _last_pose_by_mode["handheld"] = None
    if os.path.exists(_ZERO_CALIB_PATH):
        os.remove(_ZERO_CALIB_PATH)
    log.info("Zero calibration cleared")


def _scaled_camera_profile(width: int, height: int) -> CameraCalibrationProfile:
    if _camera_profile is None:
        return _synthetic_camera_profile(width, height)

    if _camera_profile.image_size is None or _camera_profile.image_size == (width, height):
        return CameraCalibrationProfile(
            camera_matrix=_camera_profile.camera_matrix.copy(),
            dist_coeffs=_camera_profile.dist_coeffs.copy(),
            calibrated=True,
            source=_camera_profile.source,
            image_size=(width, height),
        )

    ref_w, ref_h = _camera_profile.image_size
    sx = width / ref_w
    sy = height / ref_h
    matrix = _camera_profile.camera_matrix.copy()
    matrix[0, 0] *= sx
    matrix[1, 1] *= sy
    matrix[0, 2] *= sx
    matrix[1, 2] *= sy
    return CameraCalibrationProfile(
        camera_matrix=matrix,
        dist_coeffs=_camera_profile.dist_coeffs.copy(),
        calibrated=True,
        source=f"{_camera_profile.source} (scaled)",
        image_size=(width, height),
    )


def _decode_image(image_bytes: bytes) -> np.ndarray | None:
    img_array = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(img_array, cv2.IMREAD_COLOR)


def _solve_pnp_candidates(
    obj_points: np.ndarray,
    img_points: np.ndarray,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
) -> list[tuple[np.ndarray, np.ndarray]]:
    solve_points = img_points
    solve_matrix = camera_matrix
    solve_dist = dist_coeffs

    if np.any(np.abs(dist_coeffs) > 1e-12):
        solve_points = cv2.undistortPoints(
            img_points.reshape(-1, 1, 2),
            camera_matrix,
            dist_coeffs,
        ).reshape(-1, 2)
        solve_matrix = np.eye(3, dtype=np.float64)
        solve_dist = np.zeros((5, 1), dtype=np.float64)

    candidates: list[tuple[np.ndarray, np.ndarray]] = []
    try:
        solve_result = cv2.solvePnPGeneric(
            obj_points,
            solve_points,
            solve_matrix,
            solve_dist,
            flags=cv2.SOLVEPNP_IPPE_SQUARE,
        )
        success = bool(solve_result[0]) if isinstance(solve_result, tuple) else False
        if success:
            rvecs = solve_result[1]
            tvecs = solve_result[2]
            for rvec, tvec in zip(rvecs, tvecs):
                candidates.append(
                    (
                        np.asarray(rvec, dtype=np.float64).reshape(3, 1),
                        np.asarray(tvec, dtype=np.float64).reshape(3, 1),
                    )
                )
    except cv2.error:
        candidates = []

    if not candidates:
        success, rvec, tvec = cv2.solvePnP(
            obj_points,
            solve_points,
            solve_matrix,
            solve_dist,
            flags=cv2.SOLVEPNP_IPPE_SQUARE,
        )
        if success and rvec is not None and tvec is not None:
            candidates.append((np.asarray(rvec, dtype=np.float64).reshape(3, 1), np.asarray(tvec, dtype=np.float64).reshape(3, 1)))

    return candidates


def _extract_frame(image_bytes: bytes) -> DetectionFrame | None:
    img = _decode_image(image_bytes)
    if img is None:
        log.warning("Failed to decode image bytes")
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    camera_profile = _scaled_camera_profile(width, height)
    corners, ids, _ = _detector.detectMarkers(gray)
    if ids is None or len(ids) == 0:
        return None

    marker_index = 0
    if EXPECTED_MARKER_ID >= 0:
        matches = [idx for idx, marker_id in enumerate(ids) if int(marker_id[0]) == EXPECTED_MARKER_ID]
        if not matches:
            return None
        marker_index = matches[0]

    img_points = corners[marker_index][0].astype(np.float64)
    marker_area = float(cv2.contourArea(img_points.astype(np.float32)))

    candidates: list[PoseCandidate] = []
    for rvec, tvec in _solve_pnp_candidates(
        _OBJ_POINTS,
        img_points,
        camera_profile.camera_matrix,
        camera_profile.dist_coeffs,
    ):
        R, _ = cv2.Rodrigues(rvec)
        projected, _ = cv2.projectPoints(
            _OBJ_POINTS,
            rvec,
            tvec,
            camera_profile.camera_matrix,
            camera_profile.dist_coeffs,
        )
        reproj_error = float(
            np.mean(np.linalg.norm(projected.reshape(4, 2) - img_points, axis=1))
        )
        candidates.append(
            PoseCandidate(
                R=np.asarray(R, dtype=np.float64),
                rvec=rvec,
                tvec=tvec,
                reprojection_error=reproj_error,
                marker_area=marker_area,
                normal_z=float(R[2, 2]),
            )
        )

    if not candidates:
        return None

    return DetectionFrame(
        image_size=(width, height),
        img_points=img_points,
        candidates=candidates,
        camera_profile=camera_profile,
        marker_area=marker_area,
    )


def _candidate_score(candidate: PoseCandidate, mode: AngleMode) -> float:
    score = candidate.reprojection_error
    if float(candidate.tvec[2][0]) <= 0:
        score += 1000.0

    if _zero_profile is not None and int(math.copysign(1, candidate.normal_z)) != _zero_profile.normal_sign:
        score += 4.0

    last_pose = _last_pose_by_mode.get(mode)
    if last_pose is not None and mode == "mounted":
        score += min(_rotation_delta_deg(candidate.R, last_pose), 120.0) / 15.0

    return score


def _select_candidate(
    frame: DetectionFrame,
    mode: AngleMode,
) -> tuple[PoseCandidate | None, str | None]:
    ranked = sorted(frame.candidates, key=lambda item: _candidate_score(item, mode))
    if not ranked:
        return None, "No valid ArUco pose candidates were found."

    best = ranked[0]
    warning: str | None = None
    if best.reprojection_error > MAX_REPROJECTION_ERROR_PX:
        return None, "Marker pose is unreliable due to high reprojection error."

    if len(ranked) > 1:
        score_gap = _candidate_score(ranked[1], mode) - _candidate_score(best, mode)
        rotation_gap = _rotation_delta_deg(ranked[1].R, best.R)
        if score_gap < AMBIGUITY_SCORE_MARGIN and rotation_gap > 8.0:
            return None, "Ambiguous marker pose detected; please retake the image."

    if _zero_profile is not None and int(math.copysign(1, best.normal_z)) != _zero_profile.normal_sign:
        warning = "Marker facing direction differs from calibration."

    return best, warning


def _raw_confidence(candidate: PoseCandidate, frame: DetectionFrame) -> float:
    width, height = frame.image_size
    conf_reproj = max(0.0, 1.0 - candidate.reprojection_error / MAX_REPROJECTION_ERROR_PX)
    conf_size = min(1.0, math.sqrt(frame.marker_area) / (min(width, height) * 0.10))
    confidence = (conf_reproj * 0.7) + (conf_size * 0.3)
    if not frame.camera_profile.calibrated:
        confidence *= 0.8
    return max(0.0, min(1.0, confidence))


def _handheld_viewpoint_status(candidate: PoseCandidate) -> tuple[bool, str | None, float]:
    if _zero_profile is None:
        return True, None, 1.0

    view_angle = _angle_between_vectors_deg(
        candidate.tvec.reshape(3),
        _zero_profile.view_direction_zero.reshape(3),
    )
    zero_depth = max(abs(_zero_profile.depth_zero), 1e-6)
    depth_ratio = abs(float(candidate.tvec[2][0]) - _zero_profile.depth_zero) / zero_depth

    if view_angle <= HANDHELD_APPROX_ANGLE_DEG and depth_ratio <= HANDHELD_APPROX_DEPTH_RATIO:
        return True, None, 1.0

    if view_angle <= HANDHELD_REJECT_ANGLE_DEG and depth_ratio <= HANDHELD_REJECT_DEPTH_RATIO:
        return False, "Handheld viewpoint drift is moderate; angle is approximate.", 0.6

    return False, "Handheld viewpoint drift is too large; angle was rejected.", 0.0


def _detect_impl(image_bytes: bytes, mode: AngleMode) -> DetectionResult:
    frame = _extract_frame(image_bytes)
    if frame is None:
        return DetectionResult(
            angle=None,
            confidence=0.0,
            detected=False,
            calibrated=_zero_profile is not None,
            mode=mode,
            camera_calibrated=bool(_camera_profile and _camera_profile.calibrated),
            used_fallback_intrinsics=not bool(_camera_profile and _camera_profile.calibrated),
        )

    candidate, candidate_warning = _select_candidate(frame, mode)
    if candidate is None:
        return DetectionResult(
            angle=None,
            confidence=0.0,
            detected=False,
            calibrated=_zero_profile is not None,
            mode=mode,
            warning=candidate_warning,
            camera_calibrated=frame.camera_profile.calibrated,
            used_fallback_intrinsics=not frame.camera_profile.calibrated,
        )

    warning = candidate_warning
    confidence = _raw_confidence(candidate, frame)
    viewpoint_consistent: bool | None = None

    if _zero_profile is not None:
        R_rel = candidate.R @ _zero_profile.R_zero.T
        angle_deg = _rotation_angle_deg(R_rel)
    else:
        cos_val = max(-1.0, min(1.0, float(abs(candidate.R[2, 2]))))
        angle_deg = math.degrees(math.acos(cos_val))
        warning = warning or "Zero calibration not set; returned raw tilt instead of true gate angle."

    if mode == "handheld" and _zero_profile is not None:
        viewpoint_consistent, viewpoint_warning, viewpoint_scale = _handheld_viewpoint_status(candidate)
        confidence *= viewpoint_scale
        if viewpoint_warning is not None:
            warning = viewpoint_warning if warning is None else f"{warning} {viewpoint_warning}"
        if viewpoint_scale <= 0.0:
            return DetectionResult(
                angle=None,
                confidence=0.0,
                detected=False,
                calibrated=True,
                mode=mode,
                warning=warning,
                viewpoint_consistent=False,
                camera_calibrated=frame.camera_profile.calibrated,
                reprojection_error=candidate.reprojection_error,
                used_fallback_intrinsics=not frame.camera_profile.calibrated,
            )

    angle_deg = round(max(0.0, min(90.0, angle_deg)), 2)
    _last_pose_by_mode[mode] = candidate.R.copy()

    return DetectionResult(
        angle=angle_deg,
        confidence=round(max(0.0, min(1.0, confidence)), 4),
        detected=True,
        calibrated=_zero_profile is not None,
        mode=mode,
        warning=warning,
        viewpoint_consistent=viewpoint_consistent,
        camera_calibrated=frame.camera_profile.calibrated,
        reprojection_error=candidate.reprojection_error,
        used_fallback_intrinsics=not frame.camera_profile.calibrated,
    )


def detect_angle(image_bytes: bytes, mode: str = "mounted") -> DetectionResult:
    normalized_mode = _normalize_mode(mode)
    try:
        return _detect_impl(image_bytes, normalized_mode)
    except Exception as exc:
        log.error("Angle detection failed: %s", exc, exc_info=True)
        return DetectionResult(
            angle=None,
            confidence=0.0,
            detected=False,
            calibrated=_zero_profile is not None,
            mode=normalized_mode,
            warning=f"Angle detection failed: {exc}",
            camera_calibrated=bool(_camera_profile and _camera_profile.calibrated),
            used_fallback_intrinsics=not bool(_camera_profile and _camera_profile.calibrated),
        )


def calibrate_zero(image_batch: list[bytes], mode: str = "mounted") -> dict[str, Any]:
    global _zero_profile
    normalized_mode = _normalize_mode(mode)
    accepted: list[PoseCandidate] = []
    frame_profile: CameraCalibrationProfile | None = None

    for image_bytes in image_batch:
        frame = _extract_frame(image_bytes)
        if frame is None:
            continue
        frame_profile = frame.camera_profile
        candidate, _ = _select_candidate(frame, normalized_mode)
        if candidate is None:
            continue
        if candidate.reprojection_error <= MAX_REPROJECTION_ERROR_PX:
            accepted.append(candidate)

    if not accepted:
        return {
            "success": False,
            "message": "No reliable ArUco marker pose was detected in the calibration images.",
            "calibration": get_zero_calibration_status(),
        }

    R_zero = _average_rotation_matrices([candidate.R for candidate in accepted])
    tvec_zero = _average_tvecs([candidate.tvec for candidate in accepted])
    normal_sign = int(math.copysign(1, float(np.mean([candidate.normal_z for candidate in accepted]))))
    mean_reproj_error = float(np.mean([candidate.reprojection_error for candidate in accepted]))

    _zero_profile = ZeroCalibrationProfile(
        R_zero=R_zero,
        tvec_zero=tvec_zero,
        normal_sign=normal_sign or 1,
        view_direction_zero=_unit(tvec_zero.reshape(3)),
        depth_zero=float(tvec_zero[2][0]),
        samples_used=len(accepted),
        mean_reprojection_error=mean_reproj_error,
        camera_calibrated=bool(frame_profile and frame_profile.calibrated),
        camera_source=frame_profile.source if frame_profile is not None else "synthetic",
        created_at=_utc_now_iso(),
    )
    with open(_ZERO_CALIB_PATH, "w", encoding="utf-8") as handle:
        json.dump(_zero_profile_to_json(_zero_profile), handle, indent=2)

    _last_pose_by_mode["mounted"] = _zero_profile.R_zero.copy()
    _last_pose_by_mode["handheld"] = _zero_profile.R_zero.copy()

    message = "Zero calibrated successfully"
    if len(accepted) == 1:
        message = "Zero calibrated from a single frame. Upload 3-5 images for a more stable zero reference."

    return {
        "success": True,
        "message": message,
        "calibration": get_zero_calibration_status(),
    }


_load_camera_calibration()
_load_zero_calibration()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    blank = np.ones((480, 480, 3), dtype=np.uint8) * 255
    _, enc = cv2.imencode(".jpg", blank)
    result = detect_angle(enc.tobytes())
    assert result.angle is None and result.confidence == 0.0
    print("Smoke test passed: blank image -> no detection")
