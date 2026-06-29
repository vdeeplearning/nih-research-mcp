"""Synthetic NIH-style clinical research MCP server.

The server is intentionally small: it loads local mock research data, then exposes
stable MCP tools that any compatible AI client can reuse.
"""

from __future__ import annotations

import csv
import json
import re
import statistics
import sys
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
    if len(sys.argv) > 1:
        args = sys.argv[1:]
        raw_json = "--json" in args
        prompt = " ".join(arg for arg in args if arg != "--json")
        run_local_demo(prompt, raw_json=raw_json)
        return

    if sys.stdin.isatty():
        print(
            "NIH Research MCP Server\n\n"
            "This is an MCP stdio server, so natural-language prompts should be\n"
            "sent from an MCP client such as Claude Desktop, Cursor, or Codex.\n\n"
            "For a quick local terminal demo, run one of these commands:\n\n"
            '  python server.py "Find patients over 65 with AAA diameter greater than 3 cm."\n'
            '  python server.py "Compute AAA prevalence in the synthetic cohort."\n'
            '  python server.py "Search the protocols for DICOM de-identification rules."\n\n'
            "Add --json to any local demo command to print raw tool output.\n\n"
            "When launched by an MCP client, this same file will run as the server."
        )
        return

    # FastMCP handles the MCP transport lifecycle; the functions above define
    # the reusable research capability layer exposed to compatible clients.
    mcp.run()


def run_local_demo(prompt: str, raw_json: bool = False) -> None:
    """Tiny terminal demo router for humans trying the project without an MCP client."""
    normalized = prompt.lower()

    if "prevalence" in normalized or "statistics" in normalized:
        mode = "statistics"
        result = compute_aaa_statistics()
    elif "protocol" in normalized or "de-identification" in normalized or "dicom" in normalized:
        mode = "protocols"
        result = search_protocols(prompt)
    elif "publication" in normalized or "paper" in normalized or "automated" in normalized:
        mode = "publications"
        result = search_publications(prompt)
    elif "patient" in normalized or "aaa" in normalized:
        mode = "patients"
        min_age = None
        age_match = re.search(r"(?:over|older than|age greater than)\s+(\d+)", normalized)
        if age_match:
            min_age = int(age_match.group(1)) + 1

        diameter = 3.0
        diameter_match = re.search(
            r"(greater than|over|at least)\s+(\d+(?:\.\d+)?)\s*cm", normalized
        )
        if diameter_match:
            diameter = float(diameter_match.group(2))
            if diameter_match.group(1) in {"greater than", "over"}:
                diameter += 0.001

        result = find_aaa_patients(min_diameter_cm=diameter, min_age=min_age)
    else:
        mode = "help"
        result = {
            "message": "Try asking about patients, AAA prevalence, publications, or protocols.",
            "example": "Find patients over 65 with AAA diameter greater than 3 cm.",
        }

    if raw_json:
        print(json.dumps(result, indent=2))
        return

    print(format_local_demo_result(mode, result))


def format_local_demo_result(mode: str, result: Any) -> str:
    """Render local demo output as a readable assistant-style response."""
    if mode == "patients":
        if not result:
            return "No matching synthetic patients were found."

        lines = [
            f"Found {len(result)} matching synthetic patients.",
            "",
            "Patient   Age Sex  AAA cm  CT metadata",
            "--------  --- ---  ------  ------------------------------",
        ]
        for patient in result[:10]:
            lines.append(
                f"{patient['patient_id']:<8}  {patient['age']:>3} {patient['sex']:<3}"
                f"  {patient['aaa_diameter_cm']:>6.1f}  "
                f"{patient['scanner_manufacturer']}, {patient['contrast_status']}"
            )
        if len(result) > 10:
            lines.append(f"...and {len(result) - 10} more. Add --json to view every field.")
        return "\n".join(lines)

    if mode == "statistics":
        return "\n".join(
            [
                "Synthetic AAA cohort statistics",
                f"- Cohort size: {result['cohort_size']}",
                f"- AAA-positive patients: {result['aaa_positive_patients']}",
                f"- Prevalence: {result['prevalence']:.1%}",
                f"- Mean AAA diameter: {result['mean_aaa_diameter_cm']} cm",
                f"- Median AAA diameter: {result['median_aaa_diameter_cm']} cm",
                "- By sex: "
                + ", ".join(
                    f"{sex}: {values['aaa_positive']}/{values['cohort_size']}"
                    f" positive ({values['prevalence']:.1%})"
                    for sex, values in result["summary_by_sex"].items()
                ),
            ]
        )

    if mode == "protocols":
        if not result:
            return "No matching protocol excerpts were found."
        lines = [f"Found {len(result)} matching protocol document(s)."]
        for match in result:
            lines.extend(["", f"{match['document']}", match["excerpt"]])
        return "\n".join(lines)

    if mode == "publications":
        if not result:
            return "No matching synthetic publications were found."
        lines = [f"Found {len(result)} matching synthetic publication(s)."]
        for publication in result:
            authors = ", ".join(publication["authors"])
            lines.extend(
                [
                    "",
                    f"{publication['title']} ({publication['year']})",
                    f"{authors}. {publication['journal']}.",
                    publication["short_abstract"],
                ]
            )
        return "\n".join(lines)

    return f"{result['message']}\nExample: {result['example']}"


if __name__ == "__main__":
    main()
