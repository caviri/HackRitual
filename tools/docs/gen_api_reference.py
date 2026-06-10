#!/usr/bin/env python3
"""Generate a complete Markdown API reference from the OpenAPI snapshot.

Source of truth is docs/openapi.json (regenerated from the live app). This
renders every path + operation grouped by tag, with auth, parameters, request
bodies, responses, and a schema appendix — enough for anyone to build their own
frontend or client without reading the backend source.

Usage (no args; paths are relative to the repo root):
    python tools/docs/gen_api_reference.py
"""

from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = os.path.join(ROOT, "docs", "openapi.json")
OUT = os.path.join(ROOT, "docs", "api-reference.md")

METHODS = ["get", "post", "put", "patch", "delete"]


def ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def schema_label(schema: dict | None) -> str:
    """A short human label for a schema node (handles $ref, arrays, primitives)."""
    if not schema:
        return "—"
    if "$ref" in schema:
        n = ref_name(schema["$ref"])
        return f"[`{n}`](#schema-{n.lower()})"
    if schema.get("type") == "array":
        return f"array of {schema_label(schema.get('items'))}"
    if "anyOf" in schema or "oneOf" in schema:
        parts = schema.get("anyOf") or schema.get("oneOf")
        return " | ".join(schema_label(p) for p in parts)
    t = schema.get("type", "object")
    if schema.get("enum"):
        return f"{t} (enum: {', '.join(map(str, schema['enum']))})"
    fmt = schema.get("format")
    return f"{t}" + (f" ({fmt})" if fmt else "")


def anchor(tag: str) -> str:
    return tag.lower().replace(" ", "-").replace("/", "")


def render_params(params: list[dict]) -> list[str]:
    rows = []
    for p in params:
        rows.append(
            f"| `{p['name']}` | {p.get('in')} | {'yes' if p.get('required') else 'no'} "
            f"| {schema_label(p.get('schema'))} | {p.get('description', '').replace(chr(10), ' ')} |"
        )
    if not rows:
        return []
    return [
        "",
        "| name | in | required | type | description |",
        "|------|----|----------|------|-------------|",
        *rows,
    ]


def render_request_body(body: dict) -> list[str]:
    content = body.get("content", {})
    out = ["", "**Request body**" + (" *(required)*" if body.get("required") else "") + ":", ""]
    for ctype, media in content.items():
        out.append(f"- `{ctype}` → {schema_label(media.get('schema'))}")
    return out


def render_responses(responses: dict) -> list[str]:
    out = ["", "**Responses**", "", "| status | description | body |", "|--------|-------------|------|"]
    for code, resp in sorted(responses.items()):
        body = "—"
        content = resp.get("content", {})
        if content:
            first = next(iter(content.values()))
            body = schema_label(first.get("schema"))
        desc = resp.get("description", "").replace("\n", " ")
        out.append(f"| `{code}` | {desc} | {body} |")
    return out


def main() -> None:
    with open(SPEC, encoding="utf-8") as f:
        spec = json.load(f)

    info = spec.get("info", {})
    tags_meta = {t["name"]: t.get("description", "") for t in spec.get("tags", [])}
    paths = spec.get("paths", {})

    # Group operations by their first tag.
    by_tag: dict[str, list[tuple[str, str, dict]]] = {}
    for path, item in paths.items():
        for method in METHODS:
            op = item.get(method)
            if not op:
                continue
            tag = (op.get("tags") or ["untagged"])[0]
            by_tag.setdefault(tag, []).append((method, path, op))

    op_count = sum(len(v) for v in by_tag.values())

    lines: list[str] = []
    lines.append("# API Reference")
    lines.append("")
    lines.append(
        f"> Auto-generated from [`openapi.json`](openapi.json) — **do not edit by hand**. "
        f"Regenerate with `python tools/docs/gen_api_reference.py`."
    )
    lines.append("")
    lines.append(
        f"**{info.get('title', 'HackRitual')}** · version `{info.get('version', '?')}` · "
        f"{op_count} operations across {len(by_tag)} groups."
    )
    lines.append("")
    lines.append(
        "Every endpoint is listed below. The same spec is browsable interactively at "
        "`/api/docs` (Swagger UI) and `/api/redoc` (ReDoc) on a running server, and the "
        "machine-readable `openapi.json` can drive client codegen (e.g. "
        "`openapi-generator`, `openapi-typescript`)."
    )
    lines.append("")

    # Table of contents
    lines.append("## Groups")
    lines.append("")
    for tag in sorted(by_tag):
        desc = tags_meta.get(tag, "")
        lines.append(f"- [{tag}](#{anchor(tag)}) — {desc}" if desc else f"- [{tag}](#{anchor(tag)})")
    lines.append("")

    # Per-tag operations
    for tag in sorted(by_tag):
        lines.append(f"## {tag}")
        if tags_meta.get(tag):
            lines.append("")
            lines.append(tags_meta[tag])
        lines.append("")
        # stable order: by path then method
        for method, path, op in sorted(by_tag[tag], key=lambda x: (x[1], METHODS.index(x[0]))):
            summary = op.get("summary") or op.get("operationId", "")
            lines.append(f"### `{method.upper()} {path}`")
            lines.append("")
            if summary:
                lines.append(f"**{summary}**")
                lines.append("")
            if op.get("description"):
                lines.append(op["description"].strip())
                lines.append("")
            sec = op.get("security")
            if sec is not None:
                names = ", ".join(k for s in sec for k in s) or "none (public)"
                lines.append(f"_Auth: {names}_")
                lines.append("")
            params = op.get("parameters", [])
            lines.extend(render_params(params))
            if op.get("requestBody"):
                lines.extend(render_request_body(op["requestBody"]))
            lines.extend(render_responses(op.get("responses", {})))
            lines.append("")

    # Schema appendix
    schemas = spec.get("components", {}).get("schemas", {})
    if schemas:
        lines.append("## Schemas")
        lines.append("")
        lines.append("Data shapes referenced above. `*` marks a required field.")
        lines.append("")
        for name in sorted(schemas):
            s = schemas[name]
            lines.append(f"### Schema: {name}")
            lines.append("")
            if s.get("description"):
                lines.append(s["description"].strip())
                lines.append("")
            if s.get("enum"):
                lines.append(f"Enum: {', '.join(f'`{v}`' for v in s['enum'])}")
                lines.append("")
                continue
            props = s.get("properties", {})
            required = set(s.get("required", []))
            if not props:
                lines.append("_(no defined properties)_")
                lines.append("")
                continue
            lines.append("| field | type | required | description |")
            lines.append("|-------|------|----------|-------------|")
            for fname, fs in props.items():
                req = "*" if fname in required else ""
                desc = (fs.get("description", "") or "").replace("\n", " ")
                lines.append(
                    f"| `{fname}`{req} | {schema_label(fs)} | "
                    f"{'yes' if fname in required else 'no'} | {desc} |"
                )
            lines.append("")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {OUT}: {op_count} operations, {len(schemas)} schemas")


if __name__ == "__main__":
    main()
