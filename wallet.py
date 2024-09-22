import logging
import time
from telegram import Update, Bot, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from pycoingecko import CoinGeckoAPI
from requests.exceptions import Timeout

# Логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Ініціалізація CoinGecko API та бота
cg = CoinGeckoAPI()
TOKEN = '7537724449:AAG0u3MC4GjsLHtYHAJS4qVbtQY-FzspDoE'

# Кеш для результатів
cached_prices = {}
last_cache_time = 0
cache_duration = 60  # 60 секунд

# Баланс монет з вашого гаманця
wallet_balances = {
    'notcoin': 23517.73839,  # NOT
    'dogs-2': 143153.0,      # DOGS
    'the-open-network': 20.77484381,  # TON
    'catizen': 52.2543,  # CATI
    'tether': 53.7169  # USDT
}

# Мапа криптовалют для клавіатури
crypto_map = {
    "🧑‍💻 bitcoin": "bitcoin",
    "📢 ton coin": "the-open-network",
    "🐕 dogs": "dogs-2",
    "🎮 notcoin": "notcoin",
    "🐸 pepe": "pepe",
    "🐈 cati": "catizen"  # Updated from Solana to CATI
}

# Форматування цін
def format_price(price):
    if price > 100:
        return f"${price:.2f}"
    elif price > 1:
        return f"${price:.2f}"
    else:
        return f"${price:.7f}"

# Функція для кешування запитів
async def fetch_prices():
    global cached_prices, last_cache_time
    current_time = time.time()
    if current_time - last_cache_time > cache_duration:
        try:
            cached_prices = cg.get_price(ids=['bitcoin', 'notcoin', 'dogs-2', 'the-open-network', 'pepe', 'catizen', 'tether'], vs_currencies='usd', include_24hr_change='true')
            last_cache_time = current_time
        except Timeout:
            logging.warning("Запит до CoinGecko API закінчився тайм-аутом.")
        except Exception as e:
            logging.error(f"Помилка при запиті до CoinGecko: {e}")
    return cached_prices

# Функція для команди /start з клавіатурою
async def start(update: Update, context):
    start_time = time.time()
    keyboard = [
        ["🧑‍💻 Bitcoin", "📢 Ton Coin"],
        ["🐕 DOGS", "🎮 Notcoin"],
        ["🐸 Pepe", "🐈 CATI"],  # Updated the keyboard from Solana to CATI
        ["💰 Баланс"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text('Виберіть криптовалюту або перевірте баланс:', reply_markup=reply_markup)
    end_time = time.time()
    logging.info(f"Час для відповіді на /start: {end_time - start_time:.2f} секунд")

# Функція для обробки вибору криптовалюти або балансу
async def handle_message(update: Update, context):
    start_time = time.time()
    text = update.message.text.lower()

    if text == "💰 баланс":
        await balance(update, context)
    else:
        crypto = crypto_map.get(text)
        if crypto:
            try:
                # Використовуємо кешовані дані або робимо новий запит
                api_start_time = time.time()
                prices = await fetch_prices()  # Отримуємо кешовані дані
                api_end_time = time.time()
                logging.info(f"Час запиту до CoinGecko API для {crypto}: {api_end_time - api_start_time:.2f} секунд")

                if prices and crypto in prices:
                    process_start_time = time.time()
                    price_per_unit = prices[crypto]['usd']
                    # Перевіряємо чи є зміна за 24 години
                    percent_change_24h = prices[crypto].get('usd_24h_change')
                    if percent_change_24h is None:
                        percent_change_24h = "Немає даних"
                    else:
                        # Форматуємо зміну за 24 години до двох знаків після коми
                        percent_change_24h = f"{percent_change_24h:.2f}"

                    user_balance = wallet_balances.get(crypto, 0)
                    total_value = price_per_unit * user_balance

                    # Формуємо повідомлення
                    message = (
                        f"Криптовалюта: {text.capitalize()}\n"
                        f"Ціна за одиницю: {format_price(price_per_unit)} USD\n"
                        f"Кількість: {user_balance} монет\n"
                        f"Загальна вартість: {format_price(total_value)} USD\n"
                        f"Зміна за 24 години: {percent_change_24h}%"
                    )
                    process_end_time = time.time()
                    logging.info(f"Час обробки даних для {crypto}: {process_end_time - process_start_time:.2f} секунд")

                    # Відправка повідомлення через Telegram API
                    telegram_start_time = time.time()
                    await update.message.reply_text(message)
                    telegram_end_time = time.time()
                    logging.info(f"Час відправки повідомлення через Telegram API для {crypto}: {telegram_end_time - telegram_start_time:.2f} секунд")
                else:
                    await update.message.reply_text("Немає даних для вибраної криптовалюти.")
            except Exception as e:
                logging.error(f"Помилка отримання даних: {e}")
                await update.message.reply_text(f"Помилка отримання даних: {e}")

    end_time = time.time()
    logging.info(f"Час обробки запиту користувача: {end_time - start_time:.2f} секунд")

# Функція для команди /balance для відображення детальної інформації про всі монети
async def balance(update: Update, context):
    start_time = time.time()
    try:
        api_start_time = time.time()
        prices = await fetch_prices()  # Отримуємо кешовані дані
        api_end_time = time.time()
        logging.info(f"Час запиту до CoinGecko API для балансу: {api_end_time - api_start_time:.2f} секунд")

        total_value = 0
        balance_details = []

        coin_names = {
            'notcoin': 'Notcoin',
            'dogs-2': 'Dogs',
            'the-open-network': 'Ton coin',
            'catizen': 'Cati',
            'tether': 'USDT'  # Adding USDT to display it in the balance
        }

        for coin, balance in wallet_balances.items():
            if coin in prices:  # Перевіряємо, чи є ціна для монети
                coin_price = prices[coin]['usd']
                coin_value = balance * coin_price
                total_value += coin_value
                balance_details.append(f"{coin_names.get(coin, coin.capitalize())}: {balance:.6f} = {format_price(coin_value)} USD")
            else:
                balance_details.append(f"{coin_names.get(coin, coin.capitalize())}: Дані не знайдено")

        details_message = "\n".join(balance_details)
        total_message = f"Детальна інформація:\n{details_message}\n\nЗагальна вартість всіх монет: {total_value:.2f} USD"

        process_start_time = time.time()
        await update.message.reply_text(total_message)
        process_end_time = time.time()
        logging.info(f"Час обробки та відправки повідомлення через Telegram API для балансу: {process_end_time - process_start_time:.2f} секунд")

    except Exception as e:
        logging.error(f"Помилка: {e}")
        await update.message.reply_text(f"Помилка: {e}")

    end_time = time.time()
    logging.info(f"Загальний час обробки запиту балансу: {end_time - start_time:.2f} секунд")

# Основна функція для запуску бота
if __name__ == '__main__':
    bot = Bot(token=TOKEN)  # Створення об'єкта бота
    application = ApplicationBuilder().token(TOKEN).build()

    # Команда /start
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запуск бота
    logging.info("Бот запущено!")
    application.run_polling()


#cd "C:\Users\reset\OneDrive\Робочий стіл\python_files"
#python p.py
