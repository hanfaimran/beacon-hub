\# Beacon Hub

Agent that finds cybersecurity, AI and cloud opportunities (events/meetups, hackathons, courses, internships, free certifications), tracks deadlines, and reminds the user via a to-do list.



Stack: Python, FastAPI, plain HTML + htmx, SerpApi (discovery), Postgres/Tiger Data (SQLite fallback), Temporal (reminders), Gemma 4B via Ollama (extraction).



Tabs: Cyber | AI | Cloud (each with category filters: events, hackathons \[virtual/in-person], courses, internships, other) | To-Do (split by domain, checkbox moves item to a Completed stack) | Calendar. Each card has Add to To-Do and Add to Calendar buttons.



Rules:

\- LLM extracts, code verifies. Dates parsed with dateparser, must appear in source text. Return null if unsure.

\- Gemma: temperature 0, JSON output, validated with Pydantic.

\- Reminders are computed by code/Temporal, never the LLM.

\- Trusted-source allowlist in code decides "verified". Never scrape LinkedIn, only use links from search results.

\- Secrets only in .env. Never print or commit keys.

\- Cache SerpApi results, count searches, hard cap 200.

\- Keep it simple. No extra libraries without asking.



\- Only populate organization, rewards, entry fee, location, dates, and other factual fields when explicitly supported by the source text. If unsure, return null. Never label an opportunity "Free" unless the source explicitly says it is free.

\- If a deadline is later than the event date, mark the opportunity unverified rather than guessing or correcting the dates.

\- Store domains as cyber, ai, cloud; display Cybersecurity, AI, Cloud in the UI.



FRONTEND: Design assets are now supplied (see the design brief in the current prompt). Vanilla HTML/CSS/JS in app/templates/ and app/static/, no frameworks. Use textContent, never innerHTML, for any data.



Reply with code and a one-line summary only.

