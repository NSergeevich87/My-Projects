import asyncio
import random
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

NIE = "Z4186374B"
NAME = "MARC NIKIFOROV VOLKOV"
URL = "https://icp.administracionelectronica.gob.es/icpplustieb/index"
NO_CITA_TEXT = "En este momento no hay citas disponibles."


async def delay():
    """Случайная пауза 2–5 секунд между действиями."""
    await asyncio.sleep(random.uniform(2, 5))


async def run_check(page: Page) -> bool:
    """
    Проходит весь flow бронирования.
    Возвращает True если cita доступна, False если нет.
    """
    try:
        # Шаг 1: открыть страницу
        response = await page.goto(URL, timeout=30_000)
        if response and response.status >= 400:
            print(f"[ERROR] Сервер вернул HTTP {response.status} — пропускаем попытку")
            return False
        await delay()

        # Шаг 2: выбрать Barcelona в списке провинций
        await page.wait_for_selector("select#form", timeout=30_000)
        await page.select_option("select#form", label="Barcelona")
        await delay()

        # Шаг 3: Aceptar (первая кнопка)
        await page.click("input[value='Aceptar']")
        await delay()

        # Шаг 4: выбрать tramite по частичному совпадению текста
        TRAMITE_KEYWORD = "EXPEDICIÓN DE TARJETAS"
        await page.wait_for_selector("select[name='tramiteGrupo[0]']", timeout=30_000)
        # Находим value опции через JS, затем выбираем нативно через Playwright
        option_value = await page.evaluate("""(keyword) => {
            const sel = document.querySelector("select[name='tramiteGrupo[0]']");
            if (!sel) return null;
            for (const opt of sel.options) {
                if (opt.text.toUpperCase().includes(keyword.toUpperCase())) {
                    return opt.value;
                }
            }
            return null;
        }""", TRAMITE_KEYWORD)
        if not option_value:
            print(f"[ERROR] Tramite с ключевым словом '{TRAMITE_KEYWORD}' не найден в списке")
            return False
        await page.select_option("select[name='tramiteGrupo[0]']", value=option_value)
        print(f"[OK] Выбран tramite (value={option_value})")
        await delay()

        # Шаг 5: Aceptar (вторая кнопка)
        await page.click("input[value='Aceptar']")
        await delay()

        # Шаг 6: Entrar
        await page.wait_for_selector("input[value='Entrar']", timeout=30_000)
        await page.click("input[value='Entrar']")
        await delay()

        # Шаг 7–8: ввод данных
        await page.wait_for_selector("input#txtIdCitado", timeout=30_000)
        await page.fill("input#txtIdCitado", NIE)
        await delay()
        await page.fill("input#txtDesCitado", NAME)
        await delay()

        # Шаг 9: Aceptar (третья кнопка)
        await page.click("input[value='Aceptar']")
        await delay()

        # Шаг 10: Solicitar Cita
        await page.wait_for_selector("input[value='Solicitar Cita']", timeout=30_000)
        await page.click("input[value='Solicitar Cita']")
        await delay()

        # Шаг 11: проверить наличие сообщения "нет citas"
        await page.wait_for_load_state("networkidle", timeout=15_000)
        content = await page.content()

        # Проверка на серверные ошибки в теле страницы
        if "Internal Server Error" in content or "Too Many Requests" in content:
            print(f"[ERROR] Сервер вернул ошибку на странице — пропускаем попытку")
            return False

        if NO_CITA_TEXT in content:
            try:
                await page.click("input[value='Salir']", timeout=5_000)
            except PlaywrightTimeoutError:
                pass
            return False

        # Cita доступна — остаёмся на странице
        return True

    except PlaywrightTimeoutError as e:
        print(f"[TIMEOUT] {e}")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False
