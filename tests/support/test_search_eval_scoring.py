"""Scoring for the search-only eval (M3.2). Pure functions: no database."""

from agentforge.verticals.support.eval.run_search_evals import query_type, score, summarize


def _q(expected: list[str], qid: str = "topic_x", forbidden: list[str] | None = None) -> dict:
    return {"id": qid, "expected_ids": expected, "forbidden_ids": forbidden or []}


def test_partial_recall_lists_missed() -> None:
    r = score(_q(["1", "2", "3", "4"]), ["2", "4", "99"])
    assert r["recall"] == 0.5
    assert r["missed"] == ["1", "3"]
    assert r["false_hits"] == 0


def test_none_query_counts_any_result_as_false_hit() -> None:
    assert score(_q([], "none_shipping"), [])["false_hits"] == 0
    r = score(_q([], "none_shipping"), ["5", "7"])
    assert r["recall"] == 1.0
    assert r["false_hits"] == 2


def test_forbidden_and_other_tenant_ids_are_reported() -> None:
    r = score(_q(["1"], forbidden=["2"]), ["1", "2", "9001"])
    assert r["forbidden_hits"] == ["2"]
    assert r["leaks"] == ["9001"]


def test_query_type_from_id_prefix() -> None:
    assert query_type("synonym_money_back") == "synonym"
    assert query_type("status_open_bugs") == "status"
    assert query_type("billing_overview") == "topic"  # no known prefix


def test_summarize_means_by_type() -> None:
    rows = [
        score(_q(["1", "2"], "synonym_a"), ["1"]),
        score(_q(["1"], "synonym_b"), []),
        score(_q(["1"], "topic_c"), ["1"]),
    ]
    s = summarize(rows)
    assert s["recall_by_type"] == {"synonym": 0.25, "topic": 1.0}
    assert s["mean_recall"] == 0.5

def test_leaks_only_query_ignores_false_hits() -> None:
    q = {"id": "none_tenant_probe", "expected_ids": [], "search_check": "leaks_only"}
    r = score(q, ["110", "5", "9001"])
    assert r["false_hits"] == 0
    assert r["leaks"] == ["9001"]
