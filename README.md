# missionboard

**Español** · [English](README.en.md)

Una app familiar para una tablet compartida. Los niños siguen sus **misiones**
(tareas con imágenes y voz), ganan **estrellas**, las gastan en una
**tienda** y desbloquean un **premio del día** con una ruleta. Las **rutinas** guían
los momentos con prisa (prepararse para el cole, irse a dormir) con un despertador,
un reloj que habla y música. Todo se configura en la **zona de padres**, protegida
con un código.

La app está en español; el código, los comentarios y los tests, en inglés.

## Qué hace

- **Misiones de la familia:** cada misión tiene tareas, y cada tarea, sus pistas
  (lo que no hay que olvidar: dientes, cara…). Todas son
  de todos los niños, y a cada uno se le activa lo suyo. Cada misión tiene su color,
  sus días, su horario y, si se quiere, su rutina.
- **Pantallas de los niños:** cada niño se reconoce por su avatar; su día es una ruta
  de misiones, y cada misión se abre como un panel de tarjetas: cada tarea es una tarjeta
  que se marca con un toque, con sus pistas en pequeño como recordatorio. Estrellas, una celebración al completar una
  misión y un premio del día al completarlas todas. Los fondos cambian con la estación
  y el momento del día.
- **Rutinas:** le ponen tiempo a una misión: sus partes son las tareas, con sus
  minutos, entre un despertador y una meta. Se fija la hora de empezar o la de
  terminar, y el resto se coloca solo. Para los niños de la rutina manda su horario;
  los demás siguen el de la misión. En pantalla: un reloj con el tramo de cada parte,
  una voz que dice lo que toca, avisos antes de acabar cada parte, una cuenta atrás de
  diez segundos, cada niño con su misión, y música en las partes que se elijan. Una
  rutina puede sonar a una hora o lanzarse a mano.
- **Zona de padres:** niños, misiones, rutinas (con un modo de prueba que va más
  rápido y deja poner las misiones de los niños como se quiera), premios, tienda, el
  código de padres, un registro de lo que pasa (exportable a CSV) y **copias de
  seguridad**.
- **Voz natural:** las frases se dicen con [Piper](https://github.com/OHF-Voice/piper1-gpl)
  en el servidor y se guardan; si no está, se usa la voz de la propia tablet.
- **Funciona sin internet:** no depende de servicios externos; las letras y las
  imágenes van dentro de la app.

## Arrancarla

Hace falta Python 3.12.

```bash
python -m venv .venv && source .venv/bin/activate   # o un entorno de conda
pip install -r requirements.txt -r requirements-dev.txt
MISSIONBOARD_DATA_DIR=data uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

Abre <http://localhost:8002/>. El código de padres por defecto es **1234**: cámbialo
en *Configurar → Código de padres*. Una instalación nueva trae de ejemplo tres niños
(Bea, Alex y Noa) y tres misiones (Despegue, Aterrizaje y Alunizaje), con sus rutinas y
dos canciones, para cambiarlos a tu gusto.

`bash dev.sh` hace lo mismo con un entorno de conda llamado `missionboard`, y escribe
la dirección para abrirla desde una tablet de la misma red.

### La voz natural (opcional)

Sin modelo de voz, la app usa la voz del aparato. Para usar Piper, pon
[`es_ES-sharvard-medium.onnx`](https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_ES/sharvard/medium)
y su `.onnx.json` en `data/voices/`, o indica el `.onnx` en `MISSIONBOARD_VOICE_MODEL`.
La imagen de Docker lo descarga al construirse.

## Docker

```bash
docker compose up -d --build
```

La app escucha en el puerto 8003 y guarda sus datos en `./data`.

## Los datos

Todo lo que la familia configura y hace está en una carpeta de datos, nunca en el
repositorio. Su ruta la da `MISSIONBOARD_DATA_DIR`: `data/` por defecto, `/srv/data` en
la imagen de Docker (montada desde `./data`) y `/data` en el addon de Home Assistant (el
almacenamiento persistente que Home Assistant asigna a cada addon).

| Ruta | Qué hay |
|---|---|
| `config.yaml` | Niños, misiones, rutinas, premios, tienda, ajustes e interruptores |
| `missionboard.db` | SQLite: el historial (tareas marcadas, misiones hechas, estrellas, premios, compras, rutinas, registro) |
| `photos/`, `sounds/` | Fotos y canciones subidas |
| `voice-cache/` | Las frases ya dichas; si faltan, se vuelven a generar |
| `backups/` | Lo que había antes de poner una copia o de empezar de cero |

Los fondos son de la app (`app/static/backgrounds/`), uno por estación y momento del
día; las fechas y las horas de cada estación están en `settings.seasons`.

- **Migraciones:** se aplican solas al arrancar, y el archivo anterior se guarda al
  lado (`config.yaml.vN.bak`, `missionboard.db.vN.bak`). Si un archivo es de una
  versión más nueva que la app, la app no arranca en vez de cambiarlo.
- **Empezar de cero:** un `config.yaml` anterior a las misiones de la familia no se
  convierte: al arrancar se guarda una copia de todo en `backups/` y se empieza con los
  ejemplos, conservando la biblioteca de canciones. Una copia de seguridad de entonces
  no se puede restaurar.
- **Copias de seguridad:** *Configurar → Copia de seguridad* descarga todo en un
  `.zip` (configuración, historial, fotos y música) y restaura un archivo
  así: primero lo comprueba, y lo que había se guarda en `backups/`. Es la forma de
  llevar una familia a otro aparato.
- `settings` y `features` de `config.yaml` se pueden editar a mano. Al arrancar, la app
  escribe los que falten con su valor por defecto, para que estén todos a la vista; los
  que ya estén no se tocan, tampoco al actualizar. Si un valor no vale, la app no arranca
  y dice cuál. Entre ellos, las estaciones (`seasons`: inicio, amanecer y atardecer) y el
  margen de la mañana y la tarde alrededor de esas horas (`moment_margin_minutes`).

## Tests

```bash
pytest
```

Los tests prueban la API HTTP y los servicios. Uno falla si se escribe un color
fuera de `app/static/css/tokens.css`.

## Estructura

```
app/
  main.py                 la app FastAPI: rutas, estado compartido, comprobaciones al arrancar
  <funcionalidad>/        children, missions, today, routines, prizes,
                          shop, songs, events, backup, voice…
    api.py                rutas: HTTP y validación
    service.py            reglas, en Python puro
    repository.py         leer y escribir YAML o SQLite
  samples.py              los ejemplos de una instalación nueva
  storage/                config.yaml y sus migraciones, SQLite y sus migraciones, empezar de cero
  static/                 la interfaz: HTML, CSS y módulos JavaScript, sin compilar
    css/tokens.css        todos los colores, tamaños y tiempos (themes/ tiene los colores de Material)
    js/screens/           un módulo por pantalla
themes/                   exportaciones de Material Theme Builder
tools/                    generadores de temas, de la librería de imágenes y de los fondos
tests/
```

Servidor: FastAPI, PyYAML, SQLite. Interfaz: HTML, CSS y módulos JavaScript, sin
frameworks ni empaquetadores.

## Recursos de terceros

| | Licencia |
|---|---|
| [Fluent Emoji](https://github.com/microsoft/fluentui-emoji) (`app/static/libraries/fluent/`) | MIT, ver `LICENSE-fluent-emoji.txt` |
| Palabras clave en español de [Unicode CLDR](https://cldr.unicode.org/) | Unicode License, ver `LICENSE-unicode-cldr.txt` |
| [Nunito](https://fonts.google.com/specimen/Nunito) (`app/static/fonts/nunito/`) | SIL Open Font License, ver `OFL.txt` |
| [Piper](https://github.com/OHF-Voice/piper1-gpl) (`piper-tts`, se instala con pip) | Ver su repositorio |
| Modelo de voz `es_ES-sharvard-medium` (se descarga, no está en el repositorio) | Ver su [ficha](https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_ES/sharvard/medium) |

Las canciones de ejemplo (`app/samples_sounds/`: «Buenos días, solecito» y «Duerme,
Estrellita») se publican con el repositorio, bajo su licencia MIT.

Dibujados para este proyecto, con la licencia MIT del repositorio: el pijama
(`app/static/libraries/own/`) y los fondos (`app/static/backgrounds/`, con sus programas
en `tools/fondos/`, que necesitan Pillow).

## Licencia

[MIT](LICENSE). Los recursos de terceros de la tabla de arriba llevan cada uno su licencia.
