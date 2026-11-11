# ListingCheck — test cases

Run manually in GenLayer Studio after deploying
`contracts/listing_check.py` (no constructor args).

## Deterministic validation

1. `request_listing` with a title shorter than 5 characters — expect
   rejection ("title too short").
2. `request_listing` with a title longer than 200 characters — expect
   rejection ("title too long").
3. `request_listing` with an `http://` (non-https) listing URL — expect
   rejection ("listing must be https").
4. `request_listing` with criteria shorter than 10 characters — expect
   rejection ("criteria too short").
5. `request_listing("Software Engineer", <a real live listing URL>, "Open only if the page shows the role and an apply button, with no closed or expired notice.")` — expect listing id `0`, and
   `get_listing_count()` returns `1`.
6. `get_status(99)` on an unknown listing — expect rejection
   ("unknown listing").
7. `verify_listing(99)` on an unknown listing — expect rejection
   ("unknown listing").

## Non-deterministic verdict paths

8. Request a listing that is genuinely live, with a title that
   matches the page, and `verify_listing(0)` — expect `OPEN`, with
   `found_title` sharing a significant word with the requested
   title, and `is_open(0)` returns `true`.
9. Request a listing with a title that does not match anything on
   the page (for example the title of a different role, on a live
   listing page) and verify it — expect `MISMATCH`, not `OPEN`.
   The stored `found_title` should show what the page actually
   displayed.
10. Verify an already-verified listing a second time — expect
    rejection ("listing already verified"). A listing that resolved
    to `CLOSED` or `NOT_FOUND` stays in that state; submit a new
    request for a fresh check.
