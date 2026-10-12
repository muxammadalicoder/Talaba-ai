import re
import asyncio, json
import ai
from ai import ask, ask_json
from template import is_special

LANG = {"uz": "o'zbek (lotin)", "ru": "rus", "en": "ingliz"}
HINT = {
    "kurs": "Kurs ishi: 2-3 bob, har bobda 2-3 bo'lim (nazariy asos, tahlil, amaliy qism/takliflar).",
    "mustaqil": "Mustaqil ish: 1-2 bob, har bobda 2-3 bo'lim, ixcham va aniq.",
    "loyiha": "Kurs loyihasi: maqsad va vazifalar, mavjud yechimlar tahlili, loyiha/tizim tavsifi, amaliy bajarilishi, natijalar va baholash.",
}


def system(u, fmt):
    s = (f"Sen tajribali akademik muallif va taqdimot dizaynerisan. Barcha matnni {LANG[u.get('lang', 'uz')]} tilida yoz. "
         "Faktlar, raqamlar va iqtiboslarni to'qima; ishonching komil bo'lmasa umumiy yoz. "
         "Matn original, ilmiy-uslubda, takrorsiz va mantiqiy izchil bo'lsin.")
    if u.get("rules"):
        s += "\nFOYDALANUVCHI QOIDALARI (qat'iy bajar): " + u["rules"]
    t = u.get("tpl", {}).get(fmt)
    if t:
        s += ("\nSHABLON TUZILMASI (bo'lim nomlari, tartib va uslubga amal qil, mazmunini ko'chirma): " + t["info"])
    return s


_cache = {}


async def research(topic, u):
    """Veb-qidiruv orqali haqiqiy faktlar va manbalar yig'adi (RESEARCH=1 bo'lsa)."""
    if not ai.RESEARCH:
        return ""
    k = (topic, u.get("lang"))
    if k not in _cache:
        try:
            _cache[k] = await ask(
                f"Mavzu va talablar: {topic}\nVeb-qidiruv orqali ishonchli manbalardan (rasmiy saytlar, universitetlar, ilmiy nashrlar, "
                "statistika organlari) shu mavzu bo'yicha 20-30 ta aniq fakt yig': raqamlar, sanalar, statistika, ta'riflar, misollar, nazariyalar. "
                "Har faktdan keyin manba nomi va URL yoz. Oxirida «MANBALAR:» ro'yxati. Hech narsani to'qima.",
                system(u, "none"), 5000, search=True)
        except Exception:
            _cache[k] = ""
    return _cache[k]


async def plan(kind, topic, n, u, change=None, old=None):
    notes = await research(topic, u)
    extra = ""
    if change:
        extra = (f"\n\nOldingi reja:\n{json.dumps(old, ensure_ascii=False)}\n"
                 f"Uni quyidagi izohga ko'ra o'zgartir: {change}")
    if kind == "pptx":
        p = (f"Mavzu va talablar: {topic}\n\nTADQIQOT MA'LUMOTLARI (faktlar, raqamlar, manbalar; asosan shulardan foydalan, to'qima):\n{notes[:6000]}\n\n"
             f"Titul slaydidan tashqari aynan {n} ta slayd tayyorla. Talablar:\n"
             "- Mazmun boy va aniq: har slaydda 4-6 tezis, har biri 12-22 so'z, konkret fakt/raqam/sana/misol bilan (umumiy gaplar emas).\n"
             "- Slaydlar turli xil bo'lsin: layout = text | stat | chart | process | two_col. process faqat bosqichlar uchun (3-5 tezis), "
             "two_col taqqoslash uchun (4+ tezis), stat bitta muhim raqam uchun, chart faqat tadqiqotdagi HAQIQIY raqamlar bo'lsa. "
             "stat va chart kalitlarini faqat kerak bo'lganda qo'y.\n"
             "- Slaydlarning kamida yarmida \"image\": rasm uchun 2-4 so'zli aniq INGLIZCHA qidiruv so'rovi (masalan \"solar panels field\").\n"
             "- \"notes\": 5-8 gaplik batafsil so'zlab berish matni.\n"
             "- Oxirgi slayd: xulosa. \"theme\": navy|emerald|crimson|violet (mavzuga mosini tanla). \"cover_image\": titul uchun inglizcha so'rov. "
             "\"sources\": tadqiqotdagi 5-8 ta asosiy manba (sarlavha, URL).\n"
             '{"title":"","subtitle":"","theme":"navy","cover_image":"","sources":[""],"slides":[{"title":"","layout":"text","bullets":[""],"image":"","notes":""}]}' + extra)
        return await ask_json(p, system(u, "pptx"))
    p = (f"Mavzu va talablar: {topic}\nHajm: taxminan {n} bet. {HINT[kind]}\n"
         f"Tadqiqot ma'lumotlari:\n{notes[:3000]}\n"
         "Kirish, xulosa va adabiyotlarni reja ichiga qo'shma (ular avtomatik qo'shiladi).\n"
         '{"title":"Ishning to\'liq nomi","chapters":[{"title":"","sections":["",""]}]}' + extra)
    res = await ask_json(p, system(u, "docx"))
    res["topic"] = topic
    return res


async def plan_from_sample(st, topic, u, change=None, old=None):
    body = [i for i in st["items"] if not is_special(i["title"])]
    desc = "\n".join(("    " if i["level"] == 2 else "") + f"{i['title']} (~{i['words']} so'z)" for i in body)
    extra = ""
    if change:
        extra = (f"\n\nOldingi reja:\n{json.dumps(old, ensure_ascii=False)}\nUni quyidagi izohga ko'ra o'zgartir: {change}")
    p = (f"Yangi mavzu va talablar: {topic}\n\nNAMUNA ISHNING asosiy qism tuzilmasi:\n{desc}\n\n"
         "Yangi ish uchun AYNAN shu tuzilmani (boblar va bo'limlar soni, tartibi, mantiqiy vazifasi) saqla, lekin sarlavhalarni yangi mavzuga "
         "moslab to'liq yangila; namunadagi nomlarni ko'chirma. Namunada bo'limsiz bob bo'lsa, sections bo'sh ro'yxat bo'lsin. "
         "Kirish, xulosa va adabiyotlarni qo'shma.\n"
         '{"title":"Ishning to\'liq nomi","chapters":[{"title":"","sections":["",""]}]}' + extra)
    res = await ask_json(p, system(u, "none"))
    res["wps"] = st.get("wps", 300)
    res["topic"] = topic
    return res


def outline_text(plan_, kind):
    if kind == "pptx":
        return "\n".join(f"{i}. {s['title']}" for i, s in enumerate(plan_["slides"], 1))
    out = []
    for i, c in enumerate(plan_["chapters"], 1):
        out.append(f"{i}-bob. {c['title']}")
        out += [f"   {i}.{j}. {s}" for j, s in enumerate(c["sections"], 1)]
    return "\n".join(out)


async def expand_doc(plan_, kind, pages, u):
    sysm = system(u, "docx")
    topic = plan_["title"]
    outline = outline_text(plan_, kind)
    notes = await research(plan_.get("topic", topic), u)
    secs = sum(max(1, len(c["sections"])) for c in plan_["chapters"]) + 2
    words = plan_.get("wps") or max(180, pages * 270 // secs)
    base = f"Ish mavzusi: {topic}\nUmumiy reja:\n{outline}\n\nTadqiqot ma'lumotlari (faktlar va manbalar; foydalan, to'qima):\n{notes[:5000]}\n\n"
    rule = ("Faqat so'ralgan bo'lim matnini yoz: sarlavhasiz, Markdown belgilarsiz, abzaclarni bo'sh qator bilan ajrat. "
            "Zarur bo'lsa ro'yxat elementlarini '- ' bilan boshla.")
    jobs = [("h1", "KIRISH", base + f"KIRISH qismini yoz: mavzuning dolzarbligi, maqsad, vazifalar, ob'ekt va predmet, tuzilma. ~{words} so'z. " + rule)]
    for i, c in enumerate(plan_["chapters"], 1):
        if not c["sections"]:
            jobs.append(("h1", f"{i}-bob. {c['title']}", base + f"{i}-bob \"{c['title']}\" matnini yoz. ~{words} so'z. " + rule))
            continue
        jobs.append(("h1", f"{i}-bob. {c['title']}", None))
        for j, s in enumerate(c["sections"], 1):
            jobs.append(("h2", f"{i}.{j}. {s}",
                         base + f"{i}-bob \"{c['title']}\", {i}.{j} bo'limi \"{s}\" matnini yoz. ~{words} so'z. Boshqa bo'limlarni takrorlama. " + rule))
    jobs.append(("h1", "XULOSA", base + f"XULOSA yoz: asosiy natijalar va takliflar. ~{words} so'z. " + rule))
    jobs.append(("h1", "FOYDALANILGAN ADABIYOTLAR",
                 base + "Mavzuga oid 12-15 ta adabiyot ro'yxatini ber (darslik, qonun, rasmiy sayt). Avvalo tadqiqotdagi MANBALAR dan (URL bilan), so'ng mavjudligiga ishongan darslik va qonunlardan tanla. "
                        "Har biri alohida qatorda, raqamsiz, GOST/APA shaklida."))
    res = await asyncio.gather(*[ask(j[2], sysm, 3000) if j[2] else asyncio.sleep(0, "") for j in jobs])
    blocks = []
    for (t, head, _), text in zip(jobs, res):
        blocks.append({"t": t, "x": head})
        if head.startswith("FOYDALANILGAN"):
            blocks += [{"t": "ref", "x": ln.strip().lstrip("-0123456789. ").strip()} for ln in text.splitlines() if ln.strip()]
        elif text:
            blocks += [{"t": "p", "x": p.strip()} for p in text.split("\n\n") if p.strip()]
    return blocks
