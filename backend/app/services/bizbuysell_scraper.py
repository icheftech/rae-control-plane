"""BizBuySell listing scraper.

Fetches and parses financial data from a BizBuySell listing URL.
Returns best-effort results — fields may be None if not found.
"""

import json
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel


class ScrapedListing(BaseModel):
    success: bool
    error: Optional[str] = None
    title: str = ""
    asking_price: Optional[float] = None
    revenue: Optional[float] = None
    cash_flow: Optional[float] = None
    ebitda: Optional[float] = None
    ffe: Optional[float] = None
    inventory: Optional[float] = None
    location: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Maps label text → ScrapedListing field name
_LABEL_MAP = {
    "asking price": "asking_price",
    "listing price": "asking_price",
    "price": "asking_price",
    "cash flow": "cash_flow",
    "sde": "cash_flow",
    "seller's discretionary earnings": "cash_flow",
    "gross revenue": "revenue",
    "gross sales": "revenue",
    "revenue": "revenue",
    "annual revenue": "revenue",
    "ebitda": "ebitda",
    "ff&e": "ffe",
    "furniture, fixtures & equipment": "ffe",
    "inventory": "inventory",
}


def _parse_currency(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", "").strip())
    # Handle abbreviated values like "276K" or "186K"
    multiplier = 1
    if "k" in text.lower():
        multiplier = 1_000
    elif "m" in text.lower():
        multiplier = 1_000_000
    try:
        return float(cleaned) * multiplier if cleaned else None
    except ValueError:
        return None


def _try_label_map(soup: BeautifulSoup, listing: ScrapedListing) -> None:
    """Scan all text nodes looking for known label/value pairs."""
    # Strategy 1: <dt>/<dd> definition lists
    for dt in soup.find_all("dt"):
        label = dt.get_text(strip=True).lower().rstrip(":")
        field = _LABEL_MAP.get(label)
        if not field:
            continue
        dd = dt.find_next_sibling("dd")
        if dd and not getattr(listing, field):
            setattr(listing, field, _parse_currency(dd.get_text(strip=True)))

    # Strategy 2: table <td> label/value pairs
    for td in soup.find_all("td"):
        label = td.get_text(strip=True).lower().rstrip(":")
        field = _LABEL_MAP.get(label)
        if not field:
            continue
        next_td = td.find_next_sibling("td")
        if next_td and not getattr(listing, field):
            setattr(listing, field, _parse_currency(next_td.get_text(strip=True)))

    # Strategy 3: any element whose text matches a label, followed by a sibling
    for tag in soup.find_all(["span", "div", "p", "li", "strong", "b"]):
        label = tag.get_text(strip=True).lower().rstrip(":")
        field = _LABEL_MAP.get(label)
        if not field:
            continue
        sibling = tag.find_next_sibling()
        if sibling and not getattr(listing, field):
            setattr(listing, field, _parse_currency(sibling.get_text(strip=True)))


def _try_regex_fallback(text: str, listing: ScrapedListing) -> None:
    """Last-resort regex scan across raw page text."""
    patterns = {
        "asking_price": [
            r"[Aa]sking\s+[Pp]rice[^\$\d]*\$?([\d,]+)",
            r"[Ll]isting\s+[Pp]rice[^\$\d]*\$?([\d,]+)",
        ],
        "cash_flow": [
            r"[Cc]ash\s+[Ff]low[^\$\d]*\$?([\d,]+)",
            r"SDE[^\$\d]*\$?([\d,]+)",
        ],
        "revenue": [
            r"[Gg]ross\s+[Rr]evenue[^\$\d]*\$?([\d,]+)",
            r"[Gg]ross\s+[Ss]ales[^\$\d]*\$?([\d,]+)",
            r"[Aa]nnual\s+[Rr]evenue[^\$\d]*\$?([\d,]+)",
        ],
    }
    for field, pats in patterns.items():
        if getattr(listing, field):
            continue
        for pat in pats:
            m = re.search(pat, text)
            if m:
                val = _parse_currency(m.group(1))
                if val:
                    setattr(listing, field, val)
                    break


def _try_json_ld(soup: BeautifulSoup, listing: ScrapedListing) -> None:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0] if data else {}
            offers = data.get("offers", {})
            price = offers.get("price") or data.get("price")
            if price and not listing.asking_price:
                listing.asking_price = _parse_currency(str(price))
            name = data.get("name") or data.get("headline")
            if name and not listing.title:
                listing.title = str(name)
        except Exception:
            pass


async def scrape_bizbuysell_listing(url: str) -> ScrapedListing:
    listing = ScrapedListing(success=False)

    try:
        async with httpx.AsyncClient(
            timeout=20.0, follow_redirects=True, headers=_HEADERS
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        listing.error = f"HTTP {e.response.status_code} — site may be blocking automated requests. Please fill in values manually."
        return listing
    except httpx.TimeoutException:
        listing.error = "Request timed out. Please fill in values manually."
        return listing
    except Exception as e:
        listing.error = f"Could not reach URL: {e}. Please fill in values manually."
        return listing

    listing.success = True
    soup = BeautifulSoup(response.text, "lxml")

    # Title
    h1 = soup.find("h1")
    if h1:
        listing.title = h1.get_text(strip=True)

    # Location — common patterns on BizBuySell
    for selector in ["span.address", "span.location", "[class*='location']", "[class*='city']"]:
        loc = soup.select_one(selector)
        if loc:
            listing.location = loc.get_text(strip=True)
            break

    # Industry
    for selector in ["[class*='category']", "[class*='industry']", "a[href*='/businesses-for-sale/']"]:
        ind = soup.select_one(selector)
        if ind:
            listing.industry = ind.get_text(strip=True)
            break

    # Description
    for selector in ["[class*='description']", "[class*='summary']", "#description"]:
        desc = soup.select_one(selector)
        if desc:
            listing.description = desc.get_text(strip=True)[:500]
            break

    _try_json_ld(soup, listing)
    _try_label_map(soup, listing)
    _try_regex_fallback(response.text, listing)

    # If nothing was parsed, the site likely blocked us
    if not any([listing.asking_price, listing.revenue, listing.cash_flow]):
        listing.error = (
            "Could not extract financial data — site may require a browser. "
            "Values have been left blank for manual entry."
        )

    return listing
