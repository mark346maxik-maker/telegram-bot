import os
import json
import logging
import requests
import time
from pathlib import Path
import urllib3
from flask import Flask
from threading import Thread

# ========== FLASK ДЛЯ PING ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "🌌 Астрологический бот работает"

@app.route('/ping')
def ping():
    return "pong"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    print("🚀 Запуск Flask сервера...")
    app.run(host='0.0.0.0', port=8080)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== СИСТЕМА ДОСТУПА ==========
ALLOWED_USERS = [1948172415,878048905,751640039]  # 🔹 Ваш ID

def check_access(user_id):
    return user_id in ALLOWED_USERS

def private_access_required(func):
    def wrapper(message):
        if not check_access(message.get('from', {}).get('id')):
            return {"error": "Access denied"}
        return func(message)
    return wrapper

# ========== КОНФИГУРАЦИЯ ==========
# В Render Environment Variables добавьте:
# TELEGRAM_BOT_TOKEN = ваш токен
# GEN_API_KEY = sk-BupGwWxdPav0VY1eIHwryfLQAnWgcVyZjacxxyok5mw16YyK5wyqPJyRCyOb

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GEN_API_KEY = os.environ.get('GEN_API_KEY', "sk-BupGwWxdPav0VY1eIHwryfLQAnWgcVyZjacxxyok5mw16YyK5wyqPJyRCyOb")
GEN_API_URL = "https://api.gen-api.ru/api/v1/networks/gpt-4o-mini"

if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN не найден!")
    exit(1)

logger.info("✅ Все токены загружены успешно!")

# Глобальные переменные
last_update_id = 0
file_cache = {}
last_cache_update = 0

# ========== TELEGRAM ФУНКЦИИ ==========
def get_updates(token, offset=None):
    """Получение обновлений через polling"""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset

    try:
        response = requests.get(url, params=params, timeout=35)
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка получения обновлений: {e}")
        return None

def send_message(token, chat_id, text, reply_markup=None):
    """Отправка сообщения с кнопками"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        return None

def send_permanent_buttons(chat_id):
    """Отправка постоянных кнопок"""
    keyboard = {
        "keyboard": [
            [{"text": "✨ Задать вопрос"}],
            [{"text": "🔄 Сбросить"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

    send_message(TELEGRAM_BOT_TOKEN, chat_id,
                 " Приветствую вас! ✨\n\n"
                 "Задавайте вопросы связанные с аспектацией планет.\n"
                 "Используйте кнопки ниже:",
                 keyboard)

# ========== ЧТЕНИЕ ФАЙЛОВ ==========
def read_local_file(filename):
    """Читает файл с локального компьютера с кэшированием"""
    global file_cache, last_cache_update

    # Проверяем кэш
    if filename in file_cache and (time.time() - last_cache_update) < 300:
        return file_cache[filename]

    try:
        # Путь к файлам в Render
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "texts", filename)
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    file_cache[filename] = content
                    return content
                else:
                    logger.warning(f"Файл {filename} пустой")
                    return None
        else:
            logger.warning(f"Файл не найден: {file_path}")
            return None
    except Exception as e:
        logger.warning(f"Ошибка чтения файла {filename}: {e}")
        return None

def get_all_files_from_local():
    """Получает файлы с локального компьютера с оптимизацией"""
    global file_cache, last_cache_update

    # Обновляем кэш если прошло больше 5 минут
    if (time.time() - last_cache_update) > 300:
        file_cache = {}
        last_cache_update = time.time()

    all_files = []

    # Категории файлов
    categories = {
        "ПЛАНЕТЫ": [
            "planet_марс.txt", "planet_венера.txt", "planet_луна.txt",
            "planet_меркурий.txt", "planet_солнце.txt", "planet_юпитер.txt",
            "planet_сатурн.txt", "planet_уран.txt", "planet_нептун.txt",
            "planet_плутон.txt", "planet_Лилит.txt", "planet_Чёрная_луна.txt"
        ],
        "ЗНАКИ ЗОДИАКА": [
            "sign_Овен.txt", "sign_Телец.txt", "sign_Близнецы.txt",
            "sign_Рак.txt", "sign_Лев.txt", "sign_Дева.txt",
            "sign_Весы.txt", "sign_Скорпион.txt", "sign_Стрелец.txt",
            "sign_Козерог.txt", "sign_Водолей.txt", "sign_Рыбы.txt"
        ],
        "ДОМА": [
            "house_1.txt", "house_2.txt", "house_3.txt",
            "house_4.txt", "house_5.txt", "house_6.txt",
            "house_7.txt", "house_8.txt", "house_9.txt",
            "house_10.txt", "house_11.txt", "house_12.txt"
        ],
        "АСПЕКТЫ": [
            "aspect_150.txt", "aspect_180.txt", "aspect_0.txt",
            "aspect_60.txt", "aspect_90.txt", "aspect_120.txt"
        ]
    }

    total_files = sum(len(files) for files in categories.values())
    logger.info(f"Ищем {total_files} файлов...")

    found_files = 0
    for category, filenames in categories.items():
        category_content = []
        category_found = 0

        for filename in filenames:
            content = read_local_file(filename)
            if content:
                # Берем только первые 500 символов каждого файла для оптимизации
                truncated_content = content[:500] + ("..." if len(content) > 500 else "")
                category_content.append(f"[{filename}]: {truncated_content}")
                category_found += 1
                found_files += 1

        if category_content:
            all_files.append(f"=== {category} ===\n" + "\n".join(category_content) + "\n")

    logger.info(f"Прочитано: {found_files} файлов из {total_files}")
    return all_files

# ========== GEN API ФУНКЦИИ ==========
def call_gen_api(system_prompt, user_question):
    """Вызов gen-api с правильной обработкой ответа"""
    try:
        logger.info("Отправка запроса к gen-api...")

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {GEN_API_KEY}'
        }

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            "is_sync": True,
            "max_tokens": 1000,
            "temperature": 0.2
        }

        response = requests.post(GEN_API_URL, json=payload, headers=headers, timeout=45)

        if response.status_code == 200:
            result = response.json()
            logger.info(f"Полный ответ от API: {json.dumps(result, ensure_ascii=False)[:200]}...")

            # Правильная обработка ответа по новому формату
            if isinstance(result, dict):
                if 'response' in result and isinstance(result['response'], list):
                    response_list = result['response']
                    if len(response_list) > 0:
                        first_response = response_list[0]
                        if isinstance(first_response, dict) and 'message' in first_response:
                            message = first_response['message']
                            if isinstance(message, dict) and 'content' in message:
                                answer = message['content']
                                logger.info("✅ Ответ извлечен успешно (новый формат)")
                                return answer

                elif 'output' in result:
                    answer = str(result['output'])
                    logger.info("✅ Ответ извлечен успешно (output)")
                    return answer
                elif 'choices' in result and len(result['choices']) > 0:
                    choice = result['choices'][0]
                    if isinstance(choice, dict):
                        if 'message' in choice:
                            answer = str(choice['message'].get('content', ''))
                            logger.info("✅ Ответ извлечен успешно (choices)")
                            return answer
                        elif 'content' in choice:
                            answer = str(choice.get('content', ''))
                            logger.info("✅ Ответ извлечен успешно (content)")
                            return answer

            answer = str(result)
            logger.info("✅ Ответ извлечен как строка")
            return answer

        elif response.status_code == 429:
            return "❌ Превышен лимит запросов. Подождите несколько минут."
        else:
            logger.error(f"Ошибка gen-api: {response.status_code}")
            logger.error(f"Ответ: {response.text}")
            return f"❌ Ошибка gen-api: {response.status_code}"

    except requests.exceptions.Timeout:
        logger.error("Таймаут запроса к gen-api")
        return "❌ Запрос занял слишком много времени. Попробуйте уточнить вопрос."
    except Exception as e:
        logger.error(f"Ошибка запроса к gen-api: {e}")
        return "❌ Ошибка при обращении к AI-модели. Попробуйте позже."

# ========== ОБРАБОТЧИК СООБЩЕНИЙ ==========
def process_message(message):
    """Обработка одного сообщения"""
    chat_id = message.get('chat', {}).get('id')
    user_question = message.get('text', '').strip()

    if not chat_id:
        return

    logger.info(f"Сообщение: {user_question}")

    # Проверка доступа
    user_id = message.get('from', {}).get('id')
    if not check_access(user_id):
        send_message(TELEGRAM_BOT_TOKEN, chat_id, 
                    f"⛔ Доступ запрещен. Ваш ID: {user_id}\nЗапросите доступ у администратора.")
        return

    # Команды
    if user_question.lower() in ['/start', '✨ задать вопрос', 'задать вопрос', '/myid']:
        if user_question == '/myid':
            user = message.get('from', {})
            response = (
                f"🆔 *Ваш ID:* `{user.get('id', 'N/A')}`\n"
                f"👤 *Имя:* {user.get('first_name', 'N/A')}\n"
                f"📛 *Юзернейм:* @{user.get('username', 'нет')}\n"
                f"✅ *Доступ:* {'ЕСТЬ ✅' if check_access(user.get('id')) else 'НЕТ ❌'}"
            )
            send_message(TELEGRAM_BOT_TOKEN, chat_id, response)
        else:
            send_permanent_buttons(chat_id)
        return

    if user_question.lower() in ['🔄 сбросить', 'сбросить', '/reset']:
        send_permanent_buttons(chat_id)
        send_message(TELEGRAM_BOT_TOKEN, chat_id, "🔄 Диалог сброшен. Готовы к новому вопросу!")
        return

    # Пустые сообщения
    if len(user_question) < 2:
        send_message(TELEGRAM_BOT_TOKEN, chat_id,
                     "📝 Задавайте вопрос связанный с аспектацией планет.")
        send_permanent_buttons(chat_id)
        return

    # Отправляем статус
    keyboard = {
        "keyboard": [
            [{"text": "✨ Задать вопрос"}],
            [{"text": "🔄 Сбросить"}]
        ],
        "resize_keyboard": True
    }
    send_message(TELEGRAM_BOT_TOKEN, chat_id, "⏳ Идёт анализ, ждите...", keyboard)

    try:
        # Читаем файлы
        logger.info("Чтение файлов...")
        all_files_content = get_all_files_from_local()

        if not all_files_content:
            send_message(TELEGRAM_BOT_TOKEN, chat_id,
                         "❌ Не удалось прочитать файлы из базы знаний.")
            return

        # Формируем промпт
        files_text = "\n".join(all_files_content)

        system_prompt = f"""ТЫ - эксперт! Используй информацию ТОЛЬКО из предоставленных файлов.

ДОСТУПНЫЕ ДАННЫЕ:
{files_text}

ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА:

1. СТРОГО ИСПОЛЬЗУЙ ТОЛЬКО информацию из файлов выше и не бери информацию из ИНТЕРНЕТА !!!
2. СОСТАВЛЯЙ уверенно короткие предложения из ключевых слов из файлов и не используй СВОИ ЗНАНИЯ !
3. соединяй ключевые слова и сумируй их в текст
4. ОТВЕЧАЙ полноценно и четко и по делу не используй слова: трансформация, илюзии, расширения !!
5. ВАЖНО!---Не используй свои знания и информацию из интернета !!!
6. Отвечай только по теме АСПЕКТАЦИИ ПЛАНЕТ, Знаков, ДОМОВ

ВОПРОС ПОЛЬЗОВАТЕЛЯ:"""

        # Запрашиваем gen-api
        logger.info("Вызов gen-api...")
        gpt_response = call_gen_api(system_prompt, user_question)

        # Отправляем ответ
        send_message(TELEGRAM_BOT_TOKEN, chat_id, gpt_response, keyboard)
        logger.info("Ответ отправлен успешно")

    except Exception as e:
        logger.error(f"Ошибка обработки: {e}")
        send_message(TELEGRAM_BOT_TOKEN, chat_id,
                     "❌ Произошла ошибка. Попробуйте позже.", keyboard)

# ========== ГЛАВНЫЙ ЦИКЛ ==========
def telegram_polling():
    """Главный цикл Telegram"""
    global last_update_id

    logger.info("🚀 Telegram бот запущен!")

    while True:
        try:
            updates = get_updates(TELEGRAM_BOT_TOKEN, last_update_id + 1 if last_update_id > 0 else None)

            if updates and updates.get('ok') and updates.get('result'):
                for update in updates['result']:
                    update_id = update.get('update_id', 0)
                    message = update.get('message', {})

                    if message and update_id > last_update_id:
                        process_message(message)
                        last_update_id = update_id

            time.sleep(1)

        except KeyboardInterrupt:
            logger.info("🛑 Бот остановлен пользователем")
            break
        except Exception as e:
            logger.error(f"🔥 Ошибка в основном цикле: {e}")
            time.sleep(5)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    # Запускаем Flask сервер в отдельном потоке
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("=" * 50)
    print("🚀 Запуск астрологического бота...")
    print(f"🤖 Токен: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"🔑 API ключ: {GEN_API_KEY[:10]}...")
    print(f"👥 Разрешено пользователей: {len(ALLOWED_USERS)}")
    print("🌐 Flask сервер на порту 8080")
    print("📱 Идите в Telegram → найдите бота")
    print("✍️ Напишите /start или /myid")
    print("=" * 50)
    
    # Запускаем Telegram polling
    telegram_polling()
