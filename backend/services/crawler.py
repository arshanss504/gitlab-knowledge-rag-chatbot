import asyncio
import re
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from backend.core.logging import get_logger
from backend.utils.text import clean_text, content_hash

logger = get_logger(__name__)

_NOISE_SELECTORS = [
    "nav", "header", "footer", "aside",
    ".sidebar", ".nav", ".navigation", ".menu", ".breadcrumb",
    ".cookie-banner", ".announcement-banner", "#cookie-consent",
    "script", "style", "noscript", "svg",
]

_ALLOWED_DOMAINS = {"handbook.gitlab.com", "about.gitlab.com", "docs.gitlab.com"}

_MAX_PAGES = 50
_DELAY_SECONDS = 1.0
_TIMEOUT_SECONDS = 30


@dataclass
class CrawledPage:
    url: str
    title: str
    text: str
    sections: list[dict]
    content_hash: str
    source_domain: str
    metadata: dict = field(default_factory=dict)


def _is_allowed_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.netloc in _ALLOWED_DOMAINS and parsed.scheme in ("http", "https")
    except Exception:
        return False


def _extract_sections(soup: BeautifulSoup, base_url: str) -> list[dict]:
    sections = []
    current_heading = "Introduction"
    current_level = 1
    current_anchor = ""
    current_texts = []

    def flush():
        nonlocal current_texts
        text = clean_text(" ".join(current_texts))
        if text:
            sections.append({
                "heading": current_heading,
                "level": current_level,
                "text": text,
                "anchor": current_anchor,
                "url": f"{base_url}#{current_anchor}" if current_anchor else base_url,
            })
        current_texts = []

    content_area = (
        soup.find("main")
        or soup.find(id="content")
        or soup.find(class_=re.compile(r"content|main|article", re.I))
        or soup.body
    )
    if not content_area:
        return sections

    for element in content_area.descendants:
        if not isinstance(element, Tag):
            continue

        tag = element.name
        if tag in ("h1", "h2", "h3", "h4"):
            flush()
            current_heading = element.get_text(separator=" ").strip()
            current_level = int(tag[1])
            current_anchor = element.get("id", "")
        elif tag in ("p", "li", "td", "dt", "dd", "blockquote"):
            text = element.get_text(separator=" ").strip()
            if text:
                current_texts.append(text)

    flush()
    return sections


class GitLabCrawler:
    def __init__(self, known_hashes: Optional[dict[str, str]] = None):
        self._delay = _DELAY_SECONDS
        self._timeout = _TIMEOUT_SECONDS
        self._max_pages = _MAX_PAGES
        self._known_hashes = known_hashes or {}

    async def crawl(
        self, start_urls: list[str]
    ) -> AsyncIterator[Optional[CrawledPage]]:
        visited: Set[str] = set()
        queue: asyncio.Queue[str] = asyncio.Queue()
        pages_crawled = 0

        for url in start_urls:
            await queue.put(url)

        headers = {
            "User-Agent": (
                "GitLabRAGBot/1.0 (research crawler; "
                "contact: your-email@example.com)"
            ),
            "Accept": "text/html,application/xhtml+xml",
        }

        async with httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=True,
            headers=headers,
        ) as client:
            while not queue.empty() and pages_crawled < self._max_pages:
                url = await queue.get()
                url = url.split("#")[0]

                if url in visited or not _is_allowed_url(url):
                    continue
                visited.add(url)

                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning("Non-200 response", url=url, status=resp.status_code)
                        continue

                    html = resp.text
                    pages_crawled += 1

                    chash = content_hash(html)
                    if self._known_hashes.get(url) == chash:
                        logger.debug("Skipping unchanged page", url=url)
                        yield None
                        await asyncio.sleep(self._delay)
                        continue

                    page = self._parse(url, html, chash)
                    if page and len(page.text) > 100:
                        logger.info(
                            "Crawled page",
                            url=url,
                            title=page.title,
                            sections=len(page.sections),
                        )
                        yield page

                        for link_url in self._extract_links(html, url):
                            if link_url not in visited:
                                await queue.put(link_url)

                except httpx.TimeoutException:
                    logger.warning("Timeout crawling URL", url=url)
                except Exception as exc:
                    logger.error("Error crawling URL", url=url, error=str(exc))

                await asyncio.sleep(self._delay)

        logger.info("Crawl complete", pages_crawled=pages_crawled)

    def _parse(self, url: str, html: str, chash: str) -> Optional[CrawledPage]:
        soup = BeautifulSoup(html, "lxml")

        for selector in _NOISE_SELECTORS:
            for el in soup.select(selector):
                el.decompose()

        title = ""
        if soup.title:
            title = soup.title.get_text().strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text().strip()

        sections = _extract_sections(soup, url)
        full_text = "\n\n".join(
            f"{s['heading']}\n{s['text']}" for s in sections if s["text"]
        )
        full_text = clean_text(full_text)

        parsed = urlparse(url)
        return CrawledPage(
            url=url,
            title=title,
            text=full_text,
            sections=sections,
            content_hash=chash,
            source_domain=parsed.netloc,
            metadata={"title": title, "domain": parsed.netloc},
        )

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            full_url = urljoin(base_url, href).split("#")[0]
            if _is_allowed_url(full_url):
                links.append(full_url)
        return links
