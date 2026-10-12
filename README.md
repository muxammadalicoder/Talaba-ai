# StudyBot — taqdimot, kurs ishi, kurs loyihasi, mustaqil ish boti (Telegram)

## Ishga tushirish
1. `pip install -r requirements.txt`
2. `.env.example` ni `.env` ga nusxalang: @BotFather dan `BOT_TOKEN`, Anthropic konsolidan `ANTHROPIC_API_KEY`, o'zingizning Telegram ID'ingizni `ADMINS` ga yozing (limitsiz).
3. `python bot.py`

## Imkoniyatlar
- Taqdimot (PPTX): zamonaviy dizayn, har slaydga so'zlab berish matni (notes)
- Kurs ishi / mustaqil ish / kurs loyihasi (DOCX): titul, avtomatik mundarija, sahifa raqami, kirish-bob-xulosa, adabiyotlar, Times New Roman 14, 1.5 interval
- Reja avval ko'rsatiladi: ✅ tasdiqlash yoki ✏️ o'zgartirish (iterativ)
- Shablon (PPTX/DOCX) yuborish: tuzilma va uslub o'rganiladi, hujjat shu shablon ustida yaratiladi
- 🎓 AI qoidalari: doimiy ko'rsatmalar (uslub, murakkablik, talablar)
- 🧠 Vazifa bajarish: esse, masala, tushuntirish; uzun javob DOCX bo'lib keladi
- Profil (titul uchun), 3 til (uz/ru/en), kunlik limit, admin rejimi

## Namuna asosida
🔁 tugmasi: namuna .docx yuborasiz → yangi mavzu yozasiz → bot namunadagi boblar soni, tartibi, hajmi va rasmiylashtirishni saqlab, yangi ma'lumotlar bilan yozadi (matnni ko'chirmaydi).

## Muhim
- Adabiyotlar ro'yxatini AI tuzadi — har bir manbani tekshiring.
- Word birinchi ochilganda mundarijani yangilash so'raydi: «Ha» ni bosing.
- Tayyor ishni o'zingiz o'qib, tahrirlang va topshiring.

## Keyingi qadamlar (qo'shish mumkin)
Rasm/diagramma qo'shish, to'lov va obuna, antiplagiat tekshiruvi, PDF eksport, bo'limni alohida qayta yozish, veb-admin panel.

## Serverga joylash (Ubuntu VPS)
```
apt update && apt install -y python3-venv unzip
mkdir -p /opt && cd /opt && unzip ~/studybot.zip && cd studybot
python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt
cp .env.example .env && nano .env      # kalitlarni yozing
python bot.py                          # sinab ko'ring, Ctrl+C
cp studybot.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now studybot
journalctl -u studybot -f              # loglar
```
Yangilash: fayllarni almashtirib `systemctl restart studybot`.

## Rasm va tadqiqot sozlamalari
- `PEXELS_KEY` — pexels.com/api dan bepul kalit (rasmlar uchun). Bo'sh bo'lsa Wikimedia Commons ishlatiladi (sifati va mosligi pastroq).
- `RESEARCH=1` — AI veb-qidiruv orqali haqiqiy fakt va manbalarni yig'adi (Anthropic Console'da web search yoqilgan bo'lishi kerak). `0` — o'chirish (arzonroq, tezroq).
- Rasm mualliflari slayd izohlarida ko'rsatiladi. Rasm mosligini tekshiring.
