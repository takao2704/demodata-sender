import ctypes
import json
import logging
import os
import time

from demodata_sender import generate_payload, to_json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

LIBSORATUN_FILENAME = "libsoratun.so"
DEFAULT_ARC_CONFIG = "arc.json"


def _load_soratun():
    library_path = os.path.join(os.path.dirname(__file__), LIBSORATUN_FILENAME)
    soratun = ctypes.cdll.LoadLibrary(library_path)
    soratun.Send.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
    ]
    soratun.Send.restype = ctypes.c_char_p
    return soratun


def _load_arc_config() -> ctypes.c_char_p:
    config_path = os.getenv("ARC_CONFIG_PATH")
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), DEFAULT_ARC_CONFIG)
    with open(config_path, "r", encoding="utf-8") as file:
        return ctypes.c_char_p(file.read().encode("utf-8"))


def _send_with_retry(
    soratun, config: ctypes.c_char_p, payload_json: str, max_attempts: int = 3
) -> str:
    method = ctypes.c_char_p(b"POST")
    path = ctypes.c_char_p(b"/")
    body = ctypes.c_char_p(payload_json.encode("utf-8"))
    backoffs = [0.5, 1.0, 2.0]

    for attempt in range(1, max_attempts + 1):
        response_ptr = soratun.Send(config, method, path, body)
        if response_ptr is not None:
            return response_ptr.decode("utf-8")
        if attempt < max_attempts:
            sleep_for = backoffs[attempt - 1] + (0.1 * attempt)
            logger.warning("Send failed, retrying in %.2fs", sleep_for)
            time.sleep(sleep_for)
    raise RuntimeError("Failed to send payload via libsoratun after retries")


def lambda_handler(event, context):
    soratun = _load_soratun()
    config = _load_arc_config()
    payload = generate_payload()
    payload_json = to_json(payload)

    response_body = _send_with_retry(soratun, config, payload_json)
    logger.info("Sent payload: %s", json.dumps(payload, ensure_ascii=False))
    logger.info("Unified Endpoint response: %s", response_body)

    return {
        "statusCode": 200,
        "body": "Successfully sent to the unified endpoint",
    }
