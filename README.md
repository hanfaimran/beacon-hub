# beacon-hub
# Beacon Hub

> **Find → Save → Plan → Do.**

Beacon Hub is a personal opportunity tracker built for a friend who was overwhelmed by the number of hackathons, internships, courses, certifications and events she wanted to keep track of.

It brings opportunities across **Cybersecurity, AI and Cloud** into one place, so users can discover opportunities, save the ones they care about, plan deadlines and track what they have completed.

## Demo

**Live:** https://beacon-hub-e3ag.onrender.com/

Hosted on Render's free tier. The first load may take around a minute if the service is sleeping.

The hosted version contains a snapshot of **101 opportunities** collected locally. Gemma runs locally during the discovery and extraction process.

The hosted SQLite database is intended for demonstration purposes and should not be treated as persistent personal storage.

## Features

- 🔎 Discover opportunities across **Cybersecurity, AI and Cloud**
- 🏷️ Filter by events, hackathons, courses, internships, certifications and more
- 📄 Browse 10 opportunities at a time
- 📅 See event dates and application deadlines separately
- ✅ Verified / Unverified source status
- 📝 Add opportunities to a To-Do list
- 📆 Add opportunities to a monthly Calendar
- ✔️ Move completed tasks to a Completed section
- 🔔 Optional durable reminders with Temporal
- 🎨 Customizable Calendar tags

### Current dataset

| Domain | Opportunities |
|---|---:|
| AI | 61 |
| Cloud | 23 |
| Cybersecurity | 17 |
| **Total** | **101** |

## How It Works

Beacon Hub follows a simple principle:

> **Code finds the facts. Gemma handles ambiguity. Code verifies the result.**

```text
SerpApi
   ↓
Search results
   ↓
Source filtering
   ↓
Page text extraction
   ↓
Date detection
   ↓
Gemma 3 4B
   ↓
Pydantic validation
   ↓
Source verification
   ↓
SQLite
   ↓
Beacon Hub

## Services Used

| Service | Purpose |
|---|---|
| **Gemma 3 4B + Ollama** | Local AI for resolving ambiguous dates and structured opportunity extraction |
| **SerpApi** | Searches the web for relevant Cybersecurity, AI and Cloud opportunities |
| **Temporal** | Runs durable reminder workflows and survives worker interruptions |
| **Render** | Hosts the live Beacon Hub demo |
| **SQLite** | Stores opportunities, To-Do items, Calendar entries and search logs |
| **FastAPI** | Provides the backend API and serves the application |
