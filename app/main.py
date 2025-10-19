import csv
import time
import os
from pathlib import Path
from openpyxl import Workbook

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

INPUT_FILE = Path("input_dnis.csv")
OUTPUT_FILE = Path("/output/resultados.xlsx")
URL = "https://consultaelectoral.onpe.gob.pe/inicio"


def leer_dnis():
    dnis = []
    with open(INPUT_FILE, mode="r", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        for fila in lector:
            dni = fila["dni"].strip()
            if dni:
                dnis.append(dni)
    return dnis


def crear_driver():
    options = Options()
    options.binary_location = "/usr/bin/chromium"

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=es-PE")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    )

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
    })

    return driver

def encontrar_input_dni(driver, wait):
    time.sleep(5)

    # debug: guarda HTML para ver qué cargó realmente
    with open("/output/debug_onpe_inicio.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    selectores = [
        "//input[@type='text']",
        "//input[@maxlength='8']",
        "//input[contains(@placeholder,'DNI')]",
        "//input[contains(@placeholder,'dni')]",
        "//input",
    ]

    ultimo_error = None

    for xpath in selectores:
        try:
            elem = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            if elem:
                return elem
        except Exception as e:
            ultimo_error = e

    # también guarda screenshot para depurar
    driver.save_screenshot("/output/debug_onpe_inicio.png")

    raise Exception("No se encontró el campo DNI")

def hacer_click_consultar(driver, wait):
    selectores = [
        "//button[contains(., 'CONSULTAR')]",
        "//*[contains(text(),'CONSULTAR')]",
        "//*[contains(text(),'Consultar')]",
        "//input[@type='submit']",
    ]

    for xpath in selectores:
        try:
            boton = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton)
            time.sleep(5)
            driver.execute_script("arguments[0].click();", boton)
            return True
        except:
            pass

    try:
        input_dni = wait.until(EC.presence_of_element_located((By.XPATH, "//input")))
        input_dni.send_keys(Keys.ENTER)
        return True
    except:
        return False


def esperar_resultado(driver, wait):
    try:
        wait.until(lambda d: "local-de-votacion" in d.current_url.lower())
        time.sleep(3)
    except TimeoutException:
        time.sleep(5)


def texto(driver, xpath):
    try:
        return driver.find_element(By.XPATH, xpath).text.strip()
    except:
        return ""


def consultar_dni(driver, dni):
    wait = WebDriverWait(driver, 20)

    driver.get(URL)
    time.sleep(5)

    input_dni = encontrar_input_dni(driver, wait)
    input_dni.clear()
    input_dni.send_keys(dni)
    time.sleep(5)

    clic_ok = hacer_click_consultar(driver, wait)

    if not clic_ok:
        return {
            "dni": dni,
            "miembro_mesa": "Error al consultar",
            "ubicacion": "",
            "direccion": ""
        }

    esperar_resultado(driver, wait)

    pagina = driver.page_source.upper()
    url_actual = driver.current_url.lower()

    if "500" in pagina or "INTERNAL SERVER ERROR" in pagina:
        return {
            "dni": dni,
            "miembro_mesa": "Error 500 ONPE",
            "ubicacion": "",
            "direccion": ""
        }

    if "NO ERES MIEMBRO DE MESA" in pagina:
        miembro = "No"
    elif "MIEMBRO DE MESA" in pagina:
        miembro = "Si"
    else:
        miembro = "No encontrado"

    ubicacion = texto(
        driver,
        "//*[contains(text(),'Región / Provincia / Distrito')]/following-sibling::*[1]"
    )

    if not ubicacion:
        ubicacion = texto(
            driver,
            "//*[contains(text(),'Región / Provincia / Distrito')]/parent::*//*[last()]"
        )

    nombre_local = texto(
        driver,
        "//*[contains(text(),'Tu local de votación')]/following::*[1]"
    )
    direccion_local = texto(
        driver,
        "//*[contains(text(),'Tu local de votación')]/following::*[2]"
    )

    direccion = ""
    if nombre_local and direccion_local:
        direccion = f"{nombre_local} - {direccion_local}"

    if not direccion:
        direccion = texto(
            driver,
            "//*[contains(text(),'Local de votación')]/following::*[1]"
        )

    return {
        "dni": dni,
        "miembro_mesa": miembro,
        "ubicacion": ubicacion,
        "direccion": direccion
    }


def generar_excel(resultados):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Resultados"

    ws.append(["DNI", "Miembro de mesa", "Ubicacion", "Direccion"])

    for r in resultados:
        ws.append([
            r["dni"],
            r["miembro_mesa"],
            r["ubicacion"],
            r["direccion"]
        ])

    wb.save(OUTPUT_FILE)


def main():
    dnis = leer_dnis()
    resultados = []
    driver = crear_driver()

    try:
        for dni in dnis:
            print(f"Consultando {dni}")
            datos = consultar_dni(driver, dni)
            print(datos)
            resultados.append(datos)
            time.sleep(5)
    finally:
        driver.quit()

    generar_excel(resultados)
    print(f"Excel generado correctamente en {OUTPUT_FILE}")


if __name__ == "__main__":
    main()