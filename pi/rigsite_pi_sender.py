import base64
import concurrent.futures
import io
import ipaddress
import logging
import os
import subprocess
import threading
import time
from datetime import datetime

import RPi.GPIO as GPIO
import requests
from PIL import Image

BACKEND_PORT = int(os.getenv("RIGSITE_BACKEND_PORT", "18000"))
BACKEND_HOST_OVERRIDE = os.getenv("RIGSITE_BACKEND_HOST", "").strip()
DISCOVERY_TIMEOUT = 0.35
DISCOVERY_WORKERS = 16
DISCOVERY_COOLDOWN = 5.0

LED_RED    = 17
LED_GREEN  = 27
BUTTON_PIN = 22
FLOW_PIN   = 23

FLOW_K_FACTOR   = 6.6
P_MAX_SIM       = 0.193
P2_RATIO        = 0.80
Q_MAX_EST       = 25.0
LPM_TO_GPM      = 1.0 / 3.78541
SAMPLE_INTERVAL = 1.0
POLL_SLEEP      = 0.02

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("rigsite.pi")

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(LED_RED,    GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(LED_GREEN,  GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(BUTTON_PIN, GPIO.IN,  pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(FLOW_PIN,   GPIO.IN,  pull_up_down=GPIO.PUD_UP)

_pulse_lock    = threading.Lock()
_pulse_count   = 0
_polling_active = False
_poll_thread   = None
_backend_lock = threading.Lock()
_backend_base_url = None
_next_discovery_at = 0.0


def _build_base_url(host):
    host = str(host).strip()
    if not host:
        return None
    if host.startswith(("http://", "https://")):
        return host.rstrip("/")
    return f"http://{host}:{BACKEND_PORT}"


def _get_backend_base_url():
    with _backend_lock:
        return _backend_base_url


def _set_backend_base_url(base_url):
    global _backend_base_url, _next_discovery_at
    with _backend_lock:
        _backend_base_url = base_url
        _next_discovery_at = 0.0


def _schedule_discovery_backoff():
    global _next_discovery_at
    with _backend_lock:
        _next_discovery_at = time.monotonic() + DISCOVERY_COOLDOWN


def _clear_backend_base_url(reason, backoff=False):
    global _backend_base_url, _next_discovery_at
    with _backend_lock:
        previous = _backend_base_url
        _backend_base_url = None
        _next_discovery_at = time.monotonic() + DISCOVERY_COOLDOWN if backoff else 0.0
    if previous:
        log.warning("Backend connection cleared (%s): %s", reason, previous)


def _get_interface_networks():
    try:
        result = subprocess.run(
            ["ip", "-o", "-4", "addr", "show", "scope", "global"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        log.error("Could not inspect Pi network interfaces with `ip`: %s", exc)
        return []

    networks = []
    for raw_line in result.stdout.splitlines():
        parts = raw_line.split()
        if "inet" not in parts:
            continue
        inet_index = parts.index("inet")
        if inet_index == 0 or inet_index + 1 >= len(parts):
            continue
        iface = parts[1]
        cidr = parts[inet_index + 1]
        try:
            interface = ipaddress.ip_interface(cidr)
        except ValueError:
            continue
        networks.append((iface, interface))
    return networks


def _probe_backend_status(base_url, timeout=DISCOVERY_TIMEOUT):
    status_url = f"{base_url}/api/v1/pi/status"
    try:
        response = requests.get(status_url, timeout=timeout)
        if response.status_code != 200:
            return None
        payload = response.json()
        if payload.get("backend") != "online":
            return None
        return payload
    except Exception:
        return None


def _discover_backend_base_url():
    if BACKEND_HOST_OVERRIDE:
        base_url = _build_base_url(BACKEND_HOST_OVERRIDE)
        log.info("Using backend override from RIGSITE_BACKEND_HOST -> %s", base_url)
        _set_backend_base_url(base_url)
        return base_url

    networks = _get_interface_networks()
    if not networks:
        log.warning("No active IPv4 network found for backend discovery")
        _schedule_discovery_backoff()
        return None

    candidates = []
    seen_hosts = set()
    for iface, interface in networks:
        log.info("Discovery network %s -> %s", iface, interface)
        for host in interface.network.hosts():
            host_text = str(host)
            if host == interface.ip or host_text in seen_hosts:
                continue
            seen_hosts.add(host_text)
            candidates.append(host_text)

    if not candidates:
        log.warning("Backend discovery found no LAN hosts to probe")
        _schedule_discovery_backoff()
        return None

    log.info("Scanning %d host(s) on local network for RigLab backend port %d", len(candidates), BACKEND_PORT)
    with concurrent.futures.ThreadPoolExecutor(max_workers=DISCOVERY_WORKERS) as executor:
        futures = {
            executor.submit(_probe_backend_status, _build_base_url(host)): host
            for host in candidates
        }
        for future in concurrent.futures.as_completed(futures):
            host = futures[future]
            try:
                payload = future.result()
            except Exception:
                payload = None
            if not payload:
                continue

            base_url = _build_base_url(host)
            log.info(
                "Discovered backend at %s -> calibrated=%s pi_session_active=%s",
                base_url,
                payload.get("angle_calibrated"),
                payload.get("pi_session_active"),
            )
            _set_backend_base_url(base_url)
            for pending in futures:
                pending.cancel()
            return base_url

    log.warning("No RigLab backend responded on the local Wi-Fi subnet")
    _schedule_discovery_backoff()
    return None


def resolve_backend_base_url(force=False):
    cached = _get_backend_base_url()
    if cached and not force:
        return cached

    now = time.monotonic()
    with _backend_lock:
        next_allowed = _next_discovery_at
    if not force and now < next_allowed:
        return None

    return _discover_backend_base_url()


def _get_endpoint_url(path, force_discovery=False):
    base_url = resolve_backend_base_url(force=force_discovery)
    if not base_url:
        return None
    return f"{base_url}{path}"


def _flow_polling_thread():
    global _pulse_count, _polling_active
    last_state = GPIO.input(FLOW_PIN)
    while _polling_active:
        state = GPIO.input(FLOW_PIN)
        if last_state == 1 and state == 0:
            with _pulse_lock:
                _pulse_count += 1
            time.sleep(0.001)
        last_state = state
        time.sleep(0.0005)


def start_polling():
    global _polling_active, _poll_thread, _pulse_count
    with _pulse_lock:
        _pulse_count = 0
    _polling_active = True
    _poll_thread = threading.Thread(target=_flow_polling_thread, daemon=True)
    _poll_thread.start()


def stop_polling():
    global _polling_active
    _polling_active = False
    if _poll_thread is not None:
        _poll_thread.join(timeout=1.0)


def read_and_reset_pulses():
    global _pulse_count
    with _pulse_lock:
        count = _pulse_count
        _pulse_count = 0
    return count


picam2 = None
try:
    from picamera2 import Picamera2
    picam2 = Picamera2()
    cam_config = picam2.create_video_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
    picam2.configure(cam_config)
    picam2.start()
    time.sleep(2)
    log.info("Camera ready - video mode 640x480")
except Exception as exc:
    picam2 = None
    log.warning("Camera not available. (%s)", exc)


def capture_image_b64():
    if picam2 is None:
        return None
    try:
        frame = picam2.capture_array("main")
        img   = Image.fromarray(frame)
        buf   = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")
    except Exception as exc:
        log.error("Camera capture failed: %s", exc)
        return None


def get_simulated_pressures(flow_lpm):
    ratio = min(flow_lpm / Q_MAX_EST, 1.0)
    p1 = round(ratio * P_MAX_SIM, 4)
    p2 = round(p1 * P2_RATIO, 4)
    return p1, p2


def verify_backend():
    status_url = _get_endpoint_url("/api/v1/pi/status", force_discovery=True)
    if not status_url:
        log.warning("No backend discovered. Ensure the laptop is on the same Wi-Fi and port %d is open.", BACKEND_PORT)
        return False

    try:
        resp = requests.get(status_url, timeout=3.0)
        resp.raise_for_status()
        data = resp.json()
        log.info(
            "Backend online at %s -> calibrated=%s  pi_session_active=%s",
            status_url,
            data.get("angle_calibrated"),
            data.get("pi_session_active"),
        )
        return True
    except Exception as exc:
        _clear_backend_base_url(f"status probe failed: {exc}", backoff=True)
        log.warning("Backend not reachable -> %s", exc)
        return False


def send_sample(payload):
    ingest_url = _get_endpoint_url("/api/v1/pi/ingest")
    if not ingest_url:
        log.warning("Skipping sample: backend not discovered yet")
        return False

    try:
        resp = requests.post(ingest_url, json=payload, timeout=2.5)
        resp.raise_for_status()
        result = resp.json()
        state = result.get("state", "?")
        angle = result.get("gate_angle")
        mw    = result.get("mud_weight")
        log.info("-> state=%-11s  angle=%s  MW=%s",
                 state,
                 f"{angle:.1f} deg" if angle is not None else "N/A",
                 f"{mw:.3f} PPG"    if mw    is not None else "N/A")
        return True
    except requests.exceptions.ConnectionError:
        _clear_backend_base_url("connection refused during ingest", backoff=True)
        log.warning("Connection refused - backend running and reachable on Wi-Fi?")
    except requests.exceptions.Timeout:
        _clear_backend_base_url("timeout during ingest", backoff=True)
        log.warning("Request timed out (2.5 s)")
    except requests.exceptions.HTTPError as exc:
        log.error("HTTP %s: %s", exc.response.status_code, exc.response.text[:120])
    except Exception as exc:
        log.error("Unexpected send error: %s", exc)
    return False


def stop_session_on_backend():
    stop_url = _get_endpoint_url("/api/v1/pi/session/stop")
    if not stop_url:
        log.warning("Could not stop session on backend: backend not discovered")
        return False

    try:
        resp = requests.post(stop_url, timeout=3.0)
        log.info("Session stopped -> %s", resp.json())
        return True
    except Exception as exc:
        _clear_backend_base_url(f"stop-session failed: {exc}", backoff=True)
        log.warning("Could not notify backend of stop: %s", exc)
        return False


IS_RECORDING     = False
last_sample_time = time.monotonic()

try:
    log.info("System ready - press button to start")
    verify_backend()

    while True:
        now = time.monotonic()

        if GPIO.input(BUTTON_PIN) == GPIO.HIGH:
            IS_RECORDING = not IS_RECORDING

            if IS_RECORDING:
                GPIO.output(LED_RED,   GPIO.LOW)
                GPIO.output(LED_GREEN, GPIO.HIGH)
                start_polling()
                last_sample_time = time.monotonic()
                log.info("Recording started - sending every %.1f sec", SAMPLE_INTERVAL)
            else:
                GPIO.output(LED_RED,   GPIO.HIGH)
                GPIO.output(LED_GREEN, GPIO.LOW)
                stop_polling()
                log.info("Recording stopped - closing session")
                stop_session_on_backend()

            time.sleep(0.5)
            last_sample_time = time.monotonic()

        if IS_RECORDING:
            elapsed = time.monotonic() - last_sample_time

            if elapsed >= SAMPLE_INTERVAL:
                last_sample_time = time.monotonic()

                pulses   = read_and_reset_pulses()
                flow_lpm = (pulses / elapsed) / FLOW_K_FACTOR
                flow_gpm = round(flow_lpm * LPM_TO_GPM, 4)

                p1, p2 = get_simulated_pressures(flow_lpm)
                image_b64 = capture_image_b64()

                log.info(
                    "[%s] elapsed=%.2fs | pulses=%d | flow=%.3f L/min (%.4f GPM)"
                    " | P1=%.4f PSI | P2=%.4f PSI | img=%s",
                    datetime.now().strftime("%H:%M:%S"),
                    elapsed, pulses, flow_lpm, flow_gpm, p1, p2,
                    "ok" if image_b64 else "no camera",
                )

                sample = {
                    "pressure1": p1,
                    "pressure2": p2,
                    "flow":      flow_gpm,
                    "image_b64": image_b64,
                    "timestamp": time.time(),
                }
                send_sample(sample)

        time.sleep(POLL_SLEEP)

except KeyboardInterrupt:
    log.info("Shutdown (Ctrl+C)")
    if IS_RECORDING:
        stop_polling()
        stop_session_on_backend()

finally:
    stop_polling()
    if picam2 is not None:
        picam2.stop()
    GPIO.cleanup()
    log.info("GPIO cleanup done")
