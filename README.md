# WS Sender — Envío automatizado de WhatsApp

Script en Python que automatiza el envío de mensajes personalizados por **WhatsApp Web** a una lista de contactos definida en un archivo CSV, utilizando **Selenium** y **Microsoft Edge**.

> ⚠️ **Lee las advertencias antes de usarlo.** WhatsApp no autoriza oficialmente la automatización de WhatsApp Web. El uso indebido puede provocar el **baneo permanente de tu número**.

---

## Descripción

El programa:

1. Abre WhatsApp Web en un navegador Edge controlado por Selenium (perfil persistente).
2. Espera a que escanees el código QR la primera vez.
3. Lee los contactos desde `contactos.csv`.
4. Normaliza los números de teléfono (agrega el código de país, por defecto `56` para Chile).
5. Rellena una plantilla de mensaje (`mensaje.txt`) con los datos de cada contacto (`{nombre}`, `{cargo}`, `{comuna}`).
6. Envía el mensaje contactando uno por uno, con una pausa aleatoria entre envíos.
7. Registra el resultado en pantalla y en `resultado.log` (enviados, omitidos y fallidos).

---

## Estructura del proyecto

```
wssender/
├── enviar_whatsapp.py     # Script principal
├── contactos.csv          # Lista de contactos (entrada)
├── mensaje.txt            # Plantilla del mensaje
├── requirements.txt       # Dependencias de Python
├── resultado.log          # Registro de ejecuciones (se genera al correr)
└── chrome_profile/        # Perfil del navegador (se genera al correr)
```

> Nota: aunque la carpeta se llama `chrome_profile`, el script usa el navegador **Edge** (el nombre se mantiene por compatibilidad).

---

## Requisitos

- **Python 3.9+**
- **Microsoft Edge** instalado (el script usa `webdriver.Edge`; Selenium descarga el driver automáticamente).
- Una cuenta de WhatsApp activa y un teléfono para escanear el código QR.

Instalar dependencias:

```bash
pip install -r requirements.txt
```

---

## Configuración

### 1. `contactos.csv`

Archivo CSV con encabezado. Columnas usadas por el script:

| Columna    | Obligatoria | Descripción                                          |
|------------|-------------|------------------------------------------------------|
| `telefono` | Sí          | Número de teléfono (con o sin `+`, espacios o guiones) |
| `nombre`   | No          | Se reemplaza en `{nombre}`                           |
| `cargo`    | No          | Se reemplaza en `{cargo}`                            |
| `comuna`   | No          | Se reemplaza en `{comuna}`                           |

Ejemplo:

```csv
telefono,nombre,cargo,comuna
+56912341234,Carlos,Analista Regional,Viña del Mar
+56946784568,Juan Pérez,Analista Universal,Valparaíso
```

- El script limpia los números (quita símbolos) y agrega el prefijo `56` si el número empieza con `9` o `3`.
- Los números inválidos se **omiten** y quedan registrados en el log.

### 2. `mensaje.txt`

Plantilla del mensaje. Usa llaves para los campos dinámicos:

```
Buen día {nombre},
le escribo desde la comuna de {comuna} ...
```

Si un campo no existe en el CSV, se usa un valor por defecto (`estimado(a)`, `su cargo`, `su comuna`).

---

## Uso

Ejecutar con la configuración por defecto:

```bash
python enviar_whatsapp.py
```

Opciones disponibles:

| Argumento        | Descripción                                               |
|------------------|-----------------------------------------------------------|
| `--csv RUTA`     | Ruta alternativa del archivo CSV                          |
| `--mensaje RUTA` | Ruta alternativa de la plantilla de mensaje               |
| `--no-delay`     | **Desactiva la pausa entre envíos (NO recomendado)**      |

Ejemplo:

```bash
python enviar_whatsapp.py --csv contactos.csv --mensaje mensaje.txt
```

**Primera ejecución:** se abrirá Edge y deberás **escanear el código QR** con tu teléfono. La sesión queda guardada en `chrome_profile/`, así que en las siguientes ejecuciones no hará falta volver a escanear.

Para detener el proceso: `Ctrl+C`.

---

## Warnings y consideraciones importantes

### 🚫 Riesgo de baneo de WhatsApp

- **WhatsApp prohíbe el envío masivo, automatizado o no solicitado de mensajes.** Es la causa principal de bloqueos de cuenta.
- El baneo puede ser **temporal o permanente** y suele aplicarse **sin previo aviso**.
- Usar `--no-delay` aumenta drásticamente el riesgo de detección y bloqueo.
- Mensajes con **enlaces, publicidad o contenido idéntico repetido** son señales típicas de spam que disparan el bloqueo.
- Cuentas nuevas, que envían a muchos números desconocidos, o que reciben reportes de los destinatarios, tienen mayor probabilidad de ser bloqueadas.

### ⏱️ Límites recomendados

- El script usa por defecto una pausa aleatoria de **20 a 35 segundos** entre mensajes. **No la reduzcas.**
- Recomendación de buenas prácticas (no garantizan inmunidad):
  - Máximo **20–50 mensajes por día** para cuentas normales, y menos para cuentas nuevas.
  - **No enviar en ráfaga**: distribuir los envíos durante la jornada.
  - Evitar escribir a personas que **no te conocen** o que **no esperan tu mensaje**.
  - Personalizar el mensaje con datos reales para que no parezca plantilla masiva.
  - Pausar y esperar si WhatsApp muestra avisos de "actividad inusual".

### 📵 Consentimiento y spam

- Envía mensajes únicamente a personas que **hayan consentido** recibirlos o con quienes tengas una relación previa.
- El envío no solicitado de comunicaciones puede constituir **spam** y vulnerar leyes de comunicaciones no deseadas.

### ⚖️ Privacidad y protección de datos

- El archivo `contactos.csv` puede contener **datos personales**. Manipúlalos conforme a la normativa aplicable (en Chile, la **Ley 19.628** sobre protección de la vida privada y, de ser aplicable, la Ley 21.719).
- No subas este repositorio con datos reales de terceros a internet.
- **No incluyas** los archivos `contactos.csv`, `resultado.log` ni `chrome_profile/` en sistemas de control de versiones. Agrega un `.gitignore`.

### 🔐 Seguridad de la sesión

- La carpeta `chrome_profile/` contiene tu **sesión activa de WhatsApp**. Si alguien accede a ella, podría usar tu cuenta. Protégela y no la compartas.
- El script desactiva señales de automatización del navegador (`navigator.webdriver`). Esto **no** garantiza que WhatsApp no detecte el uso de Selenium, y puede dejar de funcionar cuando WhatsApp actualice el sitio.

### 🧩 Limitaciones técnicas

- El script depende de selectores del DOM de WhatsApp Web que **cambian sin aviso**; puede dejar de encontrar la caja de mensaje y fallar.
- No verifica de forma fiable la **entrega real** del mensaje: `ENVIADO` en el log significa que el script logró enviar la acción, no que el destinatario lo recibió.
- No hay reintentos automáticos; los fallos se registran y el proceso continúa.

### ✅ Buen uso

- Usa este software **bajo tu propia responsabilidad** y solo con fines legítimos (comunicaciones consentidas, avisos internos, etc.).
- Respeta los **Términos de Servicio de WhatsApp**.

---

## Registro de resultados

Al finalizar, se muestra y guarda un resumen del tipo:

```
==================================================
TOTAL CONTACTOS  : 2
ENVIADOS         : 1
OMITIDOS         : 1
FALLIDOS         : 0
==================================================
```

El detalle queda en `resultado.log`.
