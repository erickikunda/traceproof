"""Offline, script-free presentation of existing benchmark facts."""

import html
import json


def cell(value):
    if value is None:
        return "Unknown"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return html.escape(str(value))


def table(title, rows, fields):
    header = "".join(f'<th scope="col">{cell(label)}</th>' for _, label in fields)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell(row.get(key))}</td>" for key, _ in fields) + "</tr>"
        for row in rows
    )
    if not rows:
        body = f'<tr><td colspan="{len(fields)}">No rows recorded</td></tr>'
    return (
        '<div class="scroll"><table><caption>'
        + cell(title)
        + "</caption><thead><tr>"
        + header
        + "</tr></thead><tbody>"
        + body
        + "</tbody></table></div>"
    )


def render_html(report):
    metric = report["candidate_recall_proxy"]
    ratio = f"{cell(metric['numerator'])} / {cell(metric['denominator'])}"
    value = "Unknown" if metric["value"] is None else f"{metric['value']:.1%}"
    audit = report.get("report_kind") == "discovery_coverage_audit"
    if audit:
        value = "Not evaluable"
    complete = report["complete"] is True
    sections = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">",
        "<title>TraceProof benchmark scorecard</title><style>",
        "body{font:16px/1.5 system-ui,sans-serif;color:#172b42;background:#f4f6f9;"
        "margin:0;padding:24px}main{max-width:1120px;margin:auto}h1{margin-bottom:8px}"
        ".card,details,.scroll{background:white;border:1px solid #cbd5e1;border-radius:8px;"
        "padding:16px;margin:16px 0}.notice{border-left:6px solid #a45b00;padding:16px;"
        "background:#fff3d6}.metrics{display:flex;flex-wrap:wrap;gap:16px}"
        ".metrics .card{flex:1;min-width:200px}.number{font-size:28px;font-weight:700}"
        ".scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}"
        "caption{text-align:left;font-size:20px;font-weight:700;padding-bottom:12px}"
        "th,td{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #ddd;"
        "overflow-wrap:anywhere}th{background:#edf2f7}summary{cursor:pointer;font-weight:700}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere}li{margin:8px 0}"
        "@media print{body{background:white;padding:0}.scroll{overflow:visible}"
        "details{break-inside:avoid}.metrics .card{margin:4px}}",
        "</style></head><body><main><p>TRACEPROOF · BENCHMARK</p>",
        "<h1>Discovery coverage audit</h1>" if audit else "<h1>Candidate-location scorecard</h1>",
        f"<p>Dataset: <strong>{cell(report['dataset_id'])}</strong> · "
        f"Version {cell(report['dataset_version'])}</p>",
        '<p class="notice"><strong>Provisional location matches.</strong> '
        "Precision and confirmed recall are unknown. Additional predictions are unjudged, "
        "not automatically false positives.</p>",
        '<div class="metrics"><section class="card"><h2>Candidate recall proxy</h2>'
        f'<div class="number">{value}</div><p>'
        + (
            "Discovery profiles are not qualified for recall."
            if audit
            else f"{ratio} declared labels matched"
        )
        + "</p></section>",
        '<section class="card"><h2>Evaluation status</h2><div class="number">'
        + ("Complete" if complete else "Incomplete")
        + "</div><p>Completion describes evaluation, not security coverage.</p></section>",
        '<section class="card"><h2>Scope</h2>'
        f"<p>{cell(report['repository_count'])} repositories · "
        f"{cell(report['label_count'])} declared labels</p></section></div>",
        table(
            "Label outcomes",
            [{"status": key, "count": value} for key, value in report["label_counts"].items()],
            [("status", "Outcome"), ("count", "Count")],
        ),
        table(
            "Repository results",
            report["repositories"],
            [
                ("repo_id", "Repository"),
                ("status", "Status"),
                ("scope_gaps", "Scope gaps"),
                ("candidate_count", "Candidates"),
                ("label_counts", "Label outcomes"),
                ("report_id", "Report ID"),
            ],
        ),
    ]
    if "weaknesses" in report:
        sections.append(
            table(
                "Results by weakness class",
                report["weaknesses"],
                [
                    ("cwe", "CWE"),
                    ("status", "Status"),
                    ("selected_rule_scope", "Selected rule scope"),
                    ("candidate_recall_proxy_numerator", "Matched"),
                    ("label_count", "Declared labels"),
                    ("candidate_recall_proxy_value", "Recall proxy (fraction)"),
                    ("label_counts", "Label outcomes"),
                ],
            )
        )
    else:
        sections.append("<p>Per-CWE metrics unavailable in this legacy scorecard.</p>")
    for title, key, fields in [
        (
            "Label details",
            "labels",
            [
                ("repo_id", "Repository"),
                ("label_id", "Label"),
                ("cwe", "CWE"),
                ("status", "Status"),
                ("reasons", "Reasons"),
                ("candidate_fingerprints", "Candidate fingerprints"),
            ],
        ),
        (
            "Candidate details",
            "candidates",
            [
                ("repo_id", "Repository"),
                ("fingerprint", "Fingerprint"),
                ("status", "Status"),
                ("adjudication", "Adjudication"),
            ],
        ),
    ]:
        sections.append(
            "<details><summary>"
            + title
            + "</summary>"
            + table(title, report[key], fields)
            + "</details>"
        )
    provenance = {
        key: report[key]
        for key in (
            "scorecard_id",
            "schema_version",
            "evaluator_version",
            "dataset_id",
            "dataset_version",
            "label_set_version",
            "manifest_sha256",
            "labels_sha256",
            "plan_sha256",
            "evaluation_scope",
        )
    }
    sections.extend(
        [
            "<h2>Limitations</h2><ul>"
            + "".join("<li>" + cell(item) + "</li>" for item in report["limitations"])
            + "</ul>",
            "<details><summary>Provenance and evaluation configuration</summary><pre>"
            + cell(json.dumps(provenance, indent=2, ensure_ascii=False))
            + "</pre></details>",
            "<p>Expand details before printing. Use JSON or CSV for machine-readable values. "
            "This view does not run scans or recompute the scorecard.</p></main></body></html>",
        ]
    )
    return "".join(sections)
