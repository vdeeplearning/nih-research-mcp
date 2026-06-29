# DICOM De-identification Protocol

## Purpose

This synthetic protocol summarizes DICOM de-identification rules for the NIH Research MCP demo. It is written for mock infrastructure testing and does not contain real patient data.

## Required removals

Remove direct identifiers from DICOM headers before research use. Required removals include patient name, medical record number, accession number, birth date, street address, telephone number, email address, device serial number when site policy requires it, and free-text fields that may contain identifiers.

## Date handling

Replace exact dates with shifted or generalized dates according to the approved research policy. In this demo, scan dates are already synthetic and are safe for examples. Real workflows should preserve temporal relationships only when allowed by the protocol and institutional review.

## UID handling

Replace study, series, and SOP instance UIDs with deterministic research UIDs when longitudinal linkage is required. Store the linkage key in a controlled system outside the assistant-facing dataset.

## Burned-in annotations

Review pixel data for burned-in annotations before release. If annotations may contain identifiers, either remove the annotations or exclude the image from the research dataset.

## Quality assurance

Run automated header checks and manual spot checks before sharing imaging data. The de-identification report should list fields removed, fields retained, date strategy, UID strategy, and reviewer sign-off.
