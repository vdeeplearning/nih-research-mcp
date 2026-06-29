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

## Tools exposed by the server

- `search_publications(query: str)` searches synthetic publications by title and abstract keywords.
- `get_patient_metadata(patient_id: str)` returns synthetic demographics and CT metadata for one patient/study.
- `find_aaa_patients(min_diameter_cm: float = 3.0, min_age: int | None = None)` returns patients matching AAA diameter and optional age filters.
- `compute_aaa_statistics()` returns cohort-level AAA summary statistics.
- `search_protocols(query: str)` searches protocol markdown files and returns relevant excerpts.

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
