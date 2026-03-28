from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from aiogram.filters import Command
from aiohttp import web
import aiohttp
from selectolax.parser import HTMLParser

BASE_URL = "https://m.arhcity.ru/"

START_PAGES = [
    ("Инвестиционная деятельность", BASE_URL + "?page=1472/0"),
    ("Торги", BASE_URL + "?page=680/0")
]

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = "https://arhnow.bothost.ru/webhook"

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

# ---------- PARSE ----------
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
    buttons = [[InlineKeyboardButton(text=i["title"], callback_data=i["url"])] for i in items]
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="home")])
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
    html = await http.get(c.data)
    items = parse_page(html)

    if items:
        await c.message.edit_text("Раздел", reply_markup=page_kb(items))
        return

    desc = format_text(html)
    await c.message.edit_text(f"{desc[:4000]}")

dp = Dispatcher()
dp.include_router(router)

async def handle(request):
    bot = request.app["bot"]
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return web.Response()

async def on_startup(app):
    bot = app["bot"]
    await http.init()
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook установлен")

async def on_shutdown(app):
    bot = app["bot"]
    await bot.delete_webhook()
    await http.close()

bot = Bot("8500696080:AAGjjcMHCdgjBxAgA40qI3CziyQHaHwXvSs")
app = web.Application()
app["bot"] = bot

app.router.add_post(WEBHOOK_PATH, handle)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

print("Сервер стартует...")
web.run_app(app, host="0.0.0.0", port=3000)
