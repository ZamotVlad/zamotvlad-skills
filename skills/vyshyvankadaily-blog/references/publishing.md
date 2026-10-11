# Чернетка, зображення, публікація

## Формат чернетки (draft.json)

Один запис у форматі `blog_posts.json` плюс службові поля, які завантажувач ігнорує (`brief`, `secondary_keywords`, `head_terms`, `allowed_external_links`, `sources`, `notes`). `head_terms` - головні слова теми (наприклад «вишиванка», «низь»): аудитор зараховує абзац, якщо в ньому є основний ключ, додатковий ключ або головне слово. Якщо поле порожнє, береться найдовше слово основного ключа. Файл чернетки - у scratchpad, не в репо.

```json
{
  "slug": "nyz-podilska-vyshyvka",
  "status": "published",
  "category": {"slug": "techniques", "name_uk": "Техніки", "name_en": "Techniques"},
  "author_name_uk": "Владислав Замотайло",
  "cover_image_url": "https://vyshyvankadaily.live/static/blog/nyz-podilska-vyshyvka/cover-....webp",
  "uk": {
    "title": "...", "excerpt": "...", "seo_title": "...", "seo_description": "...",
    "target_keyword": "низь вишивка", "cover_image_alt": "...",
    "secondary_keywords": ["низинка", "подільська вишивка"],
    "head_terms": ["низь"],
    "body": "<p>...</p>"
  },
  "en": {
    "title": "...", "excerpt": "...", "seo_title": "...", "seo_description": "...",
    "target_keyword": "nyz embroidery", "cover_image_alt": "...",
    "secondary_keywords": ["Podillia embroidery"],
    "body": "<p>...</p>"
  },
  "allowed_external_links": [],
  "sources": [{"text": "Вінницький обласний краєзнавчий музей, колекція «Вишивка Східного Поділля»", "level": "А"}],
  "brief": {"intent": "...", "type": "...", "target_words": 1400, "competitors": ["..."], "gaps": ["..."], "faq": ["..."]},
  "future_links": [{"text": "речення в статті", "article": "запланована стаття"}],
  "notes": "що звірити, питання до Влада"
}
```

Категорії, що вже є: `styling` (Стилізація / Styling). Нові створюються автоматично при завантаженні: `techniques` (Техніки), `symbols` (Символи), `history` (Історія), `traditions` (Традиції), `culture` (Культура), `guides` (Гіди). Тримай не більше 6-8 категорій.

## HTML тіла статті

- Тільки `<p>`, `<h2>`, `<h3>`, `<ul>/<ol>/<li>`, `<table>` (з `<thead>`), `<blockquote>`, `<strong>`, `<em>`, `<a href>`, `<figure>`.
- Зображення:

```html
<figure><img src="/static/blog/<slug>/<file>.webp" alt="..." width="..." height="..." loading="lazy" decoding="async"><figcaption>Фото: автор / джерело, ліцензія</figcaption></figure>
```

- H1 у тілі не ставити - його дає шаблон із `title`.
- Зміст (TOC) сайт будує сам з H2.
- Розділ «Джерела»: `<h2>Джерела</h2><ul><li>...</li></ul>` текстом, без адрес. EN: `<h2>Sources</h2>`.

## Зображення

Мінімум: обкладинка + 2 зображення в тексті. Ставити поруч із тим місцем, про яке йдеться (таблиця видів -> фото кількох видів; згаданий експонат -> його фото). Підпис `figcaption` обов'язковий: що зображено, музей/колекція чи автор, ліцензія («Весільний рушник, Полтавщина, кінець XIX ст. Національний музей українського народного декоративного мистецтва. Фото: <автор>, CC BY-SA 4.0, Wikimedia Commons»). Якщо фото немає, а експонат описаний на сайті музею - зовнішнє посилання на сторінку експоната.

Порядок пошуку (від найкращого):
1. **Власні орнаменти сайту** - вільні від чужих прав і впізнавані. SVG дня є за адресою `/pattern/<YYYY-MM-DD>.svg`; локально відрендерити в PNG/WebP через headless Chromium (`chrome --headless --screenshot`) або Playwright і пропустити через `prepare_image.py`. Підпис: «Орнамент VyshyvankaDaily, <регіон>, <дата>».
2. **Власні інфографіки SVG -> WebP**: схема частин сорочки, таблиця кольорів регіонів, мапа, порівняння технік. Малюються кодом у стилі сайту (фон #1C1815, червоний #C23B2E, кремовий #EDE6DC), без вигаданих фактів.
3. **Wikimedia Commons** (CC0, CC BY, CC BY-SA, public domain). З контейнера Commons заблокований: знайти пошуком конкретні файли, записати в бриф назву файлу, автора, ліцензію й адресу сторінки - Влад завантажує, кладе в чат, далі `prepare_image.py`. Підпис: «Фото: <автор>, <ліцензія>, Wikimedia Commons». Для CC BY-SA - лише без змін або з тією самою ліцензією.
4. **Музеї й майстрині** - лише з письмового дозволу, з підписом автора.
5. **Згенеровані ілюстрації** (дозвіл Влада є) - тільки як ілюстрація: стилізовані, декоративні, атмосферні (полотно, нитки, натюрморт, абстрактний орнамент). Підпис «Ілюстрація». **Заборонено** генерувати фотореалістичні «справжні» вишиванки, музейні експонати, конкретні регіональні сорочки чи людей, яких можна прийняти за реальних. Claude сам растрові фото не генерує: дає готовий промпт для генератора Влада (англійською, з кольорами сайту), Влад генерує й надсилає файл.

Технічно: `python tools/prepare_image.py <вхідний-файл> <опис-латиницею-через-дефіси>` (опції `--max-kb 100`, `--max-width 1600`) -> WebP до 100 КБ, покласти в `static/blog/<slug>/`; обкладинка - `cover_image_url` з повною адресою `https://vyshyvankadaily.live/static/blog/<slug>/...`. Обкладинка - бажано 1200 px завширшки, горизонтальна. У кожного зображення alt описує, що на ньому, і не дублює H1.

## Публікація (після «ок» Влада)

```bash
# у репо
python - <<'EOF'   # додати запис з draft.json у blog_posts.json (службові поля можна лишити)
EOF
python manage.py load_blog_posts blog_posts.json --dry-run --settings=config.settings.local
python manage.py load_blog_posts blog_posts.json --settings=config.settings.local
pytest -q && ruff check .
```

Коміт від імені Vladyslav Zamotailo, без Co-Authored-By і слідів AI, повідомлення на кшталт `blog: <тема>`, push у `main`.

Влад на проді:

```bash
git push heroku main
heroku run "python manage.py load_blog_posts blog_posts.json --dry-run"
heroku run "python manage.py load_blog_posts blog_posts.json"
```

Після: Rich Results Test для UA-адреси, подати на індексацію `/blog/<slug>/` і `/en/blog/<slug>/`, оновити контент-план.
