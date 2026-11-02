"""Práctica 2.2: read, IFS, vectores, argumentos variables y descriptores."""
from .framework import E, Practice, T, eg, ok, probe

practice = Practice(
    "2.2", "Lectura de ficheros, vectores, argumentos y canales",
    """Lee `/etc/passwd` y otros ficheros reales línea a línea: `while IFS=: read`, `case`, `read -a`, `shift`, `"$@"`, `continue`, y canales propios con `exec`, `read -u` y `>&4`.
    Incluye los scripts guía, las dos actividades de laboratorio y los siete ejercicios autónomos de la Práctica 2.2.""",
    setup="""id usuario1 >/dev/null 2>&1 || useradd -m -s /bin/bash -c 'Usuario 1' usuario1
id usuario2 >/dev/null 2>&1 || useradd -m -s /bin/bash -c 'Usuario 2' usuario2
""",
    document=("afea333146e988d86123c549c02cd1db9401df46157267bbdda835a2946e3f86", "Práctica-2.2"))

P = "/etc/passwd"
practice.add(
    "registro", "Un campo de cada registro con case",
    """Script guía del apartado 1. Muestra `Registro N: VALOR` para cada línea de `/etc/passwd` y termina con `Total de registros: N`. Lee cada línea en **variables con nombre** y elige el campo con `case`.""",
    usage="CAMPO", cmds="`/etc/passwd`", structs="`while IFS=: read nombre clave uid gid gecos directorio shell; do ... done < /etc/passwd`, `case`, `;;`, `esac`",
    detail="Redirige al bloque `while`. Si usas `cat /etc/passwd | while ...`, el bucle corre en un sub-shell y el total saldría 0 al terminar la tubería.",
    success="Una línea por registro y el total.",
    tests=[T("campos", "Muestra el campo y el total correcto.", *[ok([str(n)], ref=f"""awk -F: '{{print "Registro " NR ": " ${n}}} END{{print "Total de registros: " NR}}' {P}""") for n in (1, 3, 5, 7)])],
    errors=[E("uso", 1, "Recibe exactamente un campo.", "uso: registro.sh campo", [], ["1", "2"]),
            E("formato", 2, "El campo es un entero positivo.", "el campo debe ser un entero positivo", ["x"]),
            E("rango", 3, "El campo está entre 1 y 7.", "el campo está fuera del rango de valores aceptado", ["0"], ["8"])],
    examples=[eg("1 | tail -n 3")], pages=[1, 2, 3],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=1)) && error "uso: registro.sh campo" 1
[[ ! $1 =~ ^[0-9]+$ ]] && error "el campo debe ser un entero positivo" 2
registro=0
while IFS=: read -r nombre clave uid gid gecos directorio shell; do
  ((registro++))
  case $1 in
    1) echo "Registro $registro: $nombre";;
    2) echo "Registro $registro: $clave";;
    3) echo "Registro $registro: $uid";;
    4) echo "Registro $registro: $gid";;
    5) echo "Registro $registro: $gecos";;
    6) echo "Registro $registro: $directorio";;
    7) echo "Registro $registro: $shell";;
    *) error "el campo está fuera del rango de valores aceptado" 3;;
  esac
done < /etc/passwd
echo "Total de registros: $registro"
exit 0
""")

_col = lambda *f: "awk -F: '{printf \"Registro %d:\", NR; " + " ".join(f'printf "\\t%s", ${n};' for n in f) + """ print ""} END{print "Total de registros: " NR}' """ + P
practice.add(
    "columnas", "Varios campos con vectores",
    """Apartados 2 y 3. Recibe una lista de campos y muestra por cada línea `Registro N:` seguido de cada campo separado por tabuladores, en el orden pedido y admitiendo repetidos. Termina con `Total de registros: N`. Valida **todos** los campos antes de leer el fichero.""",
    usage="CAMPO...", cmds="`echo -e`, o `printf`", structs='`IFS=: read -a vector`, `${vector[$((campo-1))]}`, `for campo in "$@"`, concatenación',
    detail="Los vectores empiezan en 0, y `${vector[1]}` necesita las llaves: `$vector[1]` imprime el primer elemento seguido del texto `[1]`.",
    success="Una línea por registro y el total.",
    tests=[T("campos", "Admite desorden y repetidos.", ok(["1"], ref=_col(1)), ok(["7", "1"], ref=_col(7, 1)), ok(["1", "5", "1"], ref=_col(1, 5, 1)))],
    errors=[E("uso", 1, "Recibe al menos un campo.", "uso: columnas.sh campos...", []),
            E("formato", 2, "Todos los campos son enteros positivos.", "x no es un entero positivo", ["1", "x"]),
            E("rango", 3, "Todos los campos están entre 1 y 7.", "9 está fuera del rango de valores aceptado", ["1", "9"])],
    examples=[eg("7 1 | head -n 2")], pages=[3, 4, 6, 7],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#<1)) && error "uso: columnas.sh campos..." 1
for campo in "$@"; do
  [[ ! $campo =~ ^[0-9]+$ ]] && error "$campo no es un entero positivo" 2
  (($campo<1 || $campo>7)) && error "$campo está fuera del rango de valores aceptado" 3
done
registro=0
while IFS=: read -r -a vector; do
  ((registro++))
  texto=""
  for campo in "$@"; do
    texto="$texto\t${vector[$(($campo-1))]}"
  done
  echo -e "Registro $registro:$texto"
done < /etc/passwd
echo "Total de registros: $registro"
exit 0
""")

_refc = "wc -l < " + P
practice.add(
    "canales", "Canales propios con exec",
    """Apartado 4. Escribe en `SALIDA` las líneas `Registro N: VALOR` y el total, usando el canal 3 para leer `/etc/passwd` y el 4 para escribir. Por defecto el fichero se sobrescribe; con `-a` se añade al final. Por pantalla muestra solo `N registros escritos`.""",
    usage="[-a] SALIDA CAMPO", cmds="`exec 3<`, `exec 4>`, `exec 4>>`, `exec 3<&-`, `exec 4>&-`", structs='`read -u3`, `>&4`, `shift`',
    detail="`exec 4>fichero` vacía el fichero al abrirlo. El cierre es `4>&-` tanto si se abrió con `>` como con `>>`. El descriptor recuerda la posición de lectura entre un `read -u3` y el siguiente.",
    success="La línea de confirmación; el fichero contiene los registros.",
    tests=[T("sobrescribe", "Sobrescribe por defecto.", ok(["@D/salida.txt", "1"], ref=f"echo \"$(wc -l < {P}) registros escritos\"", prepare="echo viejo > @D/salida.txt; chown learner: @D/salida.txt"),
             probe(f"""[ "$(cat $D/salida.txt)" = "$(awk -F: '{{print "Registro " NR ": " $1}} END{{print "Total de registros: " NR}}' {P})" ]""")),
           T("anade", "Añade con -a.", ok(["-a", "@D/salida.txt", "1"], ref=f"echo \"$(wc -l < {P}) registros escritos\""),
             probe(f"""[ "$(wc -l < $D/salida.txt)" = "$(( ($(wc -l < {P})+1)*2 ))" ]"""))],
    errors=[E("uso", 1, "Recibe salida y campo, con -a opcional delante.", "uso: canales.sh [-a] SALIDA CAMPO", ["x"], [], ["-a", "x"]),
            E("campo", 2, "El campo es un número entre 1 y 7.", "campo no válido", ["@D/salida.txt", "9"], ["@D/salida.txt", "x"]),
            E("salida", 4, "La salida se puede abrir.", "no se puede abrir la salida", ["/proc/nada/x", "1"])],
    examples=[eg("@D/salida.txt 1")], pages=[7, 8, 9],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
modo='>'
if [[ $1 == -a ]]; then modo='>>'; shift; fi
(($#!=2)) && error "uso: canales.sh [-a] SALIDA CAMPO" 1
[[ ! $2 =~ ^[1-7]$ ]] && error "campo no válido" 2
{ : >> "$1"; } 2>/dev/null || error "no se puede abrir la salida" 4
exec 3</etc/passwd
if [[ $modo == '>' ]]; then exec 4>"$1"; else exec 4>>"$1"; fi
registro=0
while IFS=: read -r -u3 -a vector; do
  ((registro++))
  echo "Registro $registro: ${vector[$2-1]}" >&4
done
echo "Total de registros: $registro" >&4
exec 3<&-
exec 4>&-
echo "$registro registros escritos"
exit 0
""")

_ug = lambda cmp, f=P: f"""awk -F: '$3{cmp}$4{{print $1 " " $3 " " $4; n++}} END{{print (n ? "Usuarios: " n : "Ningún usuario cumple la condición")}}' {f}"""
practice.add(
    "uid-gid", "Actividad 1: UID y GID",
    """Actividad de laboratorio 1. Muestra `NOMBRE UID GID` de los usuarios cuyo UID coincide con su GID o, con la opción `-d`, de aquellos en los que difieren. Al final muestra `Usuarios: N` o, si no hay ninguno, `Ningún usuario cumple la condición`.
    Acepta un fichero opcional con el mismo formato; por defecto usa `/etc/passwd`. `/dev/null` es un fichero válido y vacío.""",
    usage="[-d] [FICHERO]", cmds="`/etc/passwd`, `/dev/null`", structs="`shift`, `while IFS=: read`, `(( ))`, contador",
    detail="Procesa la opción y quítala con `shift`: así `$1` pasa a ser el fichero en ambos casos.",
    success="Los usuarios y la línea final.",
    tests=[T("iguales", "UID igual a GID.", ok(ref=_ug("=="))), T("distintos", "UID distinto de GID.", ok(["-d"], ref=_ug("!="))),
           T("ninguno", "Mensaje específico si no hay ninguno.", ok(["/dev/null"], val="Ningún usuario cumple la condición"), ok(["-d", "/dev/null"], val="Ningún usuario cumple la condición"))],
    errors=[E("uso", 1, "Recibe como mucho -d y un fichero.", "uso: uid-gid.sh [-d] [FICHERO]", ["a", "b"], ["-d", "a", "b"]),
            E("fichero", 4, "El fichero existe y se puede leer.", "no se puede leer el fichero", ["/etc/nada"], ["-d", "/etc/nada"])],
    examples=[eg("| tail -n 3"), eg("/dev/null")], pages=[9],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
distinto=0
if [[ $1 == -d ]]; then distinto=1; shift; fi
(($#>1)) && error "uso: uid-gid.sh [-d] [FICHERO]" 1
fichero=${1:-/etc/passwd}
[[ ! -r $fichero ]] && error "no se puede leer el fichero" 4
total=0
while IFS=: read -r nombre clave uid gid resto; do
  if { ((distinto==0)) && ((uid==gid)); } || { ((distinto==1)) && ((uid!=gid)); }; then
    echo "$nombre $uid $gid"
    ((total++))
  fi
done < "$fichero"
if ((total==0)); then echo "Ningún usuario cumple la condición"; else echo "Usuarios: $total"; fi
exit 0
""")

_esp = "mkdir -p '@D/con espacio'; cp /etc/shells '@D/con espacio/mis shells'; chown -R learner: '@D/con espacio'"
_n = lambda name, f: f"""echo "{name}: $(wc -l < {f})\""""
practice.add(
    "lineas", "Actividad 2: líneas de cada fichero",
    """Actividad de laboratorio 2. Muestra `NOMBRE: N` para cada fichero indicado. El primer argumento puede ser un directorio y entonces los ficheros se buscan en él; si no lo es, se buscan en el directorio actual.
    Si un nombre no corresponde a un fichero regular, escribe `no es un fichero: NOMBRE` en stderr, continúa con los demás y termina con el código 4.""",
    usage="[DIRECTORIO] FICHERO...", cmds="`wc -l <`", structs='`shift`, `for f in "$@"`, `continue`, comillas dobles',
    detail='Sin comillas en `"$@"` y en `"$dir/$f"`, un nombre con espacios se parte en dos. `break` terminaría con una lista incompleta y sin explicación: aquí se usa `continue`.',
    success="Una línea por fichero.",
    tests=[T("directorio", "Busca en el directorio indicado.", ok(["/etc", "passwd", "group"], ref=f"{_n('passwd', '/etc/passwd')}; {_n('group', '/etc/group')}")),
           T("actual", "Busca en el directorio actual.", ok(["passwd"], ref=_n("passwd", "/etc/passwd"), cwd="/etc")),
           T("espacios", "Admite nombres con espacios.", ok(["@D/con espacio", "mis shells"], ref=_n("mis shells", "/etc/shells"), prepare=_esp))],
    errors=[E("uso", 1, "Recibe al menos un fichero.", "uso: lineas.sh [DIRECTORIO] FICHERO...", [], ["/etc"]),
            E("parcial", 4, "Cada nombre es un fichero regular; si no, se avisa y se continúa.", "no es un fichero: nada",
              dict(args=["/etc", "nada", "shells"], ref=_n("shells", "/etc/shells")), dict(args=["/etc", "default", "shells"], ref=_n("shells", "/etc/shells"), msg="no es un fichero: default"),
              partial="stdout con los ficheros válidos y stderr con los demás.", eg=False)],
    examples=[eg("/etc passwd group")], pages=[9],
    solution=r"""
#!/bin/bash
(($#<1)) && { echo "uso: lineas.sh [DIRECTORIO] FICHERO..." >&2; exit 1; }
directorio=.
if [[ -d $1 ]]; then
  directorio=$1
  shift
fi
(($#<1)) && { echo "uso: lineas.sh [DIRECTORIO] FICHERO..." >&2; exit 1; }
codigo=0
for fichero in "$@"; do
  if [[ ! -f $directorio/$fichero ]]; then
    echo "no es un fichero: $fichero" >&2
    codigo=4
    continue
  fi
  echo "$fichero: $(wc -l < "$directorio/$fichero")"
done
exit $codigo
""")

_home = """id p22x >/dev/null 2>&1 || useradd -M -d /home2/p22x p22x"""
_hb = lambda d: f"""awk -F: -v d={d}/ 'index($6,d)==1{{print $1; n++}} END{{print (n ? "Usuarios: " n : "Ningún usuario cumple la condición")}}' {P}"""
practice.add(
    "homes-bajo", "Autónomo 1: homes bajo un directorio",
    """Recibe la ruta absoluta de un directorio y muestra los usuarios cuyo directorio personal está bajo él, y al final `Usuarios: N` o `Ningún usuario cumple la condición`.""",
    usage="DIRECTORIO", cmds="`/etc/passwd`", structs='`[[ $1 != /* ]]`, `[[ $home == "$dir"/* ]]`, `${1%/}`',
    detail='La parte entrecomillada del patrón es literal y la `*` no. `/home2/x` no está bajo `/home`: compara con `"$dir"/*`. `${1%/}` quita la barra final, para aceptar también `/home/`.',
    success="Los usuarios y la línea final.",
    tests=[T("reales", "Encuentra los usuarios.", ok(["/home"], ref=_hb("/home"), prepare=_home), ok(["/var"], ref=_hb("/var")), ok(["/home/"], ref=_hb("/home"))),
           T("ninguno", "Mensaje específico si no hay ninguno.", ok(["/mnt"], val="Ningún usuario cumple la condición"))],
    errors=[E("uso", 1, "Recibe exactamente un directorio.", "uso: homes-bajo.sh DIRECTORIO", [], ["/a", "/b"]),
            E("absoluta", 2, "La ruta es absoluta.", "la ruta debe ser absoluta", ["home"]),
            E("directorio", 4, "El directorio existe.", "el directorio no existe", ["/nada"], ["/etc/passwd"])],
    examples=[eg("/var"), eg("/mnt")], pages=[9],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=1)) && error "uso: homes-bajo.sh DIRECTORIO" 1
[[ $1 != /* ]] && error "la ruta debe ser absoluta" 2
[[ ! -d $1 ]] && error "el directorio no existe" 4
dir=${1%/}
total=0
while IFS=: read -r nombre c u g gecos home shell; do
  if [[ $home == "$dir"/* ]]; then
    echo "$nombre"
    ((total++))
  fi
done < /etc/passwd
if ((total==0)); then echo "Ningún usuario cumple la condición"; else echo "Usuarios: $total"; fi
exit 0
""")

_ru = lambda a, b: f"""awk -F: -v a={a} -v b={b} '$3>=a && $3<=b{{print $1 " " $3; n++}} END{{print (n ? "Usuarios: " n : "Ningún usuario cumple la condición")}}' {P}"""
_defs = "$(awk '$1==\"UID_MIN\"{print $2}' /etc/login.defs)"
practice.add(
    "rango-uid", "Autónomo 2: usuarios por rango de UID",
    """Muestra `NOMBRE UID` de los usuarios cuyo UID está en el rango, ambos incluidos, y al final `Usuarios: N` o `Ningún usuario cumple la condición`. Recibe cero o dos argumentos: sin argumentos, el rango sale de `UID_MIN` y `UID_MAX` de `/etc/login.defs`.""",
    usage="[MIN MAX]", cmds="`grep ^UID_MIN`, `tr -s`, `cut`", structs="`(( ))`, `if/else`, sustitución de comandos",
    detail="Ancla con `^UID_MIN`: `/etc/login.defs` tiene también `SUB_UID_MIN` y `SYS_UID_MIN`, y comentarios. `UID_MIN` y su valor están separados por varios espacios.",
    success="Los usuarios y la línea final.",
    tests=[T("defecto", "Lee el rango de /etc/login.defs.", ok(ref=_ru("$(awk '$1==\"UID_MIN\"{print $2}' /etc/login.defs)", "$(awk '$1==\"UID_MAX\"{print $2}' /etc/login.defs)"))),
           T("explicito", "Usa el rango indicado, incluidos los límites.", ok(["0", "12"], ref=_ru(0, 12)), ok(["3", "3"], val="adm 3\nUsuarios: 1")),
           T("ninguno", "Mensaje específico si no hay ninguno.", ok(["70000", "80000"], val="Ningún usuario cumple la condición"))],
    errors=[E("uso", 1, "Recibe cero o dos argumentos.", "uso: rango-uid.sh [MIN MAX]", ["1"], ["1", "2", "3"]),
            E("formato", 2, "Los límites son números.", "los límites deben ser números", ["a", "5"], ["5", "b"]),
            E("rango", 3, "El mínimo no supera al máximo.", "el mínimo supera al máximo", ["9", "1"])],
    examples=[eg(), eg("3 3")], pages=[9, 10],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=0 && $#!=2)) && error "uso: rango-uid.sh [MIN MAX]" 1
if (($#==2)); then
  [[ ! $1 =~ ^[0-9]+$ || ! $2 =~ ^[0-9]+$ ]] && error "los límites deben ser números" 2
  (($1>$2)) && error "el mínimo supera al máximo" 3
  minimo=$1
  maximo=$2
else
  minimo=$(grep '^UID_MIN' /etc/login.defs | tr -s ' \t' ' ' | cut -d' ' -f2)
  maximo=$(grep '^UID_MAX' /etc/login.defs | tr -s ' \t' ' ' | cut -d' ' -f2)
fi
total=0
while IFS=: read -r nombre c uid resto; do
  if ((uid>=minimo && uid<=maximo)); then
    echo "$nombre $uid"
    ((total++))
  fi
done < /etc/passwd
if ((total==0)); then echo "Ningún usuario cumple la condición"; else echo "Usuarios: $total"; fi
exit 0
""")

_sh = lambda s: f"""echo "{s}: $(awk -F: -v s={s} '{{n=split($7,a,"/"); if(a[n]==s)c++}} END{{print c+0}}' {P})\""""
practice.add(
    "cuenta-shell", "Autónomo 3: usuarios por intérprete",
    """Para cada intérprete recibido (`bash`, `sh`, `nologin`...), muestra `NOMBRE: N`, con los usuarios cuyo shell tiene ese nombre sea cual sea su ruta. Cada argumento debe tener solo letras minúsculas. Si no, escribe `no válido: ARG` en stderr, continúa y termina con el código 2.""",
    usage="INTERPRETE...", cmds="`/etc/passwd`, `basename`", structs="`${shell##*/}`, doble bucle o `grep -c`, `continue`",
    detail="`/bin/bash` y `/usr/bin/bash` tienen ambos el nombre `bash`, y `sh` no es `bash`: compara el último componente de la ruta, no busques una subcadena.",
    success="Una línea por intérprete.",
    tests=[T("cuentas", "Cuenta por nombre de intérprete.", ok(["bash"], ref=_sh("bash")), ok(["nologin", "sync"], ref=f"{_sh('nologin')}; {_sh('sync')}"), ok(["zsh"], val="zsh: 0"), ok(["sh"], ref=_sh("sh")))],
    errors=[E("uso", 1, "Recibe al menos un intérprete.", "uso: cuenta-shell.sh INTERPRETE...", []),
            E("parcial", 2, "Cada argumento tiene solo letras minúsculas; si no, se avisa y se continúa.", "no válido: Bash1", dict(args=["Bash1", "sync"], ref=_sh("sync")), partial="stdout con los válidos y stderr con los demás.", eg=False)],
    examples=[eg("bash nologin")], pages=[10],
    solution=r"""
#!/bin/bash
(($#<1)) && { echo "uso: cuenta-shell.sh INTERPRETE..." >&2; exit 1; }
codigo=0
for interprete in "$@"; do
  if [[ ! $interprete =~ ^[a-z]+$ ]]; then
    echo "no válido: $interprete" >&2
    codigo=2
    continue
  fi
  total=0
  while IFS=: read -r n c u g gecos home shell; do
    [[ ${shell##*/} == "$interprete" ]] && ((total++))
  done < /etc/passwd
  echo "$interprete: $total"
done
exit $codigo
""")

_raro = r"printf '  uno con espacios\ndos\\tbarra\ntres\ncuatro sin salto' > @D/raro.txt; chown learner: @D/raro.txt"
practice.add(
    "pares", "Autónomo 4: líneas pares o impares",
    """Muestra las líneas pares (`-p`) o impares (`-i`) de un fichero, sin alterarlas: conserva espacios iniciales y barras invertidas, e incluye una última línea aunque no acabe en salto de línea.""",
    usage="-p|-i FICHERO", cmds="`/etc/passwd`, `printf '%s\\n'`", structs='`while IFS= read -r linea || [[ -n $linea ]]`, `((n%2))`, `case`',
    detail='`IFS=` conserva los espacios iniciales, `-r` conserva las barras y `|| [[ -n $linea ]]` procesa la última línea sin `\\n`: `read` devuelve error, pero la variable sí tiene el texto.',
    success="Las líneas seleccionadas.",
    tests=[T("reales", "Selecciona en ficheros reales.", ok(["-p", P], ref=f"awk 'NR%2==0' {P}"), ok(["-i", P], ref=f"awk 'NR%2==1' {P}"), ok(["-i", "/etc/shells"], ref="awk 'NR%2==1' /etc/shells")),
           T("literal", "No altera las líneas.", ok(["-i", "@D/raro.txt"], val="  uno con espacios\ntres", prepare=_raro), ok(["-p", "@D/raro.txt"], val="dos\\tbarra\ncuatro sin salto"))],
    errors=[E("uso", 1, "Recibe opción y fichero.", "uso: pares.sh -p|-i FICHERO", ["-p"], []),
            E("opcion", 2, "La opción es -p o -i.", "opción no válida", ["-x", P]),
            E("fichero", 4, "El fichero existe.", "el fichero no existe", ["-p", "/etc/nada"])],
    examples=[eg("-i /etc/shells")], pages=[10],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=2)) && error "uso: pares.sh -p|-i FICHERO" 1
case $1 in
  -p) resto=0;;
  -i) resto=1;;
  *) error "opción no válida" 2;;
esac
[[ ! -f $2 ]] && error "el fichero no existe" 4
n=0
while IFS= read -r linea || [[ -n $linea ]]; do
  ((n++))
  ((n%2==resto)) && printf '%s\n' "$linea"
done < "$2"
exit 0
""")

_ent = lambda a, b: f"""awk 'FNR==1{{f++}} {{v[f,FNR]=$0; n[f]=FNR}} END{{m=n[1]>n[2]?n[1]:n[2]; for(i=1;i<=m;i++){{if(i<=n[1])print v[1,i]; if(i<=n[2])print v[2,i]}}}}' {a} {b}"""
practice.add(
    "entrelaza", "Autónomo 5: entrelazar dos ficheros",
    """Muestra alternando una línea de cada fichero. Cuando uno se termina, continúa con las líneas restantes del más largo.""",
    usage="FICHERO1 FICHERO2", cmds="`exec 3<`, `exec 4<`", structs="`read -u3`, `read -u4`, banderas de fin, `while`",
    detail="Este ejercicio es el motivo de tener canales propios: con una sola redirección al `while` no puedes leer de dos ficheros a la vez, porque cada `read` necesita su descriptor y su posición.",
    success="Las líneas intercaladas.",
    tests=[T("reales", "Intercala, en ambos órdenes de longitud.", ok(["/etc/shells", "/etc/default/useradd"], ref=_ent("/etc/shells", "/etc/default/useradd")), ok(["/etc/default/useradd", "/etc/shells"], ref=_ent("/etc/default/useradd", "/etc/shells")), ok([P, "/etc/shells"], ref=_ent(P, "/etc/shells")), ok(["/etc/shells", "/etc/shells"], ref=_ent("/etc/shells", "/etc/shells")))],
    errors=[E("uso", 1, "Recibe dos ficheros.", "uso: entrelaza.sh FICHERO1 FICHERO2", ["a"], []),
            E("fichero", 4, "Ambos ficheros existen.", "el fichero no existe", [P, "/etc/nada"], ["/etc/nada", P])],
    examples=[eg("/etc/shells /etc/default/useradd | head -n 4")], pages=[10],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=2)) && error "uso: entrelaza.sh FICHERO1 FICHERO2" 1
[[ ! -f $1 || ! -f $2 ]] && error "el fichero no existe" 4
exec 3<"$1"
exec 4<"$2"
fin1=0
fin2=0
while ((fin1==0 || fin2==0)); do
  if ((fin1==0)); then
    if IFS= read -r -u3 linea; then printf '%s\n' "$linea"; else fin1=1; fi
  fi
  if ((fin2==0)); then
    if IFS= read -r -u4 linea; then printf '%s\n' "$linea"; else fin2=1; fi
  fi
done
exec 3<&-
exec 4<&-
exit 0
""")

_dirs = """rm -rf @D/d1 @D/d2; mkdir -p @D/d1/sub @D/d2
cp /etc/passwd /etc/group /etc/shells @D/d1
cp /etc/group /etc/hostname @D/d2
mkdir @D/d2/shells; touch @D/d1/.oculto
chown -R learner: @D/d1 @D/d2"""
practice.add(
    "solo-uno", "Autónomo 6: ficheros solo en un directorio",
    """Muestra la ruta completa de los ficheros regulares que están en uno solo de los dos directorios, sin bajar a subdirectorios y sin contar ocultos. Primero los del primer directorio y luego los del segundo, cada grupo ordenado. Un directorio con el mismo nombre que un fichero no cuenta como fichero.""",
    usage="DIRECTORIO1 DIRECTORIO2", cmds="`*`, `-f`", structs='`for f in "$1"/*`, `${f##*/}`, función con parámetros',
    detail='Los comodines dan los nombres ordenados y no incluyen ocultos. Escribe una función que recorra un directorio contra el otro y llámala dos veces.',
    success="Una ruta por línea.",
    tests=[T("reales", "Compara dos directorios.", ok(["@D/d1", "@D/d2"], val="@D/d1/passwd\n@D/d1/shells\n@D/d2/hostname", prepare=_dirs), ok(["@D/d2", "@D/d1"], val="@D/d2/hostname\n@D/d1/passwd\n@D/d1/shells"))],
    errors=[E("uso", 1, "Recibe dos directorios.", "uso: solo-uno.sh DIRECTORIO1 DIRECTORIO2", ["/etc"], []),
            E("directorio", 4, "Ambos son directorios.", "no es un directorio", ["/etc", "/nada"], ["/nada", "/etc"])],
    examples=[eg("@D/d1 @D/d2", prepare=_dirs)], pages=[10],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
solo_en() {
  local ruta
  for ruta in "$1"/*; do
    [[ -f $ruta && ! -f $2/${ruta##*/} ]] && echo "$ruta"
  done
}
(($#!=2)) && error "uso: solo-uno.sh DIRECTORIO1 DIRECTORIO2" 1
[[ ! -d $1 || ! -d $2 ]] && error "no es un directorio" 4
solo_en "$1" "$2"
solo_en "$2" "$1"
exit 0
""")

_inv = """id p22sh >/dev/null 2>&1 || useradd -M -s /usr/local/bin/p22sh p22sh"""
_si = "awk -F: 'NR==FNR{ok[$0]=1;next} !($7 in ok){print $7}' /etc/shells " + P
practice.add(
    "shells-invalidos", "Autónomo 7: intérpretes fuera de /etc/shells",
    """Muestra los intérpretes asignados a usuarios que no aparecen en `/etc/shells`. Por defecto los muestra todos en orden de `/etc/passwd`, aunque se repitan. Con `-u` muestra cada uno una vez, ordenados.""",
    usage="[-u]", cmds="`grep -Fx`, `sort -u`", structs="`while IFS=: read`, tuberías sobre un bucle, función",
    detail="`grep -Fxq` compara la línea **entera** y de forma literal: `/bin/sh` no debe aceptarse por estar contenido en otra línea. Se puede encadenar `done < /etc/passwd | sort -u`.",
    success="Un intérprete por línea.",
    tests=[T("todos", "Muestra todos con repetidos.", ok(ref=_si, prepare=_inv)), T("unicos", "Únicos y ordenados.", ok(["-u"], ref=_si + " | sort -u"), ok(["-u"], has="/usr/local/bin/p22sh"))],
    errors=[E("uso", 1, "Recibe como mucho la opción -u.", "uso: shells-invalidos.sh [-u]", ["-x"], ["-u", "-u"])],
    examples=[eg("-u", prepare=_inv)], pages=[10],
    solution=r"""
#!/bin/bash
[[ $# -gt 1 || ( $# -eq 1 && $1 != -u ) ]] && { echo "uso: shells-invalidos.sh [-u]" >&2; exit 1; }
lista() {
  while IFS=: read -r n c u g gecos home shell; do
    grep -Fxq -- "$shell" /etc/shells || echo "$shell"
  done < /etc/passwd
}
if [[ $1 == -u ]]; then lista | sort -u; else lista; fi
exit 0
""")

practice.add(
    "parte-linea", "Partir una línea con read",
    """Apartado 1. Lee **una línea de la entrada estándar** y la parte en tres variables. Muestra `a=...`, `b=...` y `resto=...`. El separador opcional sustituye a `IFS` solo para esa lectura.""",
    usage="[SEPARADOR]", cmds="`read`", structs="`IFS=/ read a b resto`, `${1:-...}`, `if ! read ...; then`",
    detail="Si sobran campos, la última variable se queda con el resto de la línea. Si faltan, las últimas quedan vacías. `read` devuelve error cuando ya no hay nada que leer.",
    success="Las tres líneas.",
    tests=[T("espacios", "Separa por espacios.", ok(stdin="Esto es una línea más larga\nsegunda\n", val="a=Esto\nb=es\nresto=una línea más larga"), ok(stdin="solo\n", val="a=solo\nb=\nresto=")),
           T("separador", "Admite otro separador.", ok(["/"], stdin="Ahora el/separador es/una barra\n", val="a=Ahora el\nb=separador es\nresto=una barra"), ok([":"], stdin="root:x:0:0:Super User:/root:/bin/bash\n", val="a=root\nb=x\nresto=0:0:Super User:/root:/bin/bash"))],
    errors=[E("uso", 1, "Recibe como mucho un separador.", "uso: parte-linea.sh [SEPARADOR]", ["a", "b"]),
            E("entrada", 4, "Hay al menos una línea en la entrada.", "no hay nada que leer", [])],
    examples=[eg("< /etc/passwd"), eg(": < /etc/passwd")], pages=[1, 2],
    solution=r"""
#!/bin/bash
(($#>1)) && { echo "uso: parte-linea.sh [SEPARADOR]" >&2; exit 1; }
if (($#==1)); then
  IFS=$1 read -r a b resto
else
  read -r a b resto
fi
if (($?!=0)) && [[ -z $a ]]; then
  echo "no hay nada que leer" >&2
  exit 4
fi
echo "a=$a"
echo "b=$b"
echo "resto=$resto"
exit 0
""")
