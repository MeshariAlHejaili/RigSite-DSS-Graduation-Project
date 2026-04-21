import base64
import io
import logging
import threading
import time
from datetime import datetime

import RPi.GPIO as GPIO
import requests
from PIL import Image

LAPTOP_IP   = "172.20.10.4"
LAPTOP_PORT = 18000

INGEST_URL = f"http://{LAPTOP_IP}:{LAPTOP_PORT}/api/v1/pi/ingest"
STOP_URL   = f"http://{LAPTOP_IP}:{LAPTOP_PORT}/api/v1/pi/session/stop"
STATUS_URL = f"http://{LAPTOP_IP}:{LAPTOP_PORT}/api/v1/pi/status"

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
    try:
        resp = requests.get(STATUS_URL, timeout=3.0)
        data = resp.json()
        log.info("Backend online -> calibrated=%s  pi_session_active=%s",
                 data.get("angle_calibrated"), data.get("pi_session_active"))
        return True
    except Exception as exc:
        log.warning("Backend not reachable at %s -> %s", LAPTOP_IP, exc)
        return False


def send_sample(payload):
    try:
        resp = requests.post(INGEST_URL, json=payload, timeout=2.5)
        resp.raise_for_status()
        result = resp.json()
        state = result.get("state", "?")
        angle = result.get("gate_angle")
        mw    = result.get("mud_weight")
        log.info("-> state=%-11s  angle=%s  MW=%s",
                 state,
                 f"{angle:.1f} deg" if angle is not None else "N/A",
                 f"{mw:.3f} PPG"    if mw    is not None else "N/A")
    except requests.exceptions.ConnectionError:
        log.warning("Connection refused - backend running? (%s)", LAPTOP_IP)
    except requests.exceptions.Timeout:
        log.warning("Request timed out (2.5 s)")
    except requests.exceptions.HTTPError as exc:
        log.error("HTTP %s: %s", exc.response.status_code, exc.response.text[:120])
    except Exception as exc:
        log.error("Unexpected send error: %s", exc)


def stop_session_on_backend():
    try:
        resp = requests.post(STOP_URL, timeout=3.0)
        log.info("Session stopped -> %s", resp.json())
    except Exception as exc:
        log.warning("Could not notify backend of stop: %s", exc)


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
