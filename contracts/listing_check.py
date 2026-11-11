# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import typing


class ListingCheck(gl.Contract):
    """
    ListingCheck - a public listing liveness primitive.

    Job boards, rental listings, event pages and grant calls all
    share one failure mode: the listing stays up long after the
    opportunity is gone. Applicants waste applications on closed
    roles, renters chase taken flats, and aggregators keep showing
    dead links because nobody re-checks the page.

    This contract attests whether a public listing is still live.
    The expected title, the listing URL and the criteria for "still
    open" are fixed at submission time, and the verdict is taken
    by consensus against the live page. A fresh check is a fresh
    record: listings change, so a listing verified yesterday is
    not evidence about today.

    Consensus follows the structured-extraction pattern: the LLM
    only extracts a machine line, it never decides the outcome.

      STATUS|FOUND_TITLE

    STATUS is OPEN, CLOSED or NOT_FOUND, FOUND_TITLE is the title
    as shown on the page. That line is judged under strict_eq, so
    validators must extract the same status and the same title.

    Every decision after that is deterministic code, and that is
    the point. An OPEN verdict is only attested when the title
    found on the page actually matches the title that was asked
    for: at least one significant word (four letters or more) from
    the expected title must appear in the found title. A page that
    loads fine but shows a different listing, a redirect to a
    search page, or a generic "browse all jobs" page can never
    produce a false OPEN. That mismatch has its own terminal
    state, MISMATCH, so it is visible instead of being folded
    into NOT_FOUND.

    MALFORMED covers the remaining failure mode: the extraction
    did not produce a usable STATUS|FOUND_TITLE line at all.
    Like every terminal state here it is a recorded outcome,
    not a failed transaction.
    """

    listing_count: u256
    titles: TreeMap[u256, str]
    listing_urls: TreeMap[u256, str]
    criteria_map: TreeMap[u256, str]
    statuses: TreeMap[u256, str]
    found_titles: TreeMap[u256, str]

    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    NOT_FOUND = "NOT_FOUND"
    MISMATCH = "MISMATCH"
    MALFORMED = "MALFORMED"

    def __init__(self):
        self.listing_count = u256(0)

    def _title_matches(self, expected: str, found: str) -> bool:
        # At least one significant word from the expected title must
        # appear in the title found on the page. Short words (a, of,
        # the, and) prove nothing, so only words of 4+ letters count.
        expected_lower = expected.lower()
        found_lower = found.lower()
        words = expected_lower.split(" ")
        for word in words:
            if len(word) >= 4 and word in found_lower:
                return True
        return False

    @gl.public.write
    def request_listing(
        self, title: str, listing_url: str, criteria: str
    ) -> int:
        title = title.strip()
        listing_url = listing_url.strip()
        criteria = criteria.strip()

        assert len(title) >= 5, "title too short"
        assert len(title) <= 200, "title too long"
        assert listing_url.startswith("https://"), "listing must be https"
        assert len(listing_url) <= 300, "listing URL too long"
        assert len(criteria) >= 10, "criteria too short"
        assert len(criteria) <= 500, "criteria too long"

        lid = self.listing_count
        self.titles[lid] = title
        self.listing_urls[lid] = listing_url
        self.criteria_map[lid] = criteria
        self.statuses[lid] = self.PENDING
        self.found_titles[lid] = ""
        self.listing_count = lid + u256(1)
        return int(lid)

    @gl.public.write
    def verify_listing(self, listing_id: int) -> str:
        lid = u256(listing_id)
        assert lid in self.statuses, "unknown listing"
        assert self.statuses[lid] == self.PENDING, "listing already verified"

        # Copy storage into locals: non-deterministic blocks may not
        # touch contract storage, they may only capture local values.
        title = self.titles[lid]
        listing_url = self.listing_urls[lid]
        criteria = self.criteria_map[lid]

        def extract_listing() -> str:
            page = gl.nondet.web.render(listing_url, mode="text")
            prompt = f"""Check one public listing using only the page below.

Expected title: {title}
What counts as still open: {criteria}

Page content:
{page[:4000]}

Reply with exactly one line, nothing else, in this format:
STATUS|FOUND_TITLE

STATUS is one of:
OPEN - the listing is live and still accepting applications or bookings
CLOSED - the page says the listing is closed, filled, expired, or no longer accepting
NOT_FOUND - the page does not exist, was removed, or shows no such listing

FOUND_TITLE is the listing title exactly as shown on the page. If there is no listing title on the page, write NONE."""
            return gl.nondet.exec_prompt(prompt).strip()

        line = gl.eq_principle.strict_eq(extract_listing)

        # Deterministic parsing and decision. The LLM extracted
        # data; it never decided the outcome.
        sep = line.find("|")
        if sep == -1:
            self.statuses[lid] = self.MALFORMED
            return self.MALFORMED

        status_word = line[:sep].strip().upper()
        found_title = line[sep + 1:].strip()
        self.found_titles[lid] = found_title

        if status_word == "NOT_FOUND":
            final = self.NOT_FOUND
        elif status_word == "CLOSED":
            final = self.CLOSED
        elif status_word == "OPEN":
            if self._title_matches(title, found_title):
                final = self.OPEN
            else:
                final = self.MISMATCH
        else:
            final = self.MALFORMED

        self.statuses[lid] = final
        return final

    @gl.public.view
    def get_listing(self, listing_id: int) -> typing.Any:
        lid = u256(listing_id)
        assert lid in self.statuses, "unknown listing"
        return {
            "id": listing_id,
            "title": self.titles[lid],
            "listing_url": self.listing_urls[lid],
            "criteria": self.criteria_map[lid],
            "status": self.statuses[lid],
            "found_title": self.found_titles[lid],
        }

    @gl.public.view
    def get_status(self, listing_id: int) -> str:
        lid = u256(listing_id)
        assert lid in self.statuses, "unknown listing"
        return self.statuses[lid]

    @gl.public.view
    def is_open(self, listing_id: int) -> bool:
        lid = u256(listing_id)
        assert lid in self.statuses, "unknown listing"
        return self.statuses[lid] == self.OPEN

    @gl.public.view
    def get_listing_count(self) -> int:
        return int(self.listing_count)
