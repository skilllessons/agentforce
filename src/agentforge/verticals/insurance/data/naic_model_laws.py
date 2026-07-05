"""Curated NAIC model law index.

NAIC's model laws are referenced by stable MDL-NNN identifiers. They revise
infrequently (annual at most), and the canonical PDFs live at content.naic.org.
We keep a curated index here for the most-cited models so the agent can return
precise citations without scraping the search page.

Coverage scope: the models referenced in the 30 golden insurance queries plus
a few high-frequency adjacencies. Expand as needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class NaicModelLaw:
    mdl: str
    title: str
    topics: tuple[str, ...]
    url: str
    summary: str
    short_name: str | None = None
    last_reviewed: str | None = None


NAIC_MODEL_LAWS: list[NaicModelLaw] = [
    NaicModelLaw(
        mdl="MDL-672",
        title="Insurance Information and Privacy Protection Model Act",
        topics=("privacy", "consumer information", "fair credit reporting", "adverse action"),
        url="https://content.naic.org/sites/default/files/MO672.pdf",
        summary=(
            "Establishes consumer privacy protections, notice requirements, and the right to "
            "access and correct insurance information."
        ),
    ),
    NaicModelLaw(
        mdl="MDL-200",
        title="Property and Casualty Model Rating Law (Prior Approval)",
        short_name="P&C Rate Filing",
        topics=("rate filing", "prior approval", "rate", "p&c"),
        url="https://content.naic.org/sites/default/files/MO200.pdf",
        summary=(
            "Model framework for state rate review of property and casualty insurance, "
            "including prior-approval filing requirements."
        ),
    ),
    NaicModelLaw(
        mdl="MDL-880",
        title="Anti-Concurrent Causation Disclosure Model Act",
        short_name="Anti-Concurrent Causation",
        topics=(
            "anti-concurrent causation",
            "concurrent cause",
            "property",
            "flood",
            "wind vs water",
        ),
        url="https://content.naic.org/sites/default/files/MO880.pdf",
        summary=(
            "Model standards for property policy anti-concurrent causation clauses (e.g. "
            "wind-vs-water disputes after hurricanes)."
        ),
    ),
    NaicModelLaw(
        mdl="MDL-870",
        title="Unfair Trade Practices Act",
        topics=("unfair trade", "market conduct", "misrepresentation"),
        url="https://content.naic.org/sites/default/files/MO870.pdf",
        summary=(
            "Prohibits misrepresentation, unfair claim settlement practices, and discriminatory "
            "underwriting."
        ),
    ),
    NaicModelLaw(
        mdl="MDL-900",
        title="Unfair Claims Settlement Practices Act",
        topics=("unfair claims", "claims settlement", "prompt payment", "bad faith"),
        url="https://content.naic.org/sites/default/files/MO900.pdf",
        summary=(
            "Defines unfair practices in the handling of insurance claims and grants enforcement "
            "authority to state regulators."
        ),
    ),
    NaicModelLaw(
        mdl="MDL-275",
        title="Credit-Based Insurance Score Model Act",
        short_name="Credit Scoring in Personal Lines",
        topics=(
            "credit score",
            "credit scoring",
            "personal lines",
            "adverse action",
            "underwriting",
        ),
        url="https://content.naic.org/sites/default/files/MO275.pdf",
        summary=(
            "Governs the use of consumer credit information in personal lines underwriting and "
            "rating, including adverse-action notice requirements."
        ),
    ),
    NaicModelLaw(
        mdl="MDL-440",
        title="Producer Licensing Model Act",
        topics=("producer licensing", "agent licensing", "broker licensing", "continuing education"),
        url="https://content.naic.org/sites/default/files/MO440.pdf",
        summary=(
            "Uniform standards for the licensing of insurance producers, including reciprocity "
            "and continuing education."
        ),
    ),
    NaicModelLaw(
        mdl="MDL-870-A",
        title="Surplus Lines Model Act",
        short_name="Surplus Lines",
        topics=("surplus lines", "non-admitted", "declinations", "stamping fee", "nima", "slsaef"),
        url="https://content.naic.org/sites/default/files/MO870A.pdf",
        summary=(
            "Framework for surplus lines (non-admitted) placement: diligent search, declinations, "
            "stamping office, and tax remittance."
        ),
    ),
    NaicModelLaw(
        mdl="MDL-660",
        title="Property Insurance Declination, Termination and Disclosure Model Act",
        topics=("non-renewal", "cancellation", "declination", "property", "notice"),
        url="https://content.naic.org/sites/default/files/MO660.pdf",
        summary=(
            "Notice and disclosure standards when an insurer non-renews, declines, or cancels a "
            "property policy."
        ),
    ),
    NaicModelLaw(
        mdl="MDL-820",
        title="Standard Nonforfeiture Law for Individual Deferred Annuities",
        topics=("annuity", "nonforfeiture", "life"),
        url="https://content.naic.org/sites/default/files/MO820.pdf",
        summary="Minimum nonforfeiture values for individual deferred annuity contracts.",
    ),
    NaicModelLaw(
        mdl="MDL-440-1",
        title="Market Conduct Examiners Handbook (procedural)",
        short_name="Market Conduct Examination",
        topics=("market conduct", "examination", "complaint ratio", "doi", "oversight"),
        url="https://content.naic.org/market-conduct-handbook",
        summary=(
            "Procedural handbook for state market-conduct examinations: triggers (complaint "
            "ratio, financial outliers), scope, sampling."
        ),
    ),
]

_STOPWORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "of", "in", "to", "for", "on", "with", "is",
        "are", "be", "by", "as", "what", "how", "do", "does", "naic", "model",
        "regulation", "regulations", "law", "laws", "act",
    }
)


def search_model_laws(query: str, limit: int = 5) -> list[NaicModelLaw]:
    tokens = _tokenize(query)
    if not tokens:
        return []

    scored: list[tuple[NaicModelLaw, float]] = []
    for m in NAIC_MODEL_LAWS:
        haystack = _tokenize(
            f"{m.title} {m.short_name or ''} {' '.join(m.topics)} {m.summary}"
        )
        haystack_set = set(haystack)
        score = 0.0
        for t in tokens:
            if t in haystack_set:
                score += 1.0
            for topic in m.topics:
                if t in topic and len(t) >= 4:
                    score += 0.3
        if score > 0:
            scored.append((m, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [m for m, _ in scored[:limit]]


def _tokenize(s: str) -> list[str]:
    return [
        t
        for t in re.sub(r"[^a-z0-9\s-]", " ", s.lower()).split()
        if len(t) > 1 and t not in _STOPWORDS
    ]
