import os
import re
import time
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import httpx
from bs4 import BeautifulSoup
import dateparser

import json

from app.sources import is_trusted, get_source_domain
from app.search import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma:2b")

DATE_REGEX = re.compile(
    r'\b(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,\s*\d{4})?|\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{4})\b',
    re.IGNORECASE
)

TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'utm_id', 'utm_reader', 'utm_name', 'utm_cid',
    'fbclid', 'gclid', 'ref', 'ref_src', 'igshid', 'mc_cid', 'mc_eid',
}

BLOCKED_FETCH = set()

REJECTED_DOMAINS = {
    'youtube.com', 'www.youtube.com',
    'youtu.be',
    'reddit.com', 'www.reddit.com',
    'facebook.com', 'www.facebook.com',
    'instagram.com', 'www.instagram.com',
    'x.com', 'www.x.com',
    'twitter.com', 'www.twitter.com',
    'pinterest.com', 'www.pinterest.com',
    'quora.com', 'www.quora.com',
    'wikipedia.org', 'www.wikipedia.org',
    'sciencedirect.com', 'www.sciencedirect.com',
    'scribd.com', 'www.scribd.com',
    'medium.com', 'www.medium.com',
    'forum.freecodecamp.org',
}

REJECTED_PATH_SEGMENTS = {'/d/', '/search', '/browse', '/category', '/tag'}

TOPIC_KEYWORDS = {
    "cyber": ["cyber", "security", "infosec", "hacking", "soc"],
    "ai": ["ai", "artificial intelligence", "machine learning", "llm"],
    "cloud": ["cloud", "aws", "azure", "gcp", "kubernetes"],
}


def has_topic_keyword(title: str, snippet: str, domain: str) -> bool:
    keywords = TOPIC_KEYWORDS.get(domain, [])
    if not keywords:
        return True
    text = f"{title or ''} {snippet or ''}".lower()
    for kw in keywords:
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, text):
            return True
    return False


def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    query_params = parse_qsl(parsed.query, keep_blank_values=True)
    filtered_params = [
        (k, v) for k, v in query_params
        if not (k.lower() in TRACKING_PARAMS or k.lower().startswith('utm_'))
    ]
    new_query = urlencode(filtered_params)
    new_path = parsed.path.rstrip('/') if parsed.path != '/' else '/'
    normalized = urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, new_query, parsed.fragment))
    return normalized.rstrip('/') if normalized.endswith('/') and len(normalized) > parsed.scheme.__len__() + 4 else normalized


def _is_rejected_url(url: str) -> Optional[str]:
    """Return a rejection reason string if the URL should be skipped before fetching, else None."""
    parsed = urlparse(url)
    host_full = parsed.netloc.lower()
    host = host_full.lstrip('www.')
    source_dom = get_source_domain(url)

    for rej in REJECTED_DOMAINS:
        rej_clean = rej.lstrip('www.')
        if (
            host_full == rej
            or host == rej_clean
            or host.endswith('.' + rej_clean)
            or source_dom == rej_clean
            or source_dom.endswith('.' + rej_clean)
        ):
            return f"rejected domain: {host_full}"

    path = parsed.path
    for seg in REJECTED_PATH_SEGMENTS:
        if seg in path:
            return f"rejected path segment '{seg}': {path}"

    clean_path = path.rstrip('/')
    if not clean_path or clean_path.endswith(('/hackathons', '/events', '/courses')):
        return f"listing page path: {path}"

    return None


_DEADLINE_WORDS = [
    "deadline", "register by", "apply by", "applications close",
    "submit by", "closes", "last date",
]
_EVENT_WORDS = [
    "summit", "conference", "hackathon", "event", "starts", "begins", "takes place",
]

_OLLAMA_FORMAT = {
    "type": "object",
    "properties": {
        "event":    {"type": ["integer", "null"]},
        "deadline": {"type": ["integer", "null"]},
        "mode":     {"enum": ["virtual", "in_person", "hybrid", None]},
    },
    "required": ["event", "deadline", "mode"],
}


def _classify_candidates(
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Keyword-based pre-classification.
    Returns {"event": index|None, "deadline": index|None, "ambiguous": bool}.
    A role is resolved only when exactly one candidate matches it.
    """
    deadline_hits: List[int] = []
    event_hits: List[int] = []

    for i, c in enumerate(candidates):
        ctx = c["context"][:120].lower()
        is_deadline = any(w in ctx for w in _DEADLINE_WORDS)
        is_event = any(w in ctx for w in _EVENT_WORDS) and not is_deadline
        if is_deadline:
            deadline_hits.append(i)
        if is_event:
            event_hits.append(i)

    resolved_deadline = deadline_hits[0] if len(deadline_hits) == 1 else None
    resolved_event = event_hits[0] if len(event_hits) == 1 else None

    # Ambiguous when either role is still unresolved after checking
    ambiguous = not (
        (resolved_deadline is not None or not deadline_hits) and
        (resolved_event is not None or not event_hits) and
        (resolved_deadline is not None or resolved_event is not None)
    )

    return {
        "event": resolved_event,
        "deadline": resolved_deadline,
        "ambiguous": ambiguous,
    }


def _resolve_index(value: Any, candidates: List[Dict[str, Any]]) -> Optional[int]:
    """
    Tolerantly map an LLM response value to a candidate index.
    Accepts int index directly, or a string matched against candidate matched_str.
    Never returns an index outside the candidate list.
    """
    if value is None:
        return None
    if isinstance(value, int):
        return value if 0 <= value < len(candidates) else None
    if isinstance(value, str):
        for i, c in enumerate(candidates):
            if c["matched_str"] == value:
                return i
    return None


def _call_ollama(candidates: List[Dict[str, Any]], title: str) -> Optional[Dict[str, Any]]:
    title_trunc = title[:100]
    top_candidates = candidates[:6]
    cand_lines = "\n".join(
        f"{i}: {c['matched_str']} | {c['context'][:80]}"
        for i, c in enumerate(top_candidates)
    )

    prompt = (
        f'Title: {title_trunc}\n'
        f'Dates:\n{cand_lines}\n'
        'Return JSON only: {"event": index or null, "deadline": index or null, "mode": "virtual"|"in_person"|"hybrid"|null}'
    )

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": _OLLAMA_FORMAT,
        "options": {
            "num_ctx": 1024,
            "num_predict": 60,
            "temperature": 0,
            "keep_alive": "30m",
        },
    }

    t0 = time.time()
    logger.info(f"Ollama prompt length: {len(prompt)} chars")

    def _do_request() -> Optional[Dict[str, Any]]:
        raw_response_text = ""
        try:
            resp = httpx.post(
                OLLAMA_URL,
                json=payload,
                timeout=httpx.Timeout(180.0, connect=10.0),
            )
            raw_response_text = resp.text if isinstance(resp.text, str) else str(resp.text)
            resp.raise_for_status()
            content = resp.json()["message"]["content"]

            start_idx = content.find("{")
            if start_idx == -1:
                raise ValueError("No '{' found in content")

            obj, _ = json.JSONDecoder().raw_decode(content[start_idx:])

            event_val = _resolve_index(obj.get("event"), top_candidates)
            deadline_val = _resolve_index(obj.get("deadline"), top_candidates)
            mode_raw = obj.get("mode")
            mode_val = mode_raw if mode_raw in ("virtual", "in_person", "hybrid") else None

            elapsed = time.time() - t0
            logger.info(f"Ollama call succeeded in {elapsed:.2f}s")
            return {"event": event_val, "deadline": deadline_val, "mode": mode_val}
        except (httpx.ConnectError, httpx.ConnectTimeout):
            raise  # Let caller handle retry
        except httpx.TimeoutException as e:
            elapsed = time.time() - t0
            logger.warning(f"Ollama timeout ({elapsed:.2f}s): {e}")
            return None
        except Exception as e:
            elapsed = time.time() - t0
            if raw_response_text:
                logger.debug(raw_response_text[:300])
            logger.warning(f"Ollama call/validation failed ({elapsed:.2f}s): {e}")
            return None

    try:
        return _do_request()
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        elapsed = time.time() - t0
        logger.warning(f"Ollama connection error ({elapsed:.2f}s): {e}; retrying once")
        try:
            return _do_request()
        except Exception as e2:
            elapsed2 = time.time() - t0
            logger.warning(f"Ollama retry also failed ({elapsed2:.2f}s): {e2}")
            return None


def extract_candidate_dates(text: str) -> List[Dict[str, Any]]:
    candidates = []
    seen = set()
    now = time.time()
    two_years_sec = 2 * 365 * 86400

    for match in DATE_REGEX.finditer(text):
        matched_str = match.group(0).strip()
        if not matched_str or matched_str not in text:
            continue

        parsed_dt = dateparser.parse(matched_str)
        if not parsed_dt:
            continue

        timestamp = parsed_dt.timestamp()
        if timestamp < (now - 86400) or timestamp > (now + two_years_sec):
            continue

        start_idx = max(0, match.start() - 60)
        end_idx = min(len(text), match.end() + 60)
        context = text[start_idx:end_idx].replace('\n', ' ')

        tz_match = re.search(r'\b(UTC|GMT|EST|EDT|PST|PDT|CST|CDT|MST|MDT|IST)\b', context)
        tz_text = tz_match.group(0) if tz_match else None

        cand_key = (matched_str, parsed_dt.isoformat())
        if cand_key in seen:
            continue
        seen.add(cand_key)

        candidates.append({
            "matched_str": matched_str,
            "parsed_iso": parsed_dt.isoformat(),
            "context": context,
            "tz_text": tz_text
        })
    return candidates


def _call_ollama(candidates: List[Dict[str, Any]], title: str) -> Optional[Dict[str, Any]]:
    title_trunc = title[:100]
    top_candidates = candidates[:6]
    cand_lines = "\n".join(
        f"{i}: {c['matched_str']} | {c['context'][:80]}"
        for i, c in enumerate(top_candidates)
    )

    prompt = (
        f'Title: {title_trunc}\n'
        f'Dates:\n{cand_lines}\n'
        'Return JSON only: {"event": index or null, "deadline": index or null, "mode": "virtual"|"in_person"|"hybrid"|null}'
    )

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {
            "num_ctx": 1024,
            "num_predict": 60,
            "temperature": 0,
            "keep_alive": "30m",
        },
    }

    t0 = time.time()
    logger.info(f"Ollama prompt length: {len(prompt)} chars")

    raw_response_text = ""
    try:
        resp = httpx.post(
            OLLAMA_URL,
            json=payload,
            timeout=httpx.Timeout(180.0, connect=10.0),
        )
        raw_response_text = resp.text if isinstance(resp.text, str) else str(resp.text)
        resp.raise_for_status()
        content = resp.json()["message"]["content"]

        start_idx = content.find("{")
        if start_idx == -1:
            raise ValueError("No '{' found in content")

        obj, _ = json.JSONDecoder().raw_decode(content[start_idx:])
        event_val = _resolve_index(obj.get("event"), top_candidates)
        deadline_val = _resolve_index(obj.get("deadline"), top_candidates)
        mode_raw = obj.get("mode")
        mode_val = mode_raw if mode_raw in ("virtual", "in_person", "hybrid") else None
        elapsed = time.time() - t0
        logger.info(f"Ollama call succeeded in {elapsed:.2f}s")
        return {"event": event_val, "deadline": deadline_val, "mode": mode_val}
    except (json.JSONDecodeError, ValueError) as e:
        elapsed = time.time() - t0
        logger.warning(f"Ollama invalid JSON ({elapsed:.2f}s): {e}; retrying once")
        # One retry for invalid JSON
        try:
            resp2 = httpx.post(
                OLLAMA_URL,
                json=payload,
                timeout=httpx.Timeout(180.0, connect=10.0),
            )
            content2 = resp2.json()["message"]["content"]
            start_idx2 = content2.find("{")
            if start_idx2 == -1:
                raise ValueError("No '{' found in retry content")
            obj2, _ = json.JSONDecoder().raw_decode(content2[start_idx2:])
            event_val2 = _resolve_index(obj2.get("event"), top_candidates)
            deadline_val2 = _resolve_index(obj2.get("deadline"), top_candidates)
            mode_raw2 = obj2.get("mode")
            mode_val2 = mode_raw2 if mode_raw2 in ("virtual", "in_person", "hybrid") else None
            elapsed2 = time.time() - t0
            logger.info(f"Ollama retry succeeded in {elapsed2:.2f}s")
            return {"event": event_val2, "deadline": deadline_val2, "mode": mode_val2}
        except Exception as e2:
            elapsed2 = time.time() - t0
            logger.warning(f"Ollama retry also failed ({elapsed2:.2f}s): {e2}")
            return None
    except httpx.TimeoutException as e:
        elapsed = time.time() - t0
        logger.warning(f"Ollama timeout ({elapsed:.2f}s): {e}")
        return None
    except Exception as e:
        elapsed = time.time() - t0
        if raw_response_text:
            logger.debug(raw_response_text[:300])
        logger.warning(f"Ollama call/validation failed ({elapsed:.2f}s): {e}")
        return None


def _extract_rewards(text_lower: str) -> Optional[str]:
    """Keyword-based rewards/prize extraction."""
    prize_keywords = ["prize", "credit", "reward", "cash", "grant"]
    has_money = bool(re.search(r'\$\s*[\d,]+', text_lower))
    if has_money or any(k in text_lower for k in prize_keywords):
        m = re.search(
            r'(?:prize|reward|grant|cash|credit)[^\n.]{0,80}',
            text_lower
        )
        if m:
            return m.group(0).strip()
        if has_money:
            m2 = re.search(r'\$\s*[\d,]+(?:\.\d+)?(?:\s*[a-z]+)?', text_lower)
            if m2:
                return m2.group(0).strip()
    return None


def _extract_entry_fee(text_lower: str) -> Optional[str]:
    """Keyword-based entry fee extraction."""
    if "free" in text_lower and any(k in text_lower for k in ["register", "entry", "admission", "join"]):
        return "free"
    m = re.search(r'\$\s*[\d,]+(?:\.\d+)?(?:\s*(?:usd|per\s+\w+|entry|registration))?', text_lower)
    if m:
        snippet = text_lower[max(0, m.start() - 30):m.end() + 30]
        if any(k in snippet for k in ["fee", "cost", "ticket", "register", "admission"]):
            return m.group(0).strip()
    return None


def extract_opportunity(result: Dict[str, Any], domain: str, category: str) -> Optional[Dict[str, Any]]:
    start_time = time.time()
    url = result.get("url", "")
    title = result.get("title", "")
    snippet = result.get("snippet", "")

    parsed_url = urlparse(url)

    # Pre-fetch rejection
    rejection_reason = _is_rejected_url(url)
    if rejection_reason:
        logger.info(f"Skipping URL ({rejection_reason}): {url}")
        return None

    if not has_topic_keyword(title, snippet, domain):
        logger.info(f"Skipping URL (missing topic keyword for {domain}): {url}")
        return None

    host = parsed_url.netloc.lower()
    source_dom = get_source_domain(url)

    fetch_failed = False
    text = ""
    if "linkedin.com" in host:
        text = f"{title}\n{snippet}"
    elif host in BLOCKED_FETCH:
        parsed_no_query = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
        logger.info(f"Host {host} is in BLOCKED_FETCH, skipping fetch for {parsed_no_query}.")
        fetch_failed = True
        text = f"{title}\n{snippet}"
    else:
        try:
            resp = httpx.get(url, timeout=10.0, follow_redirects=True)
            if resp.status_code == 403:
                BLOCKED_FETCH.add(host)
                fetch_failed = True
                text = f"{title}\n{snippet}"
            else:
                resp.raise_for_status()
                content_bytes = resp.content[:200000]
                soup = BeautifulSoup(content_bytes, "html.parser")
                for element in soup(["script", "style", "nav", "footer", "header"]):
                    element.decompose()
                text = soup.get_text(separator=" ", strip=True)
                text = text[:6000]
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 403:
                BLOCKED_FETCH.add(host)
            fetch_failed = True
            parsed_no_query = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
            logger.warning(f"Failed to fetch {parsed_no_query}: {e}")
            text = f"{title}\n{snippet}"
        except httpx.TimeoutException as e:
            fetch_failed = True
            parsed_no_query = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
            logger.warning(f"Failed to fetch {parsed_no_query}: {e}")
            text = f"{title}\n{snippet}"
        except Exception as e:
            fetch_failed = True
            parsed_no_query = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
            logger.warning(f"Failed to fetch {parsed_no_query}: {e}")
            text = f"{title}\n{snippet}"

    # about is always derived from snippet (25 words max)
    words = (snippet or "").split()
    about = " ".join(words[:25]) if words else None

    candidates = extract_candidate_dates(text) if (not fetch_failed and text) else []

    if os.getenv("DEBUG_DATES") == "1":
        print(f"Extracted text length: {len(text)} characters")
        print("Candidate dates found:")
        for c in candidates:
            print(f" - {c['matched_str']} (parsed: {c['parsed_iso']})")
            print(f"   Context: {c['context']}")

    text_lower = text.lower()

    if fetch_failed or not candidates:
        elapsed = time.time() - start_time
        parsed_no_query = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
        logger.info(f"Extracted opportunity (fallback) from {parsed_no_query} in {elapsed:.2f}s")
        return {
            "title": title,
            "url": url,
            "domain": domain,
            "category": category,
            "mode": None,
            "organization": None,
            "location": None,
            "about": about,
            "event_date_utc": None,
            "deadline_utc": None,
            "rewards": _extract_rewards(text_lower),
            "entry_fee": _extract_entry_fee(text_lower),
            "source_domain": source_dom,
            "verified": is_trusted(url),
            "dates_missing": True,
            "source_text_snippet": snippet
        }

    if os.getenv("DEBUG_DATES") == "1":
        return {
            "title": title,
            "url": url,
            "domain": domain,
            "category": category,
            "mode": None,
            "organization": None,
            "location": None,
            "about": about,
            "event_date_utc": None,
            "deadline_utc": None,
            "rewards": None,
            "entry_fee": None,
            "source_domain": source_dom,
            "verified": is_trusted(url),
            "dates_missing": True,
            "source_text_snippet": snippet
        }

    # Step 1: keyword-based code classification
    code_res = _classify_candidates(candidates)
    event_date_utc = None
    deadline_utc = None
    mode = None

    if code_res["event"] is not None:
        event_date_utc = candidates[code_res["event"]]["parsed_iso"]
    if code_res["deadline"] is not None:
        deadline_utc = candidates[code_res["deadline"]]["parsed_iso"]

    # Step 2: call Ollama only if a role is still ambiguous
    if code_res["ambiguous"]:
        llm_res = _call_ollama(candidates, title)
        if llm_res is None:
            llm_res = {"event": None, "deadline": None, "mode": None}

        # Fill in only the roles not already resolved by code
        if event_date_utc is None:
            e_idx = llm_res.get("event")
            if isinstance(e_idx, int) and 0 <= e_idx < len(candidates):
                event_date_utc = candidates[e_idx]["parsed_iso"]

        if deadline_utc is None:
            d_idx = llm_res.get("deadline")
            if isinstance(d_idx, int) and 0 <= d_idx < len(candidates):
                deadline_utc = candidates[d_idx]["parsed_iso"]

        mode = llm_res.get("mode")

    # Mode: LLM result validated by keyword safety net
    if mode:
        if not any(k in text_lower for k in ["virtual", "online", "in-person", "on-site", "hybrid"]):
            mode = None

    rewards = _extract_rewards(text_lower)
    entry_fee = _extract_entry_fee(text_lower)

    check_failed = False
    if deadline_utc and event_date_utc and deadline_utc > event_date_utc:
        check_failed = True

    verified = is_trusted(url) and not check_failed

    elapsed = time.time() - start_time
    parsed_no_query = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
    logger.info(f"Extracted opportunity from {parsed_no_query} in {elapsed:.2f}s")

    return {
        "title": title,
        "url": url,
        "domain": domain,
        "category": category,
        "mode": mode,
        "organization": None,
        "location": None,
        "about": about,
        "event_date_utc": event_date_utc,
        "deadline_utc": deadline_utc,
        "rewards": rewards,
        "entry_fee": entry_fee,
        "source_domain": source_dom,
        "verified": True if verified else False,
        "dates_missing": not (event_date_utc or deadline_utc),
        "source_text_snippet": snippet
    }


def save_opportunity(opp: Dict[str, Any]) -> Optional[int]:
    norm_url = normalize_url(opp.get("url", ""))
    if not norm_url:
        return None

    opp_copy = dict(opp)
    opp_copy["url"] = norm_url

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if os.getenv("DATABASE_URL", "").strip():
            query = """
            INSERT INTO opportunities (
                title, url, domain, category, mode, organization, location,
                about, event_date_utc, deadline_utc, rewards, entry_fee,
                source_domain, verified, dates_missing, source_text_snippet
            ) VALUES (
                %(title)s, %(url)s, %(domain)s, %(category)s, %(mode)s, %(organization)s, %(location)s,
                %(about)s, %(event_date_utc)s, %(deadline_utc)s, %(rewards)s, %(entry_fee)s,
                %(source_domain)s, %(verified)s, %(dates_missing)s, %(source_text_snippet)s
            ) ON CONFLICT (url) DO NOTHING RETURNING id;
            """
            cursor.execute(query, opp_copy)
            res = cursor.fetchone()
            conn.commit()
            return res["id"] if res else None
        else:
            query = """
            INSERT OR IGNORE INTO opportunities (
                title, url, domain, category, mode, organization, location,
                about, event_date_utc, deadline_utc, rewards, entry_fee,
                source_domain, verified, dates_missing, source_text_snippet
            ) VALUES (
                :title, :url, :domain, :category, :mode, :organization, :location,
                :about, :event_date_utc, :deadline_utc, :rewards, :entry_fee,
                :source_domain, :verified, :dates_missing, :source_text_snippet
            )
            """
            cursor.execute(query, opp_copy)
            conn.commit()
            return cursor.lastrowid if cursor.rowcount > 0 else None
    finally:
        conn.close()
