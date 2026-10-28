# HTML to Telegram Sender (Streamlit)

This app accepts an HTML course page, extracts lesson/player URLs and PDF links, then:
- sends video URLs to a Telegram chat/channel as messages (video files are not downloaded)
- downloads linked PDFs and uploads the PDF documents to Telegram

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud
1. Push `app.py`, `requirements.txt`, and this README to a GitHub repository.
2. Create a Streamlit app and select the repository, branch, and `app.py`.
3. In **App → Settings → Secrets**, add:
   ```toml
   TELEGRAM_BOT_TOKEN = "your_bot_token"
   TELEGRAM_CHAT_ID = "your_chat_or_channel_id"
   ```
4. Add your bot to the destination chat/channel. For a channel, give it permission to post.
5. Open the app, upload the HTML, review the extracted items, and press **Telegram par bhejo**.

You can also enter the bot token and chat ID in the sidebar, but using Streamlit Secrets is safer.

## Important
- This is a user-triggered Streamlit workflow, not a continuously running Telegram bot. The app sends only after a user uploads/pastes HTML and presses the button.
- It sends video links, not video files.
- It uploads PDFs only when the PDF URL is publicly accessible to the app. Login-protected or expired links may fail.
- Use only material you own or are authorized to share.
- Large PDFs may fail due to Telegram/API or hosting limits.
- Keep your bot token private. If it is exposed, revoke it through BotFather and replace it.
