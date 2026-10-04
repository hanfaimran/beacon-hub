import sys
import logging

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from app.queries import QUERIES
from app.search import search_serpapi
from app.extract import extract_opportunity, save_opportunity


def main():
    if len(sys.argv) != 3:
        print("Usage: python -m app.pipeline <domain> <category>")
        sys.exit(1)

    domain = sys.argv[1]
    category = sys.argv[2]

    query = QUERIES[(domain, category)]

    print(f"Running search: {query}")
    results = search_serpapi(query)

    print(f"Found {len(results)} cached search results.")
    print("Testing first 5 results...\n")

    for i, result in enumerate(results[:5], start=1):
        print(f"--- {i}/5 ---")

        try:
            opportunity = extract_opportunity(
                result,
                domain=domain,
                category=category,
            )

            if opportunity is None:
                print("Extraction failed.\n")
                continue

            save_opportunity(opportunity)

            print(f"Title: {opportunity['title']}")
            print(f"Deadline: {opportunity['deadline_utc']}")
            print(f"Event date: {opportunity['event_date_utc']}")
            print(f"Verified: {opportunity['verified']}")
            print()

        except Exception as exc:
            print(f"Error: {exc}\n")


if __name__ == "__main__":
    main()