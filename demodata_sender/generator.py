from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, Optional

from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


@dataclass(frozen=True)
class LineConfig:
    line_id: str
    line_name: str
    cycle_time_range_ms: tuple[int, int]
    ng_rate: float
    temp_range_c: tuple[float, float]
    power_range_w: tuple[int, int]
    vibration_range: tuple[float, float]


LINE_CONFIGS = {
    "L1": LineConfig(
        line_id="L1",
        line_name="部品製造",
        cycle_time_range_ms=(2500, 3500),
        ng_rate=0.003,
        temp_range_c=(35.0, 45.0),
        power_range_w=(700, 1200),
        vibration_range=(0.05, 0.25),
    ),
    "L2": LineConfig(
        line_id="L2",
        line_name="組立",
        cycle_time_range_ms=(4500, 6500),
        ng_rate=0.008,
        temp_range_c=(30.0, 40.0),
        power_range_w=(500, 900),
        vibration_range=(0.05, 0.25),
    ),
    "L3": LineConfig(
        line_id="L3",
        line_name="検査",
        cycle_time_range_ms=(6000, 9000),
        ng_rate=0.012,
        temp_range_c=(28.0, 38.0),
        power_range_w=(300, 600),
        vibration_range=(0.05, 0.25),
    ),
}

MACHINE_IDS = [f"M0{index}" for index in range(1, 7)]
MATERIAL_REFILL_TARGETS = {"M02", "M03"}

ALARM_CODES = ["Q001", "Q002", "M001", "T001", "V001"]
ALARM_SEVERITY_WEIGHTS = [(1, 0.6), (2, 0.3), (3, 0.1)]

INTERVAL_WEIGHTS = [
    (60, 0.70),
    (30, 0.10),
    (120, 0.10),
    (10, 0.05),
    (300, 0.04),
    (600, 0.01),
]


def now_jst() -> datetime:
    return datetime.now(timezone.utc).astimezone(JST)


def select_interval_sec(rng: random.Random) -> int:
    roll = rng.random()
    cumulative = 0.0
    for interval, weight in INTERVAL_WEIGHTS:
        cumulative += weight
        if roll <= cumulative:
            return interval
    return INTERVAL_WEIGHTS[-1][0]


def seed_from_string(seed: str) -> int:
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % (2**32)


def jst_time_in_range(target: datetime, start: time, end: time) -> bool:
    target_time = target.timetz()
    if start <= end:
        return start <= target_time < end
    return target_time >= start or target_time < end


def is_lunch_break(current: datetime) -> bool:
    return jst_time_in_range(current, time(12, 0), time(12, 15))


def is_off_shift(current: datetime) -> bool:
    return jst_time_in_range(current, time(18, 0), time(9, 0))


def is_startup(current: datetime) -> bool:
    return jst_time_in_range(current, time(9, 0), time(9, 30))


def is_normal_morning(current: datetime) -> bool:
    return jst_time_in_range(current, time(9, 30), time(12, 0))


def is_late_morning(current: datetime) -> bool:
    return jst_time_in_range(current, time(12, 15), time(13, 0))


def is_afternoon(current: datetime) -> bool:
    return jst_time_in_range(current, time(13, 0), time(15, 30))


def is_material_refill_window(current: datetime, machine_id: str) -> bool:
    if machine_id not in MATERIAL_REFILL_TARGETS:
        return False
    base_date = current.date()
    seed = seed_from_string(f"{base_date.isoformat()}-{machine_id}-refill")
    rng = random.Random(seed)
    start_offset_min = rng.randint(0, 2)
    duration_min = rng.randint(3, 7)
    start_time = datetime.combine(base_date, time(15, 30), tzinfo=JST) + timedelta(
        minutes=start_offset_min
    )
    end_time = start_time + timedelta(minutes=duration_min)
    return start_time <= current < end_time


def choose_alarm(rng: random.Random, interval_sec: int) -> Optional[Dict[str, Any]]:
    per_second_rate = 0.2 / 86400
    probability = per_second_rate * interval_sec
    if rng.random() >= probability:
        return None
    alarm_code = rng.choice(ALARM_CODES)
    severity = weighted_choice(rng, ALARM_SEVERITY_WEIGHTS)
    duration_sec = rng.randint(30, 120)
    return {
        "alarmCode": alarm_code,
        "severity": severity,
        "durationSec": duration_sec,
    }


def weighted_choice(rng: random.Random, options: list[tuple[Any, float]]) -> Any:
    roll = rng.random()
    cumulative = 0.0
    for value, weight in options:
        cumulative += weight
        if roll <= cumulative:
            return value
    return options[-1][0]


def select_status(
    rng: random.Random, current: datetime, machine_id: str
) -> tuple[str, str]:
    if is_lunch_break(current):
        return "IDLE", "lunch_break"
    if is_off_shift(current):
        if rng.random() < 0.1:
            return "RUN", "normal_run"
        return "IDLE", "off_shift"
    if is_material_refill_window(current, machine_id):
        return "STOP", "material_refill"
    if is_startup(current):
        return weighted_status(
            rng,
            [
                ("RUN", 0.6),
                ("IDLE", 0.2),
                ("STOP", 0.1),
                ("CHANGEOVER", 0.05),
                ("MAINT", 0.05),
            ],
        )
    if is_normal_morning(current) or is_afternoon(current):
        return weighted_status(
            rng,
            [
                ("RUN", 0.85),
                ("IDLE", 0.05),
                ("STOP", 0.05),
                ("CHANGEOVER", 0.03),
                ("MAINT", 0.02),
            ],
        )
    if is_late_morning(current):
        return weighted_status(
            rng,
            [
                ("RUN", 0.7),
                ("IDLE", 0.2),
                ("STOP", 0.05),
                ("CHANGEOVER", 0.03),
                ("MAINT", 0.02),
            ],
        )
    return weighted_status(
        rng,
        [
            ("RUN", 0.8),
            ("IDLE", 0.1),
            ("STOP", 0.05),
            ("CHANGEOVER", 0.03),
            ("MAINT", 0.02),
        ],
    )


def weighted_status(
    rng: random.Random, options: list[tuple[str, float]]
) -> tuple[str, str]:
    status = weighted_choice(rng, options)
    reason = {
        "RUN": "normal_run",
        "IDLE": "end_of_shift",
        "STOP": "material_wait",
        "CHANGEOVER": "changeover",
        "MAINT": "planned_maintenance",
    }[status]
    return status, reason


def compute_cycle_time_ms(
    rng: random.Random, line: LineConfig, current: datetime
) -> int:
    min_ms, max_ms = line.cycle_time_range_ms
    if is_startup(current):
        range_padding = int((max_ms - min_ms) * 0.3)
        min_ms = max(500, min_ms - range_padding)
        max_ms = max_ms + range_padding
    return rng.randint(min_ms, max_ms)


def generate_counts(
    rng: random.Random,
    interval_sec: int,
    cycle_time_ms: int,
    ng_rate: float,
) -> tuple[int, int]:
    expected_cycles = interval_sec * 1000 / cycle_time_ms
    sample_cycles = max(0, int(rng.normalvariate(expected_cycles, expected_cycles * 0.05)))
    ng_count = sum(1 for _ in range(sample_cycles) if rng.random() < ng_rate)
    good_count = max(sample_cycles - ng_count, 0)
    return good_count, ng_count


def generate_sensors(
    rng: random.Random,
    line: LineConfig,
    status: str,
    alarm: Optional[Dict[str, Any]],
) -> Dict[str, float]:
    temp_min, temp_max = line.temp_range_c
    power_min, power_max = line.power_range_w
    vib_min, vib_max = line.vibration_range

    if status == "RUN":
        temperature = rng.uniform(temp_min, temp_max)
        power = rng.uniform(power_min, power_max)
        vibration = rng.uniform(vib_min, vib_max)
    else:
        ambient = 25.0
        temperature = rng.uniform(ambient, temp_min)
        power = rng.uniform(power_min * 0.2, power_max * 0.4)
        vibration = rng.uniform(0.0, 0.03)

    if alarm:
        alarm_code = alarm["alarmCode"]
        if alarm_code == "T001":
            temperature = rng.uniform(temp_max + 5, temp_max + 10)
        elif alarm_code == "V001":
            vibration = rng.uniform(0.3, 0.6)
        elif alarm_code == "M001":
            power = rng.uniform(power_max * 1.3, power_max * 1.8)

    return {
        "temperatureC": round(temperature, 2),
        "powerW": round(power, 1),
        "vibration": round(vibration, 3),
    }


def generate_machine_payload(
    rng: random.Random,
    current: datetime,
    interval_sec: int,
    line: LineConfig,
    machine_id: str,
) -> Dict[str, Any]:
    status, reason = select_status(rng, current, machine_id)
    alarm = None
    if status != "IDLE":
        alarm = choose_alarm(rng, interval_sec)
    if alarm:
        status = "ALARM"
        reason_map = {
            "Q001": "quality_issue",
            "Q002": "quality_issue",
            "M001": "machine_fault",
            "T001": "over_temp",
            "V001": "high_vibration",
        }
        reason = reason_map[alarm["alarmCode"]]

    run_time = idle_time = stop_time = 0
    if status == "RUN":
        run_time = interval_sec
    elif status == "IDLE":
        idle_time = interval_sec
    else:
        stop_time = interval_sec

    cycle_time_ms = None
    good_count = 0
    ng_count = 0
    if status == "RUN":
        cycle_time_ms = compute_cycle_time_ms(rng, line, current)
        ng_rate = line.ng_rate
        if is_startup(current):
            ng_rate *= 2
        if alarm and alarm["alarmCode"] in {"Q001", "Q002"}:
            ng_rate *= rng.uniform(1.5, 3.0)
        good_count, ng_count = generate_counts(rng, interval_sec, cycle_time_ms, ng_rate)

    sensors = generate_sensors(rng, line, status, alarm)

    payload: Dict[str, Any] = {
        "machineId": f"{line.line_id}-{machine_id}",
        "status": status,
        "reason": reason,
        "goodCountDelta": good_count,
        "ngCountDelta": ng_count,
        "runTimeSecDelta": run_time,
        "idleTimeSecDelta": idle_time,
        "stopTimeSecDelta": stop_time,
        "cycleTimeMs": cycle_time_ms,
        "sensors": sensors,
    }

    if alarm:
        payload["alarm"] = {
            "alarmCode": alarm["alarmCode"],
            "severity": alarm["severity"],
        }

    return payload


def generate_payload(
    current: Optional[datetime] = None, rng: Optional[random.Random] = None
) -> Dict[str, Any]:
    if rng is None:
        rng = random.Random()
    if current is None:
        current = now_jst()
    interval_sec = select_interval_sec(rng)

    lines_payload = []
    for line in LINE_CONFIGS.values():
        machines_payload = [
            generate_machine_payload(rng, current, interval_sec, line, machine_id)
            for machine_id in MACHINE_IDS
        ]
        lines_payload.append(
            {
                "lineId": line.line_id,
                "lineName": line.line_name,
                "machines": machines_payload,
            }
        )

    return {
        "schemaVersion": "1.0",
        "factoryId": "F001",
        "ts": current.isoformat(),
        "intervalSec": interval_sec,
        "lines": lines_payload,
    }


def to_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)
