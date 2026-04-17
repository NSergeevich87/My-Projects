import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from checker import run_check

RETRY_INTERVAL = 15 * 60  # 15 минут


def notify():
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n{'='*50}")
    print(f"[{ts}] CITA DISPONIBLE! Открой браузер — страница ждёт.")
    print(f"{'='*50}\n")
    print("\a")  # системный звуковой сигнал


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="es-ES",
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        attempt = 1
        while True:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] Попытка #{attempt}...")

            available = await run_check(page)

            if available:
                notify()
                print("Нажми Enter чтобы закрыть браузер...")
                input()
                break
            else:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] Cita недоступна. Следующая попытка через 10 минут.")
                attempt += 1
                await asyncio.sleep(RETRY_INTERVAL)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
