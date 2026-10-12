import asyncio, json, os, re
from dotenv import load_dotenv
from anthropic import AsyncAnthropic

load_dotenv()
BOT_TOKEN = os.environ["BOT_TOKEN"]
MODEL = os.getenv("MODEL", "claude-sonnet-5-5")
PEXELS_KEY = os.getenv("PEXELS_KEY", "")
RESEARCH = os.getenv("RESEARCH", "1") == "1"
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "5"))
ADMINS = {int(x) for x in os.getenv("ADMINS", "").split(",") if x.strip()}

_client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
_sem = asyncio.Semaphore(4)


async def ask(prompt: str, system: str = "", max_tokens: int = 4000, search: bool = False) -> str:
    kw = {"tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}]} if search else {}
    for attempt in range(3):
        try:
            async with _sem:
                r = await _client.messages.create(
                    model=MODEL, max_tokens=max_tokens, system=system,
                    messages=[{"role": "user", "content": prompt}], **kw)
            return "".join(b.text for b in r.content if b.type == "text").strip()
        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(2 * (attempt + 1))


async def ask_json(prompt: str, system: str = "") -> dict:
    for _ in range(2):
        t = await ask(prompt + "\n\nFaqat to'g'ri JSON qaytar, boshqa matn yozma.", system, 12000)
        m = re.search(r"\{.*\}", t, re.S)
        try:
            return json.loads(m.group(0))
        except Exception:
            continue
    raise ValueError("AI JSON qaytara olmadi")
