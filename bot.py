import asyncio, copy, json, logging, re, time
from pathlib import Path
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import ai, builders, gen, images, template

logging.basicConfig(level=logging.INFO)
DB, TPL, OUT = Path("data/users.json"), Path("data/tpl"), Path("data/out")
TPL.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
users = json.loads(DB.read_text()) if DB.exists() else {}


def U(uid):
    return users.setdefault(str(uid), {"lang": "uz", "rules": "", "tpl": {}, "profile": {}, "used": {}})


def save():
    DB.write_text(json.dumps(users, ensure_ascii=False, indent=1))


def day():
    return time.strftime("%Y-%m-%d")


def quota_ok(uid):
    return uid in ai.ADMINS or U(uid)["used"].get(day(), 0) < ai.DAILY_LIMIT


def use(uid):
    u = U(uid); u["used"] = {day(): u["used"].get(day(), 0) + 1}; save()


MENU = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text="📊 Taqdimot"), KeyboardButton(text="📘 Kurs ishi")],
    [KeyboardButton(text="📝 Mustaqil ish"), KeyboardButton(text="🧩 Kurs loyihasi")],
    [KeyboardButton(text="🔁 Namuna asosida")],
    [KeyboardButton(text="🧠 Vazifa bajarish"), KeyboardButton(text="📎 Shablon")],
    [KeyboardButton(text="🎓 AI qoidalari"), KeyboardButton(text="⚙️ Profil/Til")]])
KINDS = {"📊 Taqdimot": "pptx", "📘 Kurs ishi": "kurs", "📝 Mustaqil ish": "mustaqil", "🧩 Kurs loyihasi": "loyiha"}
SIZES = {"pptx": [8, 12, 16, 20], "kurs": [20, 30, 40], "mustaqil": [8, 12, 15], "loyiha": [20, 30, 40]}
UNIT = {"pptx": "slayd"}


class S(StatesGroup):
    topic = State(); edit = State(); rules = State(); task = State(); profile = State(); sample = State()


r = Router()


def safe(name):
    return re.sub(r"[^\w\- ]", "", name)[:50].strip() or "ish"


async def send_long(m: Message, text: str):
    for i in range(0, len(text), 3900):
        await m.answer(text[i:i + 3900])


@r.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear(); U(m.from_user.id); save()
    await m.answer(
        "Salom! 👋 Men akademik yordamchi botman:\n\n"
        "📊 Taqdimot (PPTX, so'zlash matni bilan)\n📘 Kurs ishi · 📝 Mustaqil ish · 🧩 Kurs loyihasi (DOCX, titul, mundarija, adabiyotlar)\n"
        "🧠 Istalgan vazifani bajarish\n📎 Shablon yuborsangiz — shunga o'xshash yarataman\n"
        "🎓 AI qoidalari — menga o'z talablaringizni tushuntiring\n\nBoshlash uchun tugmani tanlang 👇", reply_markup=MENU)


@r.message(F.text.in_(set(KINDS)))
async def pick_kind(m: Message, state: FSMContext):
    await state.clear()
    await state.update_data(kind=KINDS[m.text])
    await state.set_state(S.topic)
    await m.answer("Mavzuni yozing. Xohlasangiz talablarni ham qo'shing (masalan: «Mavzu: ..., faqat statistika bilan, 3-kurs»).")


@r.message(S.topic)
async def got_topic(m: Message, state: FSMContext):
    d = await state.update_data(topic=m.text)
    if d.get("sample"):
        res = await make_plan(m, m.from_user.id, d)
        if not res or isinstance(res, Message):
            return
        p, w = res
        await state.update_data(plan=p)
        return await w.edit_text("📋 Reja (namuna tuzilmasi asosida):\n\n" + gen.outline_text(p, d["kind"]) + "\n\nTasdiqlaysizmi?", reply_markup=review_kb())
    kb = InlineKeyboardBuilder()
    for n in SIZES[d["kind"]]:
        kb.button(text=f"{n} {UNIT.get(d['kind'], 'bet')}", callback_data=f"size:{n}")
    await m.answer("Hajmni tanlang:", reply_markup=kb.as_markup())


def review_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Boshlash", callback_data="go"); kb.button(text="✏️ O'zgartirish", callback_data="edit")
    return kb.as_markup()


async def make_plan(msg: Message, uid, d, change=None):
    if not quota_ok(uid):
        return await msg.answer(f"Bugungi limit ({ai.DAILY_LIMIT} ta) tugadi. Ertaga urinib ko'ring.")
    w = await msg.answer("⏳ Reja tuzilmoqda...")
    try:
        if d.get("sample"):
            p = await gen.plan_from_sample(d["sample"], d["topic"], U(uid), change, d.get("plan"))
        else:
            p = await gen.plan(d["kind"], d["topic"], d["n"], U(uid), change, d.get("plan"))
    except Exception as e:
        logging.exception(e); return await w.edit_text("❌ Xatolik yuz berdi, qayta urinib ko'ring.")
    return p, w


@r.callback_query(F.data.startswith("size:"))
async def size_cb(c: CallbackQuery, state: FSMContext):
    d = await state.update_data(n=int(c.data.split(":")[1]))
    await c.answer()
    res = await make_plan(c.message, c.from_user.id, d)
    if not res or isinstance(res, Message):
        return
    p, w = res
    await state.update_data(plan=p)
    await w.edit_text("📋 Reja:\n\n" + gen.outline_text(p, d["kind"]) + "\n\nTasdiqlaysizmi?", reply_markup=review_kb())


@r.callback_query(F.data == "edit")
async def edit_cb(c: CallbackQuery, state: FSMContext):
    await state.set_state(S.edit); await c.answer()
    await c.message.answer("Nimani o'zgartirish kerak? (masalan: «3-slaydni olib tashla, statistika qo'sh»)")


@r.message(S.edit)
async def edit_msg(m: Message, state: FSMContext):
    d = await state.get_data()
    res = await make_plan(m, m.from_user.id, d, change=m.text)
    if not res or isinstance(res, Message):
        return
    p, w = res
    await state.update_data(plan=p); await state.set_state(None)
    await w.edit_text("📋 Yangilangan reja:\n\n" + gen.outline_text(p, d["kind"]) + "\n\nTasdiqlaysizmi?", reply_markup=review_kb())


@r.callback_query(F.data == "go")
async def go_cb(c: CallbackQuery, state: FSMContext):
    await c.answer()
    d = await state.get_data(); uid = c.from_user.id; u = U(uid)
    if not d.get("plan"):
        return await c.message.answer("Avval mavzu tanlang.")
    if not quota_ok(uid):
        return await c.message.answer("Bugungi limit tugadi.")
    w = await c.message.answer("⚙️ Tayyorlanmoqda... (kurs ishi 2-5 daqiqa olishi mumkin)")
    try:
        kind, plan = d["kind"], d["plan"]
        base = OUT / f"{uid}_{int(time.time())}"
        tpl = d.get("sample_path") or (u["tpl"].get("pptx" if kind == "pptx" else "docx") or {}).get("path")
        if tpl and not Path(tpl).exists():
            tpl = None
        if kind == "pptx":
            plan = copy.deepcopy(plan)
            if not tpl:
                await w.edit_text("🖼 Rasmlar qidirilmoqda va dizayn yig'ilmoqda...")
                await images.attach(plan)
            f = f"{base}.pptx"; await asyncio.to_thread(builders.build_pptx, plan, f, tpl)
        else:
            blocks = await gen.expand_doc(plan, kind, d["n"], u)
            f = f"{base}.docx"; await asyncio.to_thread(builders.build_docx, plan, blocks, f, tpl, kind, u["profile"])
        use(uid)
        await c.message.answer_document(FSInputFile(f, filename=safe(plan["title"]) + Path(f).suffix),
                                        caption="✅ Tayyor! Word'da mundarijani yangilash uchun ochilganda «Ha» ni bosing. Adabiyotlarni albatta tekshiring.")
        await w.delete(); await state.clear()
    except Exception as e:
        logging.exception(e); await w.edit_text("❌ Tayyorlashda xatolik. Qayta urinib ko'ring.")


# ---- Namuna asosida ----
@r.message(F.text == "🔁 Namuna asosida")
async def sample_btn(m: Message, state: FSMContext):
    await state.clear(); await state.set_state(S.sample)
    await m.answer("Namuna kurs ishini (.docx) yuboring. Keyin yangi mavzu berasiz — men namunadagi tuzilma, hajm va rasmiylashtirish "
                   "asosida, lekin butunlay boshqa ma'lumotlar bilan yangi ish yozaman.")


@r.message(S.sample, F.document)
async def sample_doc(m: Message, state: FSMContext):
    if not (m.document.file_name or "").lower().endswith(".docx") or m.document.file_size > 20_000_000:
        return await m.answer("Faqat .docx (20 MB gacha) yuboring.")
    path = TPL / f"{m.from_user.id}_sample.docx"
    await m.bot.download(m.document, destination=path)
    try:
        st = await asyncio.to_thread(template.structure, str(path))
    except Exception:
        return await m.answer("Faylni o'qib bo'lmadi.")
    body = [i for i in st["items"] if not template.is_special(i["title"])]
    if not body:
        return await m.answer("Sarlavhalarni aniqlab bo'lmadi. Word'da sarlavhalar «Heading» uslubida bo'lsa yaxshi.")
    n = max(5, round(st["total_words"] / 270))
    await state.update_data(sample=st, sample_path=str(path), kind=st["kind"], n=n)
    await state.set_state(S.topic)
    await m.answer(f"✅ Namuna o'qildi: {len(body)} ta sarlavha, ~{st['total_words']} so'z (≈{n} bet).\n\nEndi yangi mavzuni yozing:")


# ---- Shablon ----
@r.message(F.text == "📎 Shablon")
async def tpl_info(m: Message, state: FSMContext):
    await state.clear()
    t = U(m.from_user.id)["tpl"]
    await m.answer("PPTX yoki DOCX shablon faylini yuboring — tuzilmasi va uslubini o'rganaman.\n"
                   f"Hozir: {', '.join(t) or 'yo\'q'}. O'chirish: /notpl")


@r.message(F.document)
async def got_doc(m: Message):
    ext = (m.document.file_name or "").lower().rsplit(".", 1)[-1]
    if ext not in ("pptx", "docx") or m.document.file_size > 20_000_000:
        return await m.answer("Faqat .pptx yoki .docx (20 MB gacha) qabul qilinadi.")
    path = TPL / f"{m.from_user.id}.{ext}"
    await m.bot.download(m.document, destination=path)
    try:
        info = await asyncio.to_thread(template.analyze, str(path))
    except Exception:
        return await m.answer("Faylni o'qib bo'lmadi.")
    U(m.from_user.id)["tpl"][ext] = {"path": str(path), "info": info[:3000]}; save()
    await m.answer(f"✅ {ext.upper()} shablon saqlandi. Endi {'taqdimotlar' if ext == 'pptx' else 'hujjatlar'} shu uslubda yaratiladi.")


@r.message(Command("notpl"))
async def notpl(m: Message):
    U(m.from_user.id)["tpl"] = {}; save(); await m.answer("Shablonlar o'chirildi.")


# ---- AI qoidalari ----
@r.message(F.text == "🎓 AI qoidalari")
async def rules_btn(m: Message, state: FSMContext):
    await state.set_state(S.rules)
    await m.answer(f"Hozirgi qoidalar: {U(m.from_user.id)['rules'] or 'yo\'q'}\n\nYangi qoidalarni yozing "
                   "(masalan: «Oddiy tilda yoz, har bobda amaliy misol bo'lsin, 14 shrift»). O'chirish: /norules")


@r.message(S.rules)
async def rules_set(m: Message, state: FSMContext):
    U(m.from_user.id)["rules"] = m.text[:1500]; save(); await state.clear(); await m.answer("✅ Qoidalar saqlandi.")


@r.message(Command("norules"))
async def norules(m: Message):
    U(m.from_user.id)["rules"] = ""; save(); await m.answer("Qoidalar o'chirildi.")


# ---- Profil / Til ----
@r.message(F.text == "⚙️ Profil/Til")
async def prof_btn(m: Message, state: FSMContext):
    await state.set_state(S.profile)
    kb = InlineKeyboardBuilder()
    for k, v in (("uz", "🇺🇿 O'zbekcha"), ("ru", "🇷🇺 Русский"), ("en", "🇬🇧 English")):
        kb.button(text=v, callback_data=f"lang:{k}")
    await m.answer("Tilni tanlang. Titul varag'i uchun yozing:\nIsm | Universitet | Fakultet | O'qituvchi | Shahar", reply_markup=kb.as_markup())


@r.callback_query(F.data.startswith("lang:"))
async def lang_cb(c: CallbackQuery):
    U(c.from_user.id)["lang"] = c.data[5:]; save(); await c.answer("Saqlandi ✅")


@r.message(S.profile)
async def prof_set(m: Message, state: FSMContext):
    k = ["name", "university", "faculty", "teacher", "city"]
    parts = [x.strip() for x in m.text.split("|")]
    U(m.from_user.id)["profile"] = {a: b for a, b in zip(k, parts) if b}; save()
    await state.clear(); await m.answer("✅ Profil saqlandi.")


# ---- Vazifa ----
@r.message(F.text == "🧠 Vazifa bajarish")
async def task_btn(m: Message, state: FSMContext):
    await state.clear(); await state.set_state(S.task)
    await m.answer("Vazifani yozing (masalan: «Marketingning 4P modeli bo'yicha esse yoz», «Quyidagi masalani yech...»). Chiqish uchun menyudan tanlang.")


@r.message(S.task)
async def task_run(m: Message):
    uid = m.from_user.id
    if not quota_ok(uid):
        return await m.answer("Bugungi limit tugadi.")
    w = await m.answer("⏳ Bajarilmoqda...")
    try:
        text = await ai.ask(m.text, gen.system(U(uid), "task"), 6000)
        use(uid); await w.delete()
        if len(text) <= 3900:
            return await m.answer(text)
        f = OUT / f"{uid}_{int(time.time())}.docx"
        blocks = [{"t": "p", "x": p} for p in text.split("\n\n") if p.strip()]
        await asyncio.to_thread(builders.build_docx, {"title": "Vazifa"}, blocks, str(f), None, "task", {})
        await m.answer_document(FSInputFile(f, filename="vazifa.docx"))
    except Exception as e:
        logging.exception(e); await w.edit_text("❌ Xatolik, qayta urinib ko'ring.")


async def main():
    bot = Bot(ai.BOT_TOKEN); dp = Dispatcher(); dp.include_router(r)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
