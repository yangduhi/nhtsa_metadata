from __future__ import annotations

from typing import Any


def generated_instrumentation_rows(
    test_no: int, count: int, start_curve_no: int = 1
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(count):
        curve_no = start_curve_no + index
        rows.append(
            {
                "testNo": test_no,
                "curveNo": curve_no,
                "sensorType": "ACCELEROMETER",
                "sensorLocation": f"LOCATION {curve_no}",
                "sensorAttachment": "VEHICLE",
                "axisDirofSensor": "X",
                "unit": "G",
                "firstPoint": 1,
                "lastPoint": 1000,
                "timeIncrement": 0.0001,
                "channelStatus": "OK",
                "dataStatus": "AVAILABLE",
            }
        )
    return rows
