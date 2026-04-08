import csv
import time
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
OUTPUT_FILE = Path(f"../output/resultados_{int(time.time())}.xlsx")
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
    options.add_argument("--start-maximized")
    service = Service("chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def encontrar_input_dni(driver, wait):
    selectores = [
        "//input[@type='text']",
        "//input[contains(@placeholder,'DNI')]",
        "//input",
    ]

    for xpath in selectores:
        try:
            return wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        except:
            pass

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
            time.sleep(1)
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


def texto(xpath, driver):
    try:
        return driver.find_element(By.XPATH, xpath).text.strip()
    except:
        return ""


def consultar_dni(driver, dni):
    wait = WebDriverWait(driver, 20)

    driver.get(URL)
    time.sleep(2)

    input_dni = encontrar_input_dni(driver, wait)
    input_dni.clear()
    input_dni.send_keys(dni)
    time.sleep(1)

    clic_ok = hacer_click_consultar(driver, wait)

    if not clic_ok:
        return {
            "dni": dni,
            "miembro_mesa": "Error al consultar",
            "nombres": "",
            "ubicacion": "",
            "direccion": ""
        }

    esperar_resultado(driver, wait)

    pagina = driver.page_source.upper()

    # Miembro de mesa
    if "NO ERES MIEMBRO DE MESA" in pagina:
        miembro = "No"
    elif "ERES MIEMBRO DE MESA" in pagina:
        miembro = "Si"
    else:
        miembro = "No encontrado"

    # Nombres
    nombres = texto(
        "//*[contains(text(),'Nombres y Apellidos')]/following-sibling::*[1]",
        driver
    )

    if not nombres:
        nombres = texto(
            "//*[contains(text(),'Nombres y Apellidos')]/parent::*//*[last()]",
            driver
        )

    # Ubicación
    ubicacion = texto(
        "//*[contains(text(),'Región / Provincia / Distrito')]/following-sibling::*[1]",
        driver
    )

    if not ubicacion:
        ubicacion = texto(
            "//*[contains(text(),'Región / Provincia / Distrito')]/parent::*//*[last()]",
            driver
        )

    # Dirección / local de votación
    direccion = texto(
        "//*[contains(text(),'Tu local de votación')]/ancestor::*[1]/following::*[contains(text(),'IEI') or contains(text(),'I.E.') or contains(text(),'COLEGIO')][1]",
        driver
    )

    if not direccion:
        direccion = texto(
            "//*[contains(text(),'Tu local de votación')]/following::*[contains(text(),'MZ') or contains(text(),'JR') or contains(text(),'AV')][1]",
            driver
        )

    # Mejor lectura del bloque del local
    nombre_local = texto(
        "//*[contains(text(),'Tu local de votación')]/following::*[1]",
        driver
    )
    direccion_local = texto(
        "//*[contains(text(),'Tu local de votación')]/following::*[2]",
        driver
    )

    if nombre_local and direccion_local:
        direccion = f"{nombre_local} - {direccion_local}"

    return {
        "dni": dni,
        "miembro_mesa": miembro,
        "nombres": nombres,
        "ubicacion": ubicacion,
        "direccion": direccion
    }


def generar_excel(resultados):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Resultados"

    ws.append(["DNI", "Miembro de mesa", "Nombres", "Ubicacion", "Direccion"])

    for r in resultados:
        ws.append([
            r["dni"],
            r["miembro_mesa"],
            r["nombres"],
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
            time.sleep(2)
    finally:
        driver.quit()

    generar_excel(resultados)
    print(f"Excel generado correctamente en {OUTPUT_FILE}")


if __name__ == "__main__":
    main()