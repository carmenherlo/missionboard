# CLAUDE.md · missionboard

App familiar para tablet: los niños completan misiones (tareas con pistas, voz), ganan estrellas, las gastan en una tienda, desbloquean un premio del día con una ruleta y llenan una racha semanal. Rutinas con reloj y voz. Zona de padres protegida con código.

- **El plan y el estado** (dónde lo dejamos, siguiente paso, decisiones tomadas): [docs/plan.md](docs/plan.md). Leerlo al empezar y seguir desde «Estado».
- **El alcance:** [docs/propuesta-mapa.md](docs/propuesta-mapa.md). Si algo no está ahí, se pregunta antes de hacerlo.
- **Los bocetos:** `docs/wireframes/`. `docs/` no va a git.
- Este archivo solo tiene reglas. El estado y las decisiones van a `docs/plan.md`, y lo privado a `CLAUDE.local.md`.

## Idioma

- Conversación: español. Código, comentarios, nombres, tests y commits: inglés. Textos de la app: español.

## Comandos

- Entorno: `.venv` con uv. Recrearlo: `uv venv --python 3.12 .venv && uv pip install -r requirements.txt -r requirements-dev.txt`.
- Tests: `.venv/bin/pytest` (cobertura: `--cov`).
- Antes de cada commit: `ruff format .` y `ruff check .` sin avisos (reglas en `pyproject.toml`, líneas de 120).
- Servidor de desarrollo: `bash dev.sh` (8002, datos de `data/`) y `bash dev.sh --fresh` (8003, instalación nueva en `data-fresh/`, vaciada en cada arranque).

## Stack

- Backend: FastAPI (Python 3.12).
- Configuración (niños, misiones, premios, rutinas, tienda, `settings`, `features`): YAML (`config.yaml`), la fuente de verdad, reescrita por la UI.
- Estado e historial (estrellas, misiones hechas, ruleta, rachas, registro): SQLite.
- Frontend: HTML, CSS y JavaScript vanilla, con módulos nativos. Sin frameworks, sin bundlers, sin build step.
- Tests: pytest y `TestClient` de FastAPI.

## Arquitectura

MVP que cambiará: el código debe ser **fácil de cambiar**, no estar preparado para todo. Nada de abstracciones sin un segundo caso real, pero sí los límites que abaratan el cambio.

### Backend

- Cada funcionalidad es un paquete `app/<funcionalidad>/` con `api.py` (rutas: HTTP, validación Pydantic, errores a códigos HTTP), `service.py` (reglas, Python puro, sin FastAPI ni archivos) y `repository.py` (lo único que lee y escribe YAML o SQLite).
- Las dependencias (almacén, base de datos, reloj, carpeta de datos) llegan con `Depends`; los «getters», en `app/deps.py`. Errores de dominio en `app/errors.py`; `main.py` los traduce a HTTP.
- **«Ahora» en un solo sitio:** `app/clock.py`. Nunca `datetime.now()` ni `date.today()` sueltos.
- Lo ajustable va en `settings` del YAML, con valor por defecto; lo opcional se enciende y apaga en `features`.
- SOLID con pragmatismo: un motivo para cambiar por módulo; una funcionalidad nueva es un módulo nuevo; las variantes son datos, no cadenas de `if`.

### Frontend

- `static/js/main.js` (rutas), `api.js` (único cliente: `fetch`, errores, código de padres), `dom.js`, `components/`, `screens/` (una pantalla por archivo; `screens/child/`, `screens/parents/`), `routine/`, `effects/`.
- Textos de la app: todos en `texts.js` (un solo archivo, a propósito). Iconos: `icons.js`, pedidos por nombre (`icon("home")`); nada de emojis del sistema.
- **CSS en capas** (`app/static/css/`): `themes/*.css` generados; `tokens.css` y `tokens-effects.css` son los únicos con colores, tamaños y tiempos escritos a mano; el resto solo usa `var(--…)` (un test lo vigila). Se cargan en el orden de `index.html`, y el orden importa.
- **El JS no escribe estilos:** combina clases. Única excepción: el color del niño (`--child-color` y sus tonos).
- **Función y efectos, separados:** lo que se mueve o brilla va en `effects*.css` y `static/js/effects/`. Sin ellos, todo funciona igual, quieto. «Reducir movimiento» apaga los efectos.
- Cortes de ancho solo en 600 (móvil), 860 (dos columnas) y 1000 (menú fijo), con `max-width: N − 0,02px`; altura, `max-height: 599.98px`. Lo vigila `tests/test_breakpoints.py`.
- Pantallas nuevas: mirar antes la más parecida y reutilizar sus piezas y patrones. Un patrón nuevo, solo preguntando antes.
- Guardar: lo que ya existe se guarda al momento («✓ Guardado», sin botón); lo nuevo, con un formulario corto y un botón que dice lo que hace. Excepción: el código de padres.

### Calidad

- Nombres claros, funciones cortas, sin duplicación. Los tests prueban comportamiento por la API y los servicios, no detalles internos.
- **Tamaño de archivos:** 300 líneas en Python, 400 en JS y CSS (`tests/test_file_sizes.py`). Los de `TOO_BIG` pueden bajar, no crecer.
- **Antes de cada commit:** ¿el cambio añade una responsabilidad nueva a un archivo que ya tiene otra? Si sí, va en su propio módulo, o se avisa y se hace un `refactor:` aparte.
- Las funciones con `# noqa: C901 (to split)` son deuda pendiente de partir.

## Entorno y librerías

- Claude puede instalar paquetes en `.venv` (`uv pip install`) sin preguntar, con versión fijada: lo que usa la app, en `requirements.txt`; lo de desarrollo, en `requirements-dev.txt`. Se dice en el resumen del paso.
- Se pregunta antes de instalar paquetes del sistema (`apt`, `sudo`, `npm -g`…) o de quitar o cambiar de versión algo que ya usa la app.
- La app no usa `Pillow` ni `python-multipart`: las fotos se suben como cuerpo crudo de la petición.
- Pruebas en el navegador: `selenium` con el Firefox del sistema en headless (geckodriver en `/snap/firefox/current/usr/lib/firefox/geckodriver`). El perfil y las capturas, en una carpeta de casa (`TMPDIR`), porque el Firefox de snap no ve `/tmp`. No hay Node ni Chrome.

## Puertos y datos

- **8002 y 8003 son del usuario** (`dev.sh`). Claude nunca arranca ni para nada en ellos.
- Las pruebas de Claude en el navegador, con un servidor temporal propio y `MISSIONBOARD_DATA_DIR` en una carpeta temporal, **nunca `data/`**. Puerto: el de `.agent-port` en un worktree (8011–8019), y el 8010 en la carpeta principal. Al terminar, parar el proceso `uvicorn` de verdad y comprobar que el puerto queda libre.
- Carpeta de datos (`MISSIONBOARD_DATA_DIR`): `data/` en desarrollo, `/data` en el addon de Home Assistant. `data/` nunca va a git; en ejemplos y tests, datos ficticios (`tests/fixtures/`), nunca copias de `data/`.
- **Cambiar la forma de los datos** (YAML o SQLite): avisar antes y hacer copia de `data/`. Cada cambio lleva su migración numerada (`CURRENT_VERSION` del YAML, versión de SQLite), que se aplica sola al arrancar y tiene su test. Nunca se pide editar datos a mano.
- Ids estables y fijos para todo lo que se referencia; nunca la posición en la lista. El historial guarda el id y una copia del nombre de ese momento.

## Docker

- Docker no es el entorno de desarrollo. `requirements.txt` refleja `.venv`.
- Comprobar la imagen (`docker compose build`, arrancar, abrir `/`) cuando cambien `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, rutas, variables de entorno o cómo se sirven los estáticos. Con datos temporales, y borrando el contenedor al terminar.

## Forma de trabajar

- **Un paso cada vez**, en el orden de `docs/plan.md`. No se empieza el siguiente sin el OK.
- Cada paso empieza por su boceto (`docs/wireframes/<nombre>.html`, baja fidelidad, con preguntas y una recomendación para cada una). Con el OK, se programa; lo que cambie al programar, se refleja en el boceto.
- Al terminar: la app arranca, los tests en verde, probado de verdad usándolo; resumen corto (qué cambia, cómo probarlo); actualizar «Estado» en `docs/plan.md`; commit.
- Lo que salga fuera del alcance se apunta y se pregunta; no se hace «de paso».

## Varios agentes a la vez

- **Una tarea = una rama = un worktree = un agente.** Se crea con `bash tools/worktree.sh new <tarea>` (carpeta `../missionboard2-<tarea>`, su `.venv`, su puerto, y `docs/` y `CLAUDE.local.md` enlazados a los de la carpeta principal). `list` los enseña y `remove <tarea>` los borra.
- La carpeta principal (`main`) es la del agente que coordina con el usuario. **En un worktree no se toca `main`:** ni commits, ni merge, ni push.
- **En un worktree no se edita `docs/plan.md`** (es el mismo archivo para todos). Al acabar, el agente da su resumen para «Estado»; lo escribe la sesión de `main` al unir la rama.
- Commits en su rama, como siempre. Antes de pedir la unión: `git rebase main`, tests y ruff en verde.
- **Unir** lo decide el usuario: desde la carpeta principal, `git merge --ff-only <tarea>`, tests otra vez y `tools/worktree.sh remove <tarea>`. De una en una.
- **Choques previsibles:** solo una tarea a la vez cambia la forma de los datos (`CURRENT_VERSION`, versión de SQLite). Si dos lo necesitan, la segunda en unirse renumera su migración. `texts.js`, `tokens.css`, `index.html` y `TOO_BIG` los tocan todos: al hacer rebase, conservar lo de las dos ramas.
- Repartir tareas que toquen zonas distintas (servidor de una cosa, pantalla de otra).

## Commits

- Claude hace los commits: Conventional Commits en inglés (`feat(parents): …`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`), minimalistas.
- **Sin firma:** nada de `Co-Authored-By`, `Signed-off-by` ni «Generated with…».
- Sin `git push` ni reescribir el historial (`rebase`, `amend`, `reset`) sin preguntar.
- Antes de cada commit, revisar `git status` y que no entre nada personal.
