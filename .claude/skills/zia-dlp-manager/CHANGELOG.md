# Changelog

All notable changes to the **Zscaler ZIA DLP Manager** skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Cross-tenant ID remapping (engines, dictionaries, templates, locations, groups)
- `--dry-run` CLI flag for all write operations
- Parallel rule creation with configurable concurrency
- Diff view before update / delete operations
- Support for ZPA segment policy DLP (where applicable)
- Web UI wrapper (FastAPI + minimal HTML)

---

## [1.0.0] - 2026-05-25

### Added
- **Export** (`scripts/zia_dlp_export.py`)
  - Exports DLP Web Rules, DLP Engines, DLP Dictionaries, Notification Templates, ICAP Servers, and IDM Profiles
  - Output formats: CSV, JSON, or both (controlled by `EXPORT_FORMAT`)
  - Pagination handling for large tenants
  - Read-only — no tenant mutations
- **Import** (`scripts/zia_dlp_import.py`)
  - Creates DLP Web Rules from a JSON source file
  - Modes: single by name, multiple by comma-separated names, slab (50/100/ALL) from a starting index
  - Optional `IMPORT_NAME_SUFFIX` env var to avoid duplicate-name collisions
  - Field sanitization — strips read-only fields (`id`, `lastModifiedTime`, `lastModifiedBy`, `accessControl`)
  - Audit CSV: `zia_dlp_import_audit_<timestamp>.csv`
  - Typed `IMPORT` confirmation required before any write
- **Update** (`scripts/zia_dlp_update.py`)
  - Updates existing DLP rules with field-level allow-listing
  - Modes: single, multiple, slab (5/10/50/100) from a starting `order` value
  - Idempotent merge — preserves existing fields not present in source JSON
  - Reference normalization to `{"id": N}` form for all list and object references
  - Audit CSV: `zia_dlp_update_audit_<timestamp>.csv`
  - Typed `UPDATE` confirmation required
- **Delete** (`scripts/zia_dlp_delete.py`)
  - Deletes DLP rules safely with double confirmation
  - Modes: single, multiple, slab (5/10/50/100)
  - Audit CSV: `zia_dlp_delete_audit_<timestamp>.csv`
  - Typed `DELETE` confirmation plus rule-name echo required
- **Authentication**
  - Zidentity OAuth2 `client_credentials` grant
  - Auto-retry on 401 with token refresh
  - Session-based HTTP with persistent headers
- **Activation**
  - Optional post-write activation prompt (`POST /zia/api/v1/status/activate`)
- **Skill packaging**
  - `SKILL.md` manifest with YAML frontmatter for MCP-compatible agents
  - `mcp.json` for marketplace listings
  - `README.md` with full usage docs and architecture diagram
  - Walkthrough examples in `examples/` (export, import, update, delete)
  - `.env.example` template for credentials
  - `requirements.txt` with pinned dependencies
  - MIT License

### Security
- All credentials read from environment variables (never hardcoded)
- `.gitignore` excludes `.env`, audit CSVs, and exported policy files
- Least-privilege network scope declared in `mcp.json` (`*.zsapi.net`, `*.zslogin.net`)
- Typed-token confirmation prevents accidental destructive operations
- Audit log written for every write run (created, updated, or deleted entries with errors)

### Documentation
- Architecture diagram in `README.md`
- Per-operation walkthroughs in `examples/`
- Frontmatter-validated `SKIL

