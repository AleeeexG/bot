# Arbitrage Bot (DEX ↔ MEXC)

Цей бот перевіряє ціни на MEXC (ф'ючерси) та DEX (через CoinGecko) і надсилає сигнали, коли виявлено арбітражну можливість.

## 🚀 Розгортання на [Render.com](https://render.com)

1. Зробіть **Fork** цього репозиторію у свій GitHub
2. Увійдіть на [https://render.com](https://render.com) → New → Web Service
3. Підключіть ваш форк
4. Налаштування:
   - **Environment**: Python
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `python arbitrage_bot.py`
   - **Type**: Background Worker
5. У вкладці **Environment Variables** додайте:
   - `TELEGRAM_TOKEN` — токен вашого Telegram-бота
   - `CHAT_ID` — ID вашого чату (з собою або групою)

Готово! Бот буде запускатись автоматично та надсилати сигнали 24/7.
