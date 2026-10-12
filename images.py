import asyncio, io
import httpx
from PIL import Image
from ai import PEXELS_KEY

H = {"User-Agent": "StudyBot/1.0 (educational project)"}
_sem = asyncio.Semaphore(5)


def _ok(data: bytes) -> bool:
    try:
        Image.open(io.BytesIO(data)).verify()
        return 2_000 < len(data) < 8_000_000
    except Exception:
        return False


async def _get(c, url, **kw):
    r = await c.get(url, **kw)
    r.raise_for_status()
    return r


async def fetch(q: str):
    """(bayt, muallif) yoki None. Avval Pexels (kalit bo'lsa), keyin Wikimedia Commons."""
    async with _sem, httpx.AsyncClient(timeout=15, follow_redirects=True, headers=H) as c:
        if PEXELS_KEY:
            try:
                j = (await _get(c, "https://api.pexels.com/v1/search", headers={"Authorization": PEXELS_KEY},
                                params={"query": q, "per_page": 3, "orientation": "landscape"})).json()
                for p in j.get("photos", []):
                    d = (await _get(c, p["src"]["large"])).content
                    if _ok(d):
                        return d, f"{p['photographer']} / Pexels"
            except Exception:
                pass
        try:
            j = (await _get(c, "https://commons.wikimedia.org/w/api.php", params={
                "action": "query", "generator": "search", "gsrnamespace": 6, "gsrsearch": q, "gsrlimit": 6,
                "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": 1280, "format": "json"})).json()
            for pg in j.get("query", {}).get("pages", {}).values():
                ii = pg["imageinfo"][0]
                if ii.get("mime") in ("image/jpeg", "image/png"):
                    d = (await _get(c, ii["thumburl"])).content
                    if _ok(d):
                        return d, "Wikimedia Commons"
        except Exception:
            pass
    return None


async def attach(plan: dict):
    """Reja ichiga rasmlarni biriktiradi: plan['_cover'], slide['_img']."""
    jobs = [(None, plan.get("cover_image"))] + [(s, s.get("image")) for s in plan["slides"]]
    res = await asyncio.gather(*[fetch(q) if q else asyncio.sleep(0, None) for _, q in jobs])
    for (s, _), r in zip(jobs, res):
        if r:
            if s is None:
                plan["_cover"] = r
            else:
                s["_img"] = r
