import urllib3
from urllib.parse import urljoin, urlsplit, urlunsplit, quote
import requests
from bs4 import BeautifulSoup

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

def fetch(url):
    try:
        r = requests.get(url, timeout=10, verify=False)
        return r.text
    except Exception as e:
        print(f"Ошибка при получении HTML {url}: {e}")
        return ""

def normalize(base, href):
    if not href:
        return None
    u = urljoin(base, href)
    p = urlsplit(u)
    return urlunsplit((p.scheme, p.netloc, quote(p.path), p.query, p.fragment))
    
def parse(urls):
    folders, files = [], []
    seen = set()
    for src in urls:
        url = src["url"]
        html = fetch(url)
        soup = BeautifulSoup(html, "html.parser")

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