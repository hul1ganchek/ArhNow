import aiohttp
from selectolax.parser import HTMLParser
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

BASE_URL = "https://m.arhcity.ru/"

START_PAGES = [
    ("Инвестиционная деятельность", BASE_URL + "?page=1472/0"),
    ("Торги", BASE_URL + "?page=680/0")
]

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = "https://arhnow.bothost/webhook"

class HTTP:
    def __init__(self):
        self.session = None

    async def init(self):
        self.session = aiohttp.ClientSession()

    async def get(self, url):
        try:
            async with self.session.get(url) as r:
                return await r.text()
        except:
            return ""

http = HTTP()

def fix_url(href):
    if not href:
        return ""
    if href.startswith("/"):
        return BASE_URL + href.lstrip("/")
    if href.startswith("?"):
        return BASE_URL + href
    return href.replace(" ", "%20")

def parse_page(html):
    tree = HTMLParser(html)
    body = tree.css_first("div.pagebody")
    if not body:
        return []

    items = []

    for li in body.css("li"):
        a = li.css_first("a")
        if not a:
            continue

        items.append({
            "title": "".join(a.text().split()),
            "url": fix_url(a.attributes.get("href", "")),
            "type": "folder" if "secdir-li1" in li.attributes.get("class", []) else "file"
        })

    return items

def format_text(html):
    tree = HTMLParser(html)
    body = tree.css_first("div.pagebody")
    if not body:
        return ""

    return "\n\n".join(
        el.text().strip()
        for el in body.css("p,li")
        if len(el.text().strip()) > 2
    )

def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=u)]
        for t, u in START_PAGES
    ])

def page_kb(items, parent_url):
    buttons = []

    for i in items:
        buttons.append([
            InlineKeyboardButton(text=i["title"], callback_data=i["url"])
        ])

    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="home"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="home")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

router = Router()

@router.message(Command("start"))
async def start(m: Message):
    await m.answer("Главное меню", reply_markup=main_kb())

@router.callback_query(F.data == "home")
async def home(c: CallbackQuery):
    await c.message.edit_text("Главное меню", reply_markup=main_kb())
    await c.answer()

@router.callback_query(F.data.startswith("back|"))
async def back(c: CallbackQuery):
    url = c.data.split("|", 1)[1]
    html = await http.get(url)
    items = parse_page(html)

    await c.message.edit_text(
        "Раздел",
        reply_markup=page_kb(items, BASE_URL)
    )
    await c.answer()

@router.callback_query()
async def open_page(c: CallbackQuery):
    url = c.data
    html = await http.get(url)

    items = parse_page(html)

    if items:
        await c.message.edit_text(
            "Раздел",
            reply_markup=page_kb(items, url)
        )
        await c.answer()
        return

    desc = format_text(html)

    text = f"📎 <b>Документ</b>\n{url}\n\n{desc}"

    await c.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="home")]
        ])
    )

async def on_startup(bot: Bot):
    await http.init()
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    await http.session.close()

async def main():
    bot = Bot("TOKEN")
    dp = Dispatcher()
    dp.include_router(router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    web.run_app(app, host="0.0.0.0", port=3000)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
