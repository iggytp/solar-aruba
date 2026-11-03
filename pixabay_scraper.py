import os
import time
from pathlib import Path

import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


KEYWORDS = ["solar", "panel", "sun", "energy", "photovoltaic", "placa", "paneles"]


def scrape_extra_solar_images(
    output_dir: str | Path = "solar_panel_images",
    max_images: int = 20,
    scrolls: int = 4,
    headless: bool = False,
) -> list[str]:
    """Descarga imágenes relevantes de paneles solares desde Pixabay.

    Args:
        output_dir: carpeta de salida para guardar las imágenes.
        max_images: número máximo de imágenes a guardar.
        scrolls: número de scrolls para cargar imágenes lazy-load.
        headless: si se quiere ejecutar Chrome en modo headless.

    Returns:
        Lista con las rutas locales de las imágenes guardadas.
    """
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)

    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    if headless:
        options.add_argument("--headless=new")

    driver = uc.Chrome(options=options)
    image_urls: list[str] = []
    saved_files: list[str] = []
    url = "https://pixabay.com/images/search/solar%20panel/"

    try:
        print(f"Abriendo {url}...")
        driver.get(url)

        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))

        for step in range(1, scrolls + 1):
            driver.execute_script(f"window.scrollTo(0, {step * 600});")
            time.sleep(1.2)

        for img in driver.find_elements(By.TAG_NAME, "img"):
            try:
                alt = (img.get_attribute("alt") or "").lower()
                if not any(keyword in alt for keyword in KEYWORDS):
                    continue

                is_ad = driver.execute_script(
                    'return arguments[0].closest(\'[class*="sponsor"], [class*="ad-"]\') !== null;',
                    img,
                )
                if is_ad:
                    continue

                srcset = img.get_attribute("srcset")
                src = None
                if srcset:
                    entries = srcset.split(",")
                    src = entries[-1].strip().split(" ")[0]

                if not src or "data:image" in src:
                    src = img.get_attribute("src") or img.get_attribute("data-src")

                if not src or not src.startswith("http") or src.endswith(".svg"):
                    continue

                if any(token in src for token in ["avatar", "profile", "icon"]):
                    continue

                if src not in image_urls:
                    image_urls.append(src)
                    print(f"Encontrada [{len(image_urls)}/{max_images}]: {alt[:50]}...")

                if len(image_urls) >= max_images:
                    break
            except Exception:
                continue
    finally:
        driver.quit()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print(f"\nDescargando {len(image_urls)} imágenes validadas...")

    for index, img_url in enumerate(image_urls, start=1):
        try:
            response = requests.get(img_url, headers=headers, timeout=10)
            if response.status_code != 200:
                continue

            ext = img_url.split(".")[-1].split("?")[0].lower()
            if ext not in ["jpg", "jpeg", "png", "webp"]:
                ext = "jpg"

            file_path = folder / f"solar_panel_{index:02d}.{ext}"
            file_path.write_bytes(response.content)
            saved_files.append(file_path.as_posix())
            print(f"[{index}/{len(image_urls)}] Guardada: {file_path.as_posix()}")
        except Exception as exc:
            print(f"[{index}/{len(image_urls)}] Error al descargar {img_url}: {exc}")

    print(f"\nCompletado. Total guardadas: {len(saved_files)}")
    return saved_files


if __name__ == "__main__":
    scrape_extra_solar_images(output_dir="solar_panel_images", max_images=20, scrolls=4)