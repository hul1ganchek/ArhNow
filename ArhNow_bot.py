import os
import aiohttp
from selectolax.parser import HTMLParser
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiohttp import web

BASE_URL = "https://m.arhcity.ru/"

START_PAGES = [
    ("Инвестиционная деятельность", BASE_URL + "?page=1472/0"),
    ("Торги", BASE_URL + "?page=680/0")
]

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = "https://arhnow/webhook"

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

    async def close(self):
        if self.session:
            await self.session.close()

http = HTTP()

def fix_url(href: str) -> str:
    if not href:
        return ""
    if href.startswith("/"):
        return BASE_URL + href.lstrip("/")
    if href.startswith("?"):
        return BASE_URL + href
    return href.replace(" ", "%20")

def parse_page(html: str):
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
            "title": " ".join(a.text().split()),
            "url": fix_url(a.attributes.get("href", "")),
            "type": "folder" if "secdir-li1" in (li.attributes.get("class") or []) else "file"
        })

    return items

def format_text(html: str):
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

def page_kb(items):
    buttons = [
        [InlineKeyboardButton(text=i["title"], callback_data=i["url"])]
        for i in items
    ]

    buttons.append([
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

@router.callback_query()
async def open_page(c: CallbackQuery):
    url = c.data
    html = await http.get(url)

    items = parse_page(html)

    if items:
        await c.message.edit_text(
            "Раздел",
            reply_markup=page_kb(items)
        )
        await c.answer()
        return

    desc = format_text(html)

    text = f"📎 <b>Документ</b>\n{url}\n\n{desc}"

    await c.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="home")]
        ])
    )

async def on_startup(bot: Bot):
    await http.init()
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    await http.close()

async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher()
    dp.include_router(router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    dp["bot"] = bot

    webhook_requests_handler = Dispatcher._webhook_request_handler_factory(
        dispatcher=dp,
        bot=bot,
    )

    app.router.add_post(WEBHOOK_PATH, webhook_requests_handler)

    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL)

    print("Бот запущен")

    return app

if __name__ == "__main__":
    web.run_app(main(), host="0.0.0.0", port=3000)
