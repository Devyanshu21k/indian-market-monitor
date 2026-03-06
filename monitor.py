import feedparser
import requests
import os
import hashlib

# =============================
# TELEGRAM CONFIG
# =============================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def send_telegram(message):

    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram credentials missing")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": message
        })
    except Exception as e:
        print("Telegram error:", e)


# =============================
# STORAGE FOR PROCESSED NEWS
# =============================

PROCESSED_FILE = "processed_news.txt"


def load_processed():

    try:
        with open(PROCESSED_FILE, "r") as f:
            return set(line.strip() for line in f)
    except:
        return set()


def save_processed(article_hash):

    with open(PROCESSED_FILE, "a") as f:
        f.write(article_hash + "\n")


# =============================
# NEWS SOURCES
# =============================

news_sources = [

# global geopolitics
"https://news.google.com/rss/search?q=war+oil+inflation+interest+rate+india+markets&hl=en-IN&gl=IN&ceid=IN:en",
"https://www.reuters.com/world/rss",
"https://feeds.bbci.co.uk/news/world/rss.xml",

# global economics
"https://www.reuters.com/markets/rss",
"https://feeds.bbci.co.uk/news/business/rss.xml",

# india markets
"https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",

# macro policy
"https://news.google.com/rss/search?q=federal+reserve+OR+rbi+policy+OR+interest+rates",

# commodities
"https://news.google.com/rss/search?q=oil+prices+OR+crude+oil+OPEC"

]


# =============================
# KEYWORDS
# =============================

keywords = [
"war",
"missile",
"military strike",
"oil price",
"crude oil",
"opec",
"inflation",
"interest rate",
"rate hike",
"rate cut",
"central bank",
"federal reserve",
"rbi policy",
"sanctions",
"export ban",
"trade restriction",
"bank crisis",
"market crash"
]

noise_words = [
"opinion",
"analysis",
"newsletter",
"podcast",
"live updates",
"morning briefing",
"what to watch",
"stocks to watch",
"market wrap"
]


# =============================
# FETCH NEWS
# =============================

def fetch_news():

    articles = []
    seen_hashes = load_processed()

    for source in news_sources:

        try:
            feed = feedparser.parse(
                source,
                request_headers={"User-Agent": "Mozilla/5.0"}
            )
        except Exception as e:
            print(f"RSS error for {source}: {e}")
            continue

        for entry in feed.entries:

            title = entry.title.strip()

            title_lower = title.lower()
            # short headline filter
            if len(title) < 35:
                continue

            # keyword filter
            if any(word in title_lower for word in noise_words):
                continue
            # stricter keuword filter
            if not any(word in title_lower for word in noise_words):
                continue
            # prevent very similar headline
            if any(title_lower[:40] in a["title"].lower() for a in articles):
                continue

            # create hash
            article_hash = hashlib.md5(title.encode()).hexdigest()

            if article_hash in seen_hashes:
                continue

            save_processed(article_hash)

            articles.append({
                "title": title,
                "link": entry.link
            })

    print(f"Articles fetched: {len(articles)}")

    return articles


# =============================
# CLASSIFY EVENT
# =============================

def classify_event(title):

    t = title.lower()

    if "war" in t or "missile" in t or "military" in t:
        return "Geopolitical Conflict"

    if "oil" in t or "crude" in t or "opec" in t:
        return "Oil Market Shock"

    if "inflation" in t or "cpi" in t:
        return "Inflation News"

    if "rate" in t or "federal reserve" in t or "rbi" in t:
        return "Interest Rate Policy"

    if "sanction" in t:
        return "Trade Sanctions"

    return None


# =============================
# NSE MARKET DATA
# =============================

def get_market_data():

    url = "https://www.nseindia.com/api/allIndices"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    market = {
        "nifty": 0,
        "bank": 0,
        "it": 0
    }

    try:

        response = requests.get(url, headers=headers)
        data = response.json()

        for index in data["data"]:

            if index["index"] == "NIFTY 50":
                market["nifty"] = float(index["percentChange"])

            if index["index"] == "NIFTY BANK":
                market["bank"] = float(index["percentChange"])

            if index["index"] == "NIFTY IT":
                market["it"] = float(index["percentChange"])

    except Exception as e:
        print("Market data error:", e)

    return market


# =============================
# CONFIRM EVENT
# =============================

def confirm_event(event, market):

    if event == "Geopolitical Conflict" and market["nifty"] < -0.5:
        return True

    if event == "Oil Market Shock" and market["nifty"] < -0.5:
        return True

    if event == "Inflation News" and market["bank"] < -0.5:
        return True

    if event == "Interest Rate Policy" and market["bank"] < -0.5:
        return True

    if event == "Trade Sanctions" and market["it"] < -0.5:
        return True

    return False


# =============================
# MAIN MONITOR FUNCTION
# =============================

def run_monitor():

    print("Running market monitor...")

    news = fetch_news()
    market = get_market_data()

    for article in news:

        event = classify_event(article["title"])

        if not event:
            continue

        confirmed = confirm_event(event, market)

        if confirmed:

            message = f"""
🚨 MARKET ALERT

Event: {event}

Headline:
{article['title']}

Market Data
NIFTY 50: {market['nifty']} %
NIFTY BANK: {market['bank']} %
NIFTY IT: {market['it']} %

Source:
{article['link']}
"""

            print(message)
            send_telegram(message)


# =============================
# ENTRY POINT
# =============================

if __name__ == "__main__":
    run_monitor()





