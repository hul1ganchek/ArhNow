import os, vk_api
import sqlite3
import urllib3
from urllib.parse import urljoin, urlsplit, urlunsplit, quote
from io import BytesIO
import requests
from bs4 import BeautifulSoup
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

db_name = "Storage.db"

def db_conn():
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def db_save_section(title):
    with db_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO sections(title) VALUES (?)", (title,))
        row = conn.execute("SELECT id FROM sections WHERE title = ?", (title,)).fetchone()
        return row["id"] if row else None

def db_save_subsection(section_id, parent_id, title, url, type_):
    with db_conn() as conn:
        conn.execute("""
            INSERT INTO subsections(section_id, parent_id, title, url, type)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                section_id = excluded.section_id,
                parent_id = excluded.parent_id,
                title = excluded.title,
                type = excluded.type
        """, (section_id, parent_id, title, url, type_))
        row = conn.execute("SELECT id FROM subsections WHERE url = ?", (url,)).fetchone()
        return row["id"] if row else None

def db_save_document(subsection_id, title, url, description):
    with db_conn() as conn:
        conn.execute("""
            INSERT INTO documents(subsection_id, title, url, description)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                subsection_id = excluded.subsection_id,
                title = excluded.title,
                description = excluded.description,
                parsed_at = CURRENT_TIMESTAMP
        """, (subsection_id, title, url, description))
        row = conn.execute("SELECT id FROM documents WHERE url = ?", (url,)).fetchone()
        return row["id"] if row else None

def db_save_history(vk_id, action, subsection_id=None, document_id=None):
    with db_conn() as conn:
        conn.execute("""
            INSERT INTO users_history(vk_id, action, subsection_id, document_id)
            VALUES (?, ?, ?, ?)
        """, (vk_id, action, subsection_id, document_id))

def db_save_items(section_id, parent_id, items):
    for item in items:
        db_save_subsection(section_id, parent_id, item["title"], item["url"], item["type"])

vk_session = vk_api.VkApi(token=os.getenv("vk_token"))
longpoll = VkLongPoll(vk_session)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sources = [
    {"title": "Инвестиционная деятельность", "source": [
        {"title": "Старый источник", "url": "https://m.arhcity.ru/?page=1472/0"},
        {"title": "Новый источник", "url": "https://arhcity.gosuslugi.ru/deyatelnost/napravleniya-deyatelnosti/investitsionnaya-deyatelnost/"}
    ]},
    {"title": "Торги", "source": [
        {"title": "Старый источник", "url": "https://m.arhcity.ru/?page=680/0"},
        {"title": "Новый источник", "url": "https://arhcity.gosuslugi.ru/deyatelnost/napravleniya-deyatelnosti/torgi/"}
    ]}
]

for s in sources:
    db_save_section(s["title"])

user_state = {}
page_size = 6

def fetch(url):
    try:
        r = requests.get(url, timeout=10, verify=False)
        return r.text
    except Exception as e:
        print(f"Ошибка при получении HTML {url}: {e}")
        return ""

def parse(urls):
    folders, files = [], []
    seen = set()
    for src in urls:
        url = src["url"]
        html = fetch(url)
        soup = BeautifulSoup(html, "html.parser")

        def normalize(base, href):
            if not href:
                return None
            return urljoin(base, href)

        if "gosuslugi" in url:
            for a in soup.select("li.menu-item a.menu-item-link"):
                href = normalize("https://arhcity.gosuslugi.ru/", a.get("href"))
                title = "🆕 " + a.get_text(strip=True)
                if href and href not in seen and title:
                    seen.add(href)
                    folders.append({"title": title, "url": href, "type": "folder"})
            for a in soup.select(".tpl-component-gw-file a.item-name[href], .tpl-component-gw-base-text a[href]"):
                href = normalize("https://arhcity.gosuslugi.ru/", a.get("href"))
                title = "🆕 " + a.get_text(strip=True)
                if href and href not in seen and title:
                    seen.add(href)
                    files.append({"title": title, "url": href, "type": "file"})
        else:
            pagebody = soup.find("div", class_="pagebody")
            if not pagebody:
                continue
            for li in pagebody.find_all("li"):
                a = li.find("a", href=True)
                if not a:
                    continue
                href = normalize("https://m.arhcity.ru/", a.get("href"))
                if not href or href in seen:
                    continue
                title = ""
                for e in a.contents:
                    if getattr(e, "name", None) == "span" and "secdir-small" in e.get("class", []):
                        continue
                    if getattr(e, "name", None) == "br":
                        continue
                    title += e.strip() if isinstance(e, str) else e.get_text(strip=True)
                title = " ".join(title.split())
                seen.add(href)
                if "secdir-li1" in li.get("class", []):
                    folders.append({"title": title, "url": href, "type": "folder"})
                elif "secdir-li2" in li.get("class", []):
                    files.append({"title": title, "url": href, "type": "file"})
            for a in pagebody.select("p > a[href]"):
                href = normalize("https://m.arhcity.ru/", a.get("href"))
                title = " ".join(a.get_text(" ", strip=True).split())
                if href and href not in seen and title and href != url:
                    seen.add(href)
                    files.append({"title": title, "url": href, "type": "file"})
    return folders, files

def send(uid, text, kb=None):
    vk.messages.send(user_id=uid, message=text[:4000], random_id=0, keyboard=kb.get_keyboard() if kb else None)

def section_menu():
    kb = VkKeyboard(one_time=False)
    kb.add_button("📁 Инвестиционная деятельность", VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("📁 Торги", VkKeyboardColor.SECONDARY)
    return kb

def subsection_menu(items, page=0):
    kb = VkKeyboard(one_time=False)
    start = page * page_size
    chunk = items[start:start + page_size]
    label_map = {}
    for i, item in enumerate(chunk, start=1):
        title = " ".join(item["title"].split())
        if len(title) > 22:
            title = title[:21] + "…"
        prefix = "📁" if item["type"] == "folder" else "📎"
        label = f"{prefix} {title}"
        if len(label) > 40:
            label = label[:40]
        kb.add_button(label, VkKeyboardColor.SECONDARY)
        label_map[label] = item
        kb.add_line()
    if page > 0:
        kb.add_button("◀️", VkKeyboardColor.SECONDARY)
        kb.add_line()
    if start + page_size < len(items):
        kb.add_button("▶️", VkKeyboardColor.SECONDARY)
        kb.add_line()
    kb.add_button("⬅️ Назад", VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("🏠 Главное Меню", VkKeyboardColor.NEGATIVE)
    return kb, label_map

def show_menu(uid, title, items, page=0):
    state = user_state.setdefault(uid, {"items": [], "history": [], "page": 0, "map": {}, "title": "", "section_id": None, "current_subsection_id": None})
    kb, label_map = subsection_menu(items, page)
    state["items"] = items
    state["page"] = page
    state["map"] = label_map
    state["title"] = title
    send(uid, title, kb)

def handle(uid, text):
    state = user_state.setdefault(uid, {"items": [], "history": [], "page": 0, "map": {}, "title": "", "section_id": None, "current_subsection_id": None})

    def abs_url(u):
        u = urljoin("https://arhcity.ru", u)
        p = urlsplit(u)
        return urlunsplit((p.scheme, p.netloc, quote(p.path), p.query, p.fragment))

    if text in ("Начать", "🏠 Главное Меню"):
        user_state[uid] = {"items": [], "history": [], "page": 0, "map": {}, "title": "", "section_id": None, "current_subsection_id": None}
        send(uid, "🏠 Главное Меню", section_menu())
        return

    if text == "📁 Инвестиционная деятельность":
        page = sources[0]
        section_id = db_save_section(page["title"])
        folders, files = parse(page["source"])
        db_save_items(section_id, None, folders + files)
        db_save_history(uid, "open_section")
        state["section_id"] = section_id
        state["current_subsection_id"] = None
        state["history"] = [{"title": page["title"], "source": page["source"], "subsection_id": None}]
        show_menu(uid, page["title"], folders + files, 0)
        return

    if text == "📁 Торги":
        page = sources[1]
        section_id = db_save_section(page["title"])
        folders, files = parse(page["source"])
        db_save_items(section_id, None, folders + files)
        db_save_history(uid, "open_section")
        state["section_id"] = section_id
        state["current_subsection_id"] = None
        state["history"] = [{"title": page["title"], "source": page["source"], "subsection_id": None}]
        show_menu(uid, page["title"], folders + files, 0)
        return

    if text == "⬅️ Назад":
        h = state.get("history", [])
        if len(h) <= 1:
            user_state[uid] = {"items": [], "history": [], "page": 0, "map": {}, "title": "", "section_id": None, "current_subsection_id": None}
            send(uid, "🏠 Главное Меню", section_menu())
            return
        h.pop()
        last = h[-1]
        state["current_subsection_id"] = last.get("subsection_id")
        folders, files = parse(last["source"])
        db_save_items(state.get("section_id"), state.get("current_subsection_id"), folders + files)
        show_menu(uid, last["title"], folders + files, 0)
        return

    if text == "◀️":
        show_menu(uid, state.get("title", ""), state.get("items", []), max(0, state.get("page", 0) - 1))
        return

    if text == "▶️":
        items = state.get("items", [])
        page = state.get("page", 0) + 1
        if page <= (len(items) - 1) // page_size:
            show_menu(uid, state.get("title", ""), items, page)
        return

    item = state.get("map", {}).get(text)
    if not item:
        return

    url = abs_url(item["url"])

    if item["type"] == "folder":
        section_id = state.get("section_id")
        parent_id = state.get("current_subsection_id")
        subsection_id = db_save_subsection(section_id, parent_id, item["title"], url, "folder")
        folders, files = parse([{"url": url}])
        db_save_items(section_id, subsection_id, folders + files)
        db_save_history(uid, "open_folder", subsection_id=subsection_id)
        state["history"].append({"title": item["title"], "source": [{"url": url}], "subsection_id": subsection_id})
        state["current_subsection_id"] = subsection_id
        show_menu(uid, item["title"], folders + files, 0)
        return

    html = fetch(url)
    desc_parts, links = [], []
    if html:
        soup = BeautifulSoup(html, "html.parser")
        body = soup.find("div", class_="pagebody")
        if body:
            for tag in body.find_all(["p", "li"]):
                t = tag.get_text(" ", strip=True)
                if len(t) < 3:
                    continue
                if t:
                    desc_parts.append(t)
                for a in tag.find_all("a", href=True):
                    u = abs_url(a["href"])
                    if u not in links:
                        links.append(u)

    section_id = state.get("section_id")
    parent_id = state.get("current_subsection_id")
    subsection_id = db_save_subsection(section_id, parent_id, item["title"], url, "file")
    doc_id = db_save_document(subsection_id, item["title"], url, "\n".join(desc_parts))
    db_save_history(uid, "open_document", subsection_id=subsection_id, document_id=doc_id)

    msg = f"📎 {item['title']}\n\n{url}"
    if desc_parts:
        msg += "\n\n📄 Описание страницы:\n" + "\n".join(desc_parts)
    if links:
        msg += "\n\n🔗 Ссылки на документы в тексте:\n" + "\n".join(links)
    send(uid, msg)

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        handle(event.user_id, event.text.strip())
