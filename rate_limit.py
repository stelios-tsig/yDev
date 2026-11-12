"""Απλός in-memory rate limiter (ανά IP).

Αρκεί για ένα single-instance deployment (Render free). Δύο περιορισμοί που
πρέπει να είναι συνειδητοί:

* Μηδενίζεται σε κάθε restart ή deploy. Στο free plan το instance κοιμάται
  με την αδράνεια, οπότε αυτό συμβαίνει αρκετά συχνά.
* Κάθε instance μετράει χωριστά. Σε scale-out το πραγματικό όριο
  πολλαπλασιάζεται με τον αριθμό των instances.

Αν κάποια στιγμή χρειαστεί κάτι ανθεκτικότερο, θέλει κοινό χώρο: Redis ή
ένας πίνακας στη βάση.
"""
import os
import time
from collections import deque

from fastapi import HTTPException, Request

# key -> (timestamps, window). Το window το κρατάμε για να ξέρει ο καθαρισμός
# πότε ένα κλειδί δεν χρησιμεύει πια.
_hits: dict[str, tuple[deque, int]] = {}

# "Δεν έχει σαρώσει ποτέ". Δεν βάζουμε 0.0: το time.monotonic() μετράει από
# αυθαίρετη αφετηρία (στο Linux από το boot), οπότε σε μια διεργασία που
# ξεκίνησε λίγο μετά την εκκίνηση του μηχανήματος το 0.0 θα καθυστερούσε την
# πρώτη σάρωση μέχρι να περάσει το _SWEEP_INTERVAL από το boot.
_NEVER_SWEPT = float("-inf")

_last_sweep: float = _NEVER_SWEPT

_SWEEP_INTERVAL = 300   # κάθε πόσο σαρώνουμε για ξεχασμένα κλειδιά
_MAX_KEYS = 10_000      # αν τα ξεπεράσουμε, σαρώνουμε νωρίτερα


def _trusted_proxy_count() -> int:
    """Πόσα κομμάτια του X-Forwarded-For γράφουν δικά μας proxies."""
    try:
        return max(0, int(os.getenv("TRUSTED_PROXY_COUNT", "0")))
    except ValueError:
        return 0


def _client_ip(request: Request) -> str:
    """Η IP του χρήστη, χωρίς να εμπιστευόμαστε ό,τι στέλνει ο ίδιος.

    Το X-Forwarded-For ξεκινά από τον πελάτη και το συμπληρώνει κάθε proxy
    στη διαδρομή. Παίρνοντας το ΠΡΩΤΟ κομμάτι, οποιοσδήποτε μπορούσε να
    στείλει δικό του X-Forwarded-For με τυχαία τιμή σε κάθε αίτημα, να πάρει
    κάθε φορά καθαρό μετρητή και να παρακάμψει εντελώς το rate limiting.

    Εμπιστευόμαστε μόνο όσα κομμάτια πρόσθεσαν τα δικά μας proxies: το
    τελευταίο από αυτά είναι η πραγματική IP. Χωρίς ρύθμιση δεν
    εμπιστευόμαστε τίποτα και χρησιμοποιούμε τη διεύθυνση του socket.
    """
    trusted = _trusted_proxy_count()
    if trusted:
        header = request.headers.get("x-forwarded-for", "")
        parts = [p.strip() for p in header.split(",") if p.strip()]
        if len(parts) >= trusted:
            return parts[-trusted]

    return request.client.host if request.client else "unknown"


def _sweep(now: float) -> None:
    """Πετάει κλειδιά που δεν μετράνε πια.

    Χωρίς αυτό, κάθε IP που εμφανίστηκε έστω μία φορά θα έμενε για πάντα στη
    μνήμη της διεργασίας — αργή αλλά σταθερή διαρροή.
    """
    global _last_sweep
    _last_sweep = now

    dead = [
        key
        for key, (timestamps, window) in _hits.items()
        if not timestamps or now - timestamps[-1] > window
    ]
    for key in dead:
        del _hits[key]


def rate_limit(request: Request, bucket: str, max_calls: int, window_seconds: int) -> None:
    if os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "false":
        return

    now = time.monotonic()
    if now - _last_sweep > _SWEEP_INTERVAL or len(_hits) > _MAX_KEYS:
        _sweep(now)

    key = f"{bucket}:{_client_ip(request)}"
    entry = _hits.get(key)
    if entry is None:
        entry = (deque(), window_seconds)
        _hits[key] = entry

    timestamps = entry[0]
    while timestamps and now - timestamps[0] > window_seconds:
        timestamps.popleft()

    if len(timestamps) >= max_calls:
        raise HTTPException(
            status_code=429,
            detail="Πάρα πολλές προσπάθειες. Περίμενε λίγο και δοκίμασε ξανά.",
        )

    timestamps.append(now)


def clear_all() -> None:
    """Μόνο για tests."""
    global _last_sweep
    _hits.clear()
    _last_sweep = _NEVER_SWEPT


def _key_count() -> int:
    """Μόνο για tests: πόσα κλειδιά κρατάμε αυτή τη στιγμή."""
    return len(_hits)
