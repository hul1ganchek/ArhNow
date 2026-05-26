from database import *
from parser import *
from vk_ui import *

def handle(uid, text):
    state = user_state.setdefault(uid, {"items": [], "history": [], "page": 0, "map": {}, "title": "", "section_id": None, "current_subsection_id": None})

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

    url = normalize("https://arhcity.ru", item["url"])

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
                    u = normalize("https://arhcity.ru", a["href"])
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
