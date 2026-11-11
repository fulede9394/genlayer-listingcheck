# ListingCheck — Public Listing Liveness Primitive

A standalone Intelligent Contract that attests whether a public
listing — a job post, a rental, an event page, a grant call — is
still live, instead of trusting that a link that loads is a link
that is still open.

## Why this exists

Listings stay up long after the opportunity is gone. Applicants
waste applications on closed roles, renters chase taken flats,
and aggregators keep showing dead links because nobody re-checks
the page. ListingCheck turns "is this listing still live?" into
a reusable primitive with a visible audit trail.

1. `request_listing(title, listing_url, criteria)` — the expected
   title, the listing URL and what counts as "still open" are
   fixed at submission time.
2. `verify_listing(listing_id)` — the LLM only extracts a machine
   line, `STATUS|FOUND_TITLE`, judged under strict equality.
3. Every decision after that is deterministic code. An OPEN verdict
   is only attested when the title found on the page actually
   matches the title that was asked for.

## The title-match gate

A page that loads fine proves nothing on its own: it can be a
redirect to a search page, a generic "browse all jobs" page, or
a different listing entirely. So an OPEN extraction is not
enough. The contract checks, in deterministic code, that at
least one significant word (four letters or more) from the
expected title appears in the title found on the page. Short
words like "a", "of" and "the" do not count.

A page that loads but shows the wrong listing therefore ends in
`MISMATCH`, not `OPEN` and not `NOT_FOUND` — the mismatch is
visible instead of being folded into another state.

## State design

One-way state machine per listing:
`PENDING -> OPEN | CLOSED | NOT_FOUND | MISMATCH | MALFORMED`

- `OPEN`: the listing is live, and the found title matches the
  expected title.
- `CLOSED`: the page says the listing is closed, filled, expired,
  or no longer accepting.
- `NOT_FOUND`: the page does not exist, was removed, or shows no
  such listing.
- `MISMATCH`: the page is live, but the title on it does not match
  the title that was requested. Treat as "do not act on this
  listing".
- `MALFORMED`: the extraction did not produce a usable
  `STATUS|FOUND_TITLE` line. A recorded outcome, not a failed
  transaction.

Because `found_title` is stored, anyone can see *what* the page
actually showed, instead of getting a single opaque verdict.

## Try it in GenLayer Studio

1. Paste `contracts/listing_check.py` into Studio and deploy (no args).
2. `request_listing` with, for example:
   - title: `Software Engineer`
   - listing_url: `https://www.github.com/careers` (use a real, live
     listing URL for a real check)
   - criteria: `Open only if the page shows the role and an apply button, with no closed or expired notice.`
3. `verify_listing(0)`, then `get_listing(0)` — expect `OPEN` with
   a matching `found_title`, or `CLOSED` / `NOT_FOUND` if the
   listing has gone.

## Tests

See `tests/test_cases.md` (10 cases): input validation, unknown /
double verification, the title-match gate, and all five terminal
states.
