"""Batching and ranges (plan 5.2/2): one run takes whole packages while the page count stays
within the limit; a preconverted package or one above the limit always runs alone and is
split into consecutive ranges by count."""


def select_batch(candidates, page_count, limit: int = 30):
    """Return (selected [(pkg, pages)], dropped [pkg]).

    `page_count(pkg)` may download the package (a PDF's page count is known only then); a
    package that was counted but does not fit is returned in `dropped`, so the caller deletes
    its local copy (Drive is untouched and it waits for the next run).
    """
    selected, total, dropped = [], 0, []
    for pkg in candidates:
        if selected and pkg.preconverted:
            break
        pages = page_count(pkg)
        alone = pkg.preconverted or pages > limit
        if alone and not selected:
            return [(pkg, pages)], dropped
        if alone or total + pages > limit:
            dropped.append(pkg)
            break
        selected.append((pkg, pages))
        total += pages
    return selected, dropped


def split_ranges(pages: int, limit: int = 30) -> list[tuple[int, int]]:
    """1-based inclusive ranges: 75 pages → (1, 30), (31, 60), (61, 75)."""
    return [(start, min(start + limit - 1, pages)) for start in range(1, pages + 1, limit)]
