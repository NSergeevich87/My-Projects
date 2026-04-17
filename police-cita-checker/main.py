import asyncio
from datetime import datetime
from pathlib import Path
from patchright.async_api import async_playwright
from checker import run_check

RETRY_INTERVAL = 15 * 60
BACKOFF_INTERVAL = 30 * 60

PROFILE_DIR = str(Path.home() / "chrome-cita-profile")
LOG_FILE = Path(__file__).parent / "cita_log.txt"


def log(message: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def notify():
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n{'='*50}")
    print(f"[{ts}] CITA DISPONIBLE! Открой браузер — страница ждёт.")
    print(f"{'='*50}\n")
    print("\a")
    log("*** CITA DISPONIBLE ***")


async def countdown(seconds: int):
    for remaining in range(seconds, 0, -60):
        mins = remaining // 60
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] Следующая попытка через {mins} мин...")
        await asyncio.sleep(min(60, remaining))


async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            channel="chrome",
            headless=False,
            viewport={"width": 1280, "height": 800},
            locale="es-ES",
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            },
        )
        page = await context.new_page()
        warmup_done = False
        attempt = 1

        try:
            while True:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] Попытка #{attempt}...")

                available, server_error = False, False
                try:
                    available, server_error = await run_check(page)
                except Exception as e:
                    print(f"[ERROR] {e}")

                if available:
                    notify()
                    print("Нажми Enter чтобы закрыть браузер...")
                    input()
                    break

                log(f"Попытка #{attempt}: cita недоступна{' (ошибка сервера)' if server_error else ''}")

                if server_error and not warmup_done:
                    print("\n" + "="*50)
                    print("WAF заблокировал — открываю стартовую страницу.")
                    print("Пройди форму ВРУЧНУЮ один раз в этом окне.")
                    print("Когда закончишь — нажми Enter здесь.")
                    print("="*50)
                    await page.goto("https://icp.administracionelectronica.gob.es/icpplustieb/index", timeout=30_000)
                    input()
                    warmup_done = True
                    attempt += 1
                    continue

                interval = BACKOFF_INTERVAL if server_error else RETRY_INTERVAL
                await countdown(interval)
                attempt += 1
        finally:
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())
