# History Test Telegram Bot

Bu loyiha sizning `Oʻzbekistonning eng yangi tarixi` test savollaringizni Telegram bot orqali yodlash uchun tayyorlangan starter versiya.

## Bot nima qiladi?

- DOCX fayldagi savol, toʻgʻri javob va variantlarni SQLite bazaga import qiladi.
- Telegramda 4 variantli test beradi.
- Toʻgʻri javob berilgan savollarni kamroq qaytaradi.
- Xato javob berilgan savollarni tezroq qaytaradi.
- Har bir foydalanuvchi uchun alohida progress saqlaydi.

## Oʻrnatish

1. Python 3.11 yoki undan yuqori versiya oʻrnating.
2. Papkaga kiring:

```bash
cd history_test_bot_starter
```

3. Virtual muhit yarating:

```bash
python -m venv .venv
```

4. Virtual muhitni yoqing:

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

5. Kerakli kutubxonalarni oʻrnating:

```bash
pip install -r requirements.txt
```

6. `.env.example` faylidan `.env` yarating va token qoʻying:

```bash
cp .env.example .env
```

`.env` ichida:

```env
BOT_TOKEN=BotFather_dan_olingan_token
DATABASE_PATH=questions.db
```

## Savollarni import qilish

```bash
python importer.py --docx data/history_tests.docx --db questions.db
```

Kutiladigan natija:

```text
Imported 400 questions into questions.db
```

## Botni ishga tushirish

```bash
python bot.py
```

Telegramda botga kiring va `/start` bosing.

## Komandalar

- `/start` - botni boshlash
- `/study` - test ishlash
- `/hard` - xato qilingan savollarni qayta ishlash
- `/stats` - progressni koʻrish
- `/reset` - progressni tozalash

## Keyingi qoʻshiladigan funksiyalar

- Kunlik eslatma
- Imtihon rejimi
- Eng koʻp xato qilingan savollar roʻyxati
- Admin panel
- Mavzu boʻyicha test ishlash
- Web panel yoki mini app
