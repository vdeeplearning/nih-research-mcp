"""Synthetic NIH-style clinical research MCP server.

The server is intentionally small: it loads local mock research data, then exposes
stable MCP tools that any compatible AI client can reuse.
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - exercised only when dependency is missing.
    FastMCP = None


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROTOCOL_DIR = DATA_DIR / "protocols"

class MissingMCP:
    """Small fallback so data functions remain importable before SDK install."""

    def tool(self):
        def decorator(func):
            return func

        return decorator

    def run(self) -> None:
        raise SystemExit(
            "The Python MCP SDK is required. Install this project with:\n\n"
            "  pip install -e .\n\n"
            "Then run:\n\n"
            "  python server.py"
        )


mcp = FastMCP("nih-research-mcp") if FastMCP else MissingMCP()


def load_patients() -> list[dict[str, Any]]:
    """Load the synthetic cohort table and convert numeric fields."""
    with (DATA_DIR / "patients.csv").open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    for row in rows:
        row["age"] = int(row["age"])
        row["aaa_diameter_cm"] = float(row["aaa_diameter_cm"])
    return rows


def load_imaging_metadata() -> dict[str, dict[str, Any]]:
    with (DATA_DIR / "imaging_metadata.json").open(encoding="utf-8") as file:
        metadata = json.load(file)
    return {item["patient_id"]: item for item in metadata}


def load_publications() -> list[dict[str, Any]]:
    with (DATA_DIR / "publications.json").open(encoding="utf-8") as file:
        return json.load(file)


def short_abstract(text: str, max_chars: int = 220) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def excerpt_around_match(text: str, query: str, window: int = 280) -> str:
    """Return a compact excerpt around the first matching query term."""
    lowered = text.lower()
    terms = [term for term in query.lower().split() if term]
    positions = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
    if not positions:
        return short_abstract(" ".join(text.split()), window)

    position = min(positions)
    start = max(0, position - window // 2)
    end = min(len(text), position + window // 2)
    excerpt = " ".join(text[start:end].split())
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{excerpt}{suffix}"


def patient_summary(row: dict[str, Any], imaging: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compose the patient and CT fields most useful to an assistant."""
    result = {
        "patient_id": row["patient_id"],
        "age": row["age"],
        "sex": row["sex"],
        "aaa_diameter_cm": row["aaa_diameter_cm"],
        "aaa_positive": row["aaa_positive"].lower() == "true",
    }
    if imaging:
        result.update(
            {
                "scan_date": imaging["scan_date"],
                "scanner_manufacturer": imaging["scanner_manufacturer"],
                "slice_thickness_mm": imaging["slice_thickness_mm"],
                "contrast_status": imaging["contrast_status"],
            }
        )
    return result


@mcp.tool()
def search_publications(query: str) -> list[dict[str, Any]]:
    """Search synthetic publications by title and abstract keywords."""
    query_terms = [term for term in query.lower().split() if term]
    publications = load_publications()
    scored_matches = []

    for publication in publications:
        haystack = f"{publication['title']} {publication['abstract']}".lower()
        score = sum(1 for term in query_terms if term in haystack)
        if score:
            scored_matches.append(
                {
                    "score": score,
                    "title": publication["title"],
                    "authors": publication["authors"],
                    "year": publication["year"],
                    "journal": publication["journal"],
                    "short_abstract": short_abstract(publication["abstract"]),
                }
            )

    scored_matches.sort(key=lambda item: (-item.pop("score"), -item["year"], item["title"]))
    return scored_matches


@mcp.tool()
def get_patient_metadata(patient_id: str) -> dict[str, Any]:
    """Return synthetic demographics and CT metadata for one patient/study."""
    patient_id = patient_id.strip().upper()
    patients = load_patients()
    imaging_by_patient = load_imaging_metadata()

    for patient in patients:
        if patient["patient_id"].upper() == patient_id:
            return patient_summary(patient, imaging_by_patient.get(patient["patient_id"]))

    return {"error": f"No synthetic patient found for patient_id '{patient_id}'."}


@mcp.tool()
def find_aaa_patients(
    min_diameter_cm: float = 3.0, min_age: int | None = None
) -> list[dict[str, Any]]:
    """Find patients meeting an AAA diameter threshold and optional age filter."""
    patients = load_patients()
    imaging_by_patient = load_imaging_metadata()
    matches = []

    for patient in patients:
        if patient["aaa_diameter_cm"] < min_diameter_cm:
            continue
        if min_age is not None and patient["age"] < min_age:
            continue
        matches.append(patient_summary(patient, imaging_by_patient.get(patient["patient_id"])))

    return matches


@mcp.tool()
def compute_aaa_statistics() -> dict[str, Any]:
    """Compute simple descriptive statistics for the synthetic AAA cohort."""
    patients = load_patients()
    diameters = [patient["aaa_diameter_cm"] for patient in patients]
    aaa_positive = [
        patient for patient in patients if patient["aaa_positive"].lower() == "true"
    ]

    by_sex: dict[str, dict[str, Any]] = {}
    for sex in sorted({patient["sex"] for patient in patients}):
        group = [patient for patient in patients if patient["sex"] == sex]
        positive = [patient for patient in group if patient["aaa_positive"].lower() == "true"]
        by_sex[sex] = {
            "cohort_size": len(group),
            "aaa_positive": len(positive),
            "prevalence": round(len(positive) / len(group), 3),
            "mean_aaa_diameter_cm": round(
                statistics.mean(patient["aaa_diameter_cm"] for patient in group), 2
            ),
        }

    return {
        "cohort_size": len(patients),
        "aaa_positive_patients": len(aaa_positive),
        "prevalence": round(len(aaa_positive) / len(patients), 3),
        "mean_aaa_diameter_cm": round(statistics.mean(diameters), 2),
        "median_aaa_diameter_cm": round(statistics.median(diameters), 2),
        "summary_by_sex": by_sex,
    }


@mcp.tool()
def search_protocols(query: str) -> list[dict[str, str]]:
    """Search markdown research protocol files and return relevant excerpts."""
    matches = []

    for path in sorted(PROTOCOL_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        terms = [term for term in query.lower().split() if term]
        if all(term in lowered for term in terms):
            matches.append(
                {
                    "document": path.name,
                    "excerpt": excerpt_around_match(text, query),
                }
            )

    return matches


def main() -> None:
    # FastMCP handles the MCP transport lifecycle; the functions above define
    # the reusable research capability layer exposed to compatible clients.
    mcp.run()


if __name__ == "__main__":
    main()
