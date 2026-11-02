"""Práctica 1.2: filtros, tuberías, comodines y expresiones regulares."""
from .framework import E, Practice, T, eg, ok, probe

practice = Practice(
    "1.2", "Filtros, tuberías y expresiones regulares",
    """Los ejercicios 7, 8 y 10 de la Práctica 1.2 convertidos en scripts: `cut`, `sort`, `uniq`, `tr`, `grep`, `head`, `tail`, `wc`, `nl`,
    redirecciones y comodines sobre `/etc/passwd`, `/etc`, `/dev`, `/usr/bin` y `/usr/share/dict/words`.
    La actividad del CSV de portátiles se omite porque depende de un fichero externo: está en el curso `aso-p1-2`.""",
    setup="""id usuario1 >/dev/null 2>&1 || useradd -m -s /bin/bash -c 'Usuario 1' usuario1
id usuario2 >/dev/null 2>&1 || useradd -m -s /bin/bash -c 'Usuario 2' usuario2
""",
    document=("a718df4c619ef3b71eff50595d6a45974b3de814e6b0232b857f76c92c496fe4", "Práctica-1.2"))

P = "/etc/passwd"
_a = {
    "1": f"cut -d: -f1,5 {P}", "2": f"cut -b1-3,5-8 {P}", "3": f"tr : ' ' < {P}", "4": f"tail -n +2 {P}",
    "5": f"head -n 3 {P} | sort", "6": f"cut -d: -f1 {P} | sort", "7": f"grep bash {P} | nl", "8": f"grep -c bash {P}",
}
practice.add(
    "filtros-a", "Ejercicios de filtros 1–8",
    """Un único script que resuelve los ejercicios 1 a 8 del apartado 7 sobre `/etc/passwd`, según el número recibido:

1. Primer y quinto campo de cada línea.
2. Bytes del 1 al 3 y del 5 al 8 de cada línea.
3. El fichero con los dos puntos sustituidos por un espacio.
4. Todas las líneas menos la primera.
5. Las tres primeras líneas del fichero, ordenadas alfabéticamente.
6. Los nombres de las cuentas, ordenados alfabéticamente.
7. Listado numerado (con `nl`) de las líneas que contienen `bash`.
8. Cuántas líneas contienen `bash`.""",
    usage="N", cmds="`cut -d -f`, `cut -b`, `tr`, `tail -n +K`, `head`, `sort`, `nl`, `grep -c`", structs="`case ... esac`, `[[ =~ ]]`, función `error()`",
    detail="`tail -n +2` significa «desde la línea 2»; `tail -n 2` son las dos últimas. `grep bash | wc -l` y `grep -c bash` dan lo mismo: usa el comando más sencillo.",
    success="La salida del ejercicio pedido.",
    tests=[T(f"ej{n}", f"Ejercicio {n}.", ok([n], ref=cmd), points=3) for n, cmd in _a.items()],
    errors=[E("uso", 1, "Recibe exactamente un número.", "uso: filtros-a.sh N", [], ["1", "2"]),
            E("formato", 2, "El argumento es un número.", "N debe ser un número", ["dos"]),
            E("rango", 3, "El número está entre 1 y 8.", "N debe estar entre 1 y 8", ["0"], ["9"])],
    examples=[eg("8"), eg("5")], pages=[7, 8],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=1)) && error "uso: filtros-a.sh N" 1
[[ ! $1 =~ ^[0-9]+$ ]] && error "N debe ser un número" 2
(($1<1 || $1>8)) && error "N debe estar entre 1 y 8" 3
case $1 in
  1) cut -d: -f1,5 /etc/passwd;;
  2) cut -b1-3,5-8 /etc/passwd;;
  3) tr : ' ' < /etc/passwd;;
  4) tail -n +2 /etc/passwd;;
  5) head -n 3 /etc/passwd | sort;;
  6) cut -d: -f1 /etc/passwd | sort;;
  7) grep bash /etc/passwd | nl;;
  8) grep -c bash /etc/passwd;;
esac
exit 0
""")

_b = {
    "9": f"grep bash {P} | sort -t: -k3,3n", "10": f"cut -d: -f1,5 {P} | sort -t: -k2", "11": f"grep root {P} | cut -d: -f1,5 | sort -t: -k1,1",
    "12": f"cut -d: -f1,3,5 {P} | sort -t: -k2,2n", "13": f"cut -d: -f1,3,5 {P} | sort -k1.2", "14": f"cut -d: -f4 {P} | sort | uniq -d", "15": f"cut -d: -f7 {P} | sort -u | wc -l",
}
practice.add(
    "filtros-b", "Ejercicios de filtros 9–15",
    """Igual que el anterior, para los ejercicios 9 a 15 del apartado 7 sobre `/etc/passwd`:

9. Líneas que contienen `bash`, ordenadas por UID.
10. Primer y quinto campo, ordenados alfabéticamente por el comentario.
11. Primer y quinto campo de las líneas que contienen `root`, ordenados por nombre.
12. Primer, tercer y quinto campo, ordenados por UID.
13. Primer, tercer y quinto campo, ordenados por nombre ignorando su primer carácter.
14. GID que se usan más de una vez.
15. Número de shells distintos.""",
    usage="N", cmds="`sort -t -k -n`, `sort -k1.2`, `uniq -d`, `sort -u`", structs="`case ... esac`",
    detail="Sin `-n`, `sort` ordena los UID como texto y `10` queda antes que `9`. Tras `cut -d: -f1,3,5` el UID pasa a ser el **segundo** campo. `uniq` solo detecta duplicados consecutivos: ordena antes.",
    success="La salida del ejercicio pedido.",
    tests=[T(f"ej{n}", f"Ejercicio {n}.", ok([n], ref=cmd), points=3) for n, cmd in _b.items()],
    errors=[E("uso", 1, "Recibe exactamente un número.", "uso: filtros-b.sh N", []),
            E("rango", 3, "El número está entre 9 y 15.", "N debe estar entre 9 y 15", ["8"], ["16"], ["x"])],
    examples=[eg("14"), eg("15")], pages=[8],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=1)) && error "uso: filtros-b.sh N" 1
case $1 in
  9) grep bash /etc/passwd | sort -t: -k3,3n;;
  10) cut -d: -f1,5 /etc/passwd | sort -t: -k2;;
  11) grep root /etc/passwd | cut -d: -f1,5 | sort -t: -k1,1;;
  12) cut -d: -f1,3,5 /etc/passwd | sort -t: -k2,2n;;
  13) cut -d: -f1,3,5 /etc/passwd | sort -k1.2;;
  14) cut -d: -f4 /etc/passwd | sort | uniq -d;;
  15) cut -d: -f7 /etc/passwd | sort -u | wc -l;;
  *) error "N debe estar entre 9 y 15" 3;;
esac
exit 0
""")

_words = "/usr/share/dict/words"
_re = {
    "1": "^[aeiou]", "2": "^[a-z]{5}$", "3": "^[a-z]{1,4}$", "4": "[aeiou]{2}", "5": "(ing|ed)$",
    "6": "^[aeiou].*tion$", "7": "^[aeiou][a-z]{0,3}tion$", "8": "^[b-df-hj-np-tv-z]+$", "9": "sh.*sh",
}
practice.add(
    "regex", "Expresiones regulares sobre el diccionario",
    """Muestra **cuántas** líneas de `/usr/share/dict/words` cumplen cada condición del apartado 8, sin distinguir mayúsculas. Una «letra» es de la `a` a la `z`:

1. Empiezan por vocal.
2. Tienen exactamente cinco letras (y nada más).
3. Tienen entre una y cuatro letras (y nada más).
4. Contienen dos vocales consecutivas.
5. Terminan en `ing` o `ed`.
6. Empiezan por vocal y terminan en `tion`.
7. Empiezan por vocal, terminan en `tion`, tienen hasta ocho letras y solo letras.
8. Solo tienen letras y ninguna es vocal.
9. `sh` aparece al menos dos veces.""",
    usage="N", cmds="`grep -E`, `grep -i`, `grep -c`", structs="`case`, `$( )`",
    detail="Sin anclas `^` y `$`, `[a-z]{5}` también coincide dentro de palabras más largas. El diccionario contiene guiones, dígitos y mayúsculas.",
    success="Un número.",
    tests=[T(f"re{n}", f"Condición {n}.", ok([n], ref=f"grep -icE '{rx}' {_words}", timeout=30), points=3) for n, rx in _re.items()],
    errors=[E("uso", 1, "Recibe exactamente un número.", "uso: regex.sh N", []),
            E("rango", 3, "El número está entre 1 y 9.", "N debe estar entre 1 y 9", ["0"], ["10"], ["a"])],
    examples=[eg("2"), eg("7")], pages=[8],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: regex.sh N" >&2; exit 1; }
case $1 in
  1) re='^[aeiou]';;
  2) re='^[a-z]{5}$';;
  3) re='^[a-z]{1,4}$';;
  4) re='[aeiou]{2}';;
  5) re='(ing|ed)$';;
  6) re='^[aeiou].*tion$';;
  7) re='^[aeiou][a-z]{0,3}tion$';;
  8) re='^[b-df-hj-np-tv-z]+$';;
  9) re='sh.*sh';;
  *) echo "N debe estar entre 1 y 9" >&2; exit 3;;
esac
grep -icE "$re" /usr/share/dict/words
exit 0
""")

_count = lambda d, name: f"find {d} -mindepth 1 -maxdepth 1 -not -name '.*' -name '{name}' | wc -l"
practice.add(
    "comodines", "Comodines sobre un directorio real",
    """Dado un directorio, muestra cuántos elementos no ocultos cumplen cada patrón, usando **comodines del shell**:

```text
conf: N      (terminan en .conf)
tres: N      (nombre de exactamente tres caracteres)
a-c: N       (empiezan por a, b o c)
```""",
    usage="DIRECTORIO", cmds="`*`, `?`, `[a-c]`, `shopt -s nullglob`", structs='vectores `f=("$1"/*.conf)`, `${#f[@]}`',
    detail="Si ningún fichero coincide, el shell deja el patrón sin expandir y contarías 1 en lugar de 0. Prueba con `/etc/skel`, que solo contiene ocultos; `nullglob` lo arregla.",
    success="Las tres líneas de recuento.",
    tests=[T("etc", "Cuenta en /etc.", ok(["/etc"], ref=f"""printf 'conf: %s\\ntres: %s\\na-c: %s\\n' "$({_count('/etc', '*.conf')})" "$({_count('/etc', '???')})" "$({_count('/etc', '[a-c]*')})\"""")),
           T("vacio", "Da 0 si no hay coincidencias.", ok(["/etc/skel"], val="conf: 0\ntres: 0\na-c: 0"))],
    errors=[E("uso", 1, "Recibe exactamente un directorio.", "uso: comodines.sh DIRECTORIO", []),
            E("directorio", 4, "El argumento es un directorio.", "no es un directorio", ["/etc/passwd"], ["/nada"])],
    examples=[eg("/etc"), eg("/etc/skel")], pages=[4],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: comodines.sh DIRECTORIO" >&2; exit 1; }
[[ ! -d $1 ]] && { echo "no es un directorio" >&2; exit 4; }
shopt -s nullglob
conf=("$1"/*.conf); tres=("$1"/???); ac=("$1"/[a-c]*)
echo "conf: ${#conf[@]}"
echo "tres: ${#tres[@]}"
echo "a-c: ${#ac[@]}"
exit 0
""")

_clean = "rm -rf @D/temas"
practice.add(
    "expansiones", "Expansión de llaves",
    """Crea en el directorio indicado (y los padres que falten), mediante **expansión de llaves**: `tema1.txt`...`tema5.txt` vacíos, los directorios `practica1`...`practica4` y `memoria1`...`memoria4`,
    y los ficheros `texto1.txt`...`datos4.pdf` (todas las combinaciones de `texto`/`datos`, 1–4 y `txt`/`pdf`). Termina mostrando `ficheros: N` y `directorios: N`, contando lo que realmente hay.""",
    usage="DIRECTORIO", cmds="`touch`, `mkdir -p`, `{a,b}`, `{1..5}`, `find -type`, `wc -l`", structs="`if ! mkdir ...; then`",
    detail="Las llaves generan nombres aunque no existan ficheros: los comodines solo seleccionan lo que ya existe. Por eso `echo {1..3}` funciona en cualquier directorio.",
    success="Las líneas `ficheros: 21` y `directorios: 8`.",
    tests=[T("creacion", "Crea exactamente lo pedido.", ok(["@D/temas/a/b"], val="ficheros: 21\ndirectorios: 8", prepare=_clean),
             probe("cd $D/temas/a/b && [ -f tema5.txt ] && [ -d memoria4 ] && [ -d practica1 ] && [ -f datos4.pdf ] && [ -f texto1.txt ] && [ ! -s tema1.txt ]"))],
    errors=[E("uso", 1, "Recibe exactamente un directorio.", "uso: expansiones.sh DIRECTORIO", []),
            E("crear", 4, "El directorio se puede crear.", "no se ha podido crear el directorio", ["/proc/nada/x"])],
    examples=[eg("@D/temas/ejemplo", prepare=_clean)], pages=[4, 5],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: expansiones.sh DIRECTORIO" >&2; exit 1; }
if ! mkdir -p "$1" 2>/dev/null; then
  echo "no se ha podido crear el directorio" >&2
  exit 4
fi
cd "$1" || exit 4
touch tema{1..5}.txt {texto,datos}{1..4}.{txt,pdf}
mkdir -p {practica,memoria}{1..4}
echo "ficheros: $(find . -type f | wc -l)"
echo "directorios: $(find . -mindepth 1 -type d | wc -l)"
exit 0
""")

practice.add(
    "listado", "Listado recursivo y errores separados",
    """Ejercicio autónomo 1. Guarda un listado recursivo de `/etc` en el fichero `LISTADO` y los errores de acceso en `ERRORES`, sin mostrar nada de `ls` por pantalla.
    Termina con la línea `listado: N, errores: M`, con el número de líneas de cada fichero.""",
    usage="LISTADO ERRORES", cmds="`ls -R`, `>`, `2>`, `wc -l <`", structs="`if ! : > fichero`",
    detail="`wc -l fichero` imprime también el nombre; `wc -l < fichero` solo el número, porque `wc` no sabe de dónde vienen los datos.",
    success="La línea con los dos recuentos.",
    tests=[T("separados", "Separa listado y errores como usuario normal.",
             ok(["@D/listado.txt", "@D/errores.txt"], rx=r"^listado: [0-9]+, errores: [1-9][0-9]*$"),
             probe("[ \"$(wc -l < $D/listado.txt)\" = \"$(ls -R /etc 2>/dev/null | wc -l)\" ] && [ \"$(wc -l < $D/errores.txt)\" = \"$(ls -R /etc 2>&1 >/dev/null | wc -l)\" ] && [ -s $D/errores.txt ]", user="learner"))],
    errors=[E("uso", 1, "Recibe dos ficheros.", "uso: listado.sh LISTADO ERRORES", ["a"], []),
            E("escritura", 4, "Los ficheros de salida se pueden crear.", "no se puede escribir la salida", ["/proc/nada/l", "@D/e.txt"], ["@D/l.txt", "/proc/nada/e"])],
    examples=[eg("@D/listado.txt @D/errores.txt")], pages=[9],
    solution=r"""
#!/bin/bash
(($#!=2)) && { echo "uso: listado.sh LISTADO ERRORES" >&2; exit 1; }
if ! { : > "$1"; } 2>/dev/null || ! { : > "$2"; } 2>/dev/null; then
  echo "no se puede escribir la salida" >&2
  exit 4
fi
ls -R /etc > "$1" 2> "$2"
echo "listado: $(wc -l < "$1"), errores: $(wc -l < "$2")"
exit 0
""")

practice.add(
    "linea", "La línea N de un fichero",
    """Ejercicio autónomo 2, generalizado. Muestra la línea N de un fichero combinando `head` y `tail`. Si no se indica fichero se usa `/etc/passwd`.""",
    usage="N [FICHERO]", cmds="`head -n`, `tail -n 1`, `wc -l`", structs="`${2:-valor}`, `(( ))`",
    detail="Si N supera las líneas del fichero, `head | tail` imprime la **última** línea sin avisar: compruébalo antes con `wc -l`.",
    success="Esa línea.",
    tests=[T("lineas", "Extrae líneas reales.", ok(["6"], ref=f"sed -n 6p {P}"), ok(["1", "/etc/group"], ref="sed -n 1p /etc/group"), ok(["2", "/etc/shells"], ref="sed -n 2p /etc/shells"))],
    errors=[E("uso", 1, "Recibe uno o dos argumentos.", "uso: linea.sh N [FICHERO]", [], ["1", "a", "b"]),
            E("formato", 2, "N es un entero mayor que 0.", "N debe ser un entero positivo", ["x"], ["0"]),
            E("rango", 3, "N no supera las líneas del fichero.", "el fichero no tiene tantas líneas", ["100000"], ["99999", "/etc/shells"]),
            E("fichero", 4, "El fichero existe.", "el fichero no existe", ["1", "/etc/nada"])],
    examples=[eg("6"), eg("2 /etc/shells")], pages=[9],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#<1 || $#>2)) && error "uso: linea.sh N [FICHERO]" 1
[[ ! $1 =~ ^0*[1-9][0-9]*$ ]] && error "N debe ser un entero positivo" 2
fichero=${2:-/etc/passwd}
[[ ! -f $fichero ]] && error "el fichero no existe" 4
(($1>$(wc -l < "$fichero"))) && error "el fichero no tiene tantas líneas" 3
head -n "$1" "$fichero" | tail -n 1
exit 0
""")

practice.add(
    "mayusculas", "Nombres con mayúsculas",
    """Ejercicio autónomo 4. Cuenta los elementos de un directorio cuyo nombre contiene una o más letras mayúsculas. La práctica usa `/boot`, que en este contenedor está vacío: el script debe mostrar `0` y terminar bien.""",
    usage="DIRECTORIO", cmds="`ls`, `grep -c '[A-Z]'`", structs="`if`, código de salida explícito",
    detail="`grep -c` imprime `0` pero **devuelve 1** cuando no encuentra nada. Si el script termina con ese comando, devolverá error en un caso correcto: termina con `exit 0`.",
    success="Un número.",
    tests=[T("directorios", "Cuenta en directorios reales.", ok(["/etc"], ref="ls /etc | grep -c '[A-Z]'"), ok(["/usr/share"], ref="ls /usr/share | grep -c '[A-Z]'"), ok(["/boot"], val="0"))],
    errors=[E("uso", 1, "Recibe exactamente un directorio.", "uso: mayusculas.sh DIRECTORIO", []),
            E("directorio", 4, "El argumento es un directorio.", "no es un directorio", ["/etc/passwd"])],
    examples=[eg("/etc"), eg("/boot")], pages=[9],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: mayusculas.sh DIRECTORIO" >&2; exit 1; }
[[ ! -d $1 ]] && { echo "no es un directorio" >&2; exit 4; }
ls "$1" | grep -c '[A-Z]'
exit 0
""")

practice.add(
    "sin-bash", "Usuarios que no usan /bin/bash",
    """Ejercicio autónomo 5. Lista por orden alfabético los usuarios cuyo shell no es exactamente `/bin/bash`. Con la opción `-c` muestra solo cuántos son.""",
    usage="[-c]", cmds="`grep -v`, `cut`, `sort`, `wc -l`", structs="`case`, tuberías",
    detail="Ancla el patrón con `:/bin/bash$`: un shell como `/usr/local/bin/bash` o un comentario con la palabra `bash` no deben contar como `/bin/bash`.",
    success="Los nombres, o el recuento con -c.",
    tests=[T("listado", "Lista los usuarios correctos.",
             ok(ref=f"awk -F: '$7!=\"/bin/bash\"{{print $1}}' {P} | sort", prepare="id p12otro >/dev/null 2>&1 || useradd -M -s /usr/local/bin/bash -c 'no es /bin/bash' p12otro"),
             ok(["-c"], ref=f"awk -F: '$7!=\"/bin/bash\"{{n++}} END{{print n}}' {P}"))],
    errors=[E("uso", 1, "Recibe como mucho la opción -c.", "uso: sin-bash.sh [-c]", ["-x"], ["-c", "-c"])],
    examples=[eg("-c")], pages=[9],
    solution=r"""
#!/bin/bash
[[ $# -gt 1 || ( $# -eq 1 && $1 != -c ) ]] && { echo "uso: sin-bash.sh [-c]" >&2; exit 1; }
if [[ $1 == -c ]]; then
  grep -vc ':/bin/bash$' /etc/passwd
else
  grep -v ':/bin/bash$' /etc/passwd | cut -d: -f1 | sort
fi
exit 0
""")

practice.add(
    "dispositivos", "Dispositivos de bloque y de carácter",
    """Ejercicio autónomo 6. Muestra cuántos dispositivos de bloque y de carácter hay directamente en `/dev`, a partir del primer carácter de `ls -l`:

```text
bloque: N
caracter: M
```""",
    cmds="`ls -l`, `grep -c '^b'`, `grep -c '^c'`", structs="sustitución de comandos",
    detail="En un contenedor no hay discos, así que `bloque` vale 0 y `grep -c` devuelve 1. Usa el número que imprime, no su código de salida.",
    success="Las dos líneas de recuento.",
    tests=[T("real", "Coincide con /dev.", ok(ref="""printf 'bloque: %s\\ncaracter: %s\\n' "$(find /dev -maxdepth 1 -type b | wc -l)" "$(find /dev -maxdepth 1 -type c | wc -l)\""""))],
    errors=[E("uso", 1, "No recibe argumentos.", "uso: dispositivos.sh", ["x"])],
    examples=[eg()], pages=[9],
    solution=r"""
#!/bin/bash
(($#!=0)) && { echo "uso: dispositivos.sh" >&2; exit 1; }
echo "bloque: $(ls -l /dev | grep -c '^b')"
echo "caracter: $(ls -l /dev | grep -c '^c')"
exit 0
""")

practice.add(
    "sin-comentarios", "Quitar comentarios",
    """Ejercicio autónomo 7. Muestra un fichero de texto sin comentarios: un comentario va desde `#` hasta el final de la línea. El resto de cada línea se conserva, y las líneas que eran solo comentario quedan vacías.
    `/etc/protocols` tiene comentarios a mitad de línea.""",
    usage="FICHERO", cmds="`cut -d'#' -f1`", structs="`[[ -f ]] && [[ -r ]]`",
    detail="`grep -v '#'` borraría también las líneas con datos y un comentario al final, que es justo lo que no se pide.",
    success="El contenido sin comentarios.",
    tests=[T("reales", "Limpia ficheros reales.", ok(["/etc/protocols"], ref="sed 's/#.*//' /etc/protocols"), ok(["/etc/login.defs"], ref="sed 's/#.*//' /etc/login.defs"))],
    errors=[E("uso", 1, "Recibe exactamente un fichero.", "uso: sin-comentarios.sh FICHERO", []),
            E("fichero", 4, "El fichero existe y se puede leer.", "no se puede leer el fichero", ["/etc/nada"], ["/etc/shadow"], ["/etc"])],
    examples=[eg("/etc/default/useradd")], pages=[9],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: sin-comentarios.sh FICHERO" >&2; exit 1; }
[[ ! -f $1 || ! -r $1 ]] && { echo "no se puede leer el fichero" >&2; exit 4; }
cut -d'#' -f1 "$1"
exit 0
""")

_homo = "touch /etc/p12-comun /usr/bin/p12-comun; mkdir -p /etc/p12-solodir; touch /usr/bin/p12-solodir"
practice.add(
    "homonimos", "Ficheros homónimos",
    """Ejercicio autónomo 8. Lista los nombres que corresponden a **ficheros regulares** tanto en `/usr/bin` como en `/etc` (solo su nivel superior), ordenados.""",
    cmds="`find -maxdepth 1 -type f -printf`, `sort`, `uniq -d` o `comm -12`", structs="tuberías, agrupación `{ ...; ...; }`",
    detail="`ls` no distingue un fichero de un directorio con el mismo nombre. El evaluador deja `p12-solodir` como directorio en `/etc`: no debe aparecer.",
    success="Un nombre por línea, ordenados.",
    tests=[T("comunes", "Solo ficheros regulares comunes.", ok(ref="""{ find /usr/bin -maxdepth 1 -type f -printf '%f\\n'; find /etc -maxdepth 1 -type f -printf '%f\\n'; } | LC_ALL=C sort | uniq -d""", prepare=_homo),
             ok(has="p12-comun", prepare=_homo),
             probe("! $S | grep -qx p12-solodir", user="learner"))],
    errors=[E("uso", 1, "No recibe argumentos.", "uso: homonimos.sh", ["x"])],
    examples=[eg(prepare=_homo)], pages=[9],
    solution=r"""
#!/bin/bash
(($#!=0)) && { echo "uso: homonimos.sh" >&2; exit 1; }
{ find /usr/bin -maxdepth 1 -type f -printf '%f\n'; find /etc -maxdepth 1 -type f -printf '%f\n'; } | LC_ALL=C sort | uniq -d
exit 0
""")

practice.add(
    "cuenta-palabra", "Apariciones de una palabra",
    """Ejercicio autónomo 9. Cuenta cuántas veces aparece una palabra completa en un fichero. En una misma línea puede aparecer varias veces: en `/etc/passwd`, la línea de `root` contiene dos.""",
    usage="PALABRA FICHERO", cmds="`grep -o`, `grep -w`, `grep -F`, `wc -l`", structs="comillas dobles en los argumentos",
    detail="`grep -c` cuenta **líneas**, no apariciones. `grep -o` deja una coincidencia por línea. Con `-F` la palabra es literal aunque contenga un punto.",
    success="Un número.",
    tests=[T("palabras", "Cuenta apariciones reales.",
             ok(["root", P], ref=f"tr -c 'A-Za-z0-9_' '\\n' < {P} | grep -cx root"), ok(["tcp", "/etc/protocols"], ref="tr -c 'A-Za-z0-9_' '\\n' < /etc/protocols | grep -cx tcp"),
             ok(["noexiste", P], val="0"), ok(["r..t", P], val="0"))],
    errors=[E("uso", 1, "Recibe palabra y fichero.", "uso: cuenta-palabra.sh PALABRA FICHERO", ["root"], []),
            E("fichero", 4, "El fichero existe.", "el fichero no existe", ["root", "/etc/nada"])],
    examples=[eg("root /etc/passwd")], pages=[9],
    solution=r"""
#!/bin/bash
(($#!=2)) && { echo "uso: cuenta-palabra.sh PALABRA FICHERO" >&2; exit 1; }
[[ ! -f $2 ]] && { echo "el fichero no existe" >&2; exit 4; }
grep -owF -- "$1" "$2" | wc -l
exit 0
""")

_mail = r"printf 'Contactos: hola-mundo_2026@gmail.com y aso@ulpgc.es\nsin correo: a@b y @gnu.org\nchet.ramey@case.edu.\n' > @D/contactos.txt; chown learner: @D/contactos.txt"
practice.add(
    "correos", "Direcciones de correo",
    """Ejercicio autónomo 10. Muestra las direcciones de correo de un fichero, una por línea, en orden de aparición. Debe reconocer direcciones habituales como `hola-mundo_2026@gmail.com`: parte local con letras, dígitos, `.`, `_`, `-`; un `@`; y un dominio con al menos un punto.
    La documentación real de `bash` en `/usr/share/doc/bash/bash.html` contiene varias.""",
    usage="FICHERO", cmds="`grep -oE`", structs="`[[ -f ]]`",
    detail="Dentro de `[...]` el guion debe ir al final para ser literal. Termina el dominio con letras para no capturar el punto final de una frase.",
    success="Una dirección por línea.",
    tests=[T("controlado", "Extrae las direcciones del ejemplo de la práctica.", ok(["@D/contactos.txt"], val="hola-mundo_2026@gmail.com\naso@ulpgc.es\nchet.ramey@case.edu", prepare=_mail)),
           T("real", "Funciona con la documentación real.", ok(["/usr/share/doc/bash/bash.html"], has="bfox@gnu.org"), ok(["/usr/share/doc/bash/bash.html"], has="chet.ramey@case.edu"))],
    errors=[E("uso", 1, "Recibe exactamente un fichero.", "uso: correos.sh FICHERO", []),
            E("fichero", 4, "El fichero existe.", "el fichero no existe", ["/etc/nada"])],
    examples=[eg("@D/contactos.txt", prepare=_mail)], pages=[9],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: correos.sh FICHERO" >&2; exit 1; }
[[ ! -f $1 ]] && { echo "el fichero no existe" >&2; exit 4; }
grep -oE '[[:alnum:]._-]+@[[:alnum:]-]+(\.[[:alnum:]-]+)*\.[[:alpha:]]+' "$1"
exit 0
""")

practice.add(
    "secciones-man", "En qué secciones del manual está",
    """Dado un nombre, muestra las secciones del manual en las que tiene página, una por línea y ordenadas. `passwd` está en la 1 (el comando) y en la 5 (el fichero `/etc/passwd`).""",
    usage="NOMBRE", cmds="`man -aw`, `grep -o`, `sort -u`", structs="`if ! rutas=$(...)`",
    detail="`man -w` da las rutas sin abrir el paginador; `-a` las da todas. La sección está en el directorio: `/usr/share/man/man5/passwd.5.gz`.",
    success="Una sección por línea.",
    tests=[T("paginas", "Encuentra las secciones reales.", ok(["passwd"], val="1\n5"), ok(["ls"], val="1"), ok(["crontab"], ref="man -aw crontab | grep -oE '/man[0-9]+/' | tr -dc '0-9\\n' | sort -u"))],
    errors=[E("uso", 1, "Recibe exactamente un nombre.", "uso: secciones-man.sh NOMBRE", []),
            E("sin-pagina", 4, "El nombre tiene alguna página de manual.", "no hay ninguna página de manual", ["comando-que-no-existe"])],
    examples=[eg("passwd")], pages=[1, 2],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: secciones-man.sh NOMBRE" >&2; exit 1; }
if ! rutas=$(man -aw "$1" 2>/dev/null); then
  echo "no hay ninguna página de manual" >&2
  exit 4
fi
echo "$rutas" | grep -oE '/man[0-9]+/' | tr -dc '0-9\n' | sort -u
exit 0
""")
