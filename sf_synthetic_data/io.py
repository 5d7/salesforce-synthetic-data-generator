"""Output and optional Groq enrichment helpers."""

from __future__ import annotations

import csv
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable


def groq_enrich(
    records: list[dict[str, Any]],
    fields: list[str],
    object_name: str,
    model: str,
    limit: int,
    api_key_env: str,
) -> None:
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise ValueError(f"set {api_key_env} before using --groq-fields")
    if limit < 1:
        raise ValueError("groq-limit must be at least 1")
    count = min(limit, len(records))
    for start in range(0, count, 20):
        batch = records[start : min(count, start + 20)]
        context_rows = [
            {"row": start + index, **{key: value for key, value in row.items() if key in {"Name", "StageName", "Industry", "Sales_Region__c", "Sales_District__c"}}}
            for index, row in enumerate(batch)
        ]
        prompt = (
            f"Create realistic but fictional values for these synthetic Salesforce {object_name} records. "
            f"Return JSON only as {{\"records\":[{{\"row\": integer, {', '.join(repr(field) + ': string' for field in fields)}}}]}}. "
            "Do not use real people or companies. Keep each value under 160 characters. Rows: " + json.dumps(context_rows)
        )
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": "You generate fictional CRM test data and return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.8,
        }).encode("utf-8")
        request = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
            result = json.loads(body["choices"][0]["message"]["content"])
            for item in result.get("records", []):
                row_index = int(item["row"])
                if start <= row_index < start + len(batch):
                    for field in fields:
                        if field in records[row_index] and field in item:
                            records[row_index][field] = item[field]
        except (urllib.error.URLError, KeyError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Groq enrichment failed near row {start + 1}: {exc}") from exc


def write_records(records: Iterable[dict[str, Any]], columns: list[str], path: Path, output_format: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        if output_format == "csv":
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for record in records:
                writer.writerow(record)
                count += 1
        elif output_format == "jsonl":
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
        else:
            raise ValueError(f"unsupported output format: {output_format}")
    return count
