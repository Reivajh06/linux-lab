"""Práctica 1.1: paquetes, targets, red y configuración, sobre ficheros reales de Fedora."""
from .framework import E, Practice, T, eg, ok, probe

practice = Practice(
    "1.1", "Instalación y exploración del sistema",
    """Scripts que consultan lo que la Práctica 1.1 explica durante la instalación: herramientas y paquetes (`whereis`, `dnf`),
    niveles de ejecución (`systemctl`, enlaces de `runlevelN.target`), identidad del sistema, memoria, red y ficheros de configuración.
    VirtualBox, el particionado real, GRUB y la recuperación con el CD necesitan una máquina virtual y no se evalúan aquí.""",
    setup="id usuario1 >/dev/null 2>&1 || useradd -m -s /bin/bash -G wheel -c 'Usuario 1' usuario1\n",
    document=("11cb788eab069a7b8e7c0237daa4046c0b00797879244e0466ccf7402074df8d", "Práctica-1.1"))

practice.add(
    "herramientas", "Localizar herramientas con whereis",
    """Para cada herramienta recibida como argumento, muestra `NOMBRE: RUTA` con la primera ruta de binario que indique `whereis -b`.
    Si una herramienta no está instalada, escribe `NOMBRE: no instalada` en stderr, sigue con las demás y termina con el código 3.""",
    usage="HERRAMIENTA...", cmds="`whereis -b`, `cut -s`", structs='`for x in "$@"`, `[[ -z ... ]]`, `>&2`',
    detail="`whereis` imprime `nosuch:` sin espacios cuando no encuentra nada, y `cut` devuelve la línea entera si no contiene el delimitador. Mira qué hace `cut -s`.",
    success="Una línea `NOMBRE: RUTA` por herramienta.",
    tests=[T("instaladas", "Localiza las herramientas instaladas.", ok(["tar", "bzip2"], val="tar: /usr/bin/tar\nbzip2: /usr/bin/bzip2"), ok(["bash"], ref="whereis -b bash | cut -d' ' -f2 | sed 's/^/bash: /'"))],
    errors=[E("uso", 1, "Recibe al menos una herramienta.", "uso: herramientas.sh HERRAMIENTA...", []),
            E("parcial", 3, "Cada herramienta debe estar instalada; si no, se avisa y se continúa.", "nosuch: no instalada",
              dict(args=["tar", "nosuch", "bash"], ref="whereis -b bash | cut -d' ' -f2 | sed '1i tar: /usr/bin/tar' | sed '2s/^/bash: /'"),
              partial="stdout con las herramientas encontradas y stderr con las que faltan.", eg=False)],
    examples=[eg("tar bzip2")], pages=[6, 7],
    solution=r"""
#!/bin/bash
if (($#<1)); then
  echo "uso: herramientas.sh HERRAMIENTA..." >&2
  exit 1
fi
codigo=0
for herramienta in "$@"; do
  ruta=$(whereis -b "$herramienta" | cut -s -d' ' -f2)
  if [[ -z $ruta ]]; then
    echo "$herramienta: no instalada" >&2
    codigo=3
  else
    echo "$herramienta: $ruta"
  fi
done
exit $codigo
""")

practice.add(
    "paquetes", "¿Está instalado este paquete?",
    """Para cada paquete, muestra `NOMBRE: instalado` o `NOMBRE: no instalado` consultando `dnf list --installed`.
    El nombre debe cumplir `^[a-z0-9][a-z0-9+._-]*$`; valida todos los argumentos antes de consultar ninguno.""",
    usage="PAQUETE...", cmds="`dnf list --installed`", structs="`[[ =~ ]]`, `cmd >/dev/null 2>&1 && ... || ...`",
    detail="La salida del comando interno no forma parte del resultado: redirige stdout **y** stderr. Un comando vale «verdadero» cuando devuelve 0.",
    success="Una línea por paquete, en el orden recibido.",
    tests=[T("consulta", "Distingue paquetes instalados y ausentes.", ok(["tar", "nosuch-pkg", "bzip2"], val="tar: instalado\nnosuch-pkg: no instalado\nbzip2: instalado", timeout=30))],
    errors=[E("uso", 1, "Recibe al menos un paquete.", "uso: paquetes.sh PAQUETE...", []),
            E("nombre", 2, "Cada nombre debe tener un formato válido.", "nombre de paquete no válido", ["tar", "Mal Nombre"], ["-x"])],
    examples=[eg("tar nosuch-pkg")], pages=[6, 7],
    solution=r"""
#!/bin/bash
(($#<1)) && { echo "uso: paquetes.sh PAQUETE..." >&2; exit 1; }
for paquete in "$@"; do
  [[ $paquete =~ ^[a-z0-9][a-z0-9+._-]*$ ]] || { echo "nombre de paquete no válido" >&2; exit 2; }
done
for paquete in "$@"; do
  dnf list --installed "$paquete" >/dev/null 2>&1 && echo "$paquete: instalado" || echo "$paquete: no instalado"
done
exit 0
""")

practice.add(
    "runlevel", "De nivel de ejecución a target",
    """Recibe un nivel de ejecución de 0 a 6 y muestra el nombre del target al que apunta el enlace simbólico real `/usr/lib/systemd/system/runlevelN.target`.""",
    usage="NIVEL", cmds="`readlink`, `ls -l`", structs="`[[ =~ ]]`, `(( ))`, sustitución de comandos",
    detail="Son enlaces simbólicos, por eso `readlink` da directamente el nombre del target. Compruébalo con `ls -l /usr/lib/systemd/system/runlevel*.target`.",
    success="El nombre del target.",
    tests=[T("niveles", "Resuelve todos los niveles.", *[ok([str(n)], ref=f"readlink /usr/lib/systemd/system/runlevel{n}.target") for n in range(7)])],
    errors=[E("uso", 1, "Recibe exactamente un argumento.", "uso: runlevel.sh NIVEL", [], ["1", "2"]),
            E("formato", 2, "El nivel es un número.", "el nivel debe ser un número", ["tres"], ["-1"]),
            E("rango", 3, "El nivel está entre 0 y 6.", "el nivel debe estar entre 0 y 6", ["7"])],
    examples=[eg("3"), eg("5")], pages=[8],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=1)) && error "uso: runlevel.sh NIVEL" 1
[[ ! $1 =~ ^[0-9]+$ ]] && error "el nivel debe ser un número" 2
(($1>6)) && error "el nivel debe estar entre 0 y 6" 3
readlink "/usr/lib/systemd/system/runlevel$1.target"
exit 0
""")

_reset = "rm -f /etc/systemd/system/default.target"
_text = "ln -sf /usr/lib/systemd/system/multi-user.target /etc/systemd/system/default.target"
_rescue = "ln -sf /usr/lib/systemd/system/rescue.target /etc/systemd/system/default.target"
practice.add(
    "modo-arranque", "Modo de arranque por defecto",
    """Muestra el target por defecto (`systemctl get-default`) seguido del modo de arranque, separados por `: `:
    `graphical.target: modo gráfico`, `multi-user.target: modo texto` y, para cualquier otro, `NOMBRE: otro modo`.""",
    cmds="`systemctl get-default`", structs="`case ... esac`",
    detail="`systemctl set-default` no hace más que cambiar el enlace `/etc/systemd/system/default.target`. El evaluador lo cambia para comprobar que lees el valor real.",
    success="Una línea con el target y su modo.",
    tests=[T("modos", "Refleja el target por defecto real.",
             ok(val="graphical.target: modo gráfico", prepare=_reset),
             ok(val="multi-user.target: modo texto", prepare=_text),
             ok(val="rescue.target: otro modo", prepare=_rescue),
             ok(val="graphical.target: modo gráfico", prepare=_reset))],
    errors=[E("uso", 1, "No recibe argumentos.", "uso: modo-arranque.sh", ["x"])],
    examples=[eg(prepare=_reset)], pages=[8, 9],
    solution=r"""
#!/bin/bash
(($#!=0)) && { echo "uso: modo-arranque.sh" >&2; exit 1; }
target=$(systemctl get-default)
case $target in
  graphical.target) echo "$target: modo gráfico";;
  multi-user.target) echo "$target: modo texto";;
  *) echo "$target: otro modo";;
esac
exit 0
""")

practice.add(
    "interfaz", "Descifrar el nombre de una interfaz",
    """Interpreta nombres predecibles como `enp0s3` (Ethernet `en`, bus PCI `p0`, slot `s3`) y muestra `tipo=ethernet bus=0 slot=3`.
    Acepta también `wlp2s0`, que da `tipo=wifi bus=2 slot=0`.""",
    usage="NOMBRE", cmds="`[[ =~ ]]`", structs="grupos de captura y `BASH_REMATCH`, `case`",
    detail="`BASH_REMATCH[0]` es la coincidencia completa; los grupos empiezan en el índice 1.",
    success="Una línea con tipo, bus y slot.",
    tests=[T("nombres", "Descifra varios nombres.", ok(["enp0s3"], val="tipo=ethernet bus=0 slot=3"), ok(["enp12s25"], val="tipo=ethernet bus=12 slot=25"), ok(["wlp2s0"], val="tipo=wifi bus=2 slot=0"))],
    errors=[E("uso", 1, "Recibe exactamente un nombre.", "uso: interfaz.sh NOMBRE", []),
            E("formato", 2, "El nombre sigue el patrón enpXsY o wlpXsY.", "nombre de interfaz no reconocido", ["eth0"], ["enp0s"], ["xenp0s3"])],
    examples=[eg("enp0s3")], pages=[4],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: interfaz.sh NOMBRE" >&2; exit 1; }
if [[ ! $1 =~ ^(en|wl)p([0-9]+)s([0-9]+)$ ]]; then
  echo "nombre de interfaz no reconocido" >&2
  exit 2
fi
case ${BASH_REMATCH[1]} in
  en) tipo=ethernet;;
  wl) tipo=wifi;;
esac
echo "tipo=$tipo bus=${BASH_REMATCH[2]} slot=${BASH_REMATCH[3]}"
exit 0
""")

practice.add(
    "interfaces-red", "Interfaces reales del sistema",
    """Lista por orden alfabético las interfaces de red reales a partir de `ip -o link`, una por línea y solo el nombre.""",
    cmds="`ip -o link`, `cut`, `sort`", structs="tuberías",
    detail="El nombre de una interfaz de contenedor aparece como `eth0@if27`: hay que quitar lo que sigue a `@`.",
    success="Un nombre por línea, ordenados.",
    tests=[T("reales", "Coincide con /sys/class/net.", ok(ref="ls /sys/class/net | LC_ALL=C sort"))],
    errors=[E("uso", 1, "No recibe argumentos.", "uso: interfaces-red.sh", ["eth0"])],
    examples=[eg()], pages=[13],
    solution=r"""
#!/bin/bash
(($#!=0)) && { echo "uso: interfaces-red.sh" >&2; exit 1; }
ip -o link | cut -d: -f2 | cut -d@ -f1 | tr -d ' ' | LC_ALL=C sort
exit 0
""")

practice.add(
    "memoria", "RAM y swap desde /proc/meminfo",
    """Lee `/proc/meminfo` y muestra dos líneas: `RAM: N MiB` y `Swap: N MiB`, truncando la división por 1024. Si no hay swap, la segunda línea es `Swap: sin swap`.""",
    cmds="`/proc/meminfo`", structs="`while IFS=': ' read`, `case`, `$(( ))`, redirección al bloque `while`",
    detail="La práctica explica que la swap da soporte a la memoria virtual cuando supera a la RAM. `/proc` es un sistema de ficheros virtual: se lee como cualquier otro fichero.",
    success="Las líneas de RAM y swap.",
    tests=[T("valores", "Coincide con el kernel.", ok(ref="""awk '/^MemTotal:/{print "RAM: " int($2/1024) " MiB"} /^SwapTotal:/{print ($2 ? "Swap: " int($2/1024) " MiB" : "Swap: sin swap")}' /proc/meminfo"""))],
    errors=[E("uso", 1, "No recibe argumentos.", "uso: memoria.sh", ["x"])],
    examples=[eg()], pages=[4],
    solution=r"""
#!/bin/bash
(($#!=0)) && { echo "uso: memoria.sh" >&2; exit 1; }
while IFS=': ' read -r clave valor resto; do
  case $clave in
    MemTotal) ram=$valor;;
    SwapTotal) swap=$valor;;
  esac
done < /proc/meminfo
echo "RAM: $((ram/1024)) MiB"
if ((swap==0)); then echo "Swap: sin swap"; else echo "Swap: $((swap/1024)) MiB"; fi
exit 0
""")

practice.add(
    "directiva", "Valor activo de una directiva",
    """Muestra el valor de una directiva en un fichero de configuración con formato `CLAVE VALOR`. Las líneas comentadas no cuentan y, si la clave aparece varias veces, gana la última.
    La práctica edita así `PermitRootLogin` en `sshd_config`; aquí se prueba con `/etc/login.defs`, el fichero real de valores por defecto.""",
    usage="CLAVE FICHERO", cmds="`grep -E`, `tail -n 1`, `tr -s`, `cut`", structs="`[[ -f ]]`, sustitución de comandos",
    detail="Una línea que empieza por `#` no tiene efecto: `#PermitRootLogin prohibit-password` no es la configuración activa. Ancla bien el patrón para que `UID_MIN` no coincida con `SUB_UID_MIN`.",
    success="El valor de la directiva.",
    tests=[T("login-defs", "Lee /etc/login.defs.", ok(["UMASK", "/etc/login.defs"], ref="awk '$1==\"UMASK\"{v=$2} END{print v}' /etc/login.defs"), ok(["UID_MIN", "/etc/login.defs"], ref="awk '$1==\"UID_MIN\"{v=$2} END{print v}' /etc/login.defs"), ok(["UID_MAX", "/etc/login.defs"], ref="awk '$1==\"UID_MAX\"{v=$2} END{print v}' /etc/login.defs")),
           T("comentada", "Ignora comentarios y se queda con la última.", ok(["PermitRootLogin", "@D/sshd_config"], val="yes", prepare=r"printf '#PermitRootLogin prohibit-password\nPermitRootLogin no\nPermitRootLogin yes\nXPermitRootLogin never\n' > @D/sshd_config; chown learner: @D/sshd_config"))],
    errors=[E("uso", 1, "Recibe clave y fichero.", "uso: directiva.sh CLAVE FICHERO", ["UMASK"], []),
            E("fichero", 4, "El fichero existe y es regular.", "el fichero no existe", ["UMASK", "/etc/nada"], ["UMASK", "/etc"]),
            E("clave", 5, "La clave está activa en el fichero.", "directiva no encontrada", ["NO_EXISTE", "/etc/login.defs"], dict(args=["PermitRootLogin", "@D/inactiva"], prepare=r"printf '#PermitRootLogin yes\n' > @D/inactiva; chown learner: @D/inactiva"), eg=True)],
    examples=[eg("UID_MIN /etc/login.defs")], pages=[14],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=2)) && error "uso: directiva.sh CLAVE FICHERO" 1
[[ ! -f $2 ]] && error "el fichero no existe" 4
linea=$(grep -E "^[[:space:]]*$1[[:space:]]" "$2" | tail -n 1)
[[ -z $linea ]] && error "directiva no encontrada" 5
echo "$linea" | tr -s ' \t' ' ' | sed 's/^ //' | cut -d' ' -f2
exit 0
""")

practice.add(
    "administrador", "¿Puede administrar con sudo?",
    """Indica si un usuario pertenece al grupo `wheel`, el que da privilegios de administración en Fedora: `USUARIO: administrador` o `USUARIO: sin privilegios`.""",
    usage="USUARIO", cmds="`id -nG`, `grep -qw`", structs="`if ! comando; then`",
    detail="Busca la palabra completa: un grupo llamado `wheelers` no da privilegios. `usuario1`, creado como en la instalación de la práctica, ya está en `wheel`.",
    success="Una línea con el veredicto.",
    tests=[T("usuarios", "Distingue miembros y no miembros.", ok(["usuario1"], val="usuario1: administrador"), ok(["daemon"], val="daemon: sin privilegios"),
             ok(["p11wheelers"], val="p11wheelers: sin privilegios", prepare="getent group wheelers >/dev/null || groupadd wheelers; id p11wheelers >/dev/null 2>&1 || useradd -M -G wheelers p11wheelers"))],
    errors=[E("uso", 1, "Recibe exactamente un usuario.", "uso: administrador.sh USUARIO", []),
            E("usuario", 4, "El usuario existe.", "el usuario no existe", ["nadie"])],
    examples=[eg("usuario1"), eg("daemon")], pages=[5, 7],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: administrador.sh USUARIO" >&2; exit 1; }
if ! grupos=$(id -nG "$1" 2>/dev/null); then
  echo "el usuario no existe" >&2
  exit 4
fi
if echo "$grupos" | grep -qw wheel; then echo "$1: administrador"; else echo "$1: sin privilegios"; fi
exit 0
""")

practice.add(
    "sistema", "Qué sistema tengo",
    """Lee `/etc/os-release` y muestra `NOMBRE VERSION_ID` sin comillas (por ejemplo `Fedora Linux 44`). Con la opción `-c` indica además si es la versión de la práctica: `es Fedora 44` o `no es Fedora 44`, en una segunda línea.""",
    usage="[-c]", cmds="`source` / `.`, `/etc/os-release`", structs="`[[ ]]` con `&&`, `case`",
    detail="`/etc/os-release` tiene sintaxis de asignaciones de shell, así que `. /etc/os-release` carga sus valores en variables sin tener que partir el texto.",
    success="Una o dos líneas de identificación.",
    tests=[T("identificacion", "Lee la identidad real.", ok(ref=r"""awk -F= '$1=="NAME"{gsub(/"/,"",$2);n=$2} $1=="VERSION_ID"{gsub(/"/,"",$2);v=$2} END{print n " " v}' /etc/os-release"""),
             ok(["-c"], has="es Fedora 44"))],
    errors=[E("uso", 1, "Recibe como mucho la opción -c.", "uso: sistema.sh [-c]", ["-c", "-c"], ["-x"])],
    examples=[eg(), eg("-c")], pages=[1],
    solution=r"""
#!/bin/bash
[[ $# -gt 1 || ( $# -eq 1 && $1 != -c ) ]] && { echo "uso: sistema.sh [-c]" >&2; exit 1; }
. /etc/os-release
echo "$NAME $VERSION_ID"
if [[ $1 == -c ]]; then
  [[ $ID == fedora && $VERSION_ID == 44 ]] && echo "es Fedora 44" || echo "no es Fedora 44"
fi
exit 0
""")
