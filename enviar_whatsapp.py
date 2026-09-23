import argparse
import csv
import logging
import os
import random
import re
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "contactos.csv"
MENSAJE_PATH = BASE_DIR / "mensaje.txt"
PERFIL_CHROME = BASE_DIR / "chrome_profile"
LOG_PATH = BASE_DIR / "resultado.log"


CODIGO_PAIS = "56"
MIN_DELAY = 20
MAX_DELAY = 35
TIMEOUT = 90
HEADLESS = False

SELECTORES_CAJA_MENSAJE = [
    (By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="10"]'),
    (By.CSS_SELECTOR, '*[data-testid="conversation-compose-box-input"]'),
]

MENSAJE_ERROR = "[ERROR]"


class SendResult:
    def __init__(self):
        self.enviados = 0
        self.omitidos = 0
        self.fallidos = []

    def __str__(self):
        lineas = [
            "=" * 50,
            f"TOTAL CONTACTOS  : {self.enviados + self.omitidos + len(self.fallidos)}",
            f"ENVIADOS         : {self.enviados}",
            f"OMITIDOS         : {self.omitidos}",
            f"FALLIDOS         : {len(self.fallidos)}",
            "=" * 50,
        ]
        if self.fallidos:
            lineas.append("Reporte de fallos:")
            for telefono, motivo in self.fallidos:
                lineas.append(f"  - {telefono}: {motivo}")
        return "\n".join(lineas)


def config_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_template(path):
    try:
        texto = path.read_text(encoding="utf-8").strip()
        if not texto:
            raise ValueError("La plantilla está vacía.")
        return texto
    except FileNotFoundError:
        logging.error(f"No se encontró la plantilla: {path}")
        sys.exit(1)


def load_contact_list(ruta):
    try:
        with ruta.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        logging.error(f"No se encontró el archivo CSV: {ruta}")
        sys.exit(1)


def phone_normalize(numero, codigo_pais):
    solo_digitos = re.sub(r"\D", "", str(numero))
    if solo_digitos.startswith("00"):
        solo_digitos = solo_digitos[2:]
    if not re.fullmatch(r"\d+", solo_digitos):
        return None
    if solo_digitos.startswith(codigo_pais):
        pass
    elif solo_digitos.startswith("9") or solo_digitos.startswith("3"):
        solo_digitos = codigo_pais + solo_digitos
    if not (8 <= len(solo_digitos) <= 15):
        return None
    return solo_digitos


def fill_template(plantilla, fila):
    campos = {
        "nombre": (fila.get("nombre") or "").strip() or "estimado(a)",
        "cargo": (fila.get("cargo") or "").strip() or "su cargo",
        "comuna": (fila.get("comuna") or "").strip() or "su comuna",
        "tto": (fila.get("tto") or "").strip() or "Sres.",
    }
    mensaje = plantilla
    for clave, valor in campos.items():
        mensaje = mensaje.replace("{" + clave + "}", valor)
    return mensaje


def create_driver():
    opciones = Options()
    opciones.add_argument("--start-maximized")
    opciones.add_argument("--disable-blink-features=AutomationControlled")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    if HEADLESS:
        opciones.add_argument("--headless=new")
    opciones.add_argument(f"--user-data-dir={PERFIL_CHROME}")
    opciones.add_experimental_option("excludeSwitches", ["enable-automation"])
    opciones.add_experimental_option("useAutomationExtension", False)

    servicio = Service()
    driver = webdriver.Edge(service=servicio, options=opciones)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": (
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
        },
    )
    return driver


def load_message_box(driver, numero):
    for by, selector in SELECTORES_CAJA_MENSAJE:
        try:
            return WebDriverWait(driver, TIMEOUT).until(
                EC.presence_of_element_located((by, selector))
            )
        except Exception:
            continue

    try:
        mensaje_error = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(text(), 'invalid') or contains(text(), 'inválido')]")
            )
        )
        raise RuntimeError(f"Número inválido para WhatsApp: {numero} | {mensaje_error.text[:80]}")
    except RuntimeError:
        raise
    except Exception:
        raise RuntimeError(f"No se encontró la caja de mensaje para {numero}")


def write_message(caja, mensaje):
    caja.click()
    lineas = mensaje.splitlines()
    for i, linea in enumerate(lineas):
        if i > 0:
            caja.send_keys(Keys.SHIFT + Keys.ENTER)
        caja.send_keys(linea)
    time.sleep(1)
    caja.send_keys(Keys.ENTER)


def send_to_contact(driver, numero, mensaje):
    url = f"https://web.whatsapp.com/send?phone={numero}"
    driver.get(url)
    caja = load_message_box(driver, numero)
    write_message(caja, mensaje)
    time.sleep(2)
    return True


def random_pause():
    segundos = random.randint(MIN_DELAY, MAX_DELAY)
    logging.info(f"Esperando {segundos} s antes del siguiente contacto...")
    for restante in range(segundos, 0, -1):
        if restante % 5 == 0 or restante <= 3:
            print(f"\r  -> {restante} s", end="", flush=True)
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print("\nPausa interrumpida por el usuario.")
            raise
    print("\r" + " " * 20 + "\r", end="", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Envío masivo de WhatsApp desde CSV")
    parser.add_argument(
        "--csv", type=str, default=str(CSV_PATH), help="Ruta del archivo CSV"
    )
    parser.add_argument(
        "--mensaje", type=str, default=str(MENSAJE_PATH), help="Ruta de la plantilla"
    )
    parser.add_argument(
        "--no-delay", action="store_true", help="Desactiva el delay entre envíos"
    )
    args = parser.parse_args()

    config_logging()
    plantilla = load_template(Path(args.mensaje))
    contactos = load_contact_list(Path(args.csv))
    resultado = SendResult()

    logging.info(f"Cargados {len(contactos)} contactos desde {args.csv}")
    logging.info("Iniciando navegador. Si es la primera vez, escanea el código QR con tu WhatsApp.")
    driver = create_driver()
    logging.info("Navegador listo. Conectando a WhatsApp Web...")

    try:
        driver.get("https://web.whatsapp.com")
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div[contenteditable="true"]')
            )
        )
        logging.info("Sesión de WhatsApp Web iniciada correctamente.")
    except Exception:
        logging.error("No se pudo validar la sesión. Revisa que el QR haya sido escaneado.")
        driver.quit()
        sys.exit(1)

    try:
        for idx, fila in enumerate(contactos, start=1):
            numero_original = fila.get("telefono", "").strip()
            numero = phone_normalize(numero_original, CODIGO_PAIS)
            nombre = (fila.get("nombre") or "").strip() or "sin nombre"
            if numero is None:
                logging.warning(f"[{idx}] {nombre}: teléfono inválido ({numero_original}) -> omitido")
                resultado.omitidos += 1
                continue

            mensaje = fill_template(plantilla, fila)
            try:
                send_to_contact(driver, numero, mensaje)
                resultado.enviados += 1
                logging.info(f"[{idx}] ENVIADO -> {nombre} ({numero})")
            except Exception as e:
                resultado.fallidos.append((numero, str(e)))
                logging.error(f"[{idx}] FALLO -> {nombre} ({numero}): {e}")
                time.sleep(3)

            if not args.no_delay and idx < len(contactos):
                try:
                    random_pause()
                except KeyboardInterrupt:
                    logging.info("Ejecución detenida por el usuario.")
                    break
    finally:
        driver.quit()

    resumen = str(resultado)
    logging.info("Proceso finalizado.\n" + resumen)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProceso detenido. Cierra el navegador manualmente si quedó abierto.")