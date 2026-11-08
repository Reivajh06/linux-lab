---
title: 1.1 · Instalación y exploración del sistema
folder: Prácticas ASO
order: 11
icon: terminal
tags: [sistema, instalación, ayuda]
---

Esta práctica enseña a explorar un sistema Fedora mediante consultas reales a herramientas, paquetes, arranque, red, memoria y configuración. Los ejercicios convierten esas consultas en scripts de Bash que validan argumentos y separan los resultados de los errores.

> [!summary] Lo esencial
> - Localiza binarios con `whereis -b` y consulta paquetes con `dnf list --installed`.
> - Lee los enlaces de los niveles de ejecución y el target de arranque real.
> - Identifica la distribución con `/etc/os-release` y los grupos con `id -nG`.
> - Obtén las interfaces con `ip -o link` y la memoria con `/proc/meminfo`.
> - Filtra directivas completas, ignora comentarios y aplica la regla del ejercicio para repeticiones.
> - Valida antes de consultar: resultados a stdout, errores a stderr y salida `0` al completar correctamente.

> [!note] Alcance de la colección
> VirtualBox, el particionado real, GRUB y la recuperación con CD requieren una máquina virtual y no se evalúan en estos ejercicios.
> Los datos se leen del sistema en cada ejecución; no se deben sustituir por salidas escritas a mano.

## Scripts, herramientas y paquetes

Los scripts se guardan en `/home/learner/aso/p11/`, empiezan con `#!/bin/bash` y necesitan permiso de ejecución. Un binario localizado y un paquete instalado son consultas distintas: `whereis` busca rutas y `dnf` consulta paquetes.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `chmod u+x` | Añade ejecución para el propietario. | `chmod u+x herramientas.sh` |
| `whereis -b` | Busca las rutas de los binarios. | `whereis -b tar` |
| `cut -s -d' ' -f2` | Extrae el segundo campo y omite líneas sin separador. | `cut -s -d' ' -f2` |
| `dnf list --installed` | Consulta paquetes instalados. | `dnf list --installed tar` |
| `printf` | Escribe mensajes con formato. | `printf '%s\n' 'consulta terminada'` |
| `exit` | Termina el script con un estado. | `exit 0` |

### Argumentos, canales y estado

`$#` cuenta argumentos y `"$@"` permite recorrerlos sin dividir los que contienen espacios. `$(comando)` captura stdout; `>&2` envía un mensaje a stderr y `>/dev/null 2>&1` descarta ambos canales.

```bash
#!/bin/bash
# Ejemplo del script herramientas.sh
if [[ $# -eq 0 ]]; then
    printf '%s\n' 'uso: herramientas.sh HERRAMIENTA...' >&2
    exit 1
fi
estado=0
for herramienta in "$@"; do
    ruta=$(whereis -b "$herramienta" | cut -s -d' ' -f2)
    if [[ -z $ruta ]]; then
        printf '%s: no instalada\n' "$herramienta" >&2
        estado=3
    else
        printf '%s: %s\n' "$herramienta" "$ruta"
    fi
done
exit "$estado"
```

> [!warning] Un resultado vacío no se detecta con cualquier `cut`
> Si no encuentra un binario, `whereis -b nosuch` devuelve `nosuch:` sin espacios.
> Sin `-s`, `cut` conserva esa línea y puede parecer que se ha encontrado una ruta.

### Validar todos los paquetes antes de consultar

El ejercicio admite nombres que cumplan `^[a-z0-9][a-z0-9+._-]*$`. Primero se revisan todos: si alguno es inválido, se termina con código `2` sin producir resultados parciales.

```bash
# Fragmento de paquetes.sh, tras comprobar que hay argumentos
for paquete in "$@"; do
    if [[ ! $paquete =~ ^[a-z0-9][a-z0-9+._-]*$ ]]; then
        printf '%s\n' 'nombre de paquete no válido' >&2
        exit 2
    fi
done
for paquete in "$@"; do
    if dnf list --installed "$paquete" >/dev/null 2>&1; then
        printf '%s: instalado\n' "$paquete"
    else
        printf '%s: no instalado\n' "$paquete"
    fi
done
exit 0
```

Un comando con estado `0` se considera verdadero en `if`. En `paquetes.sh`, informar de un paquete ausente es un resultado válido y el script termina con `0`; en `herramientas.sh`, una herramienta ausente exige continuar y devolver `3` al final.

## Arranque: niveles de ejecución y targets

Los nombres `runlevelN.target` son enlaces simbólicos a targets de systemd. Para resolver un nivel se lee su enlace real; para conocer el modo de arranque predeterminado se usa `systemctl get-default`.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `ls -l` | Muestra el enlace y su destino. | `ls -l /usr/lib/systemd/system/runlevel*.target` |
| `readlink` | Devuelve el destino de un enlace simbólico. | `readlink /usr/lib/systemd/system/runlevel3.target` |
| `systemctl get-default` | Consulta el target predeterminado. | `systemctl get-default` |
| `systemctl set-default` | Cambia el target predeterminado; requiere permisos. | `systemctl set-default multi-user.target` |

```bash
# Consultar los enlaces reales: 3 suele ser multi-user y 5 graphical
for nivel in 0 1 2 3 4 5 6; do
    printf '%s: ' "$nivel"
    readlink "/usr/lib/systemd/system/runlevel${nivel}.target"
done

# Clasificar el modo de arranque que tiene configurado el sistema
target=$(systemctl get-default)
case "$target" in
    graphical.target) modo='modo gráfico' ;;
    multi-user.target) modo='modo texto' ;;
    *) modo='otro modo' ;;
esac
printf '%s: %s\n' "$target" "$modo"
```

Para `runlevel.sh`, se exige un argumento: primero se comprueba `^[0-9]+$` y después el rango de `0` a `6`. La ausencia o exceso de argumentos devuelve `1`, un formato inválido devuelve `2` y un nivel fuera del rango devuelve `3`.

> [!tip] Consultar y cambiar son acciones diferentes
> `systemctl set-default` modifica el enlace `/etc/systemd/system/default.target`; no cambia inmediatamente el modo en ejecución.
> Para el ejercicio basta consultar el valor real con `get-default`, sin modificarlo.

## Identidad del sistema y administración

`/etc/os-release` contiene asignaciones de shell con la identidad de la distribución. Los grupos de un usuario se consultan con `id`; en el Fedora del laboratorio, pertenecer a `wheel` es el criterio que usa el ejercicio para identificar administradores.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `. /etc/os-release` | Carga las variables de identificación. | `. /etc/os-release` |
| `source` | Equivale a `.` en Bash. | `source /etc/os-release` |
| `id` | Consulta la identidad y comprueba si el usuario existe. | `id usuario1` |
| `id -nG` | Muestra los nombres de todos sus grupos. | `id -nG usuario1` |
| `grep -qw` | Busca una palabra completa sin imprimir coincidencias. | `grep -qw wheel` |

```bash
# Las comillas del fichero se interpretan al cargar las asignaciones
. /etc/os-release
printf '%s %s\n' "$NAME" "$VERSION_ID"
if [[ $ID == fedora && $VERSION_ID == 44 ]]; then
    printf '%s\n' 'es Fedora 44'
else
    printf '%s\n' 'no es Fedora 44'
fi
```

El ejercicio `sistema.sh` muestra siempre `NAME VERSION_ID`; solo añade la comprobación de Fedora 44 si recibe `-c`. Cualquier otra opción o más de un argumento es un error de uso con código `1`.

```bash
# Fragmento de administrador.sh, tras validar que recibe un usuario
usuario=$1
if ! id "$usuario" >/dev/null 2>&1; then
    printf '%s\n' 'el usuario no existe' >&2
    exit 4
fi
if id -nG "$usuario" | grep -qw wheel; then
    printf '%s: administrador\n' "$usuario"
else
    printf '%s: sin privilegios\n' "$usuario"
fi
exit 0
```

> [!warning] Coincidencias completas y ficheros fiables
> `wheelers` no es `wheel`: usa `grep -qw` para esta comprobación.
> `source` ejecuta el contenido como shell; aquí se aplica al fichero de identificación del sistema, no a configuraciones arbitrarias.

## Interfaces de red y memoria

La lista de interfaces se obtiene del sistema, mientras que interpretar un nombre como `enp0s3` solo describe su formato. `/proc/meminfo` es un fichero virtual del kernel que permite consultar RAM y swap sin fijar cantidades de antemano.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `ip -o link` | Muestra una línea por interfaz. | `ip -o link` |
| `cut -d: -f2` | Extrae el campo del nombre en esa salida. | `cut -d: -f2` |
| `cut -d@ -f1` | Elimina el sufijo de un nombre como `eth0@if27`. | `cut -d@ -f1` |
| `sort` | Ordena las líneas. | `LC_ALL=C sort` |
| `ls /sys/class/net` | Permite contrastar los nombres de interfaces. | `ls /sys/class/net` |
| `read -r` | Lee campos de una línea sin interpretar barras inversas. | `read -r clave valor unidad` |

```bash
# Extraer solo nombres, quitar espacios y sufijos, y ordenar
ip -o link | cut -d: -f2 | tr -d ' ' | cut -d@ -f1 | LC_ALL=C sort

# Interpretar el subconjunto de nombres que admite interfaz.sh
nombre=enp0s3
if [[ $nombre =~ ^(en|wl)p([0-9]+)s([0-9]+)$ ]]; then
    case "${BASH_REMATCH[1]}" in
        en) tipo=ethernet ;;
        wl) tipo=wifi ;;
    esac
    printf 'tipo=%s bus=%s slot=%s\n' \
        "$tipo" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}"
fi
```

`BASH_REMATCH[0]` contiene la coincidencia completa; los grupos entre paréntesis empiezan en `1`. `eth0` puede ser una interfaz real aunque no cumpla el formato que reconoce `interfaz.sh`; ese ejercicio la rechaza con código `2`.

```bash
# MemTotal y SwapTotal se expresan en kB, equivalentes aquí a KiB
while IFS=': ' read -r clave valor unidad; do
    case "$clave" in
        MemTotal) printf 'RAM: %s MiB\n' "$((valor / 1024))" ;;
        SwapTotal)
            if (( valor == 0 )); then
                printf '%s\n' 'Swap: sin swap'
            else
                printf 'Swap: %s MiB\n' "$((valor / 1024))"
            fi
            ;;
    esac
done < /proc/meminfo
```

La división entera por `1024` trunca los decimales. La swap permite respaldar páginas de memoria fuera de la RAM; `SwapTotal` indica su capacidad total, no su uso actual, y un valor `0` significa que no hay swap disponible.

## Lectura de directivas de configuración

El ejercicio `directiva.sh` lee ficheros de formato `CLAVE VALOR`, ignora comentarios y conserva la última aparición activa de la clave. Se practica con `/etc/login.defs` y con ejemplos de `PermitRootLogin`, sin asumir que todos los formatos de configuración siguen esa misma regla.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `[[ -f ... ]]` | Comprueba que la ruta corresponde a un fichero regular. | `[[ -f /etc/login.defs ]]` |
| `grep -E` | Filtra con una expresión regular extendida. | `grep -E '^[[:space:]]*UID_MIN[[:space:]]+' /etc/login.defs` |
| `tail -n 1` | Conserva la última línea encontrada. | `tail -n 1` |
| `tr -s` | Comprime secuencias de separadores. | `tr -s '[:blank:]' ' '` |
| `cut -d' ' -f2` | Extrae el valor tras normalizar espacios. | `cut -d' ' -f2` |

```bash
# Consulta concreta: UID_MIN, sin confundirla con SUB_UID_MIN
linea=$(grep -E '^[[:space:]]*UID_MIN[[:space:]]+' /etc/login.defs | tail -n 1)
if [[ -n $linea ]]; then
    # Normalizar tabuladores y espacios, y quitar el espacio inicial
    printf '%s\n' "$linea" | tr -s '[:blank:]' ' ' | sed 's/^ //' | cut -d' ' -f2
else
    printf '%s\n' 'directiva no encontrada' >&2
fi
```

El anclaje `^` y el separador tras `UID_MIN` evitan coincidencias parciales; el patrón tampoco acepta líneas cuyo primer carácter significativo sea `#`. Para el script completo, valida dos argumentos y `[[ -f "$fichero" ]]` antes de buscar: uso incorrecto devuelve `1`, fichero inválido `4` y clave ausente `5`.

> [!note] Comentada no significa activa
> `#PermitRootLogin prohibit-password` es un comentario, no una asignación activa.
> Si no se encuentra una directiva, informa de su ausencia; no inventes un valor predeterminado.

## Comandos adicionales útiles

Estas consultas y opciones ayudan a contrastar los datos del sistema y a depurar los scripts de la práctica.

| Comando | Para qué sirve | Ejemplo |
| --- | --- | --- |
| `command -v` | Comprueba cómo resolvería el shell un nombre, incluidos los ejecutables del `PATH`. | `command -v tar` |
| `type -a` | Muestra todas las coincidencias de un nombre: alias, funciones, órdenes internas y ejecutables. | `type -a printf` |
| `rpm -qf` | Identifica el paquete instalado al que pertenece un fichero. | `rpm -qf /usr/bin/tar` |
| `rpm -ql` | Lista los ficheros que proporciona un paquete instalado. | `rpm -ql tar` |
| `systemctl list-units --type=target --state=active` | Consulta los targets activos en la sesión actual del sistema. | `systemctl list-units --type=target --state=active` |
| `journalctl -b -p warning --no-pager` | Lee los avisos y errores del arranque actual sin abrir un paginador; la visibilidad depende de los permisos. | `journalctl -b -p warning --no-pager` |
| `getent passwd` | Consulta cuentas mediante las fuentes configuradas en NSS, incluidas las que no están en `/etc/passwd`. | `getent passwd root` |
| `ip -br address` | Resume el estado de las interfaces y sus direcciones IP. | `ip -br address` |
| `free -h` | Resume RAM y swap con unidades legibles; `available` estima la RAM disponible para nuevas aplicaciones. | `free -h` |
| `swapon --show` | Muestra las áreas de swap activas, su tamaño y su uso, incluida zram si está habilitada. | `swapon --show` |
| `bash -n` | Comprueba la sintaxis de un script sin ejecutarlo. | `bash -n /home/learner/aso/p11/herramientas.sh` |
| `bash -x` | Ejecuta un script mostrando en stderr las órdenes tras sus expansiones para seguir su funcionamiento. | `bash -x /home/learner/aso/p11/herramientas.sh tar` |

```bash
# Localizar tar como lo haría el shell y consultar el paquete propietario
ruta=$(command -v tar) && rpm -qf "$ruta"
```

```bash
# Si la sintaxis es válida, ejecutar el script con una traza de depuración
bash -n /home/learner/aso/p11/herramientas.sh && bash -x /home/learner/aso/p11/herramientas.sh tar
```

```bash
# Contrastar el resumen de memoria con las áreas de swap realmente activas
free -h && swapon --show
```

```bash
# Relacionar los targets activos con los avisos del arranque actual
systemctl list-units --type=target --state=active && journalctl -b -p warning --no-pager
```

> [!tip] Comprobar qué se ejecutará
> Prefiere `command -v` cuando necesites saber qué resolverá tu shell al escribir un nombre. Si sospechas que un alias, una función o varios ejecutables con el mismo nombre alteran el resultado, usa `type -a` para ver las alternativas.

## Errores frecuentes

- Escribir rutas, memoria o interfaces fijas: las consultas deben reflejar el sistema real.
- Olvidar `chmod u+x` o ejecutar desde el directorio actual sin el prefijo `./`.
- Recorrer `$@` sin comillas: `for x in "$@"` conserva cada argumento completo.
- Dejar mensajes internos de `dnf` en el resultado: descarta stdout y stderr de esa consulta.
- Consultar un paquete antes de validar todos los nombres y producir una salida parcial indebida.
- Confundir el target predeterminado con el modo que está actualmente en ejecución.
- Dejar el sufijo `@if27` en una interfaz o rechazar una interfaz real solo por llamarse `eth0`.
- Confundir MiB con los valores originales de `/proc/meminfo`, o capacidad swap con uso.
- Buscar claves por subcadenas, aceptar comentarios o conservar la primera repetición en `directiva.sh`.
- Imprimir errores en stdout o usar códigos arbitrarios: respeta los estados de cada ejercicio.

## Chuleta rápida

```bash
chmod u+x /home/learner/aso/p11/herramientas.sh  # Permiso de ejecución
/home/learner/aso/p11/herramientas.sh tar bzip2  # Ejecutar el script creado
whereis -b tar  # Localizar binarios
whereis -b tar | cut -s -d' ' -f2  # Primera ruta
dnf list --installed tar >/dev/null 2>&1; printf '%s\n' "$?"  # Estado de consulta
ls -l /usr/lib/systemd/system/runlevel*.target  # Enlaces de los niveles
readlink /usr/lib/systemd/system/runlevel3.target  # Target del nivel 3
systemctl get-default  # Target predeterminado
. /etc/os-release; printf '%s %s\n' "$NAME" "$VERSION_ID"  # Distribución
id -nG usuario1  # Grupos del usuario
id -nG usuario1 | grep -qw wheel  # Comprobar pertenencia a wheel
ip -o link | cut -d: -f2 | tr -d ' ' | cut -d@ -f1 | LC_ALL=C sort  # Interfaces
grep -E '^(MemTotal|SwapTotal):' /proc/meminfo  # Totales de RAM y swap
grep -E '^[[:space:]]*UID_MIN[[:space:]]+' /etc/login.defs | tail -n 1  # Última directiva
```
