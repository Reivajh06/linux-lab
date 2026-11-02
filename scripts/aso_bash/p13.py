"""Práctica 1.3: permisos, usuarios, contraseñas y grupos reales."""
from .framework import E, Practice, T, eg, ok, probe

practice = Practice(
    "1.3", "Permisos, usuarios y grupos",
    """Scripts que leen y administran el sistema de cuentas real: `/etc/passwd`, `/etc/shadow`, `/etc/group`, `/etc/gshadow`, `stat`, `chmod`, `useradd`, `chage`, `gpasswd`.
    Los ejercicios de administración se evalúan **como root** y comprueban el estado que dejan en el sistema; en la terminal, ejecútalos con `sudo`. Terminan con la actividad completa de laboratorio.""",
    setup="""id usuario1 >/dev/null 2>&1 || useradd -m -s /bin/bash -c 'Usuario 1' usuario1
id usuario2 >/dev/null 2>&1 || useradd -m -s /bin/bash -c 'Usuario 2' usuario2
""",
    document=("4fff130b55f626b24695f78465d28f7e99e4bdf394ba2cc4b4dad720f750eea4", "Práctica-1.3"))

practice.add(
    "permisos-octal", "De rwx a octal",
    """Convierte una cadena de nueve caracteres de permisos, como la de `ls -l`, a octal de cuatro dígitos: `rwxrw-r--` da `0764`.
    Reconoce los especiales: `s`/`S` en usuario y grupo, y `t`/`T` en otros. `rwsr-xr-x` da `4755` y `rwxr-xr-T` da `1754`.""",
    usage="PERMISOS", cmds="`stat -c %A`, `stat -c %a` para comprobar", structs="`for ((i=0;i<9;i+=3))`, `${cadena:pos:largo}`, `case`, `$(( ))`, `printf %d`",
    detail="La minúscula (`s`, `t`) indica que además hay permiso de ejecución; la mayúscula (`S`, `T`), que no. Lectura=4, escritura=2, ejecución=1.",
    success="El valor de cuatro dígitos.",
    tests=[T("cadenas", "Convierte permisos básicos y especiales.", ok(["rwxrw-r--"], val="0764"), ok(["rw-r--r--"], val="0644"), ok(["---------"], val="0000"), ok(["rwsr-xr-x"], val="4755"), ok(["rwxrwxrwt"], val="1777"), ok(["rwSr--r--"], val="4644"), ok(["rwxr-sr-x"], val="2755"), ok(["rwxr-xr-T"], val="1754")),
           T("reales", "Coincide con stat en ficheros reales.", probe("""for f in /tmp /usr/bin/passwd /etc/passwd /usr/bin/sudo /etc/shadow; do
  s=$(stat -c %A "$f"); want=$(printf '%04d' "$(stat -c %a "$f")")
  [ "$($S "${s:1}")" = "$want" ] || exit 1
done"""))],
    errors=[E("uso", 1, "Recibe exactamente una cadena.", "uso: permisos-octal.sh PERMISOS", []),
            E("formato", 2, "La cadena tiene el formato de permisos.", "cadena de permisos no válida", ["rwxrw-r-"], ["rwxrw-r--x"], ["abcdefghi"], ["rwtrwxrwx"])],
    examples=[eg("rwxrw-r--"), eg("rwsr-xr-x")], pages=[3, 4, 7],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=1)) && error "uso: permisos-octal.sh PERMISOS" 1
[[ ! $1 =~ ^[r-][w-][xsS-][r-][w-][xsS-][r-][w-][xtT-]$ ]] && error "cadena de permisos no válida" 2
especial=0
salida=""
for ((i=0;i<9;i+=3)); do
  valor=0
  [[ ${1:i:1} == r ]] && ((valor+=4))
  [[ ${1:i+1:1} == w ]] && ((valor+=2))
  x=${1:i+2:1}
  case $x in
    x|s|t) ((valor+=1));;
  esac
  case $x in
    s|S) if ((i==0)); then ((especial+=4)); else ((especial+=2)); fi;;
    t|T) ((especial+=1));;
  esac
  salida+=$valor
done
echo "$especial$salida"
exit 0
""")

practice.add(
    "umask-permisos", "Qué permisos deja una máscara",
    """Dada una máscara de tres dígitos octales, muestra los permisos de los ficheros y directorios nuevos:

```text
fichero: 644
directorio: 755
```""",
    usage="MASCARA", cmds="`umask`, `printf %03o`", structs="aritmética octal `8#$m`, operadores `&` y `~`",
    detail="La práctica lo escribe como «666 – umask», pero en realidad se **eliminan bits**: con `033` un fichero queda en `644`, no en `633`.",
    success="Las dos líneas de permisos.",
    tests=[T("mascaras", "Calcula bien, también sin restar.", ok(["022"], val="fichero: 644\ndirectorio: 755"), ok(["077"], val="fichero: 600\ndirectorio: 700"), ok(["033"], val="fichero: 644\ndirectorio: 744"), ok(["000"], val="fichero: 666\ndirectorio: 777")),
           T("real", "Coincide con el comportamiento real de umask.", probe("""for m in 027 002 137; do
  t=$(mktemp -d); (umask "$m"; touch "$t/f"; mkdir "$t/d")
  want="fichero: $(stat -c %a "$t/f")
directorio: $(stat -c %a "$t/d")"
  [ "$($S "$m")" = "$want" ] || exit 1
  rm -rf "$t"
done"""))],
    errors=[E("uso", 1, "Recibe exactamente una máscara.", "uso: umask-permisos.sh MASCARA", []),
            E("formato", 2, "La máscara tiene tres dígitos octales.", "máscara no válida", ["22"], ["088"], ["abc"])],
    examples=[eg("022"), eg("033")], pages=[5],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: umask-permisos.sh MASCARA" >&2; exit 1; }
[[ ! $1 =~ ^[0-7]{3}$ ]] && { echo "máscara no válida" >&2; exit 2; }
printf 'fichero: %03o\n' $((8#666 & ~8#$1))
printf 'directorio: %03o\n' $((8#777 & ~8#$1))
exit 0
""")

_shared = "mkdir -p /srv/p13sgid; chmod 2775 /srv/p13sgid"
practice.add(
    "info-fichero", "Ficha de un fichero",
    """Muestra la propiedad y los permisos de una ruta, siguiendo enlaces:

```text
tipo: directorio        (fichero, directorio u otro)
propietario: root
grupo: root
permisos: 1777          (lo que da stat -c %a)
especial: sticky        (suid, sgid, sticky o ninguno; si hay varios, separados por comas en ese orden)
```""",
    usage="RUTA", cmds="`stat -L -c`", structs="`if/elif`, operadores de ficheros `-f -d`, `-u -g -k`",
    detail="`/usr/bin/passwd` lleva SUID porque debe escribir en `/etc/shadow`, y `/tmp` lleva sticky bit para que cada cual solo borre lo suyo. `test` tiene operadores para ambos: `-u`, `-g`, `-k`.",
    success="Las cinco líneas de la ficha.",
    tests=[T("reales", "Describe rutas reales.",
             ok(["/tmp"], val="tipo: directorio\npropietario: root\ngrupo: root\npermisos: 1777\nespecial: sticky"),
             ok(["/usr/bin/passwd"], val="tipo: fichero\npropietario: root\ngrupo: root\npermisos: 4755\nespecial: suid"),
             ok(["/etc/passwd"], val="tipo: fichero\npropietario: root\ngrupo: root\npermisos: 644\nespecial: ninguno"),
             ok(["/dev/null"], val="tipo: otro\npropietario: root\ngrupo: root\npermisos: 666\nespecial: ninguno"),
             ok(["/srv/p13sgid"], val="tipo: directorio\npropietario: root\ngrupo: root\npermisos: 2775\nespecial: sgid", prepare=_shared))],
    errors=[E("uso", 1, "Recibe exactamente una ruta.", "uso: info-fichero.sh RUTA", []),
            E("ruta", 4, "La ruta existe.", "la ruta no existe", ["/nada"])],
    examples=[eg("/tmp"), eg("/usr/bin/passwd")], pages=[2, 6, 7],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: info-fichero.sh RUTA" >&2; exit 1; }
[[ ! -e $1 ]] && { echo "la ruta no existe" >&2; exit 4; }
if [[ -f $1 ]]; then tipo=fichero; elif [[ -d $1 ]]; then tipo=directorio; else tipo=otro; fi
especial=""
[[ -u $1 ]] && especial+=",suid"
[[ -g $1 ]] && especial+=",sgid"
[[ -k $1 ]] && especial+=",sticky"
echo "tipo: $tipo"
echo "propietario: $(stat -L -c %U "$1")"
echo "grupo: $(stat -L -c %G "$1")"
echo "permisos: $(stat -L -c %a "$1")"
especial=${especial#,}
echo "especial: ${especial:-ninguno}"
exit 0
""")

practice.add(
    "especiales", "Auditoría de SUID y SGID",
    """Lista, ordenados, los ficheros regulares de un directorio (sin subdirectorios) que tienen activado SUID (`-u`) o SGID (`-g`). Si no hay ninguno, muestra `ninguno`.""",
    usage="-u|-g DIRECTORIO", cmds="`find -maxdepth 1 -type f -perm -4000`, `sort`", structs="`case`, variable intermedia, `[[ -z ]]`",
    detail="`-perm -4000` exige que **ese bit** esté activo, sin importar los demás; `-perm 4000` pediría exactamente ese modo. SUID es peligroso: conviene auditarlo.",
    success="Una ruta por línea, o `ninguno`.",
    tests=[T("usr-bin", "Audita /usr/bin.", ok(["-u", "/usr/bin"], ref="find /usr/bin -maxdepth 1 -type f -perm -4000 | sort"), ok(["-g", "/usr/bin"], ref="find /usr/bin -maxdepth 1 -type f -perm -2000 | sort | grep . || echo ninguno")),
           T("vacio", "Indica si no hay ninguno.", ok(["-u", "/etc/skel"], val="ninguno"))],
    errors=[E("uso", 1, "Recibe opción y directorio.", "uso: especiales.sh -u|-g DIRECTORIO", ["-u"], []),
            E("opcion", 2, "La opción es -u o -g.", "opción no válida", ["-x", "/usr/bin"]),
            E("directorio", 4, "El segundo argumento es un directorio.", "no es un directorio", ["-u", "/nada"])],
    examples=[eg("-u /usr/bin")], pages=[6, 7],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=2)) && error "uso: especiales.sh -u|-g DIRECTORIO" 1
case $1 in
  -u) bit=4000;;
  -g) bit=2000;;
  *) error "opción no válida" 2;;
esac
[[ ! -d $2 ]] && error "no es un directorio" 4
lista=$(find "$2" -maxdepth 1 -type f -perm -$bit 2>/dev/null | sort)
echo "${lista:-ninguno}"
exit 0
""")

_ficha = """awk -F: -v u=%s '$1==u{print "uid: " $3; print "gid: " $4; print "comentario: " $5; print "home: " $6; print "shell: " $7}' /etc/passwd"""
practice.add(
    "ficha-usuario", "Los siete campos de /etc/passwd",
    """Muestra los campos de un usuario leyendo `/etc/passwd` con `read`:

```text
uid: 1000
gid: 1000
comentario: Usuario 1
home: /home/usuario1
shell: /bin/bash
```""",
    usage="USUARIO", cmds="`grep ^nombre:`, `man 5 passwd`", structs="`IFS=: read`, here-string `<<<`",
    detail="Busca `^usuario:` con el ancla y los dos puntos: `ad` no es `adm`. El separador se cambia solo para ese `read` escribiendo `IFS=:` en la misma línea.",
    success="Las cinco líneas de la ficha.",
    tests=[T("usuarios", "Lee usuarios reales.", ok(["root"], ref=_ficha % "root"), ok(["usuario1"], ref=_ficha % "usuario1"), ok(["adm"], ref=_ficha % "adm"), ok(["geoclue"], ref=_ficha % "geoclue"))],
    errors=[E("uso", 1, "Recibe exactamente un usuario.", "uso: ficha-usuario.sh USUARIO", []),
            E("usuario", 4, "El usuario existe.", "el usuario no existe", ["ad"], ["nadie"])],
    examples=[eg("root"), eg("usuario1")], pages=[8],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: ficha-usuario.sh USUARIO" >&2; exit 1; }
linea=$(grep "^$1:" /etc/passwd)
[[ -z $linea ]] && { echo "el usuario no existe" >&2; exit 4; }
IFS=: read -r nombre clave uid gid comentario home shell <<< "$linea"
echo "uid: $uid"
echo "gid: $gid"
echo "comentario: $comentario"
echo "home: $home"
echo "shell: $shell"
exit 0
""")

practice.add(
    "fecha-shadow", "Días desde 1970",
    """`/etc/shadow` guarda las fechas como días desde el 1 de enero de 1970. Convierte en los dos sentidos: un número de días da `AAAA-MM-DD` y una fecha `AAAA-MM-DD` da el número de días.""",
    usage="DIAS|FECHA", cmds="`date -u -d`, `date +%F`, `date +%s`", structs="`[[ =~ ]]`, `if ! f=$(date ...)`, `$(( ))`",
    detail="La práctica caduca las cuentas el 2026-12-15, que en `/etc/shadow` aparece como `20802`. Usa `-u`: con hora local un cambio de horario puede desplazar un día.",
    success="La conversión.",
    tests=[T("conversiones", "Convierte en ambos sentidos.", ok(["20802"], val="2026-12-15"), ok(["2026-12-15"], val="20802"), ok(["0"], val="1970-01-01"), ok(["1970-01-02"], val="1"), ok(["2026-12-31"], val="20818"))],
    errors=[E("uso", 1, "Recibe exactamente un valor.", "uso: fecha-shadow.sh DIAS|FECHA", []),
            E("formato", 2, "Es un número de días o tiene formato AAAA-MM-DD.", "formato no válido", ["ayer"], ["2026-12"]),
            E("fecha", 3, "La fecha existe en el calendario.", "la fecha no existe", ["2026-13-45"])],
    examples=[eg("20802"), eg("2026-12-15")], pages=[11],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=1)) && error "uso: fecha-shadow.sh DIAS|FECHA" 1
if [[ $1 =~ ^[0-9]+$ ]]; then
  date -u -d "@$(($1*86400))" +%F
elif [[ $1 =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  segundos=$(date -u -d "$1" +%s 2>/dev/null) || error "la fecha no existe" 3
  echo $((segundos/86400))
else
  error "formato no válido" 2
fi
exit 0
""")

_estado = """id p13e >/dev/null 2>&1 || useradd -m p13e
echo 'p13e:ASO2026' | chpasswd
usermod -U p13e 2>/dev/null
chage -M 30 -W 5 -I 3 -E 2026-12-31 p13e"""
practice.add(
    "estado-clave", "Estado de la contraseña en /etc/shadow",
    """Lee `/etc/shadow` y resume la política de una cuenta. Solo root puede leer ese fichero: comprueba primero que el script se ejecuta como root.

```text
clave: establecida      (bloqueada si empieza por ! o *; sin clave si el campo está vacío)
maximo: 30
aviso: 5
inactividad: 3          (- si está vacío)
caduca: 2026-12-31      (nunca si está vacío)
```""",
    usage="USUARIO", cmds="`/etc/shadow`, `chage -l`, `date`, `usermod -L`, `chpasswd`", structs="`$EUID`, `IFS=: read`, `case` con patrones (`'!'*|'*'*`), `${var:--}`",
    detail="`useradd` deja la cuenta **sin contraseña utilizable** (`!`), y `usermod -L` bloquea anteponiendo `!` a la clave cifrada: en ambos casos no se puede entrar con contraseña.",
    success="Las cinco líneas de estado.",
    tests=[T("establecida", "Cuenta con política completa.", ok(["p13e"], val="clave: establecida\nmaximo: 30\naviso: 5\ninactividad: 3\ncaduca: 2026-12-31", prepare=_estado)),
           T("bloqueada", "Cuenta bloqueada con usermod -L.", ok(["p13e"], has="clave: bloqueada", prepare=_estado + "\nusermod -L p13e")),
           T("nueva", "Cuenta recién creada.", ok(["p13n"], has="clave: bloqueada", prepare="id p13n >/dev/null 2>&1 || useradd -m p13n"),
             ok(["p13n"], has="inactividad: -"), ok(["p13n"], has="caduca: nunca"))],
    errors=[E("uso", 1, "Recibe exactamente un usuario.", "uso: estado-clave.sh USUARIO", []),
            E("permiso", 3, "Se ejecuta como root.", "hay que ser root", dict(args=["root"], user="learner")),
            E("usuario", 4, "El usuario existe.", "el usuario no existe", ["nadie"])],
    examples=[eg("p13e", prepare=_estado, user="root")], pages=[10, 11, 12],
    root=True,
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=1)) && error "uso: estado-clave.sh USUARIO" 1
((EUID!=0)) && error "hay que ser root" 3
linea=$(grep "^$1:" /etc/shadow)
[[ -z $linea ]] && error "el usuario no existe" 4
IFS=: read -r nombre clave ultimo minimo maximo aviso inactividad caduca resto <<< "$linea"
case $clave in
  '') estado="sin clave";;
  '!'*|'*'*) estado=bloqueada;;
  *) estado=establecida;;
esac
echo "clave: $estado"
echo "maximo: $maximo"
echo "aviso: $aviso"
echo "inactividad: ${inactividad:--}"
if [[ -z $caduca ]]; then
  echo "caduca: nunca"
else
  echo "caduca: $(date -u -d "@$((caduca*86400))" +%F)"
fi
exit 0
""")

_borra = "for u in p13a p13b p13c; do userdel -r $u 2>/dev/null; done; true"
practice.add(
    "alta-usuarios", "Alta de usuarios en lote",
    """Crea cuentas con directorio personal y shell `/bin/bash` y les asigna la misma contraseña sin interacción. Valida **todos** los nombres (`^[a-z_][a-z0-9_-]*$`) antes de crear ninguna cuenta.
    Por cada cuenta creada muestra `creado: NOMBRE`. Si ya existe, escribe `ya existe: NOMBRE` en stderr, continúa y termina con el código 4.""",
    usage="CLAVE NOMBRE...", cmds="`useradd -m -s`, `chpasswd`, `id`", structs='`shift`, `for n in "$@"`, doble bucle',
    detail='`passwd` es interactivo; en un script usa `echo "usuario:clave" | chpasswd`. Con `sudo`, el `sudo` debe ir delante de `chpasswd`, no de `echo`.',
    success="Una línea `creado: NOMBRE` por cuenta.",
    tests=[T("crea", "Crea las cuentas con contraseña utilizable.", ok(["ASO2026", "p13a", "p13b"], val="creado: p13a\ncreado: p13b", prepare=_borra),
             probe("""for u in p13a p13b; do
  [ "$(getent passwd $u | cut -d: -f7)" = /bin/bash ] && [ -d /home/$u ] || exit 1
  case "$(getent shadow $u | cut -d: -f2)" in ''|'!'*|'*'*) exit 1;; esac
done"""))],
    errors=[E("uso", 1, "Recibe la clave y al menos un nombre.", "uso: alta-usuarios.sh CLAVE NOMBRE...", ["clave"], []),
            E("nombre", 2, "Todos los nombres son válidos.", "nombre de usuario no válido", dict(args=["c", "p13c", "Mal"], prepare=_borra), eg=False),
            E("permiso", 3, "Se ejecuta como root.", "hay que ser root", dict(args=["c", "p13c"], user="learner")),
            E("existente", 4, "Las cuentas no existen ya; si existe una, se avisa y se continúa.", "ya existe: root", dict(args=["c", "root", "p13c"], prepare=_borra, ref="echo creado: p13c"), partial="stdout con las cuentas creadas y stderr con las existentes.", eg=False)],
    examples=[eg("ASO2026 p13a", prepare=_borra, user="root")], pages=[8, 9], root=True,
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#<2)) && error "uso: alta-usuarios.sh CLAVE NOMBRE..." 1
((EUID!=0)) && error "hay que ser root" 3
clave=$1
shift
for nombre in "$@"; do
  [[ ! $nombre =~ ^[a-z_][a-z0-9_-]*$ ]] && error "nombre de usuario no válido" 2
done
codigo=0
for nombre in "$@"; do
  if id "$nombre" >/dev/null 2>&1; then
    echo "ya existe: $nombre" >&2
    codigo=4
    continue
  fi
  useradd -m -s /bin/bash "$nombre"
  echo "$nombre:$clave" | chpasswd
  echo "creado: $nombre"
done
exit $codigo
""")

_pol = "id p13p >/dev/null 2>&1 || useradd -m p13p; chage -M 99999 -W 7 -I -1 -E -1 p13p"
practice.add(
    "politica", "Política de contraseñas con chage",
    """Aplica a un usuario la vigencia máxima, los días de aviso, el periodo de gracia y, si se indica, la fecha de caducidad de la cuenta (`AAAA-MM-DD`). Sin fecha, la cuenta no caduca nunca. Termina con `política aplicada a USUARIO`.""",
    usage="USUARIO MAX AVISO GRACIA [FECHA]", cmds="`chage -M -W -I -E`, `chage -l`", structs="`${5:--1}`, validación en bucle, `[[ =~ ]]`",
    detail="No confundas caducidad de la **contraseña** (`-M`) con caducidad de la **cuenta** (`-E`). El periodo de «inactividad» (`-I`) es en realidad una gracia tras caducar la contraseña; `-E -1` quita la caducidad.",
    success="El mensaje de confirmación.",
    tests=[T("con-fecha", "Aplica la política con fecha.", ok(["p13p", "60", "4", "2", "2026-12-15"], val="política aplicada a p13p", prepare=_pol),
             probe("""IFS=: read -r u c l mi ma av in ca r <<< "$(getent shadow p13p)"; [ "$ma:$av:$in:$ca" = 60:4:2:20802 ]""")),
           T("sin-fecha", "Quita la caducidad si no hay fecha.", ok(["p13p", "30", "5", "3"], val="política aplicada a p13p"),
             probe("""IFS=: read -r u c l mi ma av in ca r <<< "$(getent shadow p13p)"; [ "$ma:$av:$in:$ca" = 30:5:3: ]"""))],
    errors=[E("uso", 1, "Recibe cuatro o cinco argumentos.", "uso: politica.sh USUARIO MAX AVISO GRACIA [FECHA]", ["p13p", "1", "2"], []),
            E("numero", 2, "MAX, AVISO y GRACIA son números.", "los días deben ser números", ["p13p", "x", "4", "2"]),
            E("fecha", 3, "La fecha tiene formato AAAA-MM-DD.", "la fecha no tiene el formato AAAA-MM-DD", ["p13p", "60", "4", "2", "15/12/2026"]),
            E("usuario", 4, "El usuario existe.", "el usuario no existe", ["nadie", "60", "4", "2"]),
            E("permiso", 5, "Se ejecuta como root.", "hay que ser root", dict(args=["p13p", "60", "4", "2"], user="learner"))],
    examples=[eg("p13p 60 4 2 2026-12-15", prepare=_pol, user="root")], pages=[10, 11, 12], root=True,
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#<4 || $#>5)) && error "uso: politica.sh USUARIO MAX AVISO GRACIA [FECHA]" 1
for dias in "$2" "$3" "$4"; do
  [[ ! $dias =~ ^[0-9]+$ ]] && error "los días deben ser números" 2
done
[[ $# -eq 5 && ! $5 =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] && error "la fecha no tiene el formato AAAA-MM-DD" 3
id "$1" >/dev/null 2>&1 || error "el usuario no existe" 4
((EUID!=0)) && error "hay que ser root" 5
chage -M "$2" -W "$3" -I "$4" -E "${5:--1}" "$1"
echo "política aplicada a $1"
exit 0
""")

_grupo = """getent group p13g >/dev/null || groupadd p13g
id p13g1 >/dev/null 2>&1 || useradd -M -g p13g p13g1
id p13g2 >/dev/null 2>&1 || useradd -M -g p13g p13g2
id p13g3 >/dev/null 2>&1 || useradd -M p13g3
id p13g0 >/dev/null 2>&1 || useradd -M p13g0
gpasswd -M p13g3,p13g0 p13g >/dev/null"""
practice.add(
    "miembros-grupo", "Primarios y secundarios de un grupo",
    """Muestra los miembros de un grupo en dos líneas, cada lista ordenada y separada por espacios (`-` si está vacía):

```text
primarios: p13g1 p13g2      (su grupo primario es este, según /etc/passwd)
secundarios: p13g0 p13g3    (lista de /etc/group)
```""",
    usage="GRUPO", cmds="`grep`, `cut`, `tr`, `sort`, `xargs`", structs="`IFS=: read`, `while read` con redirección, `+=`",
    detail="La lista de `/etc/group` **no incluye** a quienes tienen ese grupo como primario. Hay que cruzarla con el GID de `/etc/passwd`.",
    success="Las dos líneas.",
    tests=[T("grupos", "Cruza /etc/group y /etc/passwd.", ok(["p13g"], val="primarios: p13g1 p13g2\nsecundarios: p13g0 p13g3", prepare=_grupo),
             ok(["root"], ref="""printf 'primarios: %s\\nsecundarios: -\\n' "$(awk -F: '$4==0{print $1}' /etc/passwd | sort | xargs)\""""),
             ok(["wheel"], val="primarios: -\nsecundarios: -", prepare="gpasswd -M '' wheel >/dev/null"))],
    errors=[E("uso", 1, "Recibe exactamente un grupo.", "uso: miembros-grupo.sh GRUPO", []),
            E("grupo", 4, "El grupo existe.", "el grupo no existe", ["nadie"], ["whee"])],
    examples=[eg("p13g", prepare=_grupo)], pages=[12, 14],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: miembros-grupo.sh GRUPO" >&2; exit 1; }
linea=$(grep "^$1:" /etc/group)
[[ -z $linea ]] && { echo "el grupo no existe" >&2; exit 4; }
IFS=: read -r nombre clave gid lista <<< "$linea"
primarios=""
while IFS=: read -r usuario c uid g resto; do
  ((g==gid)) && primarios+="$usuario "
done < /etc/passwd
ordena() { tr ' ,' '\n\n' | grep . | sort | xargs; }
p=$(echo "$primarios" | ordena)
s=$(echo "$lista" | ordena)
echo "primarios: ${p:--}"
echo "secundarios: ${s:--}"
exit 0
""")

_empresa = "for u in jefe trabajador1 trabajador2 trabajador3; do userdel -r $u 2>/dev/null; done; groupdel empresa 2>/dev/null; rm -rf /home/trabajo; true"
practice.add(
    "empresa", "Actividad de laboratorio completa",
    """El apartado 8 completo en un script **idempotente**, que se puede ejecutar varias veces sin error:

1. Crea `jefe`, `trabajador1`, `trabajador2` y `trabajador3` si no existen, con contraseña `ASO2026`.
2. Vigencia máxima de 60 días, aviso a 4 días y gracia de 2 días para todos. Los trabajadores solo podrán acceder hasta el 15 de diciembre de 2026.
3. Crea el grupo `empresa` con los cuatro como miembros secundarios y `jefe` como administrador.
4. Crea `/home/trabajo`, de `jefe:empresa`, con todos los permisos para usuario y grupo, ninguno para otros y sticky bit.

Termina mostrando `actividad completada`.""",
    cmds="`useradd`, `chpasswd`, `chage`, `groupadd`, `gpasswd -a -A`, `install -d` o `mkdir`, `chown`, `chmod 1770`", structs="`for u in ...`, comprobación previa con `id` y `getent`",
    detail="`gpasswd -A` y `usermod -G` sin `-a` **sustituyen** la lista completa. El modo `1770` lo revisa `ls -ld`: la `T` mayúscula indica sticky sin ejecución para otros.",
    success="El mensaje final, con el sistema en el estado pedido.",
    tests=[T("cuentas", "Crea cuentas con contraseña.", ok(val="actividad completada", prepare=_empresa, timeout=30),
             probe("""for u in jefe trabajador1 trabajador2 trabajador3; do
  case "$(getent shadow $u | cut -d: -f2)" in ''|'!'*|'*'*) exit 1;; esac
done""")),
           T("politica", "Aplica la política.", probe("""for u in jefe trabajador1 trabajador2 trabajador3; do
  IFS=: read -r n c l mi ma av in ca r <<< "$(getent shadow $u)"
  [ "$ma:$av:$in" = 60:4:2 ] || exit 1
  if [ $u = jefe ]; then [ -z "$ca" ] || exit 1; else [ "$ca" = 20802 ] || exit 1; fi
done""")),
           T("grupo", "Grupo y administrador.", probe("""for u in jefe trabajador1 trabajador2 trabajador3; do
  id -nG $u | grep -qw empresa || exit 1
  [ "$(id -gn $u)" = "$u" ] || exit 1
done
[ "$(getent gshadow empresa | cut -d: -f3)" = jefe ]""")),
           T("directorio", "Directorio compartido.", probe("""[ "$(stat -c '%a %U %G' /home/trabajo)" = '1770 jefe empresa' ]""")),
           T("idempotente", "Se puede volver a ejecutar.", ok(val="actividad completada", timeout=30), probe("""[ "$(stat -c '%a %U %G' /home/trabajo)" = '1770 jefe empresa' ] && [ "$(getent gshadow empresa | cut -d: -f3)" = jefe ]"""))],
    errors=[E("uso", 1, "No recibe argumentos.", "uso: empresa.sh", ["x"]),
            E("permiso", 3, "Se ejecuta como root.", "hay que ser root", dict(args=[], user="learner"))],
    examples=[eg(prepare=_empresa, user="root")], pages=[14, 15], root=True,
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=0)) && error "uso: empresa.sh" 1
((EUID!=0)) && error "hay que ser root" 3
getent group empresa >/dev/null || groupadd empresa
for u in jefe trabajador{1..3}; do
  id "$u" >/dev/null 2>&1 || useradd -m -s /bin/bash "$u"
  echo "$u:ASO2026" | chpasswd
  chage -M 60 -W 4 -I 2 "$u"
  [[ $u != jefe ]] && chage -E 2026-12-15 "$u"
  gpasswd -a "$u" empresa >/dev/null
done
gpasswd -A jefe empresa
mkdir -p /home/trabajo
chown jefe:empresa /home/trabajo
chmod 1770 /home/trabajo
echo "actividad completada"
exit 0
""")
