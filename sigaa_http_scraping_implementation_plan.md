# Implementation Plan: HTTP Session-Based SIGAA Scraper for UnB

## Objective

Implement a robust SIGAA scraper for UnB based on the same architectural approach used by the repository [`GeovaneSchmitz/sigaa-api`](https://github.com/GeovaneSchmitz/sigaa-api):

- custom HTTP session management
- manual cookie jar
- explicit redirect following
- HTML form parsing from the live page
- JSF `ViewState` preservation
- no Selenium / Playwright in the primary path

The immediate target is the public UnB endpoint:

- `GET https://sigaa.unb.br/sigaa/public/turmas/listar.jsf`
- then `POST` the parsed form to obtain the `#turmasAbertas table.listagem` result table

This document describes how to port that mechanism to Python step by step, while adapting it to the current codebase.

---

## External Reference Files

These files in `sigaa-api` are the main reference points for the Python design:

- [`src/session/sigaa-http.ts`](https://github.com/GeovaneSchmitz/sigaa-api/blob/master/src/session/sigaa-http.ts)
  Purpose: request building, RFC3986 POST encoding, manual redirect following.

- [`src/session/sigaa-http-session.ts`](https://github.com/GeovaneSchmitz/sigaa-api/blob/master/src/session/sigaa-http-session.ts)
  Purpose: inject cookies before requests, store cookies after responses, request orchestration.

- [`src/session/sigaa-cookies-controller.ts`](https://github.com/GeovaneSchmitz/sigaa-api/blob/master/src/session/sigaa-cookies-controller.ts)
  Purpose: manual cookie jar with domain/path/expiration filtering.

- [`src/session/sigaa-page.ts`](https://github.com/GeovaneSchmitz/sigaa-api/blob/master/src/session/sigaa-page.ts)
  Purpose: response page abstraction, `ViewState` extraction, parsed DOM access.

- [`src/session/page/sigaa-page-unb.ts`](https://github.com/GeovaneSchmitz/sigaa-api/blob/master/src/session/page/sigaa-page-unb.ts)
  Purpose: UnB-specific parsing of JSF `jsfcljs(...)` onclick POST actions.

- [`src/search/sigaa-search-teacher.ts`](https://github.com/GeovaneSchmitz/sigaa-api/blob/master/src/search/sigaa-search-teacher.ts)
  Purpose: best reference for public search flow: `GET page -> parse form -> reuse hidden inputs -> POST -> parse results`.

- [`src/helpers/sigaa-request-stack.ts`](https://github.com/GeovaneSchmitz/sigaa-api/blob/master/src/helpers/sigaa-request-stack.ts)
  Purpose: serialize requests because SIGAA may behave poorly under concurrent access.

- [`src/session/sigaa-institution-controller.ts`](https://github.com/GeovaneSchmitz/sigaa-api/blob/master/src/session/sigaa-institution-controller.ts)
  Purpose: explicit institution-specific behavior. Confirms that UnB support was treated as a first-class variant, not as an accident.

---

## Core Principle to Mirror

The main idea to port from `sigaa-api` is this:

1. Do not hardcode a static form payload as the primary strategy.
2. First fetch the real HTML page.
3. Parse the actual form action and all hidden inputs from that page.
4. Preserve `javax.faces.ViewState`.
5. Submit a POST using a controlled HTTP client with explicit cookies.
6. Follow redirects manually.
7. Treat redirect-to-home as a semantic rejection, not as success.

That is the mechanism to mirror.

---

## Proposed Python Architecture

Create a small SIGAA integration package instead of keeping all transport logic inside [`src/services/sigaa_discrepancy_service.py`](/home/bgeneto/github/ensalamento-fup/src/services/sigaa_discrepancy_service.py).

### New Package

- `src/integrations/sigaa/__init__.py`
- `src/integrations/sigaa/cookies.py`
- `src/integrations/sigaa/page.py`
- `src/integrations/sigaa/page_unb.py`
- `src/integrations/sigaa/http_session.py`
- `src/integrations/sigaa/http_client.py`
- `src/integrations/sigaa/form_parser.py`
- `src/integrations/sigaa/public_turmas_client.py`
- `src/integrations/sigaa/errors.py`

### Existing File to Refactor

- [`src/services/sigaa_discrepancy_service.py`](/home/bgeneto/github/ensalamento-fup/src/services/sigaa_discrepancy_service.py)

Goal: this service should stop owning the scraping transport details and instead depend on a high-level `SigaaPublicTurmasClient`.

---

## Python Components and Their Responsibilities

## 1. `cookies.py`

Mirror of:

- `sigaa-cookies-controller.ts`

### Responsibility

Manual cookie storage and cookie header generation.

### Why

The repository does not trust framework magic here. It stores cookies from `Set-Cookie` explicitly and decides which cookies are valid for each request based on:

- domain
- path
- expiration

### Python API Sketch

```python
@dataclass
class CookieEntry:
    name: str
    value: str
    domain: str
    path: str | None = None
    expires_at: datetime | None = None
    domain_flag: str | None = None


class SigaaCookieJar:
    def store_from_set_cookie_headers(self, domain: str, headers: list[str]) -> None: ...
    def get_cookie_header(self, domain: str, path: str) -> str | None: ...
    def clear(self) -> None: ...
```

### Notes

- Do not delegate correctness solely to `requests.Session().cookies`.
- It is acceptable to use `requests` only as transport, while cookie application remains explicit.

---

## 2. `page.py`

Mirror of:

- `sigaa-page.ts`

### Responsibility

Represent an HTML response page with:

- request metadata
- response headers
- status code
- body text
- parsed DOM
- extracted `ViewState`

### Python API Sketch

```python
@dataclass
class SigaaPage:
    url: str
    request_method: str
    request_headers: dict[str, str]
    request_body: str | None
    response_headers: Mapping[str, str]
    status_code: int
    body: str

    @cached_property
    def soup(self) -> BeautifulSoup: ...

    @cached_property
    def view_state(self) -> str | None: ...
```

### Notes

- `view_state` must come from `input[name="javax.faces.ViewState"]`.
- This object becomes the unit of parsing and diagnostics.

---

## 3. `page_unb.py`

Mirror of:

- `sigaa-page-unb.ts`

### Responsibility

Implement UnB-specific helpers, especially parsing of JSF `jsfcljs(...)` onclick patterns.

### Why

For the public `turmas/listar.jsf` form, this may not be needed immediately because the page appears to use a normal submit button.
Still, this file should exist from the start because:

- it matches the architecture of the reference repo
- it prepares the integration for future UnB SIGAA pages that rely on JSF onclick POSTs
- it keeps UnB-specific parsing isolated

### Python API Sketch

```python
class UnBSigaaPage(SigaaPage):
    def parse_jsfcljs(self, javascript_code: str) -> ParsedSigaaForm: ...
```

### Scope Decision

Phase 1:

- implement the class
- write tests for `jsfcljs(...)` parsing
- do not require it for `public/turmas/listar.jsf` if the plain form flow succeeds

---

## 4. `form_parser.py`

Main conceptual reference:

- `sigaa-search-teacher.ts`

### Responsibility

Parse a real HTML form into:

- action URL
- all non-submit input values
- textarea values
- selected option values
- available submit button names/values

### Python API Sketch

```python
@dataclass
class ParsedSigaaForm:
    action_url: str
    fields: dict[str, str]
    submit_buttons: dict[str, str]


class HtmlFormParser:
    def parse_form(self, page: SigaaPage, selector: str) -> ParsedSigaaForm: ...
```

### Important Behavior

For `form#formTurma`, preserve:

- `formTurma=formTurma`
- `javax.faces.ViewState=<value from page>`
- all other hidden inputs

Then override only:

- `formTurma:inputNivel`
- `formTurma:inputDepto`
- `formTurma:inputAno`
- `formTurma:inputPeriodo`
- and the chosen submit button for `Buscar`

### Critical Rule

Never build the primary POST body from a manually maintained string if the live HTML can be parsed.

---

## 5. `http_session.py`

Mirror of:

- `sigaa-http-session.ts`

### Responsibility

Session lifecycle orchestration:

- inject cookies before request
- store cookies after response
- optionally cache pages
- optionally serialize requests

### Python API Sketch

```python
class SigaaHttpSession:
    def __init__(self, base_url: str, cookie_jar: SigaaCookieJar): ...
    def apply_request_headers(self, url: str, headers: dict[str, str]) -> dict[str, str]: ...
    def process_response(self, url: str, response: requests.Response, request_meta: RequestMeta) -> SigaaPage: ...
```

### Minimum Phase-1 Requirement

- explicit cookie injection
- cookie storage from `Set-Cookie`
- no silent automatic redirect following

### Optional Phase-2 Features

- request de-duplication
- page cache keyed by request method + URL + body
- serialization lock per SIGAA host

---

## 6. `http_client.py`

Mirror of:

- `sigaa-http.ts`

### Responsibility

Low-level GET/POST transport with:

- explicit headers
- RFC3986-compatible encoding for POST form values
- manual redirect following
- page object creation

### Python API Sketch

```python
class SigaaHttpClient:
    def get(self, path_or_url: str) -> SigaaPage: ...
    def post(self, path_or_url: str, post_values: dict[str, str]) -> SigaaPage: ...
    def follow_all_redirects(self, page: SigaaPage) -> SigaaPage: ...
```

### Important Implementation Notes

- Use `allow_redirects=False` on both GET and POST.
- Follow redirects manually with repeated GET requests, as the TypeScript repo does.
- Record every hop in a redirect history object for diagnostics.
- If the redirect chain ends in `/sigaa/public/home.jsf`, treat that as rejection.

### Encoding Note

The TypeScript repo has custom RFC3986 encoding logic in `sigaa-http.ts`.
In Python, do not rely on default `urllib.parse.urlencode` behavior without checking compatibility.

Safer approach:

- build a helper equivalent to `encodeWithRFC3986`
- then serialize POST bodies explicitly

---

## 7. `public_turmas_client.py`

Primary functional adaptation for our use case.

### Responsibility

Implement the exact public UnB scraping flow:

1. load the page
2. parse `formTurma`
3. merge semester values into the parsed form
4. POST the form
5. follow redirects
6. validate whether the result contains `#turmasAbertas table.listagem`
7. return both HTML and detailed diagnostics

### Python API Sketch

```python
class SigaaPublicTurmasClient:
    def fetch_turmas_html(
        self,
        year: int,
        period: int,
        depto_id: str = "666",
        nivel: str = "G",
    ) -> tuple[str, dict[str, Any]]: ...
```

### Detailed Flow

#### Step 1. Candidate entry URLs

Try in this order:

- `https://sigaa.unb.br/sigaa/public/turmas/listar.jsf`
- `https://sigaa.unb.br/sigaa/public/turmas/listar.jsf?aba=p-ensino`

This matches the experimental behavior already observed in this project.

#### Step 2. GET the page

Capture:

- response status
- `Set-Cookie`
- final HTML
- extracted `ViewState`
- form action

#### Step 3. Parse the real form

Expected selector:

- `form#formTurma`

Expected inputs to preserve:

- all hidden fields
- especially `javax.faces.ViewState`
- the hidden field `formTurma=formTurma`

#### Step 4. Override semester-specific values

Set:

- `formTurma:inputNivel=G`
- `formTurma:inputDepto=666`
- `formTurma:inputAno=2026`
- `formTurma:inputPeriodo=1`

Choose the actual submit button from the form:

- e.g. `formTurma:j_id_jsp_...=Buscar`

Do not hardcode the submit field name if it can be parsed from the live page.

#### Step 5. POST to the parsed action URL

POST to the action extracted from the form itself, not to a separately maintained hardcoded endpoint if avoidable.

#### Step 6. Follow redirects manually

Equivalent to `followAllRedirect` in `sigaa-http.ts`.

If the chain ends in:

- `/sigaa/public/home.jsf`

mark it as rejected flow and return diagnostics.

#### Step 7. Validate semantic success

Semantic success means:

- found `#turmasAbertas table.listagem`
  or
- found `table.listagem tr.agrupador`

Transport success alone is insufficient.

---

## Integration with Current Project

## File to Refactor

- [`src/services/sigaa_discrepancy_service.py`](/home/bgeneto/github/ensalamento-fup/src/services/sigaa_discrepancy_service.py)

### Refactoring Goal

Keep this file focused on:

- parsing SIGAA table rows
- professor matching
- schedule normalization
- discrepancy comparison

Move transport/scraping responsibilities into:

- `src/integrations/sigaa/public_turmas_client.py`

### Target Dependency Direction

```python
SigaaDiscrepancyService
  -> SigaaPublicTurmasClient
       -> SigaaHttpClient
            -> SigaaHttpSession
                 -> SigaaCookieJar
```

This separation will make the scraper debuggable and testable without entangling browser logic with matching logic.

---

## Observability Requirements

Every failed attempt should record:

- entry URL used
- parsed form action
- submit button chosen
- extracted `ViewState`
- cookie names stored before POST
- redirect chain
- final URL
- whether `formTurma` still exists in final HTML
- whether result table exists

This is necessary because the failure mode for SIGAA is often semantic, not transport-level.

---

## Concurrency Rule

Based on the note in `sigaa-request-stack.ts`, the Python adapter should avoid concurrent requests to the same SIGAA host.

### Recommendation

Phase 1:

- use a process-level `threading.Lock` around live SIGAA requests

Phase 2:

- implement a small keyed request serializer for `sigaa.unb.br`

This matters because the reference repo explicitly warns that concurrent requests can produce broken pages.

---

## Testing Plan

## Unit Tests

### Cookie Jar

- store `Set-Cookie`
- respect domain/path
- ignore expired cookies
- produce correct `Cookie` header

### Page Parsing

- extract `ViewState`
- parse `formTurma`
- detect submit button name dynamically

### Redirect Handling

- POST returns `302`
- follow chain manually
- final URL `/public/home.jsf` is treated as rejection

### Table Detection

- success when `#turmasAbertas table.listagem` exists
- failure when final HTML is home page or empty

### JSFCLJS Parsing

- parse representative UnB `onclick="javascript:jsfcljs(...)"` samples

## Fixture-Based Tests

Add fixtures under a new directory such as:

- `tests/fixtures/sigaa/public_turmas_form.html`
- `tests/fixtures/sigaa/public_turmas_success.html`
- `tests/fixtures/sigaa/public_home_redirect.html`

## Service Tests

Refactor current tests in:

- [`tests/test_sigaa_discrepancy_service.py`](/home/bgeneto/github/ensalamento-fup/tests/test_sigaa_discrepancy_service.py)

so that:

- transport is mocked at `SigaaPublicTurmasClient`
- discrepancy logic remains independent from HTTP behavior

---

## Step-by-Step Implementation Order

## Phase 1. Build the low-level HTTP adapter

1. Add `errors.py`
2. Add `cookies.py`
3. Add `page.py`
4. Add `page_unb.py`
5. Add `http_session.py`
6. Add `http_client.py`

Deliverable:

- reusable UnB SIGAA HTTP stack with cookies + redirects + page abstraction

## Phase 2. Build the public turmas scraper

1. Add `form_parser.py`
2. Add `public_turmas_client.py`
3. Implement `fetch_turmas_html(year, period, depto_id, nivel)`
4. Add rich diagnostics

Deliverable:

- raw HTML fetcher that can succeed or fail with actionable diagnostics

## Phase 3. Connect to discrepancy flow

1. Refactor [`src/services/sigaa_discrepancy_service.py`](/home/bgeneto/github/ensalamento-fup/src/services/sigaa_discrepancy_service.py)
2. Replace current browser-based fetch path
3. Keep existing comparison logic
4. Preserve `status_by_demanda_id` output for the UI

Deliverable:

- same UI feature, new transport mechanism

## Phase 4. Harden against real-world SIGAA behavior

1. Add request serialization lock
2. Add retry policy only for safe GETs
3. Add explicit handling for home redirect
4. Add optional HTML snapshot logging in debug mode

Deliverable:

- operational robustness

---

## Suggested Python Implementation Details

## Transport Library

Use:

- `requests` for transport
- `beautifulsoup4` for HTML parsing

Avoid:

- Selenium
- Playwright

for the primary implementation path.

## Redirect Policy

Use manual redirect handling even though `requests` can do it automatically.

Reason:

- we need full observability of each hop
- we need to classify redirect-to-home as rejection
- this mirrors the reference repo

## Header Strategy

Use a browser-like header set, but keep it stable and minimal:

- `User-Agent`
- `Accept`
- `Accept-Language`
- `Content-Type` for POST
- explicit `Cookie` header from our jar

Do not overfit headers until necessary.

---

## Known Risks

## 1. SIGAA may still reject the flow

Even after mirroring the TypeScript design, UnB may still reject this specific public endpoint due to:

- WAF or anti-bot behavior
- IP reputation
- infrastructure differences in the UnB deployment
- JSF behavior specific to this page

That would not invalidate the architecture; it would only mean the endpoint has extra constraints.

## 2. Stale `ViewState`

Any cached or reused form payload can fail if `ViewState` becomes stale.

Mitigation:

- always GET a fresh page before POST in the public flow

## 3. Concurrent use

SIGAA may behave unpredictably under concurrent access.

Mitigation:

- serialize live requests

---

## Success Criteria

The implementation should be considered successful when:

1. `GET /sigaa/public/turmas/listar.jsf` returns a parsed page object
2. `formTurma` is parsed from live HTML
3. POST body is generated from live form fields, not hardcoded
4. cookies are manually applied on the POST
5. redirects are followed manually
6. final HTML contains `#turmasAbertas table.listagem`
7. the discrepancy service can compare local demands against parsed SIGAA rows
8. UI still shows per-demand SIGAA status without browser automation

---

## Recommendation

If this plan is implemented, Selenium should be removed from the primary path entirely.

The closest faithful Python adaptation of `sigaa-api` is:

- a `requests`-based client
- with a manual cookie jar
- with page/form abstractions
- with explicit redirect handling
- with UnB-specific JSF helpers available when needed

That is the cleanest way to mirror the reference implementation while adapting it to this project.
