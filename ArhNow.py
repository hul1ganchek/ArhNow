import os, aiohttp
from io import BytesIO
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

pages = [
    {"title": "Инвестиционная деятельность", "source": [
        {"title": "Старый источник", "url": "https://m.arhcity.ru/?page=1472/0"},
        {"title": "Новый источник", "url": "https://arhcity.gosuslugi.ru/deyatelnost/napravleniya-deyatelnosti/investitsionnaya-deyatelnost/"}
    ]},
    {"title": "Торги", "source": [
        {"title": "Старый источник", "url": "https://m.arhcity.ru/?page=680/0"},
        {"title": "Новый источник", "url": "https://arhcity.gosuslugi.ru/deyatelnost/napravleniya-deyatelnosti/torgi/"}
    ]}
]

image_path = os.path.join(os.path.dirname(__file__), "portal.jpeg")
with open(image_path, "rb") as f:
    image_bytes = f.read()

async def fetch_html(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.text()
    except Exception as e:
        print(f"Ошибка при получении HTML {url}: {e}")
        return ""

def format_page_text(pagebody):
    lines = []
    for tag in pagebody.find_all(["p", "li"]):
        text = tag.get_text(" ", strip=True)
        if not text or len(text) < 3:
            continue
        lines.append(text)
    return "\n\n".join(lines)

async def parse(urls):
    all_folders, all_files = [], []
    for src in urls:
        url = src["url"]
        is_new = "gosuslugi" in url
        html = await fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")
        folders, files = [], []
        def normalize(href, base):
            if not href:
                return None
            if href.startswith("/"):
                href = base + href.lstrip("/")
            elif href.startswith("?"):
                href = base + href
            return href.replace(" ", "%20")
        if is_new:
            for a in soup.select("li.menu-item a.menu-item-link"):
                title = "🆕 " + a.get_text(strip=True)
                href = normalize(a.get("href"), "https://arhcity.gosuslugi.ru/")
                if title and href:
                    folders.append({"title": title, "url": href, "type": "folder"})
            for file_block in soup.select(".tpl-component-gw-file .tpl-block-list-objects .object-item"):
                a = file_block.find("a", class_="item-name", href=True)
                if not a:
                    continue       
                href = normalize(a["href"], "https://arhcity.gosuslugi.ru/")
                if not href or "arhcity.ru/?page=" in href:
                    continue
                title = "🆕 " + a.get_text(strip=True)
                files.append({"title": title, "url": href, "type": "file"})
            for article in soup.select(".tpl-component-gw-base-text article"):
                for p in article.find_all("p"):
                    a = p.find("a", href=True)
                    if not a:
                        continue        
                    href = normalize(a["href"], "https://arhcity.gosuslugi.ru/")
                    if not href or "arhcity.ru/?page=" in href:
                        continue
                    title = "🆕 " + a.get_text(strip=True)
                    files.append({"title": title, "url": href, "type": "file"})
        else:
            pagebody = soup.find("div", class_="pagebody")   
            if pagebody:
                for li in pagebody.find_all("li"):
                    a = li.find("a", href=True)
                    if not a:
                        continue
                    title = ""
                    for elem in a.contents:
                        if getattr(elem, "name", None) == "span" and "secdir-small" in elem.get("class", []):
                            continue
                        elif getattr(elem, "name", None) == "br":
                            continue
                        else:
                            text = elem.strip() if isinstance(elem, str) else elem.get_text(strip=True)
                            title += text
                    href = normalize(a["href"], "https://m.arhcity.ru/")
                    li_classes = li.get("class", [])
                    if "secdir-li1" in li_classes:
                        folders.append({"title": title, "url": href, "type": "folder"})
                    elif "secdir-li2" in li_classes:
                        files.append({"title": title, "url": href, "type": "file"})
                for p in pagebody.find_all("p"):
                    a = p.find("a", href=True)
                    if not a:
                        continue
                    title = a.get_text(strip=True)
                    href = normalize(a["href"], "https://m.arhcity.ru/")
                    files.append({"title": title, "url": href, "type": "file"})
        all_folders.extend(folders)
        all_files.extend(files)
    return all_folders, all_files
    
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE, folders, files, path_title):
    keyboard = []
    for i, f in enumerate(folders):
        key = f"folder_{i}"
        context.user_data[key] = f
        keyboard.append([InlineKeyboardButton(f"📁 {f['title']}", callback_data=key)])
    for i, f in enumerate(files):
        key = f"file_{i}"
        context.user_data[key] = f
        keyboard.append([InlineKeyboardButton(f"📎 {f['title']}", callback_data=key)])
    if context.user_data.get("history"):
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
    if path_title not in ("Инвестиционная деятельность", "Торги"):
        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main")])
    markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        msg = update.callback_query.message
        if msg.photo:
            await msg.edit_caption(caption=path_title, reply_markup=markup)
        else:
            await msg.edit_text(path_title, reply_markup=markup)
    elif update.message:
        await update.message.reply_text(path_title, reply_markup=markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["history"] = []
    keyboard = []
    for i, page in enumerate(pages):
        key = f"root_{i}"
        context.user_data[key] = {"title": page["title"], "source": page["source"], "type": "folder"}
        keyboard.append([InlineKeyboardButton(page["title"], callback_data=key)])
    markup = InlineKeyboardMarkup(keyboard)
    photo = BytesIO(image_bytes)
    photo.name = "portal.jpeg"
    if update.callback_query:
        msg = update.callback_query.message
        if msg.photo:
            await msg.edit_caption(caption="🏠 Главное меню", reply_markup=markup)
        else:
            await msg.reply_photo(photo=photo, caption="🏠 Главное меню", reply_markup=markup)
    elif update.message:
        await update.message.reply_photo(photo=photo, caption="🏠 Главное меню", reply_markup=markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("root_"):
        item = context.user_data.get(data)
        if not item:
            return
        context.user_data["history"] = [{"title": item["title"], "source": item["source"]}]
        folders, files = await parse(item["source"])
        await menu(update, context, folders, files, item["title"])
        context.user_data["current_items"] = folders + files
        return
    if data == "main":
        await start(update, context)
        return
    if data == "back":
        history = context.user_data.get("history", [])
        if len(history) < 2:
            await start(update, context)
            return
        history.pop()
        last = history[-1]
        folders, files = await parse(last["source"])
        await menu(update, context, folders, files, last["title"])
        context.user_data["current_items"] = folders + files
        return
    item = context.user_data.get(data)
    if not item:
        msg = query.message
        if msg.photo:
            await msg.edit_caption("Ошибка выбора")
        else:
            await msg.edit_text("Ошибка выбора")
        return  
    if item["type"] == "file":
        url = item["url"]
        description = ""
        if url.startswith("https://m.arhcity.ru/?page="):
            try:
                page_html = await fetch_html(url)
                page_soup = BeautifulSoup(page_html, "html.parser")
                page_content = page_soup.find("div", class_="pagebody")
                if page_content:
                    description = format_page_text(page_content)  
            except Exception:
                description = ""
        text = f"📎 <b>{item['title']}</b>\n{url}"
        if description:
            text += f"\n\n{description}"
        text = text[:1024]
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back")],[InlineKeyboardButton("🏠 Главное меню", callback_data="main")]])
        msg = query.message
        if msg.photo:
            await msg.edit_caption(caption=text, reply_markup=markup, parse_mode="HTML")
        else:
            await msg.edit_text(text, reply_markup=markup, parse_mode="HTML")
        return
    if item["type"] == "folder":
        history = context.user_data.setdefault("history", [])
        history.append({"title": item["title"], "source": [{"url": item["url"]}]})
        folders, files = await parse([{"url": item["url"]}])
        await menu(update, context, folders, files, item["title"])        

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    if not TOKEN:
        raise ValueError("BOT_TOKEN не найден в переменных окружения")
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    print("Бот запущен...")
    app.run_polling()
