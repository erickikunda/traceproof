import copy
from html.parser import HTMLParser

from test_evaluation import evaluation as evaluation
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture

from traceproof.evaluation import render_scorecard


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.attributes = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)


def test_html_values_escaping_and_no_active_content(evaluation):
    report = evaluation[3]()
    report["dataset_id"] = '<script>alert("x")</script>'
    report["repositories"][0]["repo_id"] = "<img src=x onerror=alert(1)>"
    report["limitations"].append('</li><iframe src="https://example.com"></iframe>')
    original = copy.deepcopy(report)
    rendered = render_scorecard(report, "html")
    tags = Tags()
    tags.feed(rendered)
    assert not {"script", "img", "iframe", "a", "link"} & set(tags.tags)
    assert not any(name.startswith("on") for name, _ in tags.attributes)
    assert "&lt;script&gt;" in rendered and "Content-Security-Policy" in rendered
    assert "1 / 1 declared labels matched" in rendered and "100.0%" in rendered
    assert report["scorecard_id"] in rendered and "CWE-94" in rendered
    assert "Precision and confirmed recall are unknown" in rendered
    assert report == original


def test_html_incomplete_unknown_and_legacy(evaluation):
    evaluation[2]["reports"] = []
    report = evaluation[3]()
    rendered = render_scorecard(report, "html")
    assert "Incomplete" in rendered and "0 / 1 declared labels matched" in rendered
    report["candidate_recall_proxy"] = {"numerator": 0, "denominator": 0, "value": None}
    del report["weaknesses"]
    report["candidates"] = []
    rendered = render_scorecard(report, "html")
    assert "Unknown" in rendered and "legacy scorecard" in rendered
    assert "No rows recorded" in rendered
