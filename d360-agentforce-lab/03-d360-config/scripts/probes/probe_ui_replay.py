#!/usr/bin/env python3
"""Replay a captured JSON payload from docs or disk against a chosen endpoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPT_DIR.parent


def find_repo_root(start: Path) -> Path:
    """Find the repo root by locating the shared handoff doc."""
    for candidate in (start, *start.parents):
        if (candidate / "docs" / "HANDOFF.md").exists():
            return candidate
    raise RuntimeError("Could not locate repo root containing docs/HANDOFF.md.")


REPO_ROOT = find_repo_root(SCRIPT_DIR)
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))
for site_packages in (REPO_ROOT / ".venv" / "lib").glob("python*/site-packages"):
    if str(site_packages) not in sys.path:
        sys.path.insert(0, str(site_packages))

from _common import (
    SF_ORG_ALIAS,
    connect,
    list_markdown_replay_examples,
    load_markdown_replay_example,
    request_exception_summary,
    resolve_request_url,
    response_summary,
    write_evidence,
)

DEFAULT_DOCS_PATH = (
    REPO_ROOT / "d360-agentforce-lab" / "03-d360-config" / "docs" / "internal-endpoints.md"
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the replay scaffold."""
    parser = argparse.ArgumentParser(
        description=(
            "Replay a JSON request body from docs/internal-endpoints.md or a local file "
            "against a provided endpoint."
        )
    )
    parser.add_argument("payload_source", nargs="?")
    parser.add_argument("endpoint", nargs="?")
    parser.add_argument("--method", default="POST", help="HTTP method to use. Default: POST.")
    parser.add_argument(
        "--docs-path",
        default=str(DEFAULT_DOCS_PATH),
        help="Markdown file that contains replay-example blocks.",
    )
    parser.add_argument(
        "--list-doc-examples",
        action="store_true",
        help="List replay-example ids available in the docs file and exit.",
    )
    parser.add_argument("--timeout", type=int, default=60, help="Request timeout in seconds.")
    return parser


def load_payload(payload_source: str, docs_path: Path) -> tuple[Any, str]:
    """Load JSON from either doc:example-id or a local file path."""
    if payload_source.startswith("doc:"):
        example_id = payload_source.split(":", 1)[1]
        payload = load_markdown_replay_example(docs_path, example_id)
        return payload, f"{docs_path}#{example_id}"

    payload_path = Path(payload_source).expanduser().resolve()
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    return payload, str(payload_path)


def payload_error_summary(exc: Exception) -> dict[str, str]:
    """Normalize payload loading failures into compact evidence."""
    return {"error": f"{type(exc).__name__}: {exc}"}


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    docs_path = Path(args.docs_path).expanduser().resolve()

    if args.list_doc_examples:
        examples = list_markdown_replay_examples(docs_path)
        if not examples:
            print(f"No replay examples found in {docs_path}")
            return
        for example in examples:
            print(example)
        return

    if not args.payload_source or not args.endpoint:
        parser.print_help()
        return

    try:
        payload, payload_reference = load_payload(args.payload_source, docs_path)
    except Exception as exc:
        evidence = {
            "probe": "ui_replay",
            "status": "payload_error",
            "docs_path": str(docs_path),
            "payload_source": args.payload_source,
            "method": args.method.upper(),
            "endpoint": args.endpoint,
            "error": payload_error_summary(exc),
        }
        evidence_file = write_evidence("probe_ui_replay", evidence)
        raise SystemExit(
            f"FAIL ui_replay payload_error source={args.payload_source} evidence={evidence_file}"
        )

    instance, headers = connect()
    method = args.method.upper()
    url = resolve_request_url(instance, args.endpoint)

    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            json=payload,
            timeout=args.timeout,
        )
    except requests.RequestException as exc:
        evidence = {
            "probe": "ui_replay",
            "status": "request_error",
            "org_alias": SF_ORG_ALIAS,
            "instance_url": instance,
            "payload_source": payload_reference,
            "method": method,
            "endpoint": args.endpoint,
            "url": url,
            "payload": payload,
            "error": request_exception_summary(exc),
        }
        evidence_file = write_evidence("probe_ui_replay", evidence)
        raise SystemExit(
            f"FAIL ui_replay method={method} endpoint={args.endpoint} evidence={evidence_file}"
        )

    evidence = {
        "probe": "ui_replay",
        "status": "recorded",
        "org_alias": SF_ORG_ALIAS,
        "instance_url": instance,
        "payload_source": payload_reference,
        "method": method,
        "endpoint": args.endpoint,
        "url": url,
        "payload": payload,
        "response": response_summary(response, body_limit=1000),
    }
    evidence_file = write_evidence("probe_ui_replay", evidence)

    print(f"HTTP {response.status_code} method={method} endpoint={args.endpoint} evidence={evidence_file}")
    print(response.text[:1000])


if __name__ == "__main__":
    main()
