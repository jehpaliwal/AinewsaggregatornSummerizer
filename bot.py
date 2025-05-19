from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.helpers import escape_markdown
from newspaper import Article
from transformers import pipeline
import requests
import logging

# ✅ API Keys
BOT_TOKEN = "7397604157:AAFyGkA-R9o2dkO9pDI7jiZp5vX633Vo_AI"
NEWS_API_KEY = "565bcb4586c9436a85845e21d5067c4c"

# ✅ Summarizer
summarizer = pipeline("summarization", model="t5-small", tokenizer="t5-small")

# 🔎 Search news with keyword
def search_news_api(query):
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={query}&sortBy=publishedAt&pageSize=3&language=en&apiKey={NEWS_API_KEY}"
    )
    try:
        response = requests.get(url)
        data = response.json()
        if data.get("status") == "ok":
            return [
                {"title": a["title"], "url": a["url"]}
                for a in data.get("articles", [])
                if a.get("title") and a.get("url")
            ]
    except Exception as e:
        print("❌ Error fetching search news:", e)
    return []

# 📰 Top headlines
def fetch_latest_headlines():
    url = f"https://newsapi.org/v2/top-headlines?country=us&pageSize=3&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get("status") == "ok":
            return [
                {"title": a["title"], "url": a["url"]}
                for a in data.get("articles", [])
                if a.get("title") and a.get("url")
            ]
    except Exception as e:
        print("⚠️ Error fetching top headlines:", e)
    return []

# 📰 Extract article text
def extract_article(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        if len(article.text) < 200:
            return None
        return {"title": article.title, "text": article.text}
    except Exception as e:
        print(f"❌ Error extracting {url}: {e}")
        return None

# 🧠 Summarize text
def summarize_text(text):
    try:
        text = text.strip().replace("\n", " ")
        if len(text.split()) > 500:
            text = " ".join(text.split()[:500])
        summary = summarizer("summarize: " + text, max_length=80, min_length=30, do_sample=False)
        return summary[0]["summary_text"]
    except Exception as e:
        print("⚠️ Summarization error:", e)
        return "⚠️ Couldn't summarize."

# 🤖 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to NewsBot!*\n\n"
        "Just send me a topic like `AI`, `sports`, or `crypto` and I’ll find the top news for you.\n\n"
        "Try /latest or /help to see more.",
        parse_mode="Markdown"
    )

# 🤖 /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 *Available Commands:*\n"
        "/start - Welcome message\n"
        "/help - Show this help\n"
        "/latest - Top trending news\n\n"
        "💬 Or type any topic like `AI`, `climate`, or `tech`.",
        parse_mode="Markdown"
    )

# 🤖 /latest
async def latest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📰 Fetching top news headlines...")
    articles = fetch_latest_headlines()
    if not articles:
        await update.message.reply_text("❌ Couldn't find any top news.")
        return

    reply = "🗞 *Top Headlines:*\n\n"
    for article in articles:
        reply += (
            f"*{escape_markdown(article['title'], version=2)}*\n"
            f"🔗 [Read more]({escape_markdown(article['url'], version=2)})\n\n"
        )
    await update.message.reply_text(reply, parse_mode="MarkdownV2")

# 🤖 Handle topic input
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.message.text.strip()

        if not query or len(query) < 2:
            await update.message.reply_text("❓ Please enter a valid topic.")
            return

        await update.message.reply_text(
            f"🔍 Searching for: `{escape_markdown(query, version=2)}`",
            parse_mode="MarkdownV2"
        )

        articles = search_news_api(query)
        if not articles:
            await update.message.reply_text("❌ Couldn't find any news.")
            return

        summaries = []
        for article_info in articles:
            extracted = extract_article(article_info["url"])
            if extracted:
                summary = summarize_text(extracted["text"])
                summaries.append((extracted["title"], summary, article_info["url"]))

        if summaries:
            reply = f"🗞 *Top News on:* `{escape_markdown(query, version=2)}`\n\n"
            for title, summary, url in summaries:
                reply += (
                    f"*{escape_markdown(title, version=2)}*\n"
                    f"_{escape_markdown(summary, version=2)}_\n"
                    f"🔗 [Read more]({escape_markdown(url, version=2)})\n\n"
                )
            await update.message.reply_text(reply, parse_mode="MarkdownV2")
        else:
            await update.message.reply_text(
                "⚠️ I found articles, but couldn’t summarize them. Try another topic."
            )

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        await update.message.reply_text("⚠️ Something went wrong. Please try again later.")

# 🚀 Run the bot
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("✅ Bot is running...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("latest", latest_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()
