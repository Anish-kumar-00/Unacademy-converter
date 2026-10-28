import os
import re
import html
from urllib.parse import urlparse
from io import BytesIO

import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="HTML → Telegram", page_icon="📨", layout="wide")
st.title("📨 HTML → Telegram Sender")
st.caption("HTML se video links nikaalo aur original PDF files Telegram par bhejo.")

TELEGRAM_API = "https://api.telegram.org"

def get_setting(name: str, fallback: str = "") -> str:
    """Read a setting from Streamlit secrets first, then environment variables."""
    try:
        value = st.secrets.get(name, fallback)
    except Exception:
        value = fallback
    return str(value or os.getenv(name, fallback)).strip()

def extract_items(raw_html: str):
    soup = BeautifulSoup(raw_html, "html.parser")
    video_items = []
    pdf_items = []
    seen_video = set()
    seen_pdf = set()

    for anchor in soup.find_all("a", href=True):
        url = html.unescape(anchor["href"].strip())
        if not url.startswith(("http://", "https://")):
            continue

        title = anchor.get_text(" ", strip=True) or url
        url_lower = url.lower()
        title_lower = title.lower()

        if ".pdf" in url_lower or "pdf" in title_lower or "slides" in title_lower or "notes" in title_lower:
            if url not in seen_pdf:
                pdf_items.append({"title": title, "url": url})
                seen_pdf.add(url)
            continue

        # The supplied course HTML uses player-page links for video lessons.
        looks_like_video = (
            any(word in title_lower for word in ("▶", "video", "lecture", "watch"))
            or any(host in url_lower for host in ("youtube.com", "youtu.be", "vimeo.com", "netlify.app"))
            or bool(re.search(r"\.(mp4|m3u8|webm)(?:$|[?#])", url_lower))
        )
        if looks_like_video and url not in seen_video:
            video_items.append({"title": title, "url": url})
            seen_video.add(url)

    return video_items, pdf_items

def telegram_call(token: str, method: str, data=None, files=None):
    endpoint = f"{TELEGRAM_API}/bot{token}/{method}"
    response = requests.post(endpoint, data=data, files=files, timeout=90)
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(result.get("description", "Telegram API returned an error"))
    return result["result"]

def send_text(token: str, chat_id: str, text: str):
    # Telegram message text has a 4096-character limit; split conservatively.
    chunks = [text[i:i + 3900] for i in range(0, len(text), 3900)] or [text]
    for chunk in chunks:
        telegram_call(token, "sendMessage", {"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True})

def fetch_pdf(url: str):
    response = requests.get(
        url,
        timeout=90,
        headers={"User-Agent": "Mozilla/5.0 (compatible; HTMLTelegramSender/1.0)"},
        stream=True,
    )
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "").lower()
    data = response.content
    if not data.startswith(b"%PDF") and "pdf" not in content_type:
        raise ValueError("Link se PDF response nahi mili (shayad access/login required hai).")
    return data

def send_pdf(token: str, chat_id: str, title: str, url: str):
    data = fetch_pdf(url)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("._") or "document"
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"
    file_obj = BytesIO(data)
    file_obj.name = safe_name
    telegram_call(
        token,
        "sendDocument",
        data={"chat_id": chat_id, "caption": title[:900]},
        files={"document": (safe_name, file_obj, "application/pdf")},
    )

with st.sidebar:
    st.header("Telegram setup")
    token = st.text_input("Bot token", value=get_setting("TELEGRAM_BOT_TOKEN"), type="password")
    chat_id = st.text_input("Destination chat/channel ID", value=get_setting("TELEGRAM_CHAT_ID"))
    st.info("Bot ko destination chat/channel mein add karein. Channel ke liye bot ko post permission/admin access chahiye.")

uploaded = st.file_uploader("Apni HTML file upload karein", type=["html", "htm"])
pasted_html = st.text_area("Ya HTML yahan paste karein (optional)", height=140, placeholder="<!doctype html> ...")

raw_html = ""
if uploaded is not None:
    raw_html = uploaded.getvalue().decode("utf-8", errors="replace")
elif pasted_html.strip():
    raw_html = pasted_html

if raw_html:
    video_items, pdf_items = extract_items(raw_html)
    left, right = st.columns(2)
    with left:
        st.subheader(f"Video links: {len(video_items)}")
        for item in video_items:
            st.markdown(f"- [{item['title']}]({item['url']})")
    with right:
        st.subheader(f"PDF links: {len(pdf_items)}")
        for item in pdf_items:
            st.markdown(f"- [{item['title']}]({item['url']})")

    st.warning("Sirf wahi videos/PDFs forward ya upload karein jinke share karne ka aapke paas adhikar/permission ho.")

    if st.button("🚀 Telegram par bhejo", type="primary", disabled=not (token and chat_id)):
        if not video_items and not pdf_items:
            st.error("HTML mein video ya PDF links nahi mile.")
        else:
            progress = st.progress(0)
            status = st.empty()
            total = len(video_items) + len(pdf_items)
            completed = 0
            failures = []

            # Send video URLs as text messages; do not download video files.
            for item in video_items:
                try:
                    send_text(token, chat_id, f"▶️ {item['title']}\n{item['url']}")
                except Exception as exc:
                    failures.append(f"Video link: {item['title']} — {exc}")
                completed += 1
                progress.progress(completed / total)
                status.write(f"Video links bhej rahe hain… {completed}/{total}")

            # Download and upload the linked PDF files.
            for item in pdf_items:
                try:
                    send_pdf(token, chat_id, item["title"], item["url"])
                except Exception as exc:
                    failures.append(f"PDF: {item['title']} — {exc}")
                completed += 1
                progress.progress(completed / total)
                status.write(f"PDF upload ho rahe hain… {completed}/{total}")

            if failures:
                st.error("Kuch items send nahi hue:")
                for failure in failures:
                    st.write(f"- {failure}")
                st.warning("Private/login-protected links, oversized PDFs, ya Telegram permissions ki wajah se failure ho sakta hai.")
            else:
                st.success(f"Complete! {len(video_items)} video links aur {len(pdf_items)} PDF files Telegram par bhej di gayi.")

st.divider()
st.caption("Note: Streamlit app ko khol kar HTML upload karne aur button dabane par hi sending hoti hai. Yeh background/always-on Telegram bot nahi hai.")
