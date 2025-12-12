import aiohttp
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8500696080:AAGjjcMHCdgjBxAgA40qI3CziyQHaHwXvSs"
BASE_URL = "https://m.arhcity.ru/"

async def fetch_html(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.text()

async def parse_page(url):
    html = await fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    pagebody = soup.find("div", class_="pagebody")
    if not pagebody:
        return [], []

    folders, files = [], []

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

        href = a["href"]
        if href.startswith("/"):
            href = BASE_URL + href.lstrip("/")
        elif href.startswith("?"):
            href = BASE_URL + href
        if " " in href:
            href = href.replace(" ", "%20")

        li_classes = li.get("class", [])

        if "secdir-li1" in li_classes:
            folders.append({"title": title, "url": href, "type": "folder"})
        elif "secdir-li2" in li_classes:
            description = ""
            if href.startswith(BASE_URL + "?page="):
                try:
                    page_html = await fetch_html(href)
                    page_soup = BeautifulSoup(page_html, "html.parser")
                    page_content = page_soup.find("div", class_="pagebody")
                    if page_content:
                        description = page_content.get_text(strip=True)
                except Exception:
                    description = ""
            files.append({"title": title, "url": href, "type": "file", "description": description})

    for p in pagebody.find_all("p"):
        a = p.find("a", href=True)
        if not a:
            continue

        title = a.get_text(strip=True)
        href = a["href"]

        if href.startswith("/"):
            href = BASE_URL + href.lstrip("/")
        elif href.startswith("?"):
            href = BASE_URL + href
        if " " in href:
            href = href.replace(" ", "%20")

        files.append({"title": title, "url": href, "type": "file"})

    return folders, files

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, folders, files, path_title):
    keyboard = []

    for i, f in enumerate(folders):
        key = f"folder_{i}"
        context.user_data[key] = f
        keyboard.append([InlineKeyboardButton(f["title"], callback_data=key)])

    for i, f in enumerate(files):
        key = f"file_{i}"
        context.user_data[key] = f
        keyboard.append([InlineKeyboardButton(f["title"], callback_data=key)])

    if context.user_data.get("history"):
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])

    if path_title != "Инвестиционная деятельность":
        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main")])

    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.edit_text(path_title, reply_markup=markup)
    else:
        await update.message.reply_text(path_title, reply_markup=markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["history"] = []
    url = BASE_URL + "?page=1472/0"
    folders, files = await parse_page(url)
    await show_menu(update, context, folders, files, "Инвестиционная деятельность")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

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
        folders, files = await parse_page(last["url"])
        await show_menu(update, context, folders, files, last["title"])
        return

    item = context.user_data.get(data)
    if not item:
        await query.edit_message_text("Ошибка выбора")
        return

    if item["type"] == "file":
        text = f"📎 <b>{item['title']}</b>\n{item['url']}"
        if item.get("description"):
            text += f"\n\n{item['description']}"

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад", callback_data="back")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main")]
        ])

        await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
        return

    if item["type"] == "folder":
        history = context.user_data.setdefault("history", [])
        history.append({"title": item["title"], "url": item["url"]})
        folders, files = await parse_page(item["url"])
        await show_menu(update, context, folders, files, item["title"])

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    print("Бот запущен...")
    app.run_polling()