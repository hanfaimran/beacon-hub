import sys
import logging
from app.queries import QUERIES
from app.search import search_serpapi, get_search_count
from app.extract import (
    extract_opportunity, save_opportunity, normalize_url,
    _is_rejected_url, has_topic_keyword,
)
from app.sources import is_trusted

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def seed(target_domain: str = None):
    seen_urls = set()
    total_saved = 0

    queries_to_run = [
        (dom, cat, query)
        for (dom, cat), query in QUERIES.items()
        if target_domain is None or dom == target_domain
    ]

    for domain, category, query in queries_to_run:
        saved_count = 0
        duplicate_count = 0
        rejected_count = 0
        failed_count = 0

        try:
            results = search_serpapi(query)
        except Exception as e:
            print(f"[{domain}/{category}] Search error: {e}")
            continue

        for res in results[:8]:
            raw_url = res.get("url", "")
            title = res.get("title", "")
            snippet = res.get("snippet", "")

            # Reject blocked domains first
            if _is_rejected_url(raw_url):
                rejected_count += 1
                continue

            # Reject items without a topic keyword
            if not has_topic_keyword(title, snippet, domain):
                rejected_count += 1
                continue

            norm_url = normalize_url(raw_url)
            if not norm_url:
                rejected_count += 1
                continue

            # Skip duplicates
            if norm_url in seen_urls:
                duplicate_count += 1
                continue

            seen_urls.add(norm_url)

            try:
                opp = extract_opportunity(res, domain=domain, category=category)

                # Fallback: extract_opportunity returns None only for hard rejections
                # (rejected domain / missing topic) which were already caught above.
                # If None here, treat as failed.
                if opp is None:
                    failed_count += 1
                    continue

                opp_id = save_opportunity(opp)
                if opp_id is not None:
                    saved_count += 1
                    total_saved += 1
                else:
                    duplicate_count += 1
            except Exception as e:
                failed_count += 1

        print(
            f"[{domain}/{category}] "
            f"saved={saved_count} duplicate={duplicate_count} "
            f"rejected={rejected_count} failed={failed_count}"
        )

    print(f"\nTotal opportunities saved: {total_saved}")
    print(f"Total SerpApi searches count: {get_search_count()}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    seed(target)
