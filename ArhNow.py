import os, vk_api
import urllib3
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

vk_session = vk_api.VkApi(token=os.getenv("vk_token"))
vk = vk_session.get_api()
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
    kb.add_button("Инвестиционная деятельность", VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("Торги", VkKeyboardColor.SECONDARY)
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
        kb.add_button(label, VkKeyboardColor.SECONDARY if item["type"] == "folder" else VkKeyboardColor.SECONDARY)
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
    state = user_state.setdefault(uid, {"items": [], "history": [], "page": 0, "map": {}, "title": ""})
    kb, label_map = subsection_menu(items, page)
    state["items"] = items
    state["page"] = page
    state["map"] = label_map
    state["title"] = title
    send(uid, title, kb)

def handle(uid, text):
    state = user_state.setdefault(uid, {"items": [], "history": [], "page": 0, "map": {}, "title": ""})

    if text in ("Начать", "🏠 Главное Меню"):
        user_state[uid] = {"items": [], "history": [], "page": 0, "map": {}, "title": ""}
        send(uid, "🏠 Главное Меню", section_menu())
        return

    if text == "Инвестиционная деятельность":
        page = sources[0]
        folders, files = parse(page["source"])
        state["history"] = [{"title": page["title"], "source": page["source"]}]
        show_menu(uid, page["title"], folders + files, 0)
        return

    if text == "Торги":
        page = sources[1]
        folders, files = parse(page["source"])
        state["history"] = [{"title": page["title"], "source": page["source"]}]
        show_menu(uid, page["title"], folders + files, 0)
        return

    if text == "⬅️ Назад":
        history = state.get("history", [])
        if len(history) <= 1:
            user_state[uid] = {"items": [], "history": [], "page": 0, "map": {}, "title": ""}
            send(uid, "🏠 Главное Меню", section_menu())
            return
        history.pop()
        last = history[-1]
        folders, files = parse(last["source"])
        show_menu(uid, last["title"], folders + files, 0)
        return

    if text == "◀️":
        page = max(0, state.get("page", 0) - 1)
        show_menu(uid, state.get("title", ""), state.get("items", []), page)
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

    if item["type"] == "folder":
        folders, files = parse([{"url": item["url"]}])
        state["history"].append({"title": item["title"], "source": [{"url": item["url"]}]})
        show_menu(uid, item["title"], folders + files, 0)
        return

    desc = ""
    html = fetch(item["url"])
    if html:
        soup = BeautifulSoup(html, "html.parser")
        body = soup.find("div", class_="pagebody")
        if body:
            lines = []
            for tag in body.find_all(["p", "li"]):
                t = tag.get_text(" ", strip=True)
                if len(t) >= 3:
                    lines.append(t)
            desc = "\n\n".join(lines)

    msg = f"📎 {item['title']}\n\n{item['url']}"
    if desc:
        msg += f"\n\n{desc}"
    send(uid, msg)

print("Процесс запущен...")

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        handle(event.user_id, event.text.strip())
