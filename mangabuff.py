import time
import os
import datetime
import json
import random

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException

# --- Настройки ---
LOGIN_URL = 'https://mangabuff.ru/login'
LOGIN_EMAIL = "amethan801@gmail.com"
LOGIN_PASSWORD = "2ea73CEBd8wHKUU"
DEFAULT_START_MANGA_URL = 'https://mangabuff.ru/manga/van-pis/1/0'
TARGET_CHAPTERS_PER_DAY = 75
CHAPTERS_PER_STANDARD_RUN = 3
WAIT_HOURS_AFTER_RUN = 1
STATE_FILE = 'next_chapter_url.txt'
DAILY_STATS_FILE = 'daily_stats.json'
MAX_COMMENTS_PER_DAY = 10 # <--- Новый лимит комментариев

# --- !!! ОБНОВЛЕННЫЙ СПИСОК КОММЕНТАРИЕВ !!! ---
COMMENT_VARIATIONS = [
    "Прочитал! Интересно, что дальше.",
    "Отличная глава, спасибо команде за работу!",
    "Благодарю за перевод и редакцию!",
    "Жду не дождусь следующей главы!",
    "Спасибо за ваш труд!",
    "Глава просто огонь!",
    "Было интересно, спасибо.",
    "Спасибо за продолжение!",
    "Как всегда на высоте! Спасибо.",
    "Захватывает! Спасибо за главу.",
    "Спасибо за оперативность!",
    "Продолжайте в том же духе!",
    "Прочитано. Спасибо!",
    "Спасибо за работу над этой главой.",
    "Ура, новая глава! Спасибо!",
    # Добавьте еще уникальных вариантов
]

# --- Опции Chrome ---
chrome_options = Options()
# chrome_options.add_argument("--headless") # Headless может мешать взаимодействию с формой
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
chrome_options.add_argument("--start-maximized")
# Профиль Chrome (если нужно)
# user_data_dir = r"C:\Users\YourUser\AppData\Local\Google\Chrome\User Data"
# profile_directory = "Default"
# chrome_options.add_argument(f"user-data-dir={user_data_dir}")
# chrome_options.add_argument(f"profile-directory={profile_directory}")


# --- Функция медленной прокрутки (без изменений) ---
def slow_scroll(driver, scrolls=15, delay=0.7):
    print("Начинаю медленную прокрутку...")
    try:
        viewport_height = driver.execute_script("return window.innerHeight")
        scroll_increment = max(100, viewport_height // 4)
        current_scroll = driver.execute_script("return window.pageYOffset")
        target_scroll = driver.execute_script("return document.body.scrollHeight")
        print(f"Начальная позиция: {current_scroll}, Высота документа: {target_scroll}, Высота окна: {viewport_height}")
        num_scrolls_needed = (target_scroll - current_scroll) // scroll_increment + 1 if scroll_increment > 0 else 0
        actual_scrolls = min(scrolls, num_scrolls_needed)
        print(f"Требуется прокруток до конца: ~{num_scrolls_needed}. Будет выполнено: {actual_scrolls}")
        for i in range(actual_scrolls):
            current_scroll = driver.execute_script("return window.pageYOffset")
            driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
            print(f"Прокрутка {i + 1}/{actual_scrolls}. Позиция: {current_scroll + scroll_increment}")
            time.sleep(delay)
            if driver.execute_script("return window.pageYOffset + window.innerHeight >= document.body.scrollHeight - 10;"):
                print("Достигнут конец страницы.")
                break
    except Exception as scroll_err:
        print(f"Ошибка во время прокрутки: {scroll_err}")
    finally:
        print("Завершил медленную прокрутку.")


# --- Функция логина (без изменений) ---
def login_to_mangabuff(driver, email, password):
    # ... (код без изменений) ...
    print(f"Перехожу на страницу входа: {LOGIN_URL}")
    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, 20)
    try:
        print("Ищу поле email...")
        email_field = wait.until(EC.visibility_of_element_located((By.NAME, "email")))
        print("Поле email найдено. Ввожу email...")
        email_field.send_keys(email)
        time.sleep(0.5)
        print("Ищу поле пароля...")
        password_field = wait.until(EC.visibility_of_element_located((By.NAME, "password")))
        print("Поле пароля найдено. Ввожу пароль...")
        password_field.send_keys(password)
        time.sleep(0.5)
        print("Ищу кнопку входа...")
        login_button_xpath = "//button[contains(@class, 'login-button') and normalize-space()='Войти']"
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, login_button_xpath)))
        print("Кнопка входа найдена. Кликаю...")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", login_button)
        time.sleep(0.5)
        wait.until(EC.element_to_be_clickable((By.XPATH, login_button_xpath)))
        login_button.click()
        print("Ожидаю завершения входа (проверяю изменение URL)...")
        wait.until(EC.url_changes(LOGIN_URL))
        print(f"Вход выполнен успешно! Текущий URL: {driver.current_url}")
        time.sleep(3)
        return True
    except TimeoutException:
        print("Ошибка: Не удалось найти элементы формы входа или кнопку входа.")
        try:
            driver.save_screenshot("login_error_screenshot.png")
            print("Скриншот ошибки сохранен в login_error_screenshot.png")
        except Exception as screen_err:
            print(f"Не удалось сделать скриншот: {screen_err}")
        return False
    except Exception as e:
        print(f"Ошибка во время процесса входа: {e}")
        return False


# --- Функции статистики (get_daily_stats, save_daily_stats) - без изменений ---
def get_daily_stats():
    """Читает статистику (главы и комментарии) за день из файла."""
    today_str = datetime.date.today().isoformat()
    # Значения по умолчанию
    stats = {'date': today_str, 'chapters_read': 0, 'comments_posted_today': 0}
    try:
        if os.path.exists(DAILY_STATS_FILE):
            with open(DAILY_STATS_FILE, 'r') as f:
                loaded_stats = json.load(f)
            # Проверяем дату и наличие ключей
            if loaded_stats.get('date') == today_str and \
               'chapters_read' in loaded_stats and \
               'comments_posted_today' in loaded_stats:
                stats = loaded_stats # Используем загруженные данные
                print(f"Загружена статистика за сегодня: {stats['chapters_read']} глав, {stats['comments_posted_today']} коммент.")
            else:
                print(f"Статистика за прошлый день ({loaded_stats.get('date')}) или неполная. Начинаю новые счетчики.")
                # Сохраняем дату, сбрасываем счетчики
                stats['date'] = today_str
                stats['chapters_read'] = 0
                stats['comments_posted_today'] = 0
        else:
            print("Файл статистики не найден. Начинаю новые счетчики.")
    except (json.JSONDecodeError, FileNotFoundError, KeyError, TypeError) as e:
        print(f"Ошибка чтения файла статистики '{DAILY_STATS_FILE}' или файл поврежден: {e}. Начинаю новые счетчики.")
        # При ошибке создаем чистый словарь
        stats = {'date': today_str, 'chapters_read': 0, 'comments_posted_today': 0}
    except Exception as e:
         print(f"Непредвиденная ошибка при чтении файла статистики: {e}. Начинаю новые счетчики.")
         stats = {'date': today_str, 'chapters_read': 0, 'comments_posted_today': 0}

    # Дополнительные проверки на корректность данных (на всякий случай)
    stats.setdefault('date', today_str)
    if stats['date'] != today_str: # Если дата все же не сегодняшняя
        stats = {'date': today_str, 'chapters_read': 0, 'comments_posted_today': 0}
    stats.setdefault('chapters_read', 0)
    stats.setdefault('comments_posted_today', 0)
    if not isinstance(stats['chapters_read'], int) or stats['chapters_read'] < 0:
        stats['chapters_read'] = 0
    if not isinstance(stats['comments_posted_today'], int) or stats['comments_posted_today'] < 0:
        stats['comments_posted_today'] = 0

    return stats

def save_daily_stats(stats):
    """Сохраняет статистику (главы и комментарии) за день в файл."""
    try:
        # Убедимся, что сохраняем корректные данные
        today_str = datetime.date.today().isoformat()
        if stats.get('date') != today_str:
            print(f"Предупреждение: Попытка сохранить статистику с устаревшей датой ({stats.get('date')}). Дата будет обновлена.")
            stats['date'] = today_str # Обновляем дату перед сохранением

        # Проверка типов и значений перед сохранением
        chapters = stats.get('chapters_read', 0)
        comments = stats.get('comments_posted_today', 0)
        if not isinstance(chapters, int) or chapters < 0:
             print(f"Ошибка: Попытка сохранить некорректное значение глав: {chapters}. Сохранение отменено.")
             return
        if not isinstance(comments, int) or comments < 0:
             print(f"Ошибка: Попытка сохранить некорректное значение комментов: {comments}. Сохранение отменено.")
             return

        stats['chapters_read'] = chapters
        stats['comments_posted_today'] = comments

        with open(DAILY_STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=4)
        print(f"Статистика за {stats['date']} сохранена: {stats['chapters_read']} глав, {stats['comments_posted_today']} коммент.")
    except Exception as e:
        print(f"Не удалось сохранить статистику в файл '{DAILY_STATS_FILE}': {e}")

def save_daily_stats(stats):
    """Сохраняет статистику (главы и комментарии) за день в файл."""
    try:
        # Убедимся, что сохраняем корректные данные
        today_str = datetime.date.today().isoformat()
        if stats.get('date') != today_str:
            print(f"Предупреждение: Попытка сохранить статистику с устаревшей датой ({stats.get('date')}). Дата будет обновлена.")
            stats['date'] = today_str # Обновляем дату перед сохранением

        # Проверка типов и значений перед сохранением
        chapters = stats.get('chapters_read', 0)
        comments = stats.get('comments_posted_today', 0)
        if not isinstance(chapters, int) or chapters < 0:
             print(f"Ошибка: Попытка сохранить некорректное значение глав: {chapters}. Сохранение отменено.")
             return
        if not isinstance(comments, int) or comments < 0:
             print(f"Ошибка: Попытка сохранить некорректное значение комментов: {comments}. Сохранение отменено.")
             return

        stats['chapters_read'] = chapters
        stats['comments_posted_today'] = comments

        with open(DAILY_STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=4)
        print(f"Статистика за {stats['date']} сохранена: {stats['chapters_read']} глав, {stats['comments_posted_today']} коммент.")
    except Exception as e:
        print(f"Не удалось сохранить статистику в файл '{DAILY_STATS_FILE}': {e}")


# --- НОВАЯ ФУНКЦИЯ: Добавление комментария ---
def post_comment(driver, wait_time=25):
    """Пытается открыть форму, выбрать случайный коммент, оставить его и отправить."""
    if not COMMENT_VARIATIONS:
        print("Ошибка: Список COMMENT_VARIATIONS пуст. Комментирование пропущено.")
        return False
    chosen_comment = random.choice(COMMENT_VARIATIONS)

    print(f"Попытка оставить комментарий: '{chosen_comment}'")
    comment_wait = WebDriverWait(driver, wait_time)
    try:
        # Шаг 1: Клик по иконке открытия
        open_comment_button_selector = (By.CSS_SELECTOR, "button.reader-menu__item--comment")
        print("Ищу кнопку открытия комментариев...")
        open_button = comment_wait.until(EC.element_to_be_clickable(open_comment_button_selector))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", open_button)
        time.sleep(0.5)
        open_button = comment_wait.until(EC.element_to_be_clickable(open_comment_button_selector))
        print("Кнопка открытия найдена. Кликаю...")
        open_button.click()
        time.sleep(1.5)

        # Шаг 2: Поле ввода
        comment_textarea_selector = (By.CSS_SELECTOR, "textarea[placeholder='Напишите что нибудь...']")
        print("Ищу поле для ввода комментария...")
        comment_field = comment_wait.until(EC.visibility_of_element_located(comment_textarea_selector))
        comment_field = comment_wait.until(EC.element_to_be_clickable(comment_textarea_selector))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", comment_field)
        time.sleep(0.5)
        comment_field = comment_wait.until(EC.element_to_be_clickable(comment_textarea_selector))
        print("Поле найдено. Кликаю по полю...")
        comment_field.click()
        time.sleep(0.3)

        print("Очищаю поле и ввожу выбранный текст...")
        comment_field.clear()
        comment_field.send_keys(chosen_comment)
        time.sleep(0.5)

        # Шаг 3: Кнопка "Отправить"
        comment_submit_button_selector = (By.XPATH, "//button[contains(@class, 'comments__send-btn') and normalize-space()='Отправить']")
        print("Ищу кнопку 'Отправить'...")
        submit_button = comment_wait.until(EC.element_to_be_clickable(comment_submit_button_selector))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", submit_button)
        time.sleep(0.5)
        submit_button = comment_wait.until(EC.element_to_be_clickable(comment_submit_button_selector))
        print("Кнопка 'Отправить' найдена. Кликаю...")
        submit_button.click()
        print("Комментарий успешно отправлен.")
        time.sleep(3) # Пауза после отправки

        return True # Успех

    except (NoSuchElementException, TimeoutException, ElementNotInteractableException) as e:
        print(f"Ошибка: Не удалось найти/взаимодействовать с формой комментария: {e}")
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"comment_error_{timestamp}.png"
            driver.save_screenshot(screenshot_path)
            print(f"Скриншот ошибки комментирования сохранен в {screenshot_path}")
        except Exception as screen_err:
            print(f"Не удалось сделать скриншот ошибки комментирования: {screen_err}")
        print("Пытаюсь закрыть форму комментария после ошибки...")
        try:
             cancel_button_selector = (By.CSS_SELECTOR, "button.comments__close-form-btn")
             cancel_buttons = driver.find_elements(*cancel_button_selector)
             if cancel_buttons and cancel_buttons[0].is_displayed():
                 comment_wait.until(EC.element_to_be_clickable(cancel_buttons[0])).click()
                 print("Кнопка 'Отмена' нажата после ошибки.")
                 time.sleep(0.5)
        except Exception as cancel_err:
             print(f"Не удалось нажать 'Отмена' после ошибки: {cancel_err}")
        return False # Неудача
    except Exception as e:
        print(f"Непредвиденная ошибка при добавлении комментария: {e}")
        import traceback
        traceback.print_exc()
        return False # Неудача

# --- Основная функция бота (МОДИФИЦИРОВАНА) ---
def read_chapters():
    """Запускается через N часов после предыдущего запуска, читает главы, иногда комментирует, и обновляет страницу при долгом ожидании."""
    print(f"\n{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Запускаю сессию чтения...")

    driver = None
    last_successful_manga_url = None
    chapters_read_this_session = 0
    comment_posted_this_session = False # Флаг, что коммент в этой сессии уже был

    # --- Получение статистики и расчет глав ---
    daily_stats = get_daily_stats()
    chapters_already_read_today = daily_stats['chapters_read']
    comments_already_posted_today = daily_stats['comments_posted_today'] # Загружаем счетчик комментов

    if chapters_already_read_today >= TARGET_CHAPTERS_PER_DAY:
        print(f"Дневной лимит ({TARGET_CHAPTERS_PER_DAY} глав) уже достигнут. Пропускаю сессию.")
        return 0

    can_post_comment_today = comments_already_posted_today < MAX_COMMENTS_PER_DAY
    if not can_post_comment_today:
        print(f"Дневной лимит комментариев ({MAX_COMMENTS_PER_DAY}) достигнут.")

    chapters_remaining_today = TARGET_CHAPTERS_PER_DAY - chapters_already_read_today
    if chapters_remaining_today <= CHAPTERS_PER_STANDARD_RUN:
        chapters_to_read_this_run = chapters_remaining_today
        print(f"Завершающий цикл чтения за сегодня.")
    else:
        chapters_to_read_this_run = CHAPTERS_PER_STANDARD_RUN
        print(f"Стандартный цикл чтения.")
    print(f"Цель на сегодня: {TARGET_CHAPTERS_PER_DAY}. Уже прочитано: {chapters_already_read_today}.")
    print(f"Осталось прочитать сегодня: {chapters_remaining_today}.")
    print(f"=> Будет прочитано в ЭТОЙ сессии: {chapters_to_read_this_run}.")
    if chapters_to_read_this_run <= 0:
         print("Нет глав для чтения в этой сессии.")
         return 0

    # --- Чтение URL МАНГИ из файла состояния (без изменений) ---
    current_start_manga_url = DEFAULT_START_MANGA_URL
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                saved_url = f.readline().strip()
                if saved_url and saved_url.startswith('http') and '/manga/' in saved_url:
                    current_start_manga_url = saved_url
                    print(f"Начинаем чтение с сохраненного URL: {current_start_manga_url}")
                else:
                    print(f"Файл '{STATE_FILE}' пуст/некорректен. Начинаем с {DEFAULT_START_MANGA_URL}.")
                    current_start_manga_url = DEFAULT_START_MANGA_URL
        else:
             print(f"Файл '{STATE_FILE}' не найден. Начинаем с {DEFAULT_START_MANGA_URL}.")
             current_start_manga_url = DEFAULT_START_MANGA_URL
    except Exception as e:
        print(f"Ошибка при чтении файла '{STATE_FILE}': {e}. Начинаем с {DEFAULT_START_MANGA_URL}.")
        current_start_manga_url = DEFAULT_START_MANGA_URL

    try:
        print("Инициализация WebDriver...")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(5) # Implicit wait is generally less reliable than explicit waits
        driver.set_page_load_timeout(60)
        print("WebDriver инициализирован.")

        # --- ШАГ 1: ЛОГИН ---
        if not login_to_mangabuff(driver, LOGIN_EMAIL, LOGIN_PASSWORD):
             print("Не удалось войти в систему. Завершение сессии.")
             return 0

        # --- ШАГ 2: ПЕРЕХОД К МАНГЕ ---
        print(f"Перехожу на стартовую страницу манги: {current_start_manga_url}")
        try:
            driver.get(current_start_manga_url)
        except TimeoutException:
            print(f"Ошибка: Не удалось загрузить страницу {current_start_manga_url} за 60 секунд.")
            return 0
        time.sleep(2) # Wait for potential redirects or dynamic content loading
        current_page_url = driver.current_url
        if LOGIN_URL in current_page_url or current_page_url == 'https://mangabuff.ru/':
             print(f"Ошибка: После перехода на {current_start_manga_url} перекинуло на {current_page_url}. Возможно, ошибка авторизации или неверный URL.")
             return 0
        print(f"Страница манги загружена. Текущий URL: {current_page_url}")
        last_successful_manga_url = current_page_url
        time.sleep(1)

        # --- Цикл чтения глав ---
        wait_next = WebDriverWait(driver, 30) # Основное ожидание для кнопки "след. глава"
        wait_retry = WebDriverWait(driver, 20) # Ожидание после рефреша (можно чуть короче)

        while chapters_read_this_session < chapters_to_read_this_run:
            print(f"\n--- Чтение главы ({chapters_read_this_session + 1}/{chapters_to_read_this_run}) | Всего сегодня: {chapters_already_read_today + chapters_read_this_session + 1}/{TARGET_CHAPTERS_PER_DAY} ---")
            current_chapter_url = driver.current_url
            print(f"Текущий URL главы: {current_chapter_url}")
            last_successful_manga_url = current_chapter_url # Обновляем URL *до* прокрутки/перехода

            # --- Прокрутка текущей главы ---
            slow_scroll(driver, scrolls=60, delay=0.4 if chapters_read_this_session > 0 else 0.5) # Первая чуть медленнее

            # --- Попытка комментирования (только если можно и еще не комментили в сессии) ---
            if can_post_comment_today and not comment_posted_this_session:
                print("-" * 10 + " Попытка оставить комментарий " + "-" * 10)
                if post_comment(driver):
                    daily_stats['comments_posted_today'] += 1
                    comments_already_posted_today += 1
                    comment_posted_this_session = True
                    can_post_comment_today = comments_already_posted_today < MAX_COMMENTS_PER_DAY
                    print(f"Комментарий успешно оставлен. Всего сегодня: {daily_stats['comments_posted_today']}/{MAX_COMMENTS_PER_DAY}")
                    save_daily_stats(daily_stats) # Сохраняем сразу
                else:
                    print("Не удалось оставить комментарий в этот раз.")
                print("-" * 30)
            # --- Конец блока комментирования ---

            # --- Переход к следующей главе ---
            next_chapter_found_and_clicked = False
            try:
                # --- ПЕРВАЯ ПОПЫТКА НАЙТИ И КЛИКНУТЬ ---
                print("Ищу кнопку/ссылку 'След. глава' (попытка 1)...")
                next_chapter_xpath = "//div[contains(@class, 'reader__footer')]//a[starts-with(normalize-space(), 'След. глава')]"
                next_chapter_button = wait_next.until(EC.element_to_be_clickable((By.XPATH, next_chapter_xpath)))
                print("Найдена ссылка 'След. глава' (попытка 1).")

                print("Прокручиваю до кнопки 'След. глава'...")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", next_chapter_button)
                time.sleep(1) # Пауза после скролла
                # Повторно проверяем кликабельность после скролла
                next_chapter_button = wait_next.until(EC.element_to_be_clickable((By.XPATH, next_chapter_xpath)))

                print("Кликаю на 'След. глава' (попытка 1)...")
                # Используем try-except для клика, пробуя JS как запасной вариант
                try:
                    if not next_chapter_button.is_displayed() or not next_chapter_button.is_enabled():
                         print("Кнопка 'След. глава' стала невидимой или неактивной перед кликом.")
                         raise ElementNotInteractableException("Кнопка стала недоступной.")
                    next_chapter_button.click()
                except (ElementNotInteractableException, Exception) as click_error:
                    print(f"Прямой клик не удался ({click_error}), пробую через JavaScript...")
                    try:
                        driver.execute_script("arguments[0].click();", next_chapter_button)
                    except Exception as js_click_error:
                         print(f"Клик через JavaScript тоже не удался: {js_click_error}")
                         raise # Перевыбрасываем ошибку, чтобы внешний try-except ее поймал

                print("Ожидаю загрузки следующей главы (изменения URL)...")
                url_changed = wait_next.until(EC.url_changes(current_chapter_url)) # Используем тот же wait_next
                if not url_changed:
                    print("Ошибка: URL не изменился после клика.")
                    raise TimeoutException("URL не изменился после клика на 'След. глава'.")

                time.sleep(2) # Пауза для стабилизации
                new_url = driver.current_url
                print(f"Успешно перешел на новую главу (попытка 1): {new_url}")
                last_successful_manga_url = new_url # Обновляем URL после успешного перехода
                chapters_read_this_session += 1
                next_chapter_found_and_clicked = True

            except TimeoutException as e:
                # --- ОБРАБОТКА ТАЙМ-АУТА И ПОПЫТКА ОБНОВЛЕНИЯ ---
                print(f"Тайм-аут (30 сек) при поиске 'След. глава': {e}")
                print("Попытка обновить страницу и повторить поиск...")
                try:
                    driver.refresh()
                    print("Страница обновлена. Ожидание загрузки (5 сек)...")
                    time.sleep(5) # Даем время на перезагрузку

                    # --- ВТОРАЯ ПОПЫТКА НАЙТИ И КЛИКНУТЬ ПОСЛЕ ОБНОВЛЕНИЯ ---
                    print("Ищу кнопку/ссылку 'След. глава' (попытка 2 после обновления)...")
                    next_chapter_button_retry = wait_retry.until(EC.element_to_be_clickable((By.XPATH, next_chapter_xpath))) # Используем wait_retry
                    print("Найдена ссылка 'След. глава' (попытка 2).")

                    print("Прокручиваю до кнопки 'След. глава' (попытка 2)...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", next_chapter_button_retry)
                    time.sleep(1)
                    next_chapter_button_retry = wait_retry.until(EC.element_to_be_clickable((By.XPATH, next_chapter_xpath)))

                    print("Кликаю на 'След. глава' (попытка 2)...")
                    try:
                        if not next_chapter_button_retry.is_displayed() or not next_chapter_button_retry.is_enabled():
                             print("Кнопка 'След. глава' стала невидимой или неактивной перед кликом (попытка 2).")
                             raise ElementNotInteractableException("Кнопка стала недоступной (попытка 2).")
                        next_chapter_button_retry.click()
                    except (ElementNotInteractableException, Exception) as click_error_retry:
                        print(f"Прямой клик не удался ({click_error_retry}) (попытка 2), пробую через JavaScript...")
                        try:
                            driver.execute_script("arguments[0].click();", next_chapter_button_retry)
                        except Exception as js_click_error_retry:
                            print(f"Клик через JavaScript тоже не удался (попытка 2): {js_click_error_retry}")
                            raise # Перевыбрасываем

                    print("Ожидаю загрузки следующей главы после обновления (изменения URL)...")
                    url_changed_retry = wait_retry.until(EC.url_changes(current_chapter_url))
                    if not url_changed_retry:
                         print("Ошибка: URL не изменился после клика (попытка 2).")
                         raise TimeoutException("URL не изменился после клика на 'След. глава' (попытка 2).")

                    time.sleep(2)
                    new_url = driver.current_url
                    print(f"Успешно перешел на новую главу (попытка 2): {new_url}")
                    last_successful_manga_url = new_url # Обновляем URL
                    chapters_read_this_session += 1
                    next_chapter_found_and_clicked = True

                except (NoSuchElementException, TimeoutException, ElementNotInteractableException) as retry_e:
                    print(f"Не удалось найти/кликнуть 'След. глава' ДАЖЕ ПОСЛЕ ОБНОВЛЕНИЯ: {retry_e}")
                    print(f"Останавливаюсь на URL: {driver.current_url}")
                    last_successful_manga_url = driver.current_url # Сохраняем текущий URL перед выходом
                    # break # Выходим из цикла while глав - НЕ НУЖНО, так как next_chapter_found_and_clicked останется False
                except Exception as retry_general_e:
                    print(f"Непредвиденная ошибка при переходе ПОСЛЕ ОБНОВЛЕНИЯ: {retry_general_e}")
                    import traceback
                    traceback.print_exc()
                    last_successful_manga_url = driver.current_url
                    # break # Выходим из цикла while глав

            except (NoSuchElementException, ElementNotInteractableException) as e:
                 print(f"Не смог найти/кликнуть кнопку 'Следующая глава' (не тайм-аут): {e}")
                 print(f"Останавливаюсь на URL: {driver.current_url}")
                 last_successful_manga_url = driver.current_url
                 # break # Выходим из цикла while глав

            except Exception as e:
                print(f"Произошла НЕПРЕДВИДЕННАЯ ошибка при переходе на следующую главу: {e}")
                import traceback
                traceback.print_exc()
                last_successful_manga_url = driver.current_url
                # break # Выходим из цикла while глав
            # --- Конец блока перехода ---

            # Если ни первая попытка, ни вторая (после обновления) не увенчались успехом:
            if not next_chapter_found_and_clicked:
                print("Переход на следующую главу не удался. Прерываю чтение глав в этой сессии.")
                break # Выходим из цикла while глав

        # --- Конец цикла while ---

        print(f"\n{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Завершена сессия чтения (прочитано {chapters_read_this_session} глав).")

        # --- Обновление статистики глав ---
        if chapters_read_this_session > 0:
             daily_stats['chapters_read'] += chapters_read_this_session
             save_daily_stats(daily_stats) # Сохраняем итоговую статистику глав (комментарии уже сохранены ранее)
        else:
             print("В этой сессии главы не были прочитаны, статистика глав не обновлена.")

        # --- Запись URL ---
        if last_successful_manga_url:
            try:
                # Убедимся, что URL валиден перед сохранением
                if isinstance(last_successful_manga_url, str) and last_successful_manga_url.startswith('http'):
                    with open(STATE_FILE, 'w') as f:
                        f.write(last_successful_manga_url)
                    print(f"Сохранен URL для следующего запуска: {last_successful_manga_url}")
                else:
                     print(f"Ошибка: Попытка сохранить невалидный URL: {last_successful_manga_url}. Файл '{STATE_FILE}' не обновлен.")
            except Exception as e:
                print(f"Не удалось сохранить URL в файл '{STATE_FILE}': {e}")
        else:
             # Если last_successful_manga_url остался None или пустым, значит была ошибка еще до загрузки первой главы сессии
             print(f"URL для сохранения не определен (возможно, ошибка на самой первой главе сессии или при логине), файл '{STATE_FILE}' не обновлен.")

    except Exception as e:
        print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Произошла ГЛОБАЛЬНАЯ ошибка в сессии чтения: {e}")
        import traceback
        traceback.print_exc()
        # Пытаемся сохранить последний известный URL даже при глобальной ошибке, если он есть
        if last_successful_manga_url and isinstance(last_successful_manga_url, str) and last_successful_manga_url.startswith('http'):
             try:
                 with open(STATE_FILE, 'w') as f:
                     f.write(last_successful_manga_url)
                 print(f"[Ошибка] Сохранен последний известный URL: {last_successful_manga_url}")
             except Exception as save_err:
                 print(f"[Ошибка] Не удалось сохранить последний URL '{last_successful_manga_url}' при ошибке: {save_err}")
        chapters_read_this_session = 0 # Считаем, что ничего не прочитали при глобальной ошибке
    finally:
       if driver:
            try:
                driver.quit()
                print("Браузер закрыт.")
            except Exception as quit_err:
                print(f"Ошибка при закрытии браузера: {quit_err}")
       return chapters_read_this_session


# --- ГЛАВНЫЙ ЦИКЛ (без изменений) ---
if __name__ == "__main__":
    print("=" * 30)
    print("   Манга-Бот v2.7 (Refresh on Timeout) Запущен   ") # <-- Версия обновлена
    print("=" * 30)
    print(f"Цель: {TARGET_CHAPTERS_PER_DAY} глав в день.")
    print(f"Глав за стандартный запуск: {CHAPTERS_PER_STANDARD_RUN}.")
    print(f"Максимум комментариев в день: {MAX_COMMENTS_PER_DAY}.")
    print(f"Пауза после запуска: {WAIT_HOURS_AFTER_RUN} час(а).")
    print("Комментарии: Случайные, не более 1 за сессию, лимит {MAX_COMMENTS_PER_DAY}/день.")
    print(f"Файл состояния URL: {STATE_FILE}")
    print(f"Файл дневной статистики: {DAILY_STATS_FILE}")
    print("-" * 30)
    print("НОВАЯ ФУНКЦИЯ: Обновление страницы при тайм-ауте (30 сек) поиска кнопки 'След. глава'.")
    print("!!! ВАЖНО: Убедитесь, что селекторы для комментирования и 'След. глава' в коде верны! !!!")
    print("-" * 30)

    while True:
        chapters_done_this_run = 0
        start_time = time.time()
        try:
            chapters_done_this_run = read_chapters()
            print(f"Сессия завершена. Прочитано глав в этой сессии: {chapters_done_this_run}")

        except Exception as main_loop_error:
            print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - КРИТИЧЕСКАЯ ОШИБКА В ГЛАВНОМ ЦИКЛЕ: {main_loop_error}")
            import traceback
            traceback.print_exc()
            print("!!! Попытка продолжить работу после критической ошибки !!!")
            chapters_done_this_run = 0 # Сбрасываем счетчик на всякий случай

        end_time = time.time()
        run_duration = end_time - start_time
        print(f"Длительность сессии: {run_duration:.2f} секунд.")

        # --- Расчет паузы ---
        # Проверяем, достигнута ли дневная цель
        current_stats = get_daily_stats() # Снова читаем статистику
        chapters_today = current_stats.get('chapters_read', 0)
        wait_seconds = WAIT_HOURS_AFTER_RUN * 60 * 60

        if chapters_today >= TARGET_CHAPTERS_PER_DAY:
             # Если цель достигнута, ждем до следующего дня
             now = datetime.datetime.now()
             tomorrow = datetime.date.today() + datetime.timedelta(days=1)
             midnight_tomorrow = datetime.datetime.combine(tomorrow, datetime.time.min)
             # Добавляем небольшую случайную задержку (1-10 минут) к полуночи
             random_delay = random.randint(60, 600)
             wait_until = midnight_tomorrow + datetime.timedelta(seconds=random_delay)
             wait_seconds = (wait_until - now).total_seconds()
             print(f"Дневная цель ({TARGET_CHAPTERS_PER_DAY} глав) достигнута. Следующий запуск ~ {wait_until.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
             print(f"Дневная цель НЕ достигнута ({chapters_today}/{TARGET_CHAPTERS_PER_DAY}).")
             # Обычная пауза между сессиями
             wait_seconds = WAIT_HOURS_AFTER_RUN * 60 * 60

        actual_wait = max(60, wait_seconds) # Ждем минимум минуту

        print(f"Следующий запуск через ~{actual_wait / 3600:.2f} час(а) (пауза {actual_wait:.0f} секунд)...")
        print("-" * 30)
        time.sleep(actual_wait)