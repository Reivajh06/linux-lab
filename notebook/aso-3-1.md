---
title: 3.1 · Procesos
folder: Prácticas ASO
order: 31
icon: activity
tags: [procesos, ps, señales]
---

Esta práctica enseña a identificar, consultar, filtrar y contar procesos, interpretar su consumo de recursos y relacionar padres e hijos. También trabaja el envío de señales y la ejecución en segundo plano mediante scripts Bash que validan argumentos y separan resultados de errores.

> [!summary] Lo esencial
> - Usa `ps` para una fotografía de los procesos y `top -b -n 1` para una captura acotada.
> - Distingue PID de PPID, `comm` de `cmd` y tiempo de CPU de tiempo transcurrido.
> - Filtra campos exactos y elimina las cabeceras antes de contar u ordenar.
> - Comprueba el grupo primario en el campo 4 de `passwd`.
> - Envía señales solo a procesos de prueba; guarda `$!` y recoge los hijos con `wait`.
> - Devuelve resultados por stdout, errores por stderr y código `0` cuando el script cumple su cometido.

## Identificar procesos con ps

Un proceso tiene un PID; su PPID identifica al padre. `ps` muestra una instantánea: los procesos pueden aparecer o terminar entre dos consultas, así que los resultados reales no son constantes.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `ps -e` | Selecciona todos los procesos | `ps -e` |
| `ps -ef` | Lista todos con formato completo | `ps -ef` |
| `ps -o` | Elige las columnas | `ps -eo pid,ppid,user,comm` |
| `ps -p PID` | Consulta un PID concreto | `ps -p 1 -o pid,ppid,comm` |
| `--no-headers` o `campo=` | Suprime cabeceras | `ps -eo pid=,comm=` |
| `ps --ppid PID` | Selecciona hijos directos | `ps --ppid 1 -o pid,comm` |
| `ps --forest` | Representa relaciones en árbol | `ps -eo pid,ppid,cmd --forest` |
| `pstree -p` | Muestra el árbol con PID | `pstree -p` |

```bash
# PID, propietario y línea completa, ordenados por usuario
ps -eo pid,user,cmd --sort user --no-headers

# Consulta del propio shell; $$ es su PID
ps -p "$$" -o pid=,ppid=,comm=
ps --ppid "$$" -o pid,comm --sort pid --no-headers
```

### Columnas, terminal y estados

`comm` es el nombre del comando; `cmd` o `args` incluyen su línea de argumentos. `tty` identifica la terminal de control y `?` indica que no hay ninguna.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `ps -o stat` | Muestra estado y modificadores | `ps -eo pid,user,stat` |
| `ps -o tty` | Permite comprobar la terminal | `ps -u usuario1 -o pid,tty,comm` |
| `man ps` | Documenta opciones y estados | `man ps` |

Los estados básicos incluyen `R` (ejecutándose o listo), `S` (espera interrumpible), `T` (detenido) y `Z` (zombi: terminado, pendiente de ser recogido por su padre). `stat` puede añadir modificadores: `s` indica líder de sesión y `+`, pertenencia al grupo en primer plano de la terminal.

```bash
# Coincidencia exacta: S no incluye Ss ni S+
ps -eo pid,user,stat --no-headers | awk '$3 == "S"'

# Solo procesos de usuario1 asociados a una terminal
ps -u usuario1 -o pid,tty,time,comm --sort tty --no-headers |
  awk '$2 != "?"'
```

> [!warning] Opciones con y sin guion
> `ps -ef` y `ps ef` no significan lo mismo. Mantén un estilo de opciones coherente y especifica las columnas necesarias.

## Buscar, filtrar y contar

Las búsquedas por nombre y por línea completa responden a preguntas distintas. Para recuentos fiables, selecciona el campo adecuado y exige coincidencia exacta cuando el enunciado lo pida.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `pgrep -x` | Busca el nombre exacto | `pgrep -x sleep` |
| `pgrep -f` | Busca una expresión en la línea completa | `pgrep -f bash` |
| `pgrep -u` | Limita por propietario efectivo | `pgrep -u p31_contador -xc sleep` |
| `pidof` | Obtiene PID por nombre de programa | `pidof sleep` |
| `grep -Fxc` | Cuenta líneas completas iguales a un texto literal | `grep -Fxc -- ana` |
| `sort -u` | Ordena y elimina duplicados | `sort -u usuarios.txt` |
| `wc -l` | Cuenta líneas | `wc -l usuarios.txt` |

```bash
# Número de procesos del usuario actual, sin contar cabeceras
ps -u "$(id -u)" -o pid= | wc -l

# Número de propietarios distintos; uniq solo elimina duplicados contiguos
ps -eo user= | sort -u | wc -l

# Dentro de un script de búsqueda: excluir su propio PID
todos=$(pgrep -f -- bash)
lista=$(printf '%s\n' "$todos" | grep -vx "$$")
[[ -z $lista ]] || printf '%s\n' "$lista"
```

> [!tip] Búsquedas que se encuentran a sí mismas
> El script puede contener el patrón en sus argumentos. Captura primero `pgrep` sin tubería y filtra después `$$`, como en el ejemplo: una tubería dentro de la sustitución puede introducir otro shell coincidente.
> `pgrep -f` usa expresiones regulares; no equivale en general a una búsqueda literal con `grep -F`.

### El volcado de los 20 ejercicios

En la colección corregida, los ejercicios 1–14 y 20 leen `procesos.psv`; los ejercicios 15–19 consultan procesos reales. El volcado usa `|`, no tiene cabecera y sus campos son: 1 PID, 2 USUARIO, 3 PPID, 4 ESTADO, 5 %CPU, 6 %MEM, 7 TIEMPO_CPU, 8 TIEMPO_TRANSCURRIDO, 9 COMANDO, 10 TTY y 11 LÍNEA_COMPLETA.

```bash
datos=/home/learner/lab/aso-procesos/datos
f="$datos/procesos.psv"

# Contar a ana por el campo 2; cero coincidencias sigue siendo un resultado
n=$(cut -d'|' -f2 "$f" | grep -Fxc -- ana)
printf 'ana: %s\n' "$n"

# PID cuyo estado sea exactamente S+, con + literal en la expresión extendida
grep -E '^([^|]*\|){3}S\+\|' "$f" | cut -d'|' -f1

# Filtrar la línea completa, sin perder el PID de su fila
awk -F'|' 'index($11, "bash") {print $1}' "$f"
```

> [!note] Una búsqueda vacía puede ser correcta
> `grep` y `pgrep` devuelven `1` cuando no encuentran coincidencias. Si el ejercicio admite cero resultados, gestiona ese estado y termina el script con `0`; una línea vacía producida por `echo` tampoco debe contarse como un PID.

## CPU, memoria, antigüedad y top

`time` mide CPU acumulada; `etime`, tiempo desde el arranque del proceso; `pcpu`, porcentaje de CPU. Un `sleep` puede llevar mucho tiempo vivo y acumular casi nada de CPU; `vsz` expresa memoria virtual en KiB y no equivale a memoria física ocupada.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `--sort time` | Ordena por CPU acumulada ascendente | `ps -eo pid,comm,time --sort time` |
| `--sort -time` | Ordena por CPU acumulada descendente | `ps -eo pid,comm,time --sort -time` |
| `--sort start_time` | Sitúa primero los más antiguos | `ps -eo pid,comm,etime --sort start_time` |
| `ps -o vsz` | Muestra memoria virtual | `ps -eo pid,comm,vsz` |
| `head -n N` | Conserva las primeras N líneas | `head -n 5` |
| `sort -n` | Ordena números en lugar de texto | `sort -n cantidades.txt` |
| `top -b -n 1` | Captura una actualización sin interacción | `top -b -n 1 -p 1` |
| `top -u` | Limita por usuario | `top -b -n 1 -u learner` |

```bash
# Cinco procesos con más CPU acumulada: cinco filas, sin cabecera
ps -eo pid,comm,time --sort -time --no-headers | head -n 5

# Diez más antiguos, mostrando CPU y tiempo transcurrido
ps -eo pid,comm,time,etime --sort start_time --no-headers | head -n 10

# En el volcado: porcentaje decimal descendente y empates estables
sort -s -t'|' -k5,5nr "$f" | head -n 5 | cut -d'|' -f1,5,9

# En el volcado: tiempo de CPU fijo HH:MM:SS, descendente
sort -s -t'|' -k7,7r "$f" | head -n 5 | cut -d'|' -f1,7,9
```

`sort -s` conserva el orden de entrada en los empates; `-k5,5nr` limita la clave al campo 5 y aplica orden numérico inverso. `cut` conserva el orden original de las columnas: no las reordena según el orden escrito en `-f`.

```bash
# Guardar top permite comprobar tanto el éxito como su cabecera
if captura=$(top -b -n 1 -p "$$"); then
  if printf '%s\n' "$captura" | grep -q '^top -'; then
    printf 'CAPTURA OK\n'
  fi
fi
```

> [!warning] Formatos que no conviene dar por hechos
> La ordenación textual del tiempo funciona en el volcado porque usa ancho fijo `HH:MM:SS`; no la generalices a tiempos reales con días. Para ordenar por tamaño numérico con `sort`, identifica bien la columna y los espacios iniciales de `ps`.
> Si cuentas filas de `top` saltando siete líneas con `tail -n +8`, comprueba antes su cabecera y elimina líneas vacías. En scripts usa siempre `-b` y un límite `-n`.

## Usuarios, grupo primario y contrato del script

Existir como usuario y tener procesos son comprobaciones diferentes: valida con `id` y cuenta con `ps`. Para seleccionar por grupo primario, lee el cuarto campo de `/etc/passwd`; la pertenencia a un grupo secundario no satisface ese criterio.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `id` | Comprueba una cuenta y muestra sus identificadores | `id p31a` |
| `ps -u` | Selecciona por usuario efectivo | `ps -u p31a --no-headers` |
| `ps -N -u root` | Invierte la selección de root | `ps -N -u root -o pid,user,comm,vsz` |
| `while IFS=: read -r` | Lee los campos de passwd | `while IFS=: read -r u clave uid gid resto; do ...; done` |
| `chmod u+x` | Añade permiso de ejecución al propietario | `chmod u+x procesos-usuario.sh` |
| `printf ... >&2` | Escribe un diagnóstico por stderr | `printf 'Uso: USUARIO\n' >&2` |
| `exit N` | Fija el código final del script | `exit 0` |

```bash
#!/bin/bash
# Ejemplo de recuento real: conserva el orden de los argumentos
if (($# < 1)); then
  printf 'uso: procesos-usuario.sh USUARIOS...\n' >&2
  exit 1
fi
codigo=0
for u in "$@"; do
  if ! id -- "$u" >/dev/null 2>&1; then
    printf 'el usuario no existe: %s\n' "$u" >&2
    codigo=4
    continue
  fi
  n=$(ps -u "$u" -o pid= | wc -l)
  printf '%s: %s\n' "$u" "$n"
done
exit "$codigo"
```

```bash
# Fragmento tras validar G y P como enteros no negativos
G=23102; P=2
while IFS=: read -r u clave uid gid resto; do
  ((gid == G)) || continue
  n=$(ps -u "$u" -o pid= | wc -l)
  if ((n >= P)); then
    printf '%s: %s\n' "$u" "$n"
  fi
done < /etc/passwd
```

> [!note] Respeta la variante del ejercicio
> En los laboratorios reales de grupo, distingue «no hay cuentas con ese GID primario» (`4`) de «ninguna alcanza el umbral» (`5`) y conserva el orden de `/etc/passwd`.
> En el ejercicio 20 del volcado, usa `cuentas.passwd` y `procesos.psv`: exige `n >= mínimo` y `n > 0`, ordena por usuario y muestra `Sin resultados` con éxito si nadie cumple.
> Los códigos de error concretos dependen del enunciado: no hay una tabla universal. En un éxito ordinario, stdout contiene resultados, stderr queda vacío y el código es `0`; algunos ejercicios permiten resultados parciales junto con errores.

## Señales y procesos en segundo plano

Una señal solicita una acción al proceso: `SIGTERM` permite terminar de forma ordenada y `SIGKILL` fuerza la terminación sin poder capturarse ni ignorarse. Con `&` el shell continúa sin esperar; guarda inmediatamente `$!` para poder esperar después a ese hijo con `wait`.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `kill -0 PID` | Comprueba existencia y permiso sin enviar señal | `kill -0 "$pid"` |
| `kill -TERM PID` | Solicita terminar; es la señal predeterminada | `kill -TERM "$pid"` |
| `kill -KILL PID` | Fuerza la terminación; equivale a `-9` | `kill -KILL "$pid"` |
| `kill -l` | Lista señales o convierte nombre y número | `kill -l TERM` |
| `comando &` | Lanza un trabajo en segundo plano | `sleep 30 &` |
| `jobs` | Lista trabajos del shell actual | `jobs -l` |
| `wait PID` | Espera a un hijo y devuelve su estado | `wait "$pid"` |
| `man 7 signal` | Documenta las señales | `man 7 signal` |

```bash
# Prueba controlada: actuar solo sobre el proceso que acabamos de lanzar
sleep 30 &
pid=$!
if kill -0 "$pid" 2>/dev/null; then
  kill -TERM "$pid"
  wait "$pid" 2>/dev/null  # Puede devolver no cero por terminar mediante señal
fi
```

> [!warning] PID y alcance de la señal
> Valida un PID decimal positivo antes de usarlo: `0` y los valores negativos tienen significados especiales para `kill`. Un fallo de `kill -0` puede indicar falta de permisos, además de ausencia del proceso; una comprobación correcta tampoco garantiza que siga existiendo después.
> Practica con procesos propios. `pkill` y `killall` pueden afectar a varios procesos; si se exige un PID concreto, usa `kill` sobre ese PID.

En la variante de terminación escalonada se envía `TERM`, se espera un segundo y solo si continúa se recurre a `KILL`. Un proceso detenido puede no atender `TERM` hasta reanudarse; el ejercicio 19 corregido solicita únicamente `TERM`.

```bash
# Tres hijos concurrentes: duración cercana a 0,7 s, más sobrecostes
pids=()
for ((i=0; i<3; i++)); do
  sleep 0.7 &
  pids+=("$!")
done
terminados=0
for pid in "${pids[@]}"; do
  if wait "$pid"; then
    ((terminados+=1))
  fi
done
printf 'lanzados: %s\nterminados: %s\n' "${#pids[@]}" "$terminados"
```

## Comandos adicionales útiles

Estos comandos complementan la práctica al observar procesos con más detalle, ajustar su ejecución y preparar pruebas controladas en Fedora.

| Comando | Para qué sirve | Ejemplo |
| --- | --- | --- |
| `nice -n` | Lanza un programa con mayor niceness para ceder prioridad de CPU | `nice -n 10 sleep 5` |
| `renice -n -p` | Aumenta la niceness de un proceso propio ya iniciado; reducirla suele requerir privilegios | `renice -n 15 -p "$pid"` |
| `timeout --signal --kill-after` | Limita la duración de un comando y fuerza su fin si no atiende la señal inicial | `timeout --signal=TERM --kill-after=2s 5s sleep 30` |
| `watch -n -d` | Repite una consulta en la terminal y resalta los cambios entre capturas | `watch -n 1 -d 'ps -eo pid,comm,pcpu,rss --sort=-pcpu'` |
| `trap` | Ejecuta una acción al recibir una señal capturable o al salir del script | `trap 'printf "Interrumpido\n" >&2; exit 130' INT` |
| `getent passwd` | Consulta cuentas mediante NSS, incluidas las fuentes configuradas además de los archivos locales | `getent passwd "$(id -u)"` |
| `readlink -f` | Resuelve enlaces simbólicos; en `/proc/PID/exe` permite identificar el ejecutable, si hay permisos | `readlink -f "/proc/$$/exe"` |
| `taskset -pc` | Consulta la lista de CPU en las que puede ejecutarse un PID, sin modificarla | `taskset -pc "$$"` |
| `prlimit --pid` | Muestra los límites de recursos de un proceso, como archivos abiertos o tiempo de CPU | `prlimit --pid "$$"` |
| `pidstat -u -r -p` | Muestrea CPU y memoria de un PID; en Fedora pertenece al paquete `sysstat` | `pidstat -u -r -p "$$" 1 3` |

```bash
# Lanzar un hijo con menor prioridad y reducirla de nuevo antes de recogerlo
nice -n 10 sleep 5 & pid=$!; renice -n 15 -p "$pid"; wait "$pid"
```

```bash
# Observar CPU y memoria durante cinco segundos en una terminal interactiva
timeout --signal=TERM --kill-after=2s 5s watch -n 1 -d 'ps -eo pid,comm,pcpu,rss --sort=-pcpu'
```

```bash
# Inspeccionar el ejecutable, la afinidad y los límites del shell actual
readlink -f "/proc/$$/exe"; taskset -pc "$$"; prlimit --pid "$$"
```

> [!tip] Acotar una prueba desde el principio
> Prefiere `timeout` cuando quieras limitar la duración de un comando de prueba: permite fijar el plazo y escalar de `TERM` a `KILL` con `--kill-after`. Normalmente devuelve `124` si vence el plazo; tenlo en cuenta al interpretar el resultado del script.

## Errores frecuentes

- Contar la cabecera de `ps`: usa `--no-headers` o columnas con `=`.
- Confundir usuario inexistente con usuario sin procesos; `ps` puede devolver `1` si la selección está vacía.
- Buscar `root`, `S` o `bash` en toda una fila cuando se pide un campo exacto; en `grep -E`, escapa el `+` literal.
- Ordenar números como texto, perder el orden de los empates o confundir CPU acumulada con antigüedad.
- Suponer que una búsqueda sin coincidencias es un error del script; gestiona explícitamente su estado.
- Consultar procesos reales cuando se pide el volcado, o reutilizar los criterios de salida de otra variante.
- Escribir diagnósticos por stdout, olvidar el shebang o no dar permiso de ejecución al script.
- Sobrescribir `$!`, omitir `wait` o enviar señales a un PID sin comprobar su valor y procedencia.

## Chuleta rápida

```bash
ps -eo pid,ppid,user,stat,tty,cmd                   # Vista general
ps -eo pid,user,cmd --sort user --no-headers       # Orden por propietario
ps -p "$$" -o pid=,ppid=,comm=                     # Datos del shell actual
ps --ppid "$$" -o pid,comm --no-headers            # Hijos directos
ps -u "$(id -u)" -o pid= | wc -l                  # Recuento propio
ps -eo user= | sort -u | wc -l                    # Propietarios distintos
ps -N -u root -o pid,user,comm,vsz --no-headers    # Excluir root
ps -eo pid,comm,time --sort -time --no-headers | head -n 5  # Más CPU
ps -eo pid,comm,etime --sort start_time --no-headers | head -n 10  # Antiguos
pgrep -x sleep | sort -n                          # Nombre exacto
pgrep -f bash                                    # Línea completa, patrón regex
top -b -n 1 -p "$$"                              # Una captura del shell
kill -l TERM                                     # Número de SIGTERM
sleep 1 & pid=$!; wait "$pid"                     # Lanzar y esperar un hijo
sleep 30 & pid=$!; kill -TERM "$pid"; wait "$pid"  # Terminar un hijo propio
```
