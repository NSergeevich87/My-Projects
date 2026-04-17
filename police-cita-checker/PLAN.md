# Police Cita Checker — Implementation Plan

## Цель

Автоматический мониторинг доступности записи на получение TIE (карта иностранца) в полиции Барселоны. Скрипт циклически проходит весь flow бронирования и либо останавливается на странице при появлении свободных слотов, либо повторяет попытку через 10 минут.

---

## Стек

- **Python 3.11+**
- **Playwright** (браузерная автоматизация, лучше справляется с JS-heavy страницами чем Selenium)
- **asyncio** (асинхронный цикл повторов)

---

## Flow (шаги автоматизации)

```
1. Открыть https://icp.administracionelectronica.gob.es/icpplustieb/index
2. Выбрать в "PROVINCIAS DISPONIBLES" → "Barcelona"
3. Нажать "Aceptar"
4. Выбрать в "TRAMITES POLICIA NACIONAL" → "POLICÍA-EXPEDICIÓN DE TARJETAS CUYA AUTORIZACIÓN RESUELVE LA DIRECCIÓN GENERAL DE GESTIÓN MIGRATORIA"
5. Нажать "Aceptar"
6. Нажать "Entrar"
7. Ввести в поле N.I.E. → "Z4186374B"
8. Ввести в поле Nombre y apellidos → "MARC NIKIFOROV VOLKOV"
9. Нажать "Aceptar"
10. Нажать "Solicitar Cita"
11. Проверить наличие сообщения:
    "En este momento no hay citas disponibles."
    - Если сообщение ЕСТЬ  → нажать "Salir" → ждать 10 минут → перейти к шагу 1
    - Если сообщения НЕТ  → остановиться, уведомить пользователя
```

---

## Структура проекта

```
police-cita-checker/
├── PLAN.md              # этот файл
├── main.py              # точка входа, цикл повторов
├── checker.py           # Playwright flow (все шаги 1–11)
└── requirements.txt     # зависимости
```

---

## Детали реализации

### `checker.py` — основная логика

```python
async def run_check(page) -> bool:
    """
    Проходит весь flow.
    Возвращает True если cita доступна, False если нет.
    """
```

- Использовать `page.wait_for_selector()` перед каждым взаимодействием
- Добавить разумные таймауты (30с) чтобы не зависать при падении сети
- Детектить сообщение по тексту: `"En este momento no hay citas disponibles."`

### `main.py` — цикл

```python
RETRY_INTERVAL = 10 * 60  # 10 минут в секундах

while True:
    available = await run_check(page)
    if available:
        notify()   # звук / лог в консоль
        break
    await asyncio.sleep(RETRY_INTERVAL)
```

### Уведомление при успехе

- Печать в консоль с временной меткой
- Системный звуковой сигнал (`print('\a')`)
- Опционально: Telegram-бот уведомление

---

## Установка и запуск

```bash
pip install playwright
playwright install chromium

python main.py
```

---

## Важные нюансы

| Проблема | Решение |
|---|---|
| Captcha | Запускать в **headful** режиме (видимый браузер), проходить вручную при необходимости |
| Сессия истекла | Всегда начинать flow с шага 1 (свежая страница) |
| Сайт временно недоступен | Обернуть в try/except, логировать ошибку и продолжить цикл |
| Изменение структуры страницы | Использовать стабильные селекторы (text-based > id > css) |

---

## Порядок имплементации

- [ ] Настроить проект, установить зависимости
- [ ] Реализовать `checker.py` — пройти flow вручную через Playwright inspector
- [ ] Добавить детекцию сообщения и возврат результата
- [ ] Реализовать `main.py` — цикл с задержкой
- [ ] Протестировать полный цикл
- [ ] Добавить уведомления
