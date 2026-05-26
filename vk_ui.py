import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

vk_session = vk_api.VkApi(token="vk1.a.vToJwMVDOFKdfy4mT1yfviYsLKWKK-2wcIPx2LPKYfQnez4EUXrxFZFfyRBxS1rSiNWJ8j40PtDA-NO1Yoz9KkFdyTHCC2xVC2Vp27jyfJ2NS74yorT6bOKgTTYD_mWY0vIJ_ZslSKeRtGCUytbW20F2Ql8Xxo034xlFwrsPjgEcNDaGleJ1zUs1_qy-hyeGwYTz-42yG93kESZDV6XbtA")
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

user_state = {}
page_size = 6

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