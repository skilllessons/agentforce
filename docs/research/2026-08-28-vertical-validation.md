# Vertical validation research — 2026-08-28

**Status:** partial. Timeboxed and stopped by the founder mid-sweep. 4 of 5 planned
lenses returned; the CEO agent never delivered its recommendation (it spawned
subagents and returned status lines twice). The session's WebSearch budget was
fully exhausted (200/200), so remaining gaps need a fresh session.

**Question asked:** is insurance the right first vertical, and what use case are we
actually solving?

---

## Headline: the gated-data moat as written in CLAUDE.md is falsified

CLAUDE.md says: *"Big AI gives general web search. We give gated domain data (ISO
forms, Westlaw, ClaimSearch, EDGAR deep parse, FHIR)... That is the moat."*

Between Dec 2025 and Aug 2026 all four major labs shipped licensed-data connector
programs covering finance, legal, and medical.

- **Verisk — ISO's parent — is a named Anthropic connector as of 2026-05-05**,
  described as "property, casualty, and specialty insurance data for underwriting,
  claims, and risk analysis." This is the exact source `ISO_forms_search` is stubbed
  waiting for. https://www.anthropic.com/news/finance-agents
- **Thomson Reuters** ships its own MCP server over 1.9B Westlaw + Practical Law
  documents and 1.4B KeyCite signals, gated on a CoCounsel subscription.
  https://legal-mcp.thomsonreuters.com/docs/connector-guide
- **LSEG** shipped an MCP connector into ChatGPT (week of 2025-12-08), explicit
  "LSEG Everywhere" multi-platform strategy.
- **LexisNexis** embedded Anthropic's legal plugin suite into Lexis+ with Protégé
  (2026-05-13).
- **Google** launched Gemini Enterprise for Financial Services and for Legal on
  **2026-08-25** — three days before this research ran. All MCP-based connectors.
- **OpenAI** ChatGPT Health connects US EHR records via FHIR incl. Epic and Oracle
  Health, powered by b.well (2.2M+ providers).

**Structural point:** the labs did not build these connectors. They signed the data
providers, and the providers increasingly ship their own MCP servers to be
everywhere at once. The gatekeepers are disintermediating the middle layer.

### The public-source fallback is also contested

MCP registry crawl (direct pagination of registry.modelcontextprotocol.io):
**25,487 unique servers enumerated before the crawl stopped — a lower bound.**
Already published by third parties:

- `ai.serff/ca-rate-filings` — NL search over California rate, rule & form filings
  → overlaps our `state_DOI_query`
- `com.brelsfordsoftware.agentweb/insurance-ai-regulation` — NAIC AI model bulletin
  adoption by state, with citations → overlaps our `NAIC_lookup`
- 53 insurance-matching entries, 20 FHIR, 42 EDGAR, 11 Avalara

Zero results for lexis, westlaw, thomson, factset, moody, verisk, claimsearch,
am best, clarivate — premium providers reach users via curated lab partnerships,
not the open registry.

### What survives

1. **Insurance is the least-covered vertical, but the door is closing.** No lab has
   an insurance product; `claude.com/solutions/insurance` 404s while /legal,
   /life-sciences, /healthcare all 200. Google's finance edition has zero insurance
   sources. Anthropic has exactly one (Verisk), with no underwriting/claims agent
   templates. Verisk's May 2026 launch is the clock on this window.
2. **The product shape is the real difference.** Labs sell a connector inside a
   chat/office surface. We sell REST + webhook + structured `ResearchOutput` JSON
   for flow designers. None of the lab offerings target n8n/Flowise/Zapier.
   *Restated as "workflow-native structured output over composed domain sources,"
   the moat survives. As "access to gated data," it does not.*

---

## Data accessibility (interim findings — agent killed before final report)

All confirmed by live API calls, not docs.

**The insurance crux is negative.** SERFF Filing Access has **no public API** —
per-state JS SPA, no robots.txt, voluntary state participation. NAIC publishes web
lookups, not data feeds. State open-data portals carry no rate or form filings.

**Live, keyless, current:** ClinicalTrials.gov v2, openFDA (CC0, commercial use
explicit), USAspending v2, data.cms.gov, NPPES, RxNav, DailyMed, NIH RePORTER,
CFPB HMDA + complaints, FEMA NFHL, eCFR, Federal Register, TED v3 (EU tenders),
GLEIF, FDIC, Treasury FiscalData, US Tax Court DAWSON, ProPublica 990, Census
geocoder, NYC/Cook/LA/King County parcel APIs.

**Keyed but free:** SEC EDGAR (10 req/s + User-Agent), govinfo, USPTO ODP, EPO OPS,
Companies House.

**Healthcare crux is positive:** CMS mandates a machine-readable index at
`/cms-hpt.txt` on every hospital domain. 2 of 4 majors verified returning clean
schema-v2.0.0 JSON; one MRF was 843MB of payer-specific negotiated rates keyed to
CPT codes. Wrinkle: CPT is AMA-licensed.

**Procurement standout:** HigherGov Starter is **$500/year including API access**.

---

## Demand evidence (complete report)

### Pricing — nobody in the enterprise tier publishes a number

Contact-sales confirmed for AgentSync, EZLynx, Patra, Federato, Kalepa, Sixfold,
Zywave, HawkSoft, hyperexponential. Federato ($75–300K/yr) and Kalepa
($6,250–37,500/mo) figures circulating are **third-party estimates from
softwarefinder.com, explicitly labeled as benchmarks — do not quote as vendor
pricing.**

Two exceptions define the prosumer band:
- **AgencyZoom** — $149/$199/$349 per month, 7 seats included, 14-day trial,
  self-serve credit-card signup. https://www.agencyzoom.com/pricing
- **QuoteSweep** — $49/$99/$299 per month; closest analogue to us; explicit ICP is
  "5–20 person agencies on HawkSoft, NowCerts, or QQCatalyst, not locked into
  Applied or Vertafore." Caveat: three contradictory price stories across its own
  site, and signup gated behind a setup call.

Metering unit that has emerged: **submissions/month + seats + carrier count, at
$49–$299/mo per agency.** There is no published price anywhere between $349/mo and
~$75K/yr.

### Displaceable labor

The job is the **$20–30/hr underwriting assistant / technician / surplus-lines
coordinator**, ~$45–65K fully loaded. salary.com "Underwriting Assistant II" median
**$54,091** as of 2026-08-01. Verified listings: Ryan Specialty $20.45–24.05/hr,
AIG Senior UW Assistant $59–68K, Arch Capital $45–50K, WAHVE $25–30/hr.

Ryan Specialty's UW Technical Assistant JD names our job verbatim: *"Gather relevant
market data for risk assessment"*, *"Review policy language and forms to ensure
compliance."*

### Pain signals

- **Ivans 2025 Connectivity survey** (700+ respondents, pub. 2025-12-02): **29% cite
  real-time appetite information as the #1 factor in carrier selection, up from 12%
  in 2024** — a 2.4× YoY jump. 72% want greater commercial submission automation.
- **J.D. Power 2025 Independent Agent Study** (6,893 evaluations): 61% say it's not
  "very easy" to work with their insurer; only 56–57% say carriers deliver on
  "communicating risk appetite and client qualification signals."

### Negative findings — these matter as much as the positives

- **Incumbent review complaints are not about research.** Across 275 AMS reviews
  (Vertafore AMS360 3.6/5 n=58, Applied Epic 4.2/5 n=142, EZLynx 3.7/5 n=75), the
  recurring complaints are data entry, reporting, support, UI. The closest is a
  "search function" complaint — but about searching *their own book*, not external
  research. **"Displace the incumbent's research gap" is unsupported.**
- **Flow-designer footprint is ~zero.** n8n has 4 insurance templates out of 11,790,
  with 2/1/1/0 views. `underwriting` returns 3 forum topics, none insurance. Make.com
  has no insurance templates. Zapier has **no insurance category** and no Applied
  Epic / AgencyZoom / HawkSoft / NowCerts apps. EZLynx (13 triggers) is the one real
  bridge. **We would be creating the category, not entering it.**
- **Public procurement is a null result.** FPDS-NG ATOM feed for "insurance rate
  filing" returned zero. CA DOI / NY DFS / TX TDI / NAIC procurement pages all 404.
  Texas ESBD keyword hits are boilerplate insurance clauses in unrelated contracts.
- **Appetite research is being commoditized to $0** by carrier-funded distribution
  platforms (First Connect Appetite Finder, Ivans Markets via the AMS). Do not build
  the wedge there.

---

## Competitive landscape (complete report)

**Submission triage: CLOSED, high confidence.** Federato, Sixfold, Roots/Bevaya,
Shift, Gradient, Verisk, Cytora, Send, Kalepa, Indico, INSTANDA, Novee/Novella,
EvolutionIQ, Assured, Five Sigma, Tractable, plus a 2026 cohort: Poetic, Reserv,
mea, Artificial Labs, Harper, Outmarket, Qumis, Akur8, Comeryx.

**Subrogation: OPEN**, contingency-priced, medium confidence.

**Regulatory compliance research: the candidate wedge**, partially verified.
- Verified: Perr&Knight's offering and its PK1Cloud/Pythia AI partnership; SERFF's
  unpublished fee schedule and non-AI modernization; **Qumis as the nearest
  AI-native adjacent player — coverage analysis, not statutory research**;
  **56% of insurers cite compliance as their top AI blocker.**
- Unverified: Wolters Kluwer NILS INsource scope/pricing, S&P Global's regulatory
  offering, real contract sizes, Celent/Datos RegTech coverage, and whether a pure
  AI-native multi-state regulatory research startup exists.

Pattern verified in both the data layer and the compliance layer: **incumbents are
wiring AI in themselves** (Perr&Knight via Pythia, Verisk via MCP with a top-10
carrier live). Argues the "gated data access" half of the moat is eroding faster
than the "domain-tuned prompt + eval + structured output" half.

---

## Convergent conclusion

Four lenses independently point at **surplus lines / state DOI filing compliance**
as the surviving slice:

- 189 open postings on one job board; funded roles at $54–75K (InsCipher Compliance
  Analyst, Risk Strategies Surplus Lines Tax Analyst, Ryan Specialty Surplus Lines
  Rep)
- Genuinely 50-jurisdiction drudgery **with correct answers** — what a structured
  research agent is good at, and auditable
- No AI-native player aiming at it; Qumis is adjacent, not competing
- Buyer is a compliance director at a mid-size wholesaler: $1–5K/mo, 1–3 month
  cycle — reachable by a solo founder, unlike a carrier CUO (9–18 months, and they
  will ask where our ISO/Verisk data rights come from)

**Unresolved tension:** this wedge leans on state DOI data, and SERFF has no API.
Whether surplus-lines *tax and filing* rules (state statutes, stamping offices,
deadlines) are more reachable than SERFF *rate filings* is the open question and
should be answered before committing.

---

## Research quality caveats

- WebSearch budget exhausted at 200/200 mid-sweep.
- **All Reddit blocked** at both fetch and search layers — no peer-forum verbatims.
  This is a real hole in the pain-intensity picture.
- 403s from BLS, ZipRecruiter, Adzuna, Indeed, Glassdoor, CareerBuilder,
  TrustRadius, insurance-forums.com, openai.com, cnbc.com, Wolters Kluwer,
  S&P Global. SAM.gov is JS-rendered and needs a key.
- Job-posting volumes are one board's exact-phrase counts and undercount badly.
- The Accenture/McKinsey "40% of underwriter time is admin" stat is only available
  secondhand through a vendor blog; the primary 404s. **Source it before using it
  in a deck.**
- Absence of evidence for Bloomberg/Verisk/NAIC first-party MCP servers is
  unverified, not disproven — searches were blocked rather than returning negatives.

## Open items

1. Rewrite the moat paragraph in CLAUDE.md — it currently asserts something false.
2. Surplus-lines data reachability: is it obtainable without SERFF?
3. Close the Q2 gap (Wolters Kluwer, S&P Global, contract sizes, AI-native
   competitor check) in a fresh session with search budget.
4. Decide: stay / narrow to surplus-lines compliance / switch. Not yet decided.

---

## The reframe (2026-08-28, post-research)

The research killed: *"we have gated data ChatGPT can't reach."*

It did **not** kill: **"your data, our grounded structured output, your workflow."**

A customer-onboarded knowledge base is a **switching-cost moat, not an access
moat** — and unlike the access moat it needs zero partnerships, so it is available
to a solo founder today. Every carrier/MGA/wholesaler has underwriting guidelines,
coverage memos and claim files no lab connector will ever index. That data is
genuinely gated, and gated *to them*, which is better than gated to Verisk.

Implication: the platform direction is the correct response to the research, not a
retreat from it. What we sell becomes the machinery (grounded citations + structured
`ResearchOutput` + workflow-native delivery) run over the customer's own corpus.
