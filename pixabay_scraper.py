import os
import time
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

output_folder = "solar_panel_images"
os.makedirs(output_folder, exist_ok=True)

options = uc.ChromeOptions()
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")

driver = uc.Chrome(options=options)

url = "https://pixabay.com/images/search/solar%20panel/"
print(f"Abriendo {url}...")
driver.get(url)

wait = WebDriverWait(driver, 15)
# Esperar a que cargue la lista de fotos
wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))

# Scroll gradual para forzar la carga perezosa de imágenes reales
for step in range(1, 5):
    driver.execute_script(f"window.scrollTo(0, {step * 600});")
    time.sleep(1.2)

# Obtener todos los elementos <img>
all_imgs = driver.find_elements(By.TAG_NAME, "img")

image_urls = []
for img in all_imgs:
    try:
        alt = (img.get_attribute("alt") or "").lower()
        
        # 1. Descartar avatares, fotos de perfil o imágenes sin descripción relevante
        # Filtramos palabras clave mínimas para asegurar que sean paneles / energía
        keywords = ["solar", "panel", "sun", "energy", "photovoltaic", "placa", "paneles"]
        if not any(k in alt for k in keywords):
            continue

        # 2. Descartar anuncios patrocinados (iStock / Shutterstock suelen venir en contenedores con clases sponsor/sponsored)
        parent_html = driver.execute_script(
            "return arguments[0].closest('[class*=\"sponsor\"], [class*=\"ad-\"]') !== null;", 
            img
        )
        if parent_html:
            continue

        # 3. Extraer la URL de mayor resolución del srcset
        srcset = img.get_attribute("srcset")
        src = None
        if srcset:
            entries = srcset.split(",")
            src = entries[-1].strip().split(" ")[0]
        
        if not src or "data:image" in src:
            src = img.get_attribute("src") or img.get_attribute("data-src")

        # 4. Validar formato de URL web estándar de Pixabay
        if src and src.startswith("http") and not src.endswith(".svg"):
            # Evitar avatares o iconos del sistema
            if "avatar" in src or "profile" in src or "icon" in src:
                continue

            if src not in image_urls:
                image_urls.append(src)
                print(f"Encontrada [{len(image_urls)}/20]: {alt[:50]}...")

        if len(image_urls) >= 20:
            break

    except Exception:
        continue

print(f"\nDescargando {len(image_urls)} imágenes validadas...")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

for i, img_url in enumerate(image_urls, start=1):
    try:
        resp = requests.get(img_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            ext = img_url.split(".")[-1].split("?")[0].lower()
            if ext not in ["jpg", "jpeg", "png", "webp"]:
                ext = "jpg"
                
            path = os.path.join(output_folder, f"solar_panel_{i:02d}.{ext}")
            with open(path, "wb") as f:
                f.write(resp.content)
            print(f"[{i}/20] Guardada: {path}")
    except Exception as e:
        print(f"[{i}/20] Error al descargar {img_url}: {e}")

driver.quit()
print("\nCompletado con éxito.")