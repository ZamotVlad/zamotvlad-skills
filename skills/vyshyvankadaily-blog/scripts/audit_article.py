#!/usr/bin/env python3
"""Аудит чернетки статті VyshyvankaDaily (UA + EN) і HTML-звіт для рев'ю.

Використання:
    python3 audit_article.py draft.json [--repo PATH] [--out review.html] [--min-words 900]

draft.json - один запис формату blog_posts.json (або список; береться перший),
можна зі службовими полями secondary_keywords, allowed_external_links, sources, brief, notes.
Без зовнішніх залежностей: лише стандартна бібліотека Python 3.8+.
Код виходу: 0 - помилок немає, 1 - є помилки.
"""

import argparse
import html
import json
import re
import statistics
import sys
from html.parser import HTMLParser
from pathlib import Path

REGION_SLUGS = {
    "ar-krym", "cherkaska-oblast", "chernihivska-oblast", "chernivetska-oblast",
    "dnipropetrovska-oblast", "donetska-oblast", "ivano-frankivska-oblast",
    "kharkivska-oblast", "khersonska-oblast", "khmelnytska-oblast",
    "kirovohradska-oblast", "kyivska-oblast", "luhanska-oblast", "lvivska-oblast",
    "m-kyiv", "m-sevastopol", "mykolaivska-oblast", "odeska-oblast",
    "poltavska-oblast", "rivnenska-oblast", "sumska-oblast", "ternopilska-oblast",
    "vinnytska-oblast", "volynska-oblast", "zakarpatska-oblast", "zaporizka-oblast",
    "zhytomyrska-oblast",
}
STATIC_PAGES = {"", "regions", "blog", "archive", "faq", "about", "contacts", "terms-of-use", "privacy-policy"}
OWN_HOSTS = ("vyshyvankadaily.live", "ko-fi.com/vyshyvankadaily")
TRUSTED_HOSTS = (
    "wikipedia.org", "wikimedia.org", "unesco.org", "gov.ua", "esu.com.ua", "archive.org",
    "nlu.org.ua", "nbuv.gov.ua", "britannica.com", "forbes.com", "forbes.ua", "bbc.com",
    "bbc.co.uk", "suspilne.media", "ukrinform.ua", "ukrinform.net", "theguardian.com",
    "nytimes.com", "pravda.com.ua", "nv.ua", "radiosvoboda.org", "metmuseum.org",
    "vam.ac.uk", "ukrainer.net", "fashionweek.ua", "museum-digital.org",
)
BLOCKED_HOSTS = (
    "facebook.com", "fb.com", "instagram.com", "tiktok.com", "t.me", "telegram.me",
    "twitter.com", "x.com", "threads.net", "pinterest.com", "vk.com",
)


REGION_ANCHOR = re.compile(r"вишив|вишиван|орнамент|сорочк|узор|embroider|vyshyvank|ornament|shirt|blouse|pattern")
MUSEUM_WORD = re.compile(r"музе|museum", re.IGNORECASE)


def _host(href):
    host = re.sub(r"^https?://", "", href).split("/")[0].split(":")[0].lower()
    return host[4:] if host.startswith("www.") else host


def _host_in(host, hosts):
    return any(host == h or host.endswith("." + h) for h in hosts)

# (шаблон, максимум на статтю, підказка)
PATTERNS = {
    "uk": [
        (r"варто (зазначити|відзначити|згадати|наголосити)", 0, "прибрати вступну формулу"),
        (r"важливо (підкреслити|зазначити|розуміти)", 0, "прибрати вступну формулу"),
        (r"слід (зауважити|зазначити)", 0, "прибрати вступну формулу"),
        (r"\bцікаво,? що\b", 0, "просто сказати факт"),
        (r"\bнасправді\b", 1, "зазвичай зайве"),
        (r"\bпо суті\b", 0, "зайве"),
        (r"\bбуквально\b", 1, "лише в прямому значенні"),
        (r"не секрет,? що|як відомо", 0, "прибрати"),
        (r"живий приклад|яскравий приклад", 0, "сказати, що саме показує приклад"),
        (r"справжн(ій|ім|ього) скарб|перлин(а|ою)", 0, "пафос"),
        (r"візитівк", 0, "пафос, замінити на конкретику"),
        (r"неповторн|неймовірн|надзвичайн", 1, "оцінка замість факту"),
        (r"\bунікальн", 1, "лише для справді єдиного випадку"),
        (r"код нації|генетичн(ий|ого) код", 0, "кліше (крім назв і цитат)"),
        (r"відіграє (важливу|ключову|значну|велику) роль", 0, "сказати, що саме робить"),
        (r"є (невід'ємною частиною|свідченням)", 0, "кліше"),
        (r"підкреслює (значущість|важливість)", 0, "кліше"),
        (r"у сучасному світі|з давніх-давен|споконвіку", 0, "кліше"),
        (r"у підсумку|отже,? як бачимо|підсумовуючи", 0, "без підсумкових формул"),
        (r"\bсаме (ця|цей|це|ці|тому|завдяки|так|він|вона|воно|вони|його|її)\b", 2, "«саме» як підсилювач"),
        (r"не лише\b[^.]{0,80}?\bа й\b|не тільки\b[^.]{0,80}?\bа й\b", 2, "протиставлення-шаблон"),
        (r"не просто\b[^.]{0,60}?, а\b", 1, "протиставлення-шаблон"),
        (r"\bце не\b[^.]{0,60}?, а\b", 1, "протиставлення-шаблон"),
    ],
    "en": [
        (r"\bdelve", 0, "AI-слово"),
        (r"\btapestry\b", 0, "AI-слово"),
        (r"\btestament\b", 0, "AI-слово"),
        (r"\bvibrant\b", 0, "AI-слово"),
        (r"\bshowcas", 0, "AI-слово"),
        (r"\bpivotal\b|\bcrucial\b", 0, "AI-слово"),
        (r"\bseamless|\brobust\b|\bnestled\b|\bboasts?\b", 0, "AI-слово"),
        (r"\blandscape\b", 1, "лише в прямому значенні"),
        (r"\brich\b", 1, "лише в прямому значенні"),
        (r"it'?s worth noting|in today'?s world|plays? a (vital|key|crucial|pivotal) role", 0, "кліше"),
        (r"\bserves as\b|\bstands as\b", 0, "писати is"),
        (r"not (just|only|merely)\b[^.]{0,80}?\bbut\b", 1, "протиставлення-шаблон"),
        (r"\bunique\b", 1, "лише для справді єдиного випадку"),
    ],
}

FINAL_LINE = {
    "uk": ("Якщо ви побачили помилку", "/contacts/"),
    "en": ("If you notice a mistake", "/en/contacts/"),
}
FAQ_MARK = {"uk": ("часті", "питання", "faq"), "en": ("frequently", "faq", "questions")}
SOURCES_MARK = {"uk": "джерела", "en": "sources"}


class Doc(HTMLParser):
    """Збирає блоки (p/li/h2/h3/td), посилання й зображення з тіла статті."""

    BLOCKS = {"p", "li", "h1", "h2", "h3", "h4", "td", "th", "figcaption", "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.links = []
        self.images = []
        self._stack = []
        self._link = None
        self._bid = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.BLOCKS:
            self._bid += 1
            self._stack.append([tag, "", self._bid])
        if tag == "a":
            block = self._stack[-1][2] if self._stack else 0
            self._link = {"href": a.get("href", ""), "rel": a.get("rel") or "", "text": "", "block": block}
        if tag == "img":
            self.images.append(a)

    def handle_endtag(self, tag):
        if tag == "a" and self._link is not None:
            self.links.append(self._link)
            self._link = None
        if tag in self.BLOCKS and self._stack:
            for i in range(len(self._stack) - 1, -1, -1):
                if self._stack[i][0] == tag:
                    t, text, _ = self._stack.pop(i)
                    self.blocks.append((t, " ".join(text.split())))
                    break

    def handle_data(self, data):
        if self._stack:
            self._stack[-1][1] += data
        if self._link is not None:
            self._link["text"] += data


def words(text):
    return re.findall(r"[\w'’-]+", text, re.UNICODE)


def stems(phrase):
    out = []
    for w in words(phrase.lower()):
        if len(w) <= 3:
            out.append(w)
        else:
            out.append(w[: max(4, len(w) - 3)])
    return out


def has_phrase(text, phrase):
    low = text.lower()
    tokens = [w.lower() for w in words(low)]
    st = stems(phrase)
    if not st:
        return False
    return all(any(t.startswith(s) for t in tokens) for s in st)


def count_phrase(text, phrase):
    """Скільки разів трапляється перше значуще слово ключа поруч з іншими (за основами)."""
    st = stems(phrase)
    if not st:
        return 0
    tokens = [w.lower() for w in words(text)]
    hits = 0
    for i, t in enumerate(tokens):
        if t.startswith(st[0]):
            window = tokens[max(0, i - 4): i + 5]
            if all(any(w.startswith(s) for w in window) for s in st):
                hits += 1
    return hits


class Report:
    def __init__(self):
        self.rows = []

    def add(self, lang, level, check, detail=""):
        self.rows.append((lang, level, check, detail))

    @property
    def errors(self):
        return [r for r in self.rows if r[1] == "error"]

    @property
    def warnings(self):
        return [r for r in self.rows if r[1] == "warn"]


def audit_lang(entry, lang, rep, min_words, repo):
    data = entry.get(lang) or {}
    body = data.get("body", "")
    if not body:
        rep.add(lang, "error", "Тіло статті", "порожнє")
        return {}
    doc = Doc()
    doc.feed(body)
    text_blocks = [(t, s) for t, s in doc.blocks if s]
    paragraphs = [s for t, s in text_blocks if t == "p"]
    h2 = [s for t, s in text_blocks if t == "h2"]
    h3 = [s for t, s in text_blocks if t == "h3"]
    all_text = " ".join(s for _, s in text_blocks)
    n_words = len(words(all_text))
    kw = (data.get("target_keyword") or "").strip()
    extra = [k for k in data.get("secondary_keywords", []) if k.strip()]
    keys = [kw] + extra if kw else extra
    stats = {"words": n_words, "h2": len(h2), "paragraphs": len(paragraphs)}

    # обсяг
    target = (entry.get("brief") or {}).get("target_words")
    floor = min_words if lang == "uk" else int(min_words * 0.85)
    if n_words < floor:
        rep.add(lang, "error", "Обсяг", f"{n_words} слів, мінімум {floor}")
    elif target and lang == "uk" and n_words < target * 0.9:
        rep.add(lang, "warn", "Обсяг", f"{n_words} слів, ціль брифу {target}")
    else:
        rep.add(lang, "ok", "Обсяг", f"{n_words} слів")

    # мета
    def length(field, lo, hi, level="warn"):
        v = (data.get(field) or "").strip()
        if not v:
            rep.add(lang, "error", field, "порожньо")
        elif not (lo <= len(v) <= hi):
            rep.add(lang, level, field, f"{len(v)} знаків, треба {lo}-{hi}")
        else:
            rep.add(lang, "ok", field, f"{len(v)} знаків")

    length("title", 20, 90)
    length("seo_title", 25, 60)
    length("seo_description", 110, 160)
    length("excerpt", 60, 170)
    length("cover_image_alt", 15, 140)
    if (data.get("seo_title") or "").strip().lower() == (data.get("title") or "").strip().lower():
        rep.add(lang, "warn", "title / seo_title", "однакові - H1 краще зробити людською довшою назвою")

    # ключ
    if not kw:
        rep.add(lang, "error", "Ключ", "target_keyword порожній")
    else:
        for field in ("seo_title", "title", "seo_description"):
            if not has_phrase(data.get(field, ""), kw):
                rep.add(lang, "error" if field != "seo_description" else "warn", f"Ключ у {field}", f"«{kw}» не знайдено")
        first100 = " ".join(words(all_text)[:100])
        if has_phrase(first100, kw):
            rep.add(lang, "ok", "Ключ у перших 100 словах")
        else:
            rep.add(lang, "error", "Ключ у перших 100 словах", f"«{kw}» не знайдено")
        h2_hits = sum(has_phrase(h, kw) for h in h2)
        rep.add(lang, "ok" if h2_hits >= 2 else "warn", "Ключ у H2", f"{h2_hits} з {len(h2)} (треба 2+)")
        density = count_phrase(all_text, kw) / max(n_words, 1) * 100
        if density > 2.5:
            rep.add(lang, "warn", "Щільність ключа", f"{density:.1f} на 100 слів - схоже на переспам")
        elif density < 0.4:
            rep.add(lang, "warn", "Щільність ключа", f"{density:.1f} на 100 слів - замало")
        else:
            rep.add(lang, "ok", "Щільність ключа", f"{density:.1f} на 100 слів")

    # ключ у кожному змістовному абзаці
    final_mark = FINAL_LINE[lang][0]
    content_pars = [p for p in paragraphs if len(words(p)) >= 25 and final_mark not in p]
    heads = [h for h in data.get("head_terms", []) if h.strip()]
    if not heads and kw:
        heads = [max(words(kw), key=len)]
    para_keys = keys + heads
    missing = [p for p in content_pars if not any(has_phrase(p, k) for k in para_keys)]
    if content_pars:
        share = 1 - len(missing) / len(content_pars)
        level = "ok" if share >= 0.8 else ("warn" if share >= 0.6 else "error")
        detail = f"{share:.0%} абзаців ({len(content_pars) - len(missing)}/{len(content_pars)}), рахуються: {', '.join(para_keys)}"
        if missing:
            detail += "; без ключа: " + " | ".join(m[:70] + "…" for m in missing[:6])
        rep.add(lang, level, "Ключ в абзацах", detail)

    # заголовки
    if any(t == "h1" for t, _ in text_blocks):
        rep.add(lang, "error", "H1 у тілі", "H1 дає шаблон, у тілі його не має бути")
    if len(h2) < 4:
        rep.add(lang, "warn", "Кількість H2", f"{len(h2)} - замало для статті")
    dup = {h for h in h2 if h2.count(h) > 1}
    if dup:
        rep.add(lang, "warn", "Однакові H2", ", ".join(dup))

    # FAQ
    faq_idx = next((i for i, h in enumerate(h2) if any(m in h.lower() for m in FAQ_MARK[lang])), None)
    questions = [q for q in h3 if q.endswith("?")]
    if faq_idx is None:
        rep.add(lang, "warn", "FAQ", "немає розділу з питаннями")
    elif len(questions) < 3:
        rep.add(lang, "warn", "FAQ", f"{len(questions)} питань, треба 3-5")
    else:
        rep.add(lang, "ok", "FAQ", f"{len(questions)} питань")

    # джерела
    if not any(SOURCES_MARK[lang] in h.lower() for h in h2):
        rep.add(lang, "warn", "Розділ «Джерела»", "немає H2 з джерелами")

    # фінальний рядок
    last_p = paragraphs[-1] if paragraphs else ""
    mark, contact = FINAL_LINE[lang]
    contact_link = any(link["href"] == contact for link in doc.links)
    if mark in last_p and contact_link:
        rep.add(lang, "ok", "Фінальний рядок")
    else:
        rep.add(lang, "error", "Фінальний рядок", f"останній абзац має містити «{mark}» з посиланням на {contact}")

    # посилання
    allowed = set(entry.get("allowed_external_links", []))
    internal = []
    internal_blocks = []
    external_count = 0
    for link in doc.links:
        href = link["href"].strip()
        anchor = " ".join(link["text"].split())
        if href.startswith(("http://", "https://")):
            if any(h in href for h in OWN_HOSTS):
                continue
            host = _host(href)
            external_count += 1
            if _host_in(host, BLOCKED_HOSTS):
                rep.add(lang, "error", "Посилання на соцмережу", f"{href} («{anchor}»)")
            elif not (_host_in(host, TRUSTED_HOSTS) or href in allowed):
                rep.add(lang, "warn", "Зовнішнє посилання", f"{host} не в списку довірених: перевірити й додати в allowed_external_links ({anchor})")
            if "noopener" not in link.get("rel", ""):
                rep.add(lang, "warn", "rel=noopener", href)
            continue
        if href.startswith("mailto:") or href.startswith("#"):
            continue
        internal.append((href, anchor))
        internal_blocks.append(link.get("block", 0))
        path = href
        if lang == "en":
            if not path.startswith("/en/"):
                rep.add(lang, "error", "EN-посилання без /en/", href)
                continue
            path = path[3:]
        elif path.startswith("/en/"):
            rep.add(lang, "error", "UA-посилання на /en/", href)
        m = re.match(r"^/regions/([^/]+)/$", path)
        if m and m.group(1) not in REGION_SLUGS:
            rep.add(lang, "error", "Невідомий регіон", href)
        elif m and not REGION_ANCHOR.search(anchor.lower()):
            rep.add(lang, "warn", "Анкор на регіон", f"«{anchor}» не каже, що там вишивка/орнаменти регіону (напр. «орнаменти вишиванок ...», ключ сторінки) -> {href}")
        elif not m and not path.startswith("/blog/"):
            first = path.strip("/").split("/")[0]
            if first not in STATIC_PAGES:
                rep.add(lang, "warn", "Перевірити посилання", href)
        if anchor.lower() in {"тут", "за посиланням", "here", "click here", "link", "посилання"}:
            rep.add(lang, "warn", "Анкор", f"«{anchor}» -> {href}")
        if "vyshyvankadaily" in anchor.lower() and path not in ("/", ""):
            rep.add(lang, "warn", "Брендовий анкор", f"«{anchor}» має вести лише на головну, зараз {href}")
    content = [(h, b) for (h, _), b in zip(internal, internal_blocks) if contact not in h]
    content_links = [h for h, _ in content]
    per_k = len(content_links) / max(n_words, 1) * 1000
    regions_linked = sorted({h for h in content_links if "/regions/" in h})
    level = "warn" if per_k > 6 else "ok"
    rep.add(lang, level, "Внутрішні посилання", f"{len(content_links)} ({per_k:.1f} на 1000 слів), регіонів: {len(regions_linked)}; мінімуму немає, лише доречні (тест читача)")
    for href in sorted({h for h in content_links if content_links.count(h) > 1}):
        rep.add(lang, "warn", "Повторне посилання", f"{href} - {content_links.count(href)} рази, лишити одне")
    blocks_seen = [b for _, b in content if b]
    for b in sorted({b for b in blocks_seen if blocks_seen.count(b) > 1}):
        rep.add(lang, "warn", "Кілька посилань в абзаці", f"абзац №{b}: {blocks_seen.count(b)} внутрішніх посилань")
    if external_count > 3:
        rep.add(lang, "warn", "Зовнішні посилання", f"{external_count}, рекомендовано до 3")
    stats["regions"] = regions_linked

    # зображення
    for img in doc.images:
        src = img.get("src", "")
        alt = (img.get("alt") or "").strip()
        if src.startswith(("http://", "https://")):
            rep.add(lang, "warn", "Зовнішнє зображення", f"скачати й покласти в static/blog/<slug>/ перед публікацією: {file_page(src)}")
        if not alt:
            rep.add(lang, "error", "Зображення без alt", src)
        elif alt.lower() == (data.get("title") or "").strip().lower():
            rep.add(lang, "warn", "alt дублює H1", src)
        for attr in ("width", "height"):
            if not img.get(attr):
                rep.add(lang, "warn", f"Зображення без {attr}", src)
        if img.get("loading") != "lazy":
            rep.add(lang, "warn", "Зображення без loading=lazy", src)
        if repo and src.startswith("/static/"):
            f = Path(repo) / src.lstrip("/")
            if not f.exists():
                rep.add(lang, "error", "Файл зображення не знайдено", src)
            else:
                kb = f.stat().st_size / 1024
                if kb > 105:
                    rep.add(lang, "warn", "Зображення > 100 КБ", f"{src}: {kb:.0f} КБ")
                if f.suffix.lower() != ".webp":
                    rep.add(lang, "warn", "Не WebP", src)
    if not entry.get("cover_image_url"):
        rep.add(lang, "warn", "Обкладинка", "cover_image_url порожній")
    n_img = len(doc.images)
    if n_img < 2:
        rep.add(lang, "error", "Візуал", f"зображень у тексті: {n_img}, потрібно щонайменше 2 з підписом")
    else:
        rep.add(lang, "ok", "Візуал", f"зображень у тексті: {n_img}")
    n_cap = sum(1 for tag, _ in doc.blocks if tag == "figcaption")
    if n_cap < n_img:
        rep.add(lang, "warn", "Підписи до зображень", f"{n_img} зображень, підписів {n_cap}: що на фото, музей/автор, ліцензія")
    if MUSEUM_WORD.search(re.sub(r"<[^>]+>", " ", body)) and external_count == 0 and n_img == 0:
        rep.add(lang, "warn", "Музеї без візуалу", "у тексті згадано музей/експонат, але немає ні фото, ні посилання на сторінку музею")

    # типографіка
    plain = html.unescape(re.sub(r"<[^>]+>", " ", body))
    meta_text = " ".join(str(data.get(f, "")) for f in ("title", "seo_title", "seo_description", "excerpt", "cover_image_alt"))
    dashes = len(re.findall("[—–]", plain + meta_text))
    if dashes:
        rep.add(lang, "error", "Довге/середнє тире", f"{dashes} шт. - замінити на дефіс з пробілами")
    if lang == "uk":
        straight = len(re.findall(r'"', plain))
        if straight:
            rep.add(lang, "warn", "Прямі лапки", f"{straight} шт. - в українському тексті «ялинки»")
    # шаблонні звороти
    low = plain.lower()
    found = []
    for pat, limit, hint in PATTERNS[lang]:
        n = len(re.findall(pat, low))
        if n > limit:
            sample = re.search(pat, low)
            ctx = low[max(0, sample.start() - 30): sample.end() + 30].replace("\n", " ") if sample else ""
            found.append(f"{n}× {hint}: …{ctx.strip()}…")
    if found:
        rep.add(lang, "warn", "Шаблонні звороти", " || ".join(found))
    else:
        rep.add(lang, "ok", "Шаблонні звороти", "не знайдено")

    # ритм
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", " ".join(paragraphs)) if len(words(s)) > 2]
    lengths = [len(words(s)) for s in sentences]
    if lengths:
        long_ones = [s for s in sentences if len(words(s)) > 35]
        sd = statistics.pstdev(lengths) if len(lengths) > 1 else 0
        detail = f"середнє {statistics.mean(lengths):.0f} слів, розкид {sd:.1f}"
        level = "ok"
        if sd < 5:
            level, detail = "warn", detail + " - монотонно, урізноманітнити довжину"
        if long_ones:
            level = "warn"
            detail += f"; довгі (>35 слів): {len(long_ones)}, напр. «{long_ones[0][:80]}…»"
        rep.add(lang, level, "Ритм речень", detail)
        run = 0
        for a, b in zip(lengths, lengths[1:]):
            run = run + 1 if abs(a - b) <= 2 else 0
            if run >= 3:
                rep.add(lang, "warn", "Ритм речень", "4+ речень поспіль однакової довжини")
                break
    long_pars = [p for p in paragraphs if len(words(p)) > 120]
    if long_pars:
        rep.add(lang, "warn", "Довгі абзаци", f"{len(long_pars)} абзаців понад 120 слів")

    # самореклама
    promo = len(re.findall(r"генератор|generator", low))
    if promo > 2:
        rep.add(lang, "warn", "Самореклама", f"«генератор» згадано {promo} рази, достатньо 1")
    return stats


CSS = """
:root{--bg:#1C1815;--fg:#EDE6DC;--muted:#b9afa3;--red:#C23B2E;--card:#26211d;--ok:#5d9a5d;--warn:#d9a441;--err:#e05a4a}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.65 Georgia,'PT Serif',serif}
main{max-width:880px;margin:0 auto;padding:24px 16px 80px}
h1,h2,h3{font-family:system-ui,sans-serif;line-height:1.25}
.meta{background:var(--card);border-radius:8px;padding:12px 16px;margin:12px 0}
.meta dt{color:var(--muted);font:600 12px system-ui;text-transform:uppercase;letter-spacing:.04em;margin-top:8px}
.meta dd{margin:2px 0 0}
table.checks{width:100%;border-collapse:collapse;font:14px/1.45 system-ui;margin:12px 0}
table.checks td,table.checks th{border-bottom:1px solid #3a332d;padding:6px 8px;vertical-align:top;text-align:left}
.lvl{font-weight:700;white-space:nowrap}.ok{color:var(--ok)}.warn{color:var(--warn)}.error{color:var(--err)}
.summary{font:600 18px system-ui;margin:8px 0}
article{background:#fbf8f3;color:#1C1815;border-radius:8px;padding:8px 28px 24px;margin:16px 0}
article a{color:#9b2a20}article table{border-collapse:collapse}article td,article th{border:1px solid #d8cfc4;padding:4px 8px}
article img{max-width:100%;height:auto}.ph{border:2px dashed #c8913a;padding:24px;margin:8px 0;background:#fbf6ec;color:#3a2f25;word-break:break-all}article figcaption{font-size:13px;color:#6b6157}
nav a{color:var(--fg);margin-right:16px}
"""


def file_page(src):
    """Сторінка файлу на Commons для Special:FilePath, інакше сама адреса."""
    m = re.search(r"Special:FilePath/([^?\"]+)", src)
    return f"https://commons.wikimedia.org/wiki/File:{m.group(1)}" if m else src


def embed_images(body, repo):
    """Вбудовує локальні зображення як data URI, щоб звіт показував фото на будь-якому комп'ютері."""
    import base64

    def repl(m):
        src = m.group(1)
        if repo:
            f = Path(repo) / src.lstrip("/")
            if f.exists():
                mime = "image/webp" if f.suffix.lower() == ".webp" else "image/" + f.suffix.lower().lstrip(".")
                return 'src="data:%s;base64,%s"' % (mime, base64.b64encode(f.read_bytes()).decode())
        return 'src="https://vyshyvankadaily.live%s"' % src

    def placeholder(m):
        tag = m.group(0)
        src = re.search(r'src="([^"]+)"', tag).group(1)
        alt = re.search(r'alt="([^"]*)"', tag)
        page = file_page(src)
        return (
            '<div class="ph"><b>Фото чекає завантаження</b><br>'
            f'{alt.group(1) if alt else ""}<br><a href="{page}" target="_blank" rel="noopener">{page}</a></div>'
        )

    body = body.replace(' loading="lazy"', "")
    body = re.sub(r'<img[^>]+src="https?://[^"]+"[^>]*>', placeholder, body)
    return re.sub(r'src="(/static/[^"]+)"', repl, body)


def downloads_html(entry):
    def esc(v):
        return html.escape(str(v or ""))

    items = entry.get("photos_to_download") or []
    if not items:
        return ""
    rows = "".join(
        f"<li><a href='{esc(i.get('page'))}' target='_blank' rel='noopener'>{esc(i.get('page'))}</a>"
        f" - зберегти як <code>{esc(i.get('save_as'))}</code>; {esc(i.get('caption', ''))}</li>"
        for i in items
    )
    return f"<h2 id='photos'>Фото для завантаження</h2><ol>{rows}</ol>"


def render(entry, rep, stats, out, repo=None):
    def esc(v):
        return html.escape(str(v or ""))

    rows = "".join(
        f"<tr><td>{esc(lang.upper())}</td><td class='lvl {lvl}'>{ {'ok':'ok','warn':'увага','error':'помилка'}[lvl] }</td><td>{esc(check)}</td><td>{esc(detail)}</td></tr>"
        for lang, lvl, check, detail in sorted(rep.rows, key=lambda r: ({"error": 0, "warn": 1, "ok": 2}[r[1]], r[0]))
    )
    brief = entry.get("brief") or {}
    brief_html = "".join(f"<dt>{esc(k)}</dt><dd>{esc(', '.join(v) if isinstance(v, list) else v)}</dd>" for k, v in brief.items())
    sources = "".join(f"<li>{esc(s.get('text') if isinstance(s, dict) else s)} {('['+esc(s.get('level'))+']') if isinstance(s, dict) and s.get('level') else ''}</li>" for s in entry.get("sources", []))

    def lang_block(lang):
        d = entry.get(lang) or {}
        st = stats.get(lang, {})
        meta = "".join(
            f"<dt>{f}</dt><dd>{esc(d.get(f))}</dd>"
            for f in ("seo_title", "seo_description", "title", "excerpt", "target_keyword", "secondary_keywords", "cover_image_alt")
        )
        prefix = "/en" if lang == "en" else ""
        return (
            f"<h2 id='{lang}'>{'Українська' if lang == 'uk' else 'English'} · {st.get('words', 0)} слів</h2>"
            f"<dl class='meta'><dt>URL</dt><dd>https://vyshyvankadaily.live{prefix}/blog/{esc(entry.get('slug'))}/</dd>{meta}</dl>"
            f"<article><h1>{esc(d.get('title'))}</h1>{embed_images(d.get('body', ''), repo)}</article>"
        )

    page = f"""<!doctype html><html lang="uk"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Рев'ю: {esc((entry.get('uk') or {}).get('title'))}</title><style>{CSS}</style></head><body><main>
<nav><a href="#checks">Перевірки</a><a href="#uk">UA</a><a href="#en">EN</a></nav>
<h1>{esc((entry.get('uk') or {}).get('title'))}</h1>
<p class="summary"><span class="error">помилок: {len(rep.errors)}</span> · <span class="warn">попереджень: {len(rep.warnings)}</span></p>
<dl class="meta"><dt>slug</dt><dd>{esc(entry.get('slug'))}</dd><dt>категорія</dt><dd>{esc((entry.get('category') or {}).get('name_uk'))}</dd>
<dt>обкладинка</dt><dd>{esc(entry.get('cover_image_url'))}</dd>{brief_html}
{('<dt>джерела</dt><dd><ul>'+sources+'</ul></dd>') if sources else ''}
{('<dt>нотатки</dt><dd>'+esc(entry.get('notes'))+'</dd>') if entry.get('notes') else ''}</dl>
{downloads_html(entry)}
<h2 id="checks">Перевірки</h2><table class="checks"><tr><th>Мова</th><th>Рівень</th><th>Перевірка</th><th>Деталі</th></tr>{rows}</table>
{lang_block('uk')}{lang_block('en')}
</main></body></html>"""
    Path(out).write_text(page, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("draft")
    ap.add_argument("--repo", help="корінь репозиторію, щоб перевірити файли зображень")
    ap.add_argument("--out", help="шлях до HTML-звіту для рев'ю")
    ap.add_argument("--min-words", type=int, default=900)
    args = ap.parse_args()

    data = json.loads(Path(args.draft).read_text(encoding="utf-8"))
    entry = data[0] if isinstance(data, list) else data
    rep = Report()
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", entry.get("slug", "")):
        rep.add("uk", "error", "slug", f"«{entry.get('slug')}» - лише латиниця, цифри й дефіси")
    for field in ("status", "category", "author_name_uk"):
        if not entry.get(field):
            rep.add("uk", "error", field, "порожньо")
    stats = {lang: audit_lang(entry, lang, rep, args.min_words, args.repo) for lang in ("uk", "en")}
    uk_w, en_w = stats["uk"].get("words", 0), stats["en"].get("words", 0)
    if uk_w and en_w and not (0.8 <= en_w / uk_w <= 1.5):
        rep.add("en", "warn", "Обсяг EN проти UA", f"{en_w} проти {uk_w} - перевірити, чи нічого не пропущено")
    if stats["uk"].get("regions") is not None and stats["en"].get("regions") is not None:
        uk_r = {r.replace("/en", "") for r in stats["uk"]["regions"]}
        en_r = {r.replace("/en", "") for r in stats["en"]["regions"]}
        if uk_r != en_r:
            rep.add("en", "warn", "Регіони UA ≠ EN", f"лише UA: {sorted(uk_r - en_r)}, лише EN: {sorted(en_r - uk_r)}")

    for lang, lvl, check, detail in sorted(rep.rows, key=lambda r: ({"error": 0, "warn": 1, "ok": 2}[r[1]], r[0])):
        mark = {"error": "ПОМИЛКА", "warn": "увага ", "ok": "ok     "}[lvl]
        print(f"{mark} [{lang}] {check}{': ' + detail if detail else ''}")
    print(f"\nПомилок: {len(rep.errors)}, попереджень: {len(rep.warnings)}")
    if args.out:
        render(entry, rep, stats, args.out, args.repo)
        print(f"Звіт: {args.out}")
    sys.exit(1 if rep.errors else 0)


if __name__ == "__main__":
    main()
