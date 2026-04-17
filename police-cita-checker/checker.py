import asyncio
import random
from patchright.async_api import Page, TimeoutError as PlaywrightTimeoutError

NIE = "Z4186374B"
NAME = "MARC NIKIFOROV VOLKOV"
URL = "https://icp.administracionelectronica.gob.es/icpplustieb/index"
NO_CITA_TEXT = "En este momento no hay citas disponibles."
WAF_TEXT = "The requested URL was rejected"


async def delay():
    await asyncio.sleep(random.uniform(2, 5))


async def check_waf(page: Page) -> bool:
    return WAF_TEXT in await page.content()


async def human_click(page: Page, selector: str):
    await page.hover(selector)
    await asyncio.sleep(random.uniform(0.3, 0.8))
    await page.click(selector)


async def human_type(page: Page, selector: str, text: str):
    await page.click(selector)
    await asyncio.sleep(random.uniform(0.2, 0.5))
    await page.type(selector, text, delay=random.randint(80, 160))


async def run_check(page: Page) -> tuple[bool, bool]:
    """
    Проходит весь flow бронирования.
    Возвращает (cita_available, server_error).
    """
    try:
        # Шаг 1: открыть страницу
        print("[1/11] Открываю страницу...")
        response = await page.goto(URL, timeout=30_000)
        if response and response.status >= 400:
            print(f"[ERROR] Сервер вернул HTTP {response.status} — пропускаем попытку")
            return False, True
        print(f"[1/11] Страница загружена (HTTP {response.status if response else '?'})")
        if await check_waf(page):
            print("[ERROR] WAF заблокировал запрос")
            return False, True
        await delay()

        # Шаг 2: выбрать Barcelona в списке провинций
        print("[2/11] Выбираю провинцию Barcelona...")
        await page.wait_for_selector("select#form", timeout=30_000)
        await page.hover("select#form")
        await asyncio.sleep(random.uniform(0.3, 0.7))
        await page.select_option("select#form", label="Barcelona")
        print("[2/11] Barcelona выбрана")
        await delay()

        # Шаг 3: Aceptar (первая кнопка)
        print("[3/11] Нажимаю Aceptar (1)...")
        await human_click(page, "input[value='Aceptar']")
        await page.wait_for_load_state("domcontentloaded", timeout=15_000)
        if await check_waf(page):
            print("[ERROR] WAF заблокировал после Aceptar (1)")
            return False, True
        print("[3/11] OK")
        await delay()

        # Шаг 4: выбрать tramite по частичному совпадению текста
        TRAMITE_KEYWORD = "EXPEDICIÓN DE TARJETAS"
        print(f"[4/11] Ищу tramite '{TRAMITE_KEYWORD}'...")
        await page.wait_for_selector("select[name='tramiteGrupo[0]']", timeout=30_000)
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
            return False, False
        await page.hover("select[name='tramiteGrupo[0]']")
        await asyncio.sleep(random.uniform(0.3, 0.7))
        await page.select_option("select[name='tramiteGrupo[0]']", value=option_value)
        print(f"[4/11] Выбран tramite (value={option_value})")
        await delay()

        # Шаг 5: Aceptar (вторая кнопка)
        print("[5/11] Нажимаю Aceptar (2)...")
        await human_click(page, "input[value='Aceptar']")
        await page.wait_for_load_state("domcontentloaded", timeout=15_000)
        if await check_waf(page):
            print("[ERROR] WAF заблокировал после Aceptar (2)")
            return False, True
        print("[5/11] OK")
        await delay()

        # Шаг 6: Entrar
        print("[6/11] Жду кнопку Entrar...")
        await page.wait_for_selector("input[value='Entrar']", timeout=30_000)
        await human_click(page, "input[value='Entrar']")
        print("[6/11] Нажал Entrar")
        await delay()

        # Шаг 7–8: ввод данных
        print("[7/11] Жду форму ввода данных...")
        await page.wait_for_selector("input#txtIdCitado", timeout=30_000)
        print(f"[7/11] Ввожу NIE: {NIE}")
        await human_type(page, "input#txtIdCitado", NIE)
        await delay()
        print(f"[8/11] Ввожу имя: {NAME}")
        await human_type(page, "input#txtDesCitado", NAME)
        await delay()

        # Шаг 9: Aceptar (третья кнопка)
        print("[9/11] Нажимаю Aceptar (3)...")
        await human_click(page, "input[value='Aceptar']")
        await page.wait_for_load_state("domcontentloaded", timeout=15_000)
        if await check_waf(page):
            print("[ERROR] WAF заблокировал после Aceptar (3)")
            return False, True
        print("[9/11] OK")
        await delay()

        # Шаг 10: Solicitar Cita
        print("[10/11] Жду кнопку Solicitar Cita...")
        await page.wait_for_selector("input[value='Solicitar Cita']", timeout=30_000)
        await human_click(page, "input[value='Solicitar Cita']")
        print("[10/11] Нажал Solicitar Cita")
        await delay()

        # Шаг 11: проверить наличие сообщения "нет citas"
        print("[11/11] Жду ответ сервера...")
        await page.wait_for_load_state("networkidle", timeout=15_000)
        content = await page.content()

        if "Internal Server Error" in content or "Too Many Requests" in content:
            print("[ERROR] Сервер вернул ошибку на странице — пропускаем попытку")
            return False, True

        if NO_CITA_TEXT in content:
            print("[11/11] Cita недоступна — нет свободных слотов")
            return False, False

        # Cita доступна — остаёмся на странице
        return True, False

    except PlaywrightTimeoutError as e:
        print(f"[TIMEOUT] {e}")
        return False, False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False, False
