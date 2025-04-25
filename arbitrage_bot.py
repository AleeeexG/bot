import requests
import time
from datetime import datetime
import asyncio
import telegram
from telegram import Bot

# Налаштування
SPREAD_MIN = 3.0  # Мінімальний спред 3%
SPREAD_MAX = 50.0  # Максимальний спред 50% (відсіюємо великі коливання)
VOLUME_MIN = 100000  # Мінімальний об'єм торгів ($)
CHECK_INTERVAL = 30  # Перевірка кожні 30 сек
TELEGRAM_TOKEN = "  # Опціонально
CHAT_ID = "  # Опціонально

class ArbitrageBot:
    def __init__(self):
        self.active_signals = {}
        self.bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN and CHAT_ID else None
        self.session = requests.Session()
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

    def get_mexc_futures(self):
        """Отримує ф'ючерсні пари MEXC з об'ємом"""
        try:
            url = "https://api.mexc.com/api/v3/ticker/24hr"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [
                (ticker['symbol'], float(ticker['quoteVolume']))
                for ticker in data 
                if ticker['symbol'].endswith('USDT') and float(ticker['quoteVolume']) >= VOLUME_MIN
            ]
        except Exception as e:
            print(f"⚠️ Помилка отримання пар MEXC: {e}")
            return []

    def get_dex_price(self, coin_id):
        """Ціна з CoinGecko"""
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()[coin_id]['usd']
        except:
            return None

    def check_pair(self, symbol):
        """Перевіряє пару на арбітраж з обмеженням коливань"""
        try:
            ticker_url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
            response = self.session.get(ticker_url, timeout=5)
            response.raise_for_status()
            mexc_price = float(response.json()['price'])
            
            coin_id = symbol.lower().replace('usdt', '')
            dex_price = self.get_dex_price(coin_id)
            if not dex_price:
                return None
                
            spread = ((mexc_price - dex_price) / dex_price) * 100
            
            # Фільтрація занадто великих коливань
            if abs(spread) > SPREAD_MAX:
                print(f"ℹ️ Пропущено {symbol}: спред {abs(spread):.2f}% > {SPREAD_MAX}% (завелике коливання)")
                return None
                
            return spread, mexc_price, dex_price
        except Exception as e:
            print(f"⚠️ Помилка перевірки пари {symbol}: {e}")
            return None

    async def send_alert(self, symbol, spread, mexc_price, dex_price, is_new=True):
        """Надсилає/оновлює сигнал"""
        direction = "MEXC > DEX" if spread > 0 else "MEXC < DEX"
        action = "Купуйте на DEX, продавайте на MEXC" if spread > 0 else "Купуйте на MEXC, продавайте на DEX"
        
        msg = (
            f"\n{'🚨 НОВИЙ СИГНАЛ' if is_new else '🔄 ОНОВЛЕННЯ'} | {datetime.now().strftime('%H:%M:%S')}\n"
            f"📌 {symbol} | {direction}\n"
            f"▪ MEXC: {mexc_price:.8f} $\n"
            f"▪ DEX:  {dex_price:.8f} $\n"
            f"📊 Спред: {abs(spread):.2f}%\n"
            f"💡 {action}"
        )
        print(msg)

        if self.bot:
            try:
                await self.bot.send_message(chat_id=CHAT_ID, text=msg)
            except Exception as e:
                print(f"⚠️ Помилка Telegram: {e}")

    async def run(self):
        """Головний цикл"""
        print(f"🔍 Старт моніторингу (спред {SPREAD_MIN}%-{SPREAD_MAX}%, об'єм ≥ ${VOLUME_MIN:,})...")
        
        while True:
            try:
                futures = self.get_mexc_futures()
                print(f"\n🔎 Перевірка {len(futures)} пар | {datetime.now().strftime('%H:%M:%S')}")
                
                for symbol, volume in futures:
                    result = self.check_pair(symbol)
                    if not result:
                        continue
                        
                    spread, mexc_price, dex_price = result
                    
                    # Фільтр за мінімальним спредом
                    if abs(spread) < SPREAD_MIN:
                        if symbol in self.active_signals:
                            print(f"❌ СКАСОВАНО {symbol} | {datetime.now().strftime('%H:%M:%S')}")
                            del self.active_signals[symbol]
                        continue
                    
                    if symbol in self.active_signals:
                        prev_spread, _ = self.active_signals[symbol]
                        if abs(spread - prev_spread) > 1.0:
                            await self.send_alert(symbol, spread, mexc_price, dex_price, is_new=False)
                            self.active_signals[symbol] = (spread, spread > 0)
                    else:
                        await self.send_alert(symbol, spread, mexc_price, dex_price)
                        self.active_signals[symbol] = (spread, spread > 0)
                
                await asyncio.sleep(CHECK_INTERVAL)
            except KeyboardInterrupt:
                print("\n🛑 Зупинка моніторингу...")
                break
            except Exception as e:
                print(f"⚠️ Критична помилка: {e}")
                await asyncio.sleep(60)

if __name__ == '__main__':
    bot = ArbitrageBot()
    try:
        asyncio.run(bot.run())
    finally:
        if hasattr(bot, 'session'):
            bot.session.close()
