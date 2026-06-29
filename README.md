# NIH Research MCP Demo

This is a small, synthetic Model Context Protocol (MCP) server for NIH-style clinical research workflows. It exposes reusable biomedical research tools over MCP so an LLM assistant can search publications, inspect cohort metadata, query AAA measurements, compute summary statistics, and retrieve protocol guidance.

All data in this repository is synthetic/mock data. It does not contain PHI.

## What MCP is in this project

MCP is the interface layer between an AI assistant and external research capabilities. In this demo, the MCP server wraps a synthetic patient cohort, CT imaging metadata, publications, and protocol documents behind a small set of typed tools.

Instead of every assistant needing custom code to read CSV files, JSON metadata, and markdown protocols, the tools are implemented once in `server.py` and exposed through MCP.

```text
Claude / MCP Client
        |
        v
NIH Research MCP Server
        |
        v
Synthetic patient cohort, CT metadata, publications, protocols
```

## Why MCP is useful for NIH-style biomedical research

Biomedical research systems often span cohort tables, imaging metadata, literature collections, SOPs, and analysis utilities. MCP provides a clean abstraction layer over those resources. A research team can expose validated tools and data access patterns once, then allow multiple AI assistants or applications to reuse them consistently.

That makes it easier to:

- Reuse the same research infrastructure across AI clients.
- Keep data access logic centralized and auditable.
- Separate assistant behavior from biomedical data plumbing.
- Provide domain-specific tools without embedding data handling code into every chat application.

## Tool reference

The server exposes five MCP tools. In a real LLM application, the user asks a natural-language question, the MCP client chooses one of these tools, and the server returns structured data for the assistant to summarize.

### `search_publications(query: str)`

Searches `data/publications.json`, a synthetic collection of NIH-style research publication records.

Arguments:

- `query`: Keyword query used to search publication titles and abstracts. Example: `"automated AAA detection"`.

Returns:

- A list of matching publications.
- Each result includes `title`, `authors`, `year`, `journal`, and `short_abstract`.

Example use:

```text
Find publications about automated AAA detection.
```

Why it matters:

This simulates an assistant searching a curated biomedical literature index or internal research knowledge base through a reusable MCP tool instead of custom application code.

### `get_patient_metadata(patient_id: str)`

Returns demographics and CT imaging metadata for one synthetic patient/study.

Arguments:

- `patient_id`: Synthetic patient identifier. Example: `"SYN-017"`.

Returns:

- `patient_id`
- `age`
- `sex`
- `aaa_diameter_cm`
- `aaa_positive`
- `scan_date`
- `scanner_manufacturer`
- `slice_thickness_mm`
- `contrast_status`

Example use:

```text
Return metadata for patient SYN-017.
```

Why it matters:

This simulates an assistant retrieving approved study-level metadata from a clinical research cohort or imaging archive. The demo uses synthetic local files, but the same MCP tool shape could sit in front of a secure database or imaging metadata service.

### `find_aaa_patients(min_diameter_cm: float = 3.0, min_age: int | None = None)`

Finds synthetic patients whose abdominal aortic aneurysm diameter meets a threshold, with an optional age filter.

Arguments:

- `min_diameter_cm`: Minimum AAA diameter in centimeters. Default is `3.0`, the demo threshold for AAA-positive status.
- `min_age`: Optional minimum age filter. Use `null` or omit it when no age filter is needed.

Returns:

- A list of matching synthetic patients.
- Each result includes demographics, AAA diameter, AAA-positive status, scan date, scanner manufacturer, slice thickness, and contrast status.

Example use:

```text
Find patients over 65 with AAA diameter greater than 3 cm.
```

An MCP client might translate that prompt into a structured tool call similar to:

```json
{
  "tool": "find_aaa_patients",
  "arguments": {
    "min_diameter_cm": 3.0,
    "min_age": 66
  }
}
```

Why it matters:

This simulates cohort discovery: an LLM assistant can ask a controlled backend tool for patients matching research criteria rather than directly reading or reasoning over raw clinical tables.

### `compute_aaa_statistics()`

Computes descriptive statistics for the full synthetic AAA cohort.

Arguments:

- None.

Returns:

- `cohort_size`
- `aaa_positive_patients`
- `prevalence`
- `mean_aaa_diameter_cm`
- `median_aaa_diameter_cm`
- `summary_by_sex`, including cohort size, AAA-positive count, prevalence, and mean AAA diameter for each sex group.

Example use:

```text
Compute AAA prevalence in the synthetic cohort.
```

Why it matters:

This simulates a reusable analysis function exposed through MCP. Instead of each assistant implementing its own statistics logic, the validated computation lives once in the server.

### `search_protocols(query: str)`

Searches markdown research protocol documents in `data/protocols`.

Arguments:

- `query`: Keyword query used to search protocol text. Example: `"DICOM de-identification rules"`.

Returns:

- A list of matching protocol documents.
- Each result includes `document` and a relevant `excerpt`.

Example use:

```text
Search the protocols for DICOM de-identification rules.
```

Why it matters:

This simulates an assistant retrieving controlled research SOPs, measurement rules, or data governance procedures through MCP. In a real NIH-style environment, the protocol files could be replaced by an approved document repository.

## Install and run

Use Python 3.10 or newer.

```bash
pip install -e .
python server.py
```

When you run `python server.py` directly in a terminal, it prints local demo
instructions. When an MCP client launches the same file with stdio pipes, it
runs as the MCP server.

You can try the data tools from PowerShell without configuring an MCP client:

```powershell
python server.py "Find patients over 65 with AAA diameter greater than 3 cm."
python server.py "Search the protocols for DICOM de-identification rules."
python server.py "Compute AAA prevalence in the synthetic cohort."
python server.py "Find publications about automated AAA detection."
```

The local demo prints a concise human-readable summary. Add `--json` to any
demo command to inspect the raw tool output.

The project uses the official Python MCP SDK package, declared in `pyproject.toml` as `mcp`. The server follows the common `FastMCP` pattern:

```python
from mcp.server.fastmcp import FastMCP
```

## Example prompts

- "Find patients over 65 with AAA diameter greater than 3 cm."
- "Search the protocols for DICOM de-identification rules."
- "Compute AAA prevalence in the synthetic cohort."
- "Find publications about automated AAA detection."

More examples are available in [examples/example_queries.md](examples/example_queries.md).

## Project structure

```text
nih-research-mcp/
  README.md
  pyproject.toml
  server.py
  data/
    patients.csv
    imaging_metadata.json
    publications.json
    protocols/
      aaa_screening.md
      dicom_deidentification.md
  examples/
    example_queries.md
```

## Why this matters

Traditional LLM applications often require custom integration code for every data source or tool. This project demonstrates how biomedical research capabilities can be exposed once through MCP, allowing multiple AI applications to reuse the same tools and data access patterns.
