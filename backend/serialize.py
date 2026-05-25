"""Convert FastF1 / pandas objects to JSON-safe structures."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, (pd.Timedelta, np.timedelta64)):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def dataframe_preview(df: pd.DataFrame, max_rows: int = 25) -> dict[str, Any]:
    columns = [
        {"name": name, "dtype": str(df[name].dtype)}
        for name in df.columns
    ]
    preview_rows = []
    for _, row in df.head(max_rows).iterrows():
        preview_rows.append(
            {name: serialize_value(row[name]) for name in df.columns}
        )
    return {
        "columns": columns,
        "rowCount": int(len(df)),
        "previewRows": preview_rows,
    }
