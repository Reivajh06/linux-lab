"""Práctica 3.2: unidades de systemd, drop-ins, vi y cgroups con las herramientas reales."""
from .framework import E, Practice, T, eg, ok, probe

practice = Practice(
    "3.2", "Servicios, drop-ins, vi y recursos",
    """Trabaja con los **ficheros de unidad reales** de Fedora en `/usr/lib/systemd/system` y `/etc/systemd/system`, con `systemctl --root=/`, con ficheros *drop-in*, con `vi` en modo no interactivo y con los límites `cgroup` que el contenedor tiene aplicados.
    Este contenedor no arranca `systemd` como PID 1, por lo que `systemctl start/stop/status/show`, `systemd-run`, `systemd-cgls`, Apache y `firewall-cmd` necesitan una máquina virtual: esa parte de la hoja no se evalúa aquí.
    En lugar de simular esos comandos, los ejercicios usan lo que sí es real: `list-unit-files`, `is-enabled`, `enable`, `disable`, `get-default` y `systemd-delta`. Como `httpd` no está instalado, los drop-ins se aplican a `atd.service`.""")

S = "/usr/lib/systemd/system"
E_ = "/etc/systemd/system"
_tabla = "\n".join(f"{n} {t}.target" for n, t in enumerate(["poweroff", "rescue", "multi-user", "multi-user", "multi-user", "graphical", "reboot"]))
practice.add(
    "targets", "Niveles de ejecución y target por defecto",
    """Apartado 1.1. Sin argumentos, muestra una línea `N TARGET` para cada nivel del 0 al 6, leyendo los enlaces reales `runlevelN.target`. Con `-d` muestra solo el target por defecto.""",
    usage="[-d]", cmds="`readlink`, `systemctl get-default`", structs="`for n in {0..6}`, `case`",
    detail="Los niveles 2, 3 y 4 apuntan al mismo `multi-user.target`: los números solo se conservan por compatibilidad.",
    success="La tabla, o el target por defecto.",
    tests=[T("tabla", "Lee los enlaces.", ok(val=_tabla)), T("defecto", "Lee el target por defecto.", ok(["-d"], ref="systemctl get-default", prepare="rm -rf /run/systemd/system"))],
    errors=[E("uso", 1, "Recibe como mucho la opción -d.", "uso: targets.sh [-d]", ["-x"], ["-d", "-d"])],
    examples=[eg(), eg("-d", prepare="rm -rf /run/systemd/system")],
    solution=r"""
#!/bin/bash
[[ $# -gt 1 || ( $# -eq 1 && $1 != -d ) ]] && { echo "uso: targets.sh [-d]" >&2; exit 1; }
if [[ $1 == -d ]]; then
  systemctl get-default
else
  for n in {0..6}; do
    echo "$n $(readlink "/usr/lib/systemd/system/runlevel$n.target")"
  done
fi
exit 0
""")

_clean_u = f"rm -f {E_}/atd.service; rm -rf /run/systemd/system"
_en_run = f"{_clean_u}; mkdir -p /run/systemd/system; cp {S}/atd.service /run/systemd/system/"
practice.add(
    "ubicacion", "Qué fichero de unidad manda",
    """Apartado 1.2. Muestra la ruta del fichero de unidad que tiene prioridad, buscando en este orden: `/etc/systemd/system`, `/run/systemd/system` y `/usr/lib/systemd/system`.""",
    usage="UNIDAD", cmds="`/etc/systemd/system`, `/run/systemd/system`, `/usr/lib/systemd/system`", structs='`for d in a b c`, `-e`, `exit` dentro del bucle',
    detail="La configuración del administrador en `/etc` gana a la del tiempo de ejecución en `/run`, y esta a la de los paquetes en `/usr/lib`. Por eso los paquetes no pisan tus cambios al actualizarse. En este contenedor no dejes creado `/run/systemd/system`: su existencia hace creer a `systemctl` que `systemd` está en marcha.",
    success="La ruta efectiva.",
    tests=[T("prioridad", "Respeta el orden de prioridad.",
             ok(["atd.service"], val=f"{S}/atd.service", prepare=_clean_u),
             ok(["atd.service"], val="/run/systemd/system/atd.service", prepare=_en_run),
             ok(["atd.service"], val=f"{E_}/atd.service", prepare=f"{_en_run}; cp {S}/atd.service {E_}/"),
             ok(["crond.service"], val=f"{S}/crond.service", prepare=_clean_u))],
    errors=[E("uso", 1, "Recibe exactamente una unidad.", "uso: ubicacion.sh UNIDAD", []),
            E("unidad", 4, "La unidad existe en alguno de los directorios.", "la unidad no existe", ["noexiste.service"])],
    examples=[eg("atd.service", prepare=_clean_u)],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: ubicacion.sh UNIDAD" >&2; exit 1; }
for directorio in /etc/systemd/system /run/systemd/system /usr/lib/systemd/system; do
  if [[ -e $directorio/$1 ]]; then
    echo "$directorio/$1"
    exit 0
  fi
done
echo "la unidad no existe" >&2
exit 4
""")

_prop = lambda sec, key, unit="atd.service": f"""awk -v s='[{sec}]' -v k={key} '/^\\[/{{c=($0==s)}} c && index($0,k"=")==1{{v=substr($0,length(k)+2)}} END{{print v}}' {S}/{unit}"""
practice.add(
    "propiedad", "Leer una propiedad de un fichero de unidad",
    """Apartado 5.1. Muestra el valor de una propiedad dentro de una sección de un fichero de `/usr/lib/systemd/system`. La misma clave en otra sección no cuenta. Si aparece varias veces en la sección, gana la última.""",
    usage="UNIDAD SECCION CLAVE", cmds="`/usr/lib/systemd/system/*.service`, `less`", structs='`while IFS= read -r linea`, `case "$linea" in`, una variable de estado `dentro`, `${linea#*=}`',
    detail="Una línea `[Sección]` cambia de sección. El valor puede contener `=`: quita solo hasta el **primer** `=` con `${linea#*=}`.",
    success="El valor de la propiedad.",
    tests=[T("reales", "Lee unidades reales.", ok(["atd.service", "Unit", "Description"], ref=_prop("Unit", "Description")), ok(["atd.service", "Service", "ExecStart"], ref=_prop("Service", "ExecStart")), ok(["atd.service", "Install", "WantedBy"], ref=_prop("Install", "WantedBy")), ok(["crond.service", "Service", "ExecStart"], ref=_prop("Service", "ExecStart", "crond.service")))],
    errors=[E("uso", 1, "Recibe unidad, sección y clave.", "uso: propiedad.sh UNIDAD SECCION CLAVE", ["a", "b"], []),
            E("unidad", 4, "La unidad existe.", "la unidad no existe", ["no.service", "Unit", "Description"]),
            E("clave", 5, "La clave existe en esa sección.", "la propiedad no existe en esa sección", ["atd.service", "Unit", "ExecStart"], ["atd.service", "Nada", "Description"])],
    examples=[eg("atd.service Service ExecStart")],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=3)) && error "uso: propiedad.sh UNIDAD SECCION CLAVE" 1
fichero=/usr/lib/systemd/system/$1
[[ ! -f $fichero ]] && error "la unidad no existe" 4
dentro=0
encontrado=0
while IFS= read -r linea; do
  case $linea in
    "[$2]") dentro=1;;
    "["*) dentro=0;;
    "$3="*) if ((dentro==1)); then valor=${linea#*=}; encontrado=1; fi;;
  esac
done < "$fichero"
((encontrado==0)) && error "la propiedad no existe en esa sección" 5
echo "$valor"
exit 0
""")

_lista = lambda st: f"systemctl --root=/ list-unit-files --type=service --state={st} --no-legend --no-pager | awk '{{print $1}}'"
practice.add(
    "servicios", "Servicios por estado",
    """Apartado 4. Lista solo el nombre de los ficheros de unidad de tipo servicio que están en el estado indicado: `enabled`, `disabled` o `static`.""",
    usage="ESTADO", cmds="`systemctl --root=/ list-unit-files --type=service --state= --no-legend --no-pager`, `cut` o `awk`", structs="`case`, tuberías",
    detail="`--root=/` trabaja sobre los ficheros sin hablar con `systemd`, por eso funciona aquí. `--no-legend` quita cabecera y pie, y `--no-pager` evita el paginador.",
    success="Un nombre por línea.",
    tests=[T("estados", "Lista cada estado.", ok(["enabled"], ref=_lista("enabled"), timeout=30), ok(["disabled"], ref=_lista("disabled"), timeout=30), ok(["static"], ref=_lista("static"), timeout=30))],
    errors=[E("uso", 1, "Recibe exactamente un estado.", "uso: servicios.sh ESTADO", []),
            E("estado", 2, "El estado es enabled, disabled o static.", "estado no válido", ["activo"])],
    examples=[eg("enabled | head -n 3")],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: servicios.sh ESTADO" >&2; exit 1; }
case $1 in
  enabled|disabled|static) ;;
  *) echo "estado no válido" >&2; exit 2;;
esac
systemctl --root=/ list-unit-files --type=service --state="$1" --no-legend --no-pager | awk '{print $1}'
exit 0
""")

practice.add(
    "wants", "Enlaces de los servicios habilitados",
    """Apartado 3.2. Habilitar crea un enlace en `/etc/systemd/system/TARGET.wants/`. Recorre esos directorios y muestra `TARGET: SERVICIO` por cada enlace a un `.service`, ordenado.""",
    cmds="`ls`, `sort`", structs='`for d in /etc/systemd/system/*.wants`, `${d##*/}`, `${x%.wants}`, bucle anidado, `-L`',
    detail="Quita ruta y sufijo con expansiones: `${d##*/}` elimina hasta la última barra y `${d%.wants}` elimina el final. Encadena `done | sort`.",
    success="Una línea por enlace.",
    tests=[T("enlaces", "Coincide con los enlaces reales.", ok(ref=f"""find {E_} -mindepth 2 -maxdepth 2 -path '*.wants/*.service' -printf '%h: %f\\n' | sed 's|^.*/||; s|\\.wants: |: |' | sort"""), ok(has="multi-user.target: atd.service"))],
    errors=[E("uso", 1, "No recibe argumentos.", "uso: wants.sh", ["x"])],
    examples=[eg("| head -n 3")],
    solution=r"""
#!/bin/bash
(($#!=0)) && { echo "uso: wants.sh" >&2; exit 1; }
for directorio in /etc/systemd/system/*.wants; do
  target=${directorio##*/}
  target=${target%.wants}
  for enlace in "$directorio"/*.service; do
    [[ -L $enlace ]] && echo "$target: ${enlace##*/}"
  done
done | sort
exit 0
""")

practice.add(
    "conmuta", "Habilitar y deshabilitar",
    """Apartado 3.2. Habilita o deshabilita una unidad con `systemctl --root=/` sin mostrar los mensajes del comando, y muestra `UNIDAD: ESTADO` con el estado final de `is-enabled`. Se evalúa como root.""",
    usage="enable|disable UNIDAD", cmds="`systemctl --root=/ enable`, `disable`, `is-enabled`", structs="`case`, `$EUID`, `$(...)`",
    detail="Activar y habilitar son operaciones distintas. `is-enabled` devuelve 1 si la unidad está deshabilitada, pero imprime igualmente el estado: captura la salida, no el código.",
    success="Una línea con el estado final.",
    tests=[T("disable", "Deshabilita y elimina el enlace.", ok(["disable", "atd.service"], val="atd.service: disabled"), probe(f"[ ! -e {E_}/multi-user.target.wants/atd.service ]")),
           T("enable", "Habilita y crea el enlace.", ok(["enable", "atd.service"], val="atd.service: enabled"), probe(f"[ -L {E_}/multi-user.target.wants/atd.service ]"))],
    errors=[E("uso", 1, "Recibe acción y unidad.", "uso: conmuta.sh enable|disable UNIDAD", ["enable"], []),
            E("accion", 2, "La acción es enable o disable.", "acción no válida", ["start", "atd.service"]),
            E("permiso", 3, "Se ejecuta como root.", "hay que ser root", dict(args=["enable", "atd.service"], user="learner")),
            E("unidad", 4, "La unidad existe.", "la unidad no existe", ["enable", "no.service"])],
    examples=[eg("enable atd.service", user="root")], root=True,
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=2)) && error "uso: conmuta.sh enable|disable UNIDAD" 1
[[ $1 != enable && $1 != disable ]] && error "acción no válida" 2
((EUID!=0)) && error "hay que ser root" 3
[[ ! -f /usr/lib/systemd/system/$2 ]] && error "la unidad no existe" 4
systemctl --root=/ "$1" "$2" >/dev/null 2>&1
echo "$2: $(systemctl --root=/ is-enabled "$2")"
exit 0
""")

_nodrop = f"rm -rf {E_}/atd.service.d"
_dropin = f"{E_}/atd.service.d"
practice.add(
    "dropin", "Crear un fichero drop-in",
    """Apartado 5. Crea `/etc/systemd/system/UNIDAD.d/NOMBRE.conf` con la cabecera de la sección y una línea por cada propiedad, sustituyendo el fichero si ya existía. Termina mostrando la ruta. Se evalúa como root.""",
    usage="UNIDAD NOMBRE SECCION CLAVE=VALOR...", cmds="`mkdir -p`, `systemd-delta`, `man 5 systemd.service`", structs='`shift 3`, `for p in "$@"`, agrupación `{ ...; } > fichero`',
    detail="El directorio se llama `atd.service.d`. Valida todas las propiedades **antes** de escribir para no dejar un fichero a medias. `systemd-delta` lista la unidad como `[EXTENDED]`. Tras un cambio real haría falta `systemctl daemon-reload`.",
    success="La ruta creada.",
    tests=[T("crea", "Crea el drop-in con el formato correcto.", ok(["atd.service", "restart-policy", "Service", "Restart=on-failure", "RestartSec=20"], val=f"{_dropin}/restart-policy.conf", prepare=_nodrop),
             probe(f"""[ "$(cat {_dropin}/restart-policy.conf)" = "[Service]
Restart=on-failure
RestartSec=20" ]"""), probe(f"systemd-delta --no-pager --type=extended | grep -q '{_dropin}/restart-policy.conf'")),
           T("sustituye", "Sustituye el fichero existente.", ok(["atd.service", "restart-policy", "Service", "RestartSec=5"], val=f"{_dropin}/restart-policy.conf"),
             probe(f"""[ "$(cat {_dropin}/restart-policy.conf)" = "[Service]
RestartSec=5" ]"""))],
    errors=[E("uso", 1, "Recibe unidad, nombre, sección y al menos una propiedad.", "uso: dropin.sh UNIDAD NOMBRE SECCION CLAVE=VALOR...", ["atd.service", "x", "Service"], []),
            E("seccion", 2, "La sección es Unit, Service o Install.", "sección no válida", ["atd.service", "x", "Nada", "A=1"]),
            E("propiedad", 3, "Cada propiedad tiene la forma Clave=valor.", "propiedad no válida", ["atd.service", "x", "Service", "sinigual"], ["atd.service", "x", "Service", "A=1", "=2"]),
            E("unidad", 4, "La unidad existe.", "la unidad no existe", ["no.service", "x", "Service", "A=1"]),
            E("permiso", 5, "Se ejecuta como root.", "hay que ser root", dict(args=["atd.service", "x", "Service", "A=1"], user="learner"))],
    examples=[eg("atd.service restart-policy Service Restart=on-failure RestartSec=20", prepare=_nodrop, user="root")], root=True,
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#<4)) && error "uso: dropin.sh UNIDAD NOMBRE SECCION CLAVE=VALOR..." 1
case $3 in
  Unit|Service|Install) ;;
  *) error "sección no válida" 2;;
esac
unidad=$1; nombre=$2; seccion=$3
shift 3
for propiedad in "$@"; do
  [[ ! $propiedad =~ ^[A-Za-z]+=.*$ ]] && error "propiedad no válida" 3
done
[[ ! -f /usr/lib/systemd/system/$unidad ]] && error "la unidad no existe" 4
((EUID!=0)) && error "hay que ser root" 5
directorio=/etc/systemd/system/$unidad.d
mkdir -p "$directorio"
{
  echo "[$seccion]"
  for propiedad in "$@"; do echo "$propiedad"; done
} > "$directorio/$nombre.conf"
echo "$directorio/$nombre.conf"
exit 0
""")

practice.add(
    "exec-debug", "Sustituir ExecStart",
    """Apartado 5.2. Crea el drop-in `execstart-debug.conf` de una unidad para añadir una opción a su comando de inicio. Lee el `ExecStart` del fichero original y escribe:

```ini
[Service]
ExecStart=
ExecStart=COMANDO-ORIGINAL OPCION
```

Termina mostrando la nueva línea `ExecStart=...`. Se evalúa como root.""",
    usage="UNIDAD OPCION", cmds="`grep ^ExecStart=`, `cut -d= -f2-`, `systemd-delta`", structs="agrupación con redirección, `printf`",
    detail="`ExecStart` tiene una peculiaridad: para sustituirlo hay que **vaciarlo primero** con `ExecStart=`, o `systemd` lo tomaría como un segundo comando. Este cambio además exige `daemon-reload` y reiniciar el servicio.",
    success="La nueva línea.",
    tests=[T("crea", "Escribe el vaciado y el comando nuevo.", ok(["atd.service", "-d"], ref=f"""echo "$(grep '^ExecStart=' {S}/atd.service) -d\"""", prepare=_nodrop),
             probe(f"""[ "$(cat {_dropin}/execstart-debug.conf)" = "[Service]
ExecStart=
$(grep '^ExecStart=' {S}/atd.service) -d" ]"""))],
    errors=[E("uso", 1, "Recibe unidad y opción.", "uso: exec-debug.sh UNIDAD OPCION", ["a"], []),
            E("unidad", 4, "La unidad existe.", "la unidad no existe", ["no.service", "-d"]),
            E("sin-exec", 5, "La unidad tiene ExecStart.", "la unidad no tiene ExecStart", ["multi-user.target", "-d"]),
            E("permiso", 6, "Se ejecuta como root.", "hay que ser root", dict(args=["atd.service", "-d"], user="learner"))],
    examples=[eg("atd.service -d", prepare=_nodrop, user="root")], root=True,
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=2)) && error "uso: exec-debug.sh UNIDAD OPCION" 1
fichero=/usr/lib/systemd/system/$1
[[ ! -f $fichero ]] && error "la unidad no existe" 4
original=$(grep '^ExecStart=' "$fichero" | head -n 1)
[[ -z $original ]] && error "la unidad no tiene ExecStart" 5
((EUID!=0)) && error "hay que ser root" 6
mkdir -p "/etc/systemd/system/$1.d"
{
  echo "[Service]"
  echo "ExecStart="
  echo "$original $2"
} > "/etc/systemd/system/$1.d/execstart-debug.conf"
echo "$original $2"
exit 0
""")

practice.add(
    "actividad", "Actividad de laboratorio",
    """Apartado 7, puntos 3 a 5, aplicados a la unidad indicada (`httpd.service` en la máquina virtual; aquí, `atd.service`). Crea tres drop-ins en `/etc/systemd/system/UNIDAD.d/`:

- `description.conf`: la descripción pasa a ser `My Apache HTTP Server`.
- `restart-policy.conf`: se reinicia ante un fallo, 10 segundos después.
- `memoria.conf`: mínimo garantizado de 1 GB y máximo de 2 GB.

Termina mostrando `3 drop-ins en DIRECTORIO`. Se evalúa como root.""",
    usage="UNIDAD", cmds="`Description=`, `Restart=on-failure`, `RestartSec=`, `MemoryMin=`, `MemoryMax=`, `man 5 systemd.resource-control`", structs="función `escribe()`, `printf '%s\\n'`",
    detail="`Description` va en `[Unit]`; el resto, en `[Service]`. Un fichero por motivo permite deshacer cada cambio borrando solo ese fichero.",
    success="La línea de confirmación.",
    tests=[T("ficheros", "Crea los tres drop-ins.", ok(["atd.service"], val=f"3 drop-ins en {_dropin}", prepare=_nodrop), probe(f"""[ "$(ls {_dropin} | wc -l)" = 3 ] && systemd-delta --no-pager --type=extended | grep -q {_dropin}/memoria.conf""")),
           T("descripcion", "Cambia la descripción.", probe(f"""grep -qx '\\[Unit\\]' {_dropin}/description.conf && grep -qx 'Description=My Apache HTTP Server' {_dropin}/description.conf""")),
           T("reinicio", "Política de reinicio.", probe(f"""grep -qx '\\[Service\\]' {_dropin}/restart-policy.conf && grep -qx 'Restart=on-failure' {_dropin}/restart-policy.conf && grep -qx 'RestartSec=10' {_dropin}/restart-policy.conf""")),
           T("memoria", "Límites de memoria.", probe(f"""grep -qx '\\[Service\\]' {_dropin}/memoria.conf && grep -qx 'MemoryMin=1G' {_dropin}/memoria.conf && grep -qx 'MemoryMax=2G' {_dropin}/memoria.conf"""))],
    errors=[E("uso", 1, "Recibe exactamente una unidad.", "uso: actividad.sh UNIDAD", []),
            E("permiso", 3, "Se ejecuta como root.", "hay que ser root", dict(args=["atd.service"], user="learner")),
            E("unidad", 4, "La unidad existe.", "la unidad no existe", ["no.service"])],
    examples=[eg("atd.service", prepare=_nodrop, user="root")], root=True,
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
escribe() {
  local fichero=$1
  shift
  printf '%s\n' "$@" > "$directorio/$fichero.conf"
}
(($#!=1)) && error "uso: actividad.sh UNIDAD" 1
((EUID!=0)) && error "hay que ser root" 3
[[ ! -f /usr/lib/systemd/system/$1 ]] && error "la unidad no existe" 4
directorio=/etc/systemd/system/$1.d
mkdir -p "$directorio"
escribe description '[Unit]' 'Description=My Apache HTTP Server'
escribe restart-policy '[Service]' 'Restart=on-failure' 'RestartSec=10'
escribe memoria '[Service]' 'MemoryMin=1G' 'MemoryMax=2G'
echo "3 drop-ins en $directorio"
exit 0
""")

_dos = f"{_nodrop}; mkdir -p {_dropin}; echo '[Service]' > {_dropin}/a.conf; echo '[Service]' > {_dropin}/b.conf; echo otro > {_dropin}/nota.txt"
practice.add(
    "revertir", "Deshacer drop-ins",
    """Apartado 5.2. Elimina el drop-in `NOMBRE.conf` de una unidad o, sin nombre, todos sus `.conf`. Si el directorio queda vacío, lo elimina también. Muestra `eliminados: N`. Se evalúa como root.""",
    usage="UNIDAD [NOMBRE]", cmds="`rm`, `rmdir`, `shopt -s nullglob`", structs='vector `f=("$dir"/*.conf)`, `${#f[@]}`, `(( ))`',
    detail="Borrar un fichero solo cambia el disco: en un sistema real hay que ejecutar `systemctl daemon-reload`, y también reiniciar si afecta al comando de inicio.",
    success="La línea con el recuento.",
    tests=[T("uno", "Elimina uno y conserva el resto.", ok(["atd.service", "a"], val="eliminados: 1", prepare=_dos), probe(f"[ ! -e {_dropin}/a.conf ] && [ -e {_dropin}/b.conf ]")),
           T("todos", "Elimina todos los .conf.", ok(["atd.service"], val="eliminados: 2", prepare=_dos), probe(f"[ -e {_dropin}/nota.txt ] && [ ! -e {_dropin}/a.conf ]")),
           T("directorio", "Elimina el directorio si queda vacío.", ok(["atd.service"], val="eliminados: 2", prepare=f"{_dos}; rm {_dropin}/nota.txt"), probe(f"[ ! -e {_dropin} ]")),
           T("nada", "Sin drop-ins no falla.", ok(["atd.service"], val="eliminados: 0", prepare=_nodrop))],
    errors=[E("uso", 1, "Recibe una unidad y un nombre opcional.", "uso: revertir.sh UNIDAD [NOMBRE]", [], ["a", "b", "c"]),
            E("permiso", 3, "Se ejecuta como root.", "hay que ser root", dict(args=["atd.service"], user="learner"))],
    examples=[eg("atd.service", prepare=_dos, user="root")], root=True,
    solution=r"""
#!/bin/bash
(($#<1 || $#>2)) && { echo "uso: revertir.sh UNIDAD [NOMBRE]" >&2; exit 1; }
((EUID!=0)) && { echo "hay que ser root" >&2; exit 3; }
directorio=/etc/systemd/system/$1.d
shopt -s nullglob
if (($#==2)); then
  ficheros=("$directorio/$2.conf")
  [[ -e ${ficheros[0]} ]] || ficheros=()
else
  ficheros=("$directorio"/*.conf)
fi
((${#ficheros[@]}>0)) && rm -f "${ficheros[@]}"
[[ -d $directorio ]] && rmdir "$directorio" 2>/dev/null
echo "eliminados: ${#ficheros[@]}"
exit 0
""")

_copia = "cp /etc/login.defs @D/defs; cp /etc/shells @D/shells; chown learner: @D/defs @D/shells"
practice.add(
    "vi-sustituye", "Sustituir con vi desde un script",
    """Apartado 2.1. Aplica `:%s/ORIGEN/DESTINO/g` a un fichero usando `vi` en modo no interactivo, guarda y muestra `líneas con ORIGEN: N`, contando antes de editar. Si no hay coincidencias, el fichero no cambia y la cuenta es 0. `ORIGEN` y `DESTINO` son rutas o textos que pueden contener `/`.""",
    usage="FICHERO ORIGEN DESTINO", cmds="`vi -es -c '...' -c x`, `:%s`, `grep -c`", structs="`#` como delimitador, sustitución de comandos",
    detail="La `g` sustituye todas las apariciones de cada línea y el `%`, en todas las líneas. Cualquier carácter sirve de delimitador: `%s#/bin/#/sbin/#g`. El indicador `e` evita el error de `vi` cuando no hay coincidencias.",
    success="La línea con el recuento.",
    tests=[T("copia-real", "Modifica una copia de /etc/login.defs.", ok(["@D/defs", "UID", "IDU"], ref="echo \"líneas con UID: $(grep -c UID /etc/login.defs)\"", prepare=_copia), probe("""[ "$(cat $D/defs)" = "$(sed 's/UID/IDU/g' /etc/login.defs)" ]""")),
           T("barras", "Admite barras.", ok(["@D/shells", "/bin/", "/sbin/"], ref="echo \"líneas con /bin/: $(grep -c /bin/ /etc/shells)\"", prepare=_copia), probe("""[ "$(cat $D/shells)" = "$(sed 's#/bin/#/sbin/#g' /etc/shells)" ]""")),
           T("sin-coincidencias", "Sin coincidencias no cambia nada.", ok(["@D/defs", "zzzz", "y"], val="líneas con zzzz: 0", prepare=_copia), probe("""cmp -s $D/defs /etc/login.defs"""))],
    errors=[E("uso", 1, "Recibe fichero, origen y destino.", "uso: vi-sustituye.sh FICHERO ORIGEN DESTINO", ["a", "b"], []),
            E("fichero", 4, "El fichero existe.", "el fichero no existe", ["/nada", "a", "b"])],
    examples=[eg("@D/shells /bin/ /sbin/", prepare=_copia)],
    solution=r"""
#!/bin/bash
(($#!=3)) && { echo "uso: vi-sustituye.sh FICHERO ORIGEN DESTINO" >&2; exit 1; }
[[ ! -f $1 ]] && { echo "el fichero no existe" >&2; exit 4; }
total=$(grep -c -- "$2" "$1")
vi -es -c "%s#$2#$3#ge" -c x "$1"
echo "líneas con $2: $total"
exit 0
""")

practice.add(
    "vi-borra", "Borrar líneas con vi",
    """Apartado 2.1. Borra el rango de líneas `INICIO`–`FIN`, ambos incluidos, de un fichero usando `vi` en modo no interactivo y muestra `quedan N líneas`. Es lo que hace `3dd` con el cursor en la línea adecuada.""",
    usage="FICHERO INICIO FIN", cmds="`vi -es -c 'I,Fd' -c x`, `wc -l <`", structs="`[[ =~ ]]`, `(( ))` con varias condiciones",
    detail="En `vi` el rango `2,4d` borra por número de línea. Con `:q!` saldrías sin guardar: aquí `x` guarda y sale.",
    success="La línea con las líneas restantes.",
    tests=[T("borra", "Borra el rango en una copia real.", ok(["@D/shells", "2", "3"], ref="echo \"quedan $(sed '2,3d' /etc/shells | wc -l) líneas\"", prepare=_copia), probe("""[ "$(cat $D/shells)" = "$(sed '2,3d' /etc/shells)" ]""")),
           T("una", "Borra una sola línea.", ok(["@D/shells", "1", "1"], ref="echo \"quedan $(sed '1d' /etc/shells | wc -l) líneas\"", prepare=_copia))],
    errors=[E("uso", 1, "Recibe fichero, inicio y fin.", "uso: vi-borra.sh FICHERO INICIO FIN", ["a", "1"], []),
            E("formato", 2, "Inicio y fin son enteros mayores que 0.", "inicio y fin deben ser enteros positivos", ["/etc/shells", "a", "1"], ["/etc/shells", "1", "0"]),
            E("rango", 3, "Inicio no supera a fin, ni fin al número de líneas.", "rango de líneas no válido", ["/etc/shells", "3", "2"], ["/etc/shells", "1", "9999"]),
            E("fichero", 4, "El fichero existe.", "el fichero no existe", ["/nada", "1", "1"])],
    examples=[eg("@D/shells 2 3", prepare=_copia)],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=3)) && error "uso: vi-borra.sh FICHERO INICIO FIN" 1
[[ ! $2 =~ ^0*[1-9][0-9]*$ || ! $3 =~ ^0*[1-9][0-9]*$ ]] && error "inicio y fin deben ser enteros positivos" 2
[[ ! -f $1 ]] && error "el fichero no existe" 4
(($2>$3 || $3>$(wc -l < "$1"))) && error "rango de líneas no válido" 3
vi -es -c "$2,$3d" -c x "$1"
echo "quedan $(wc -l < "$1") líneas"
exit 0
""")

_lim = """printf 'memoria: %s\\nprocesos: %s\\ncpu: %s\\n' \
"$(awk '{print ($1=="max" ? "sin límite" : int($1/1048576) " MiB")}' /sys/fs/cgroup/memory.max)" \
"$(awk '{print ($1=="max" ? "sin límite" : $1)}' /sys/fs/cgroup/pids.max)" \
"$(awk '{print ($1=="max" ? "sin límite" : int($1*100/$2) "%")}' /sys/fs/cgroup/cpu.max)\""""
practice.add(
    "limites", "Los cgroups de este contenedor",
    """Apartado 6. Los límites de este entorno son `cgroups` reales: Linux Lab los aplica al contenedor. Lee `memory.max`, `pids.max` y `cpu.max` de `/sys/fs/cgroup` y muestra:

```text
memoria: 2048 MiB      (o sin límite)
procesos: 256          (o sin límite)
cpu: 200%              (o sin límite)
```""",
    cmds="`/sys/fs/cgroup/memory.max`, `pids.max`, `cpu.max`", structs="`read cuota periodo < fichero`, función, `$(( ))`",
    detail="Un valor `max` significa sin límite. `cpu.max` contiene `CUOTA PERIODO`: el porcentaje es `CUOTA*100/PERIODO`. Es lo que `CPUQuota=25%` o `MemoryMax=300M` configuran en un servicio.",
    success="Las tres líneas.",
    tests=[T("reales", "Coincide con el cgroup real.", ok(ref=_lim))],
    errors=[E("uso", 1, "No recibe argumentos.", "uso: limites.sh", ["x"])],
    examples=[eg()],
    solution=r"""
#!/bin/bash
(($#!=0)) && { echo "uso: limites.sh" >&2; exit 1; }
read -r memoria < /sys/fs/cgroup/memory.max
read -r procesos < /sys/fs/cgroup/pids.max
read -r cuota periodo < /sys/fs/cgroup/cpu.max
if [[ $memoria == max ]]; then echo "memoria: sin límite"; else echo "memoria: $((memoria/1048576)) MiB"; fi
if [[ $procesos == max ]]; then echo "procesos: sin límite"; else echo "procesos: $procesos"; fi
if [[ $cuota == max ]]; then echo "cpu: sin límite"; else echo "cpu: $((cuota*100/periodo))%"; fi
exit 0
""")

practice.add(
    "reparto-cpu", "Reparto de CPU con CPUWeight",
    """Apartado 6.2. Dados dos valores de `CPUWeight`, muestra qué porcentaje entero (truncado) de CPU recibe cada servicio si compiten. El segundo es opcional y vale 100, el valor por defecto de `CPUWeight`.""",
    usage="PESO1 [PESO2]", cmds="`CPUWeight=`", structs="`${2:-100}`, `$(( ))`, `for`",
    detail="La hoja reduce la prioridad a la mitad con `CPUWeight=50`: frente a otro servicio con 100 recibe 1/3 de la CPU. El rango válido va de 1 a 10000.",
    success="Dos líneas `PESO: N%`.",
    tests=[T("repartos", "Calcula el reparto.", ok(["50"], val="50: 33%\n100: 66%"), ok(["100", "100"], val="100: 50%\n100: 50%"), ok(["1", "3"], val="1: 25%\n3: 75%"), ok(["10000", "1"], val="10000: 99%\n1: 0%"))],
    errors=[E("uso", 1, "Recibe uno o dos pesos.", "uso: reparto-cpu.sh PESO1 [PESO2]", [], ["1", "2", "3"]),
            E("formato", 2, "Los pesos son enteros.", "los pesos deben ser enteros", ["a"], ["1", "b"]),
            E("rango", 3, "Los pesos están entre 1 y 10000.", "los pesos deben estar entre 1 y 10000", ["0"], ["1", "10001"])],
    examples=[eg("50")],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#<1 || $#>2)) && error "uso: reparto-cpu.sh PESO1 [PESO2]" 1
a=$1
b=${2:-100}
for peso in "$a" "$b"; do
  [[ ! $peso =~ ^[0-9]+$ ]] && error "los pesos deben ser enteros" 2
  ((peso<1 || peso>10000)) && error "los pesos deben estar entre 1 y 10000" 3
done
echo "$a: $((a*100/(a+b)))%"
echo "$b: $((b*100/(a+b)))%"
exit 0
""")

practice.add(
    "demonios", "Servicios con nombre de demonio",
    """Apartado 1. Muchos demonios tienen un nombre terminado en `d`. Lista por orden alfabético los ficheros `.service` de `/usr/lib/systemd/system` cuyo nombre, sin la extensión, termina en `d`. Excluye las plantillas (`nombre@.service`). Con `-c` muestra solo cuántos son.""",
    usage="[-c]", cmds="`/usr/lib/systemd/system`, `sort`, `wc -l`", structs='`for f in .../*.service`, `${f##*/}`, `[[ =~ ]]`',
    detail="`[[ $n =~ d\\.service$ ]]`: el punto se escapa porque en una expresión regular significa «cualquier carácter». `crond.service` cumple; `getty@.service` no.",
    success="Los nombres, o el recuento.",
    tests=[T("lista", "Filtra los nombres reales.", ok(ref=f"""find {S} -maxdepth 1 -name '*d.service' -printf '%f\\n' | LC_ALL=C sort"""), ok(has="crond.service")),
           T("cuenta", "Cuenta con -c.", ok(["-c"], ref=f"""find {S} -maxdepth 1 -name '*d.service' | wc -l"""))],
    errors=[E("uso", 1, "Recibe como mucho la opción -c.", "uso: demonios.sh [-c]", ["-x"], ["-c", "-c"])],
    examples=[eg("-c")],
    solution=r"""
#!/bin/bash
[[ $# -gt 1 || ( $# -eq 1 && $1 != -c ) ]] && { echo "uso: demonios.sh [-c]" >&2; exit 1; }
lista() {
  for fichero in /usr/lib/systemd/system/*.service; do
    nombre=${fichero##*/}
    [[ $nombre =~ d\.service$ ]] && echo "$nombre"
  done | LC_ALL=C sort
}
if [[ $1 == -c ]]; then lista | wc -l; else lista; fi
exit 0
""")
