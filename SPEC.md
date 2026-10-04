\# Beacon Hub



Beacon Hub is an opportunity discovery and personal tracking platform focused on \*\*Cybersecurity, AI, and Cloud\*\* opportunities.



The platform finds and organizes:

\- Events / Meetups

\- Hackathons

\- Courses

\- Internships

\- Free Certifications

\- Other useful opportunities



The goal is not just to discover opportunities, but to let users decide which opportunities they actually want to pursue, add them to a personal To-Do list, and/or add them to a customizable personal Calendar.



\---



\## STACK



\- Python

\- FastAPI

\- Plain HTML + htmx

\- SerpApi for opportunity discovery

\- PostgreSQL / Tiger Data

\- SQLite as fallback

\- Temporal for reminders

\- Gemma 4B via Ollama for extraction

\- Pydantic for validation

\- dateparser for date extraction



Keep the implementation simple.



Do not add extra libraries without asking.



\---



\# MAIN NAVIGATION



The application has exactly five main tabs:



1\. Cyber

2\. AI

3\. Cloud

4\. To-Do

5\. Calendar



\---



\# CYBER, AI AND CLOUD TABS



Cyber, AI and Cloud are the three main opportunity-discovery sections.



Each of these three tabs must have the same category filters:



\- Events / Meetups

\- Hackathons

&#x20; - Virtual

&#x20; - In-person

\- Courses

\- Internships

\- Free Certifications

\- Other



Example:



CYBER

├── Events / Meetups

├── Hackathons

│   ├── Virtual

│   └── In-person

├── Courses

├── Internships

├── Free Certifications

└── Other



AI uses the same structure.



Cloud uses the same structure.



The category structure should be clearly visible and easy to filter.



\---



\# OPPORTUNITY CARDS



Each discovered opportunity should appear as a card.



Where information is available, the card should contain:



\- Opportunity title

\- Domain: Cybersecurity / AI / Cloud

\- Opportunity type

\- Virtual / In-person status for hackathons

\- Organization

\- Deadline

\- Event date

\- Location

\- Short description

\- Source / official link

\- Verified status

\- Rewards / benefits where available

\- Entry fee where available

\- Add to To-Do button

\- Add to Calendar button



Example:



┌──────────────────────────────────────────┐

│ AWS GenAI Hackathon                      │

│                                          │

│ CLOUD · HACKATHON · VIRTUAL              │

│                                          │

│ 📅 Deadline: October 12                  │

│ 🎁 AWS credits + prizes                  │

│ 💰 Free                                  │

│                                          │

│ Build a GenAI application using AWS...   │

│                                          │

│ ✓ Verified                               │

│ Source: AWS                              │

│                                          │

│ \[ + Add to To-Do ] \[ + Add to Calendar ]│

└──────────────────────────────────────────┘



The card should prioritize quick scanning rather than large amounts of text.



Do not turn cards into long AI-generated descriptions.



\---



\# TO-DO SYSTEM



The To-Do tab is a personal opportunity tracker.



It must be divided into three active sections:



\## Cybersecurity



\## AI



\## Cloud



When an opportunity is added to To-Do, preserve:



\- Title

\- Domain

\- Opportunity type

\- Deadline

\- Short description

\- Source / official link



Each active To-Do item must contain:



\- Checkbox

\- Opportunity title

\- Domain

\- Opportunity type

\- Deadline

\- Short description

\- Source link

\- Add to Calendar button



Example:



TO-DO



\### CYBERSECURITY



☐ Google Cybersecurity Hackathon

&#x20;  🏷 Hackathon

&#x20;  🌐 Virtual

&#x20;  📅 Deadline: October 12

&#x20;  About: Build...

&#x20;  \[Add to Calendar]



\### AI



☐ AI Course

&#x20;  🏷 Course

&#x20;  📅 Deadline: October 20

&#x20;  About: ...

&#x20;  \[Add to Calendar]



\### CLOUD



☐ AWS Hackathon

&#x20;  🏷 Hackathon

&#x20;  🌐 Virtual

&#x20;  📅 Deadline: October 15

&#x20;  \[Add to Calendar]



\---



\# COMPLETED TO-DOS



When the user checks the checkbox on an active To-Do item:



1\. The item is marked completed.

2\. It automatically moves out of the active section.

3\. It appears in a separate Completed section below.

4\. The completed item must remain visible.

5\. The completed item must retain its original information.



Example:



\## COMPLETED



✓ AWS GenAI Hackathon

&#x20;  CLOUD · HACKATHON

&#x20;  Deadline: October 12



Completed items should not be deleted.



The user should be able to visually distinguish active and completed items.



\---



\# TO-DO AND CALENDAR ARE INDEPENDENT



Adding an opportunity to To-Do and adding it to Calendar are two separate actions.



The user can:



\- Add an opportunity only to To-Do.

\- Add an opportunity only to Calendar.

\- Add an opportunity to both.

\- Remove it from Calendar without removing it from To-Do.

\- Remove it from To-Do without removing it from Calendar.



Do not automatically add every discovered opportunity to the Calendar.



The Calendar should contain only opportunities that the user has explicitly chosen to track.



\---



\# ADD TO CALENDAR



Every opportunity card in the Cyber, AI and Cloud tabs must have:



\[ + Add to Calendar ]



Every To-Do item must also have:



\[ + Add to Calendar ]



This allows the user to add an opportunity directly to the Calendar without first adding it to To-Do.



After an opportunity has been added, the button should change state:



\[ ✓ In Calendar ]



Similarly, the To-Do button should become:



\[ ✓ In To-Do ]



This makes the saved state obvious.



\---



\# CALENDAR



The Calendar is a personal planning space for opportunities the user is interested in.



It should NOT automatically contain all discovered opportunities.



The Calendar should display opportunities that the user explicitly added from:



\- Cyber tab

\- AI tab

\- Cloud tab

\- To-Do tab



The Calendar should use a familiar calendar interface similar in concept to Google Calendar.



A month view is preferred for the initial implementation.



Users should be able to click a calendar entry to see the opportunity details and source link.



\---



\# EVENT DATE VS DEADLINE



Event date and application deadline are two separate pieces of information.



Do NOT treat them as the same date.



For example:



Event:

October 20



Application deadline:

October 12



Both should be stored and displayed separately.



If an opportunity has both an event date and an application deadline, the Calendar should represent both clearly.



The interface should visually distinguish:



\- Event date

\- Application deadline



\---



\# CALENDAR TAGS



Calendar entries must have customizable tags.



Default tags should correspond to the three domains:



\- Cybersecurity

\- AI

\- Cloud



Opportunity types can also be displayed as secondary labels:



\- Event / Meetup

\- Hackathon

\- Course

\- Internship

\- Free Certification

\- Other



The user must be able to customize the color associated with calendar tags, similar to Google Calendar.



For example:



CYBERSECURITY 🔴

AI 🟣

CLOUD 🔵



The actual colors must be customizable by the user.



Users should be able to:



\- Change a tag's color.

\- Assign a tag to a calendar entry.

\- See the tag color consistently across the calendar.

\- Create additional custom tags if appropriate.

\- Change tag colors without changing the underlying opportunity.



Calendar tag colors are user preferences and should be stored separately from the opportunity information.



Do not let the LLM decide calendar colors.



\---



\# CALENDAR ENTRY DATA



Each calendar entry should preserve:



\- Opportunity title

\- Domain

\- Opportunity type

\- Event date, if applicable

\- Application deadline, if applicable

\- Location, if applicable

\- Source / official link

\- Assigned calendar tag

\- Tag color



The user should be able to remove an opportunity from the Calendar without deleting:



\- The original discovered opportunity

\- The To-Do item



\---



\# PERSONAL OPPORTUNITY WORKFLOW



The main product workflow should be:



DISCOVER

↓

FILTER BY DOMAIN / CATEGORY

↓

VIEW OPPORTUNITY

↓

Choose:

&#x20;   ├── Add to To-Do

&#x20;   ├── Add to Calendar

&#x20;   └── Both

↓

If added to To-Do:

&#x20;   Track deadline

&#x20;   ↓

&#x20;   Complete checkbox

&#x20;   ↓

&#x20;   Move to Completed



If added to Calendar:

&#x20;   Show event/deadline

&#x20;   ↓

&#x20;   User can customize tag/color



The user is always in control of which opportunities become part of their personal planning system.



\---



\# DATA / VALIDATION RULES



LLM extracts information, but code verifies it.



Dates must be parsed with dateparser.



A date must actually appear in the source text.



If the date cannot be confidently extracted, return null rather than guessing.



Gemma should use:



\- Temperature: 0

\- JSON output

\- Pydantic validation



Reminders are computed by code / Temporal.



The LLM must never determine when a reminder should trigger.



Trusted-source allowlist in code determines whether a source is verified.



Never scrape LinkedIn.



If LinkedIn opportunities are discovered through search results, only use the links returned by the search results.



Never invent opportunity information.



\---



\# SECURITY



Secrets must only exist in `.env`.



Never print API keys.



Never commit `.env`.



Never expose secrets in frontend code.



`.env` must remain in `.gitignore`.



\---



\# SERPAPI



Use SerpApi for opportunity discovery.



Cache SerpApi results.



Track the number of searches.



Hard cap SerpApi searches at 200.



Avoid unnecessary repeated searches.



\---



\# FRONTEND



The user will provide design assets separately later, including:



\- Background image

\- Style references

\- Other visual assets



Until those assets are provided:



\- Build only minimal, functional HTML.

\- Do not invent a visual design.

\- Do not choose colors.

\- Do not choose fonts.

\- Do not fetch external images.

\- Do not add decorative UI unnecessarily.



Frontend files must be placed in:



app/static/



and:



app/templates/



The initial frontend should focus on functionality and correct information architecture.



\---



\# IMPORTANT PRODUCT PRINCIPLES



1\. Discovery and personal tracking are separate concepts.

2\. The Calendar should contain only opportunities the user explicitly chooses.

3\. To-Do and Calendar are independent but connected.

4\. The user can add directly to Calendar from any domain tab.

5\. The user can also add directly to Calendar from To-Do.

6\. Completing a To-Do moves it to Completed rather than deleting it.

7\. Event dates and application deadlines must never be confused.

8\. Calendar tags and colors are user-customizable.

9\. Opportunity categories must be consistent across Cyber, AI and Cloud.

10\. Keep the interface simple and scannable.

11\. Do not invent data that cannot be verified.



\---



\# RESPONSE RULE FOR CODING AGENT



When implementing tasks, reply with code and a one-line summary only.

