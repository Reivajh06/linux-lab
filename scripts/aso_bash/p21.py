"""Práctica 2.1: estructuras básicas de Bash, códigos de error y funciones."""
from .framework import E, Practice, T, eg, ok, probe

practice = Practice(
    "2.1", "Programación de scripts en Bash",
    """Los scripts que desarrolla la Práctica 2.1, las dos actividades de laboratorio y los seis ejercicios autónomos: validación de argumentos, `if`, `while`, `(( ))`, `[[ ]]`, `=~`, `$?`, funciones y sustitución de comandos.
    Se aplican las buenas prácticas de la hoja: validar número y formato de argumentos, limitar la salida a lo previsto, usar el canal adecuado y un código distinto para cada error.""",
    setup="""id usuario1 >/dev/null 2>&1 || useradd -m -s /bin/bash -c 'Usuario 1' usuario1
id usuario2 >/dev/null 2>&1 || useradd -m -s /bin/bash -c 'Usuario 2' usuario2
""",
    document=("efd91fbc43b01be04792f99c5f99517d0c31ea71b2991ff5ba99d49ab0ac3a74", "Práctica-2.1"))

_hola = lambda n: "\n".join(f"{k}: hola, mundo" for k in range(1, n + 1))
practice.add(
    "hola", "Mensaje repetido con validación",
    """El script guía de los apartados 3 a 3.2: muestra `k: hola, mundo` tantas veces como indique el argumento, que debe ser un entero entre 2 y 20, **ambos incluidos**.""",
    usage="ITERACIONES", cmds="`echo`", structs='`while ((k<=$1))`, `((k++))`, `if/elif`, `[[ ! $1 =~ ^[0-9]+$ ]]`, `$#`, `$0`, `exit`',
    detail='Sin espacios en `mensaje="hola"`. Cuidado con los límites: la hoja usa `-le 2 || -ge 20`, que **excluye** el 2 y el 20 aunque el mensaje los admita. Aquí deben aceptarse.',
    success="Una línea por iteración.",
    tests=[T("iteraciones", "Repite el mensaje, incluidos los límites.", ok(["3"], val=_hola(3)), ok(["2"], val=_hola(2)), ok(["20"], val=_hola(20)))],
    errors=[E("uso", 1, "Recibe exactamente un argumento.", "uso: hola.sh iteraciones", [], ["3", "4"]),
            E("formato", 2, "El argumento es un entero positivo.", "el argumento debe ser un entero positivo", ["tres"], ["-5"], ["2.5"], [""]),
            E("rango", 3, "El valor está entre 2 y 20.", "el argumento debe estar entre 2 y 20", ["1"], ["21"], ["0"])],
    examples=[eg("3")], pages=[3, 4, 5, 6],
    solution=r"""
#!/bin/bash
if (($#!=1)); then
  echo "uso: hola.sh iteraciones" >&2
  exit 1
elif [[ ! $1 =~ ^[0-9]+$ ]]; then
  echo "el argumento debe ser un entero positivo" >&2
  exit 2
elif (($1<2 || $1>20)); then
  echo "el argumento debe estar entre 2 y 20" >&2
  exit 3
fi
mensaje="hola, mundo"
k=1
while ((k<=$1)); do
  echo "$k: $mensaje"
  ((k++))
done
exit 0
""")

_sal = "rm -rf @D/salida"
practice.add(
    "hola-fichero", "Volcar la salida a un fichero",
    """Apartado 3.4. Añade las líneas `k: hola, mundo` al fichero `salida.txt` dentro de `DIRECTORIO`, creándolo si no existe. Por pantalla muestra solo `N líneas añadidas`.""",
    usage="ITERACIONES DIRECTORIO", cmds="`mkdir -p`, `>>`, `2>/dev/null`", structs='`if ! mkdir -p "$dir" 2>/dev/null; then`, `$?`',
    detail="Un comando es «verdadero» si devuelve 0, así que puedes integrarlo en el `if`. Sin `2>/dev/null` el mensaje de `mkdir` se mezclaría con el tuyo.",
    success="La línea de confirmación; el fichero contiene las líneas.",
    tests=[T("crea", "Crea el directorio y el fichero.", ok(["3", "@D/salida/uno/dos"], val="3 líneas añadidas", prepare=_sal), probe("[ \"$(cat $D/salida/uno/dos/salida.txt)\" = \"1: hola, mundo\n2: hola, mundo\n3: hola, mundo\" ]")),
           T("anade", "Añade sin sobrescribir.", ok(["2", "@D/salida/uno/dos"], val="2 líneas añadidas"), probe("[ \"$(wc -l < $D/salida/uno/dos/salida.txt)\" = 5 ]"))],
    errors=[E("uso", 1, "Recibe iteraciones y directorio.", "uso: hola-fichero.sh ITERACIONES DIRECTORIO", ["3"], []),
            E("formato", 2, "Las iteraciones son un entero positivo.", "el argumento debe ser un entero positivo", ["x", "@D/salida"]),
            E("crear", 4, "El directorio se puede crear.", "no se ha podido crear el directorio", ["3", "/proc/nada/x"], ["3", "/etc/passwd/x"])],
    examples=[eg("3 @D/salida/ejemplo", prepare=_sal)], pages=[7, 8],
    solution=r"""
#!/bin/bash
(($#!=2)) && { echo "uso: hola-fichero.sh ITERACIONES DIRECTORIO" >&2; exit 1; }
[[ ! $1 =~ ^[0-9]+$ ]] && { echo "el argumento debe ser un entero positivo" >&2; exit 2; }
if ! mkdir -p "$2" 2>/dev/null; then
  echo "no se ha podido crear el directorio" >&2
  exit 4
fi
k=1
while ((k<=$1)); do
  echo "$k: hola, mundo" >> "$2/salida.txt"
  ((k++))
done
echo "$1 líneas añadidas"
exit 0
""")

practice.add(
    "suma", "Funciones: error y sumar",
    """Apartado 4. Suma dos enteros positivos y muestra `Resultado: N`. Usa una función `error()` para los errores y una función `sumar()` para el cálculo.""",
    usage="SUMANDO1 SUMANDO2", cmds="`echo`", structs="funciones, `$(( ))`, `$(funcion args)`, `&&`",
    detail="`return` no devuelve resultados: solo un código de 0 a 255. Con `return $(($1+$2))`, 200+100 daría 44. La función debe **imprimir** el resultado y capturarlo con `$(sumar $1 $2)`.",
    success="La línea con el resultado.",
    tests=[T("sumas", "Suma, también por encima de 255.", ok(["2", "3"], val="Resultado: 5"), ok(["200", "100"], val="Resultado: 300"), ok(["0", "0"], val="Resultado: 0"), ok(["100000", "234567"], val="Resultado: 334567"))],
    errors=[E("uso", 1, "Recibe dos sumandos.", "uso: suma.sh sumando1 sumando2", ["1"], [], ["1", "2", "3"]),
            E("formato", 2, "Ambos son enteros positivos.", "los argumentos deben ser enteros positivos", ["a", "1"], ["1", "b"], ["-1", "1"])],
    examples=[eg("200 100")], pages=[9, 10, 11, 12],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
sumar() { echo $(($1+$2)); }
(($#!=2)) && error "uso: suma.sh sumando1 sumando2" 1
[[ ! $1 =~ ^[0-9]+$ || ! $2 =~ ^[0-9]+$ ]] && error "los argumentos deben ser enteros positivos" 2
echo "Resultado: $(sumar "$1" "$2")"
exit 0
""")

_w = "/usr/share/dict/words"
practice.add(
    "letra", "Actividad 1: palabras por letra",
    """Actividad de laboratorio 1. Recibe una única letra, mayúscula o minúscula, y muestra cuántas palabras de `/usr/share/dict/words` empiezan por ella, sin distinguir entre ambas.""",
    usage="LETRA", cmds="`grep -ic`", structs="`[[ =~ ^[A-Za-z]$ ]]`",
    detail='Ancla con `^` y entrecomilla: `grep -ic "^$1"`. Sin el ancla contarías las palabras que **contienen** la letra.',
    success="Un número.",
    tests=[T("letras", "Cuenta sin distinguir mayúsculas.", ok(["a"], ref=f"grep -ic '^a' {_w}"), ok(["A"], ref=f"grep -ic '^a' {_w}"), ok(["z"], ref=f"grep -ic '^z' {_w}"))],
    errors=[E("uso", 1, "Recibe exactamente un argumento.", "uso: letra.sh LETRA", [], ["a", "b"]),
            E("formato", 2, "El argumento es una sola letra.", "el argumento debe ser una letra", ["ab"], ["1"], [""])],
    examples=[eg("z")], pages=[12],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=1)) && error "uso: letra.sh LETRA" 1
[[ ! $1 =~ ^[A-Za-z]$ ]] && error "el argumento debe ser una letra" 2
grep -ic "^$1" /usr/share/dict/words
exit 0
""")

_c = lambda a, b, f="/etc/passwd": f"awk -F: '{{print ${a} \":\" ${b}}}' {f}"
_copia = "cp /etc/passwd @D/copia; chown learner: @D/copia"
practice.add(
    "campos", "Actividad 2: dos campos de un fichero",
    """Actividad de laboratorio 2. Muestra `CAMPO1:CAMPO2` de cada línea de un fichero con formato de `/etc/passwd`. El tercer argumento es opcional; por defecto se usa `/etc/passwd`. Los campos se muestran **en el orden pedido**.""",
    usage="CAMPO1 CAMPO2 [FICHERO]", cmds="`cut`, o `read`", structs="`${3:-/etc/passwd}`, `(( ))`, `||` en condiciones",
    detail="`cut -f7,1` muestra los campos en el orden del fichero, no en el pedido: `cut -d: -f7,1` y `-f1,7` dan lo mismo. Hace falta otro enfoque, como dos `cut` o `read`.",
    success="Una línea por registro.",
    tests=[T("defecto", "Usa /etc/passwd y respeta el orden.", ok(["1", "3"], ref=_c(1, 3)), ok(["7", "1"], ref=_c(7, 1)), ok(["6", "6"], ref=_c(6, 6))),
           T("fichero", "Acepta un fichero.", ok(["1", "7", "@D/copia"], ref=_c(1, 7), prepare=_copia))],
    errors=[E("uso", 1, "Recibe dos o tres argumentos.", "uso: campos.sh CAMPO1 CAMPO2 [FICHERO]", ["1"], [], ["1", "2", "3", "4"]),
            E("formato", 2, "Los campos son números.", "los campos deben ser números", ["a", "1"], ["1", "b"]),
            E("rango", 3, "Los campos están entre 1 y 7.", "los campos deben estar entre 1 y 7", ["0", "1"], ["1", "8"]),
            E("fichero", 4, "El fichero existe.", "el fichero no existe", ["1", "2", "/etc/nada"])],
    examples=[eg("7 1 | head -n 2", note="Respeta el orden pedido.")], pages=[12],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#<2 || $#>3)) && error "uso: campos.sh CAMPO1 CAMPO2 [FICHERO]" 1
[[ ! $1 =~ ^[0-9]+$ || ! $2 =~ ^[0-9]+$ ]] && error "los campos deben ser números" 2
(($1<1 || $1>7 || $2<1 || $2>7)) && error "los campos deben estar entre 1 y 7" 3
fichero=${3:-/etc/passwd}
[[ ! -f $fichero ]] && error "el fichero no existe" 4
paste -d: <(cut -d: -f"$1" "$fichero") <(cut -d: -f"$2" "$fichero")
exit 0
""")

practice.add(
    "existe", "Autónomo 1: ¿existe el fichero?",
    """Muestra `el fichero existe` o `el fichero no existe` (ambos por stdout y con código 0). Resuélvelo en una línea con `&&` y `||`.""",
    usage="FICHERO", cmds="`test -e`", structs='`[[ -e "$1" ]] && ... || ...`',
    detail="Entrecomilla el argumento: un nombre con espacios se partiría en dos con `[ -e $1 ]`.",
    success="Uno de los dos mensajes.",
    tests=[T("rutas", "Distingue rutas reales.", ok(["/etc/passwd"], val="el fichero existe"), ok(["/nada/de/nada"], val="el fichero no existe"), ok(["/etc"], val="el fichero existe"),
             ok(["@D/con espacio"], val="el fichero existe", prepare="touch '@D/con espacio'"), ok(["@D/con otro"], val="el fichero no existe"))],
    errors=[E("uso", 1, "Recibe exactamente un argumento.", "uso: existe.sh FICHERO", [], ["a", "b"])],
    examples=[eg("/etc/passwd"), eg("/nada")], pages=[13],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: existe.sh FICHERO" >&2; exit 1; }
[[ -e $1 ]] && echo "el fichero existe" || echo "el fichero no existe"
exit 0
""")

practice.add(
    "numero", "Autónomo 2: cuántos dígitos",
    """Muestra `no es un número`, `es un número de un dígito`, `es un número de dos dígitos` o `es un número de tres o más dígitos` según la cadena recibida. Todos son resultados normales con código 0.""",
    usage="CADENA", cmds="`echo`", structs="`[[ =~ ]]`, `${#1}`, `if/elif/else` o `case`",
    detail="`${#var}` da la longitud de la cadena. `007` tiene tres dígitos aunque valga 7: no compares su valor numérico.",
    success="Uno de los cuatro mensajes.",
    tests=[T("cadenas", "Clasifica las cadenas.", ok(["abc"], val="no es un número"), ok([""], val="no es un número"), ok(["-5"], val="no es un número"), ok(["1a"], val="no es un número"), ok(["7"], val="es un número de un dígito"), ok(["42"], val="es un número de dos dígitos"), ok(["123"], val="es un número de tres o más dígitos"), ok(["007"], val="es un número de tres o más dígitos"))],
    errors=[E("uso", 1, "Recibe exactamente un argumento.", "uso: numero.sh CADENA", [], ["1", "2"])],
    examples=[eg("42"), eg("abc")], pages=[13],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: numero.sh CADENA" >&2; exit 1; }
if [[ ! $1 =~ ^[0-9]+$ ]]; then
  echo "no es un número"
elif ((${#1}==1)); then
  echo "es un número de un dígito"
elif ((${#1}==2)); then
  echo "es un número de dos dígitos"
else
  echo "es un número de tres o más dígitos"
fi
exit 0
""")

practice.add(
    "consulta", "Autónomo 3: usuario o grupo",
    """Con `-u` indica si existe un usuario y con `-g` si existe un grupo: `existe el usuario X`, `no existe el usuario X`, `existe el grupo X` o `no existe el grupo X`.""",
    usage="-u|-g NOMBRE", cmds="`grep -q`, `getent`", structs="`case`, variables con la ruta y el texto",
    detail="Busca `^nombre:`. Sin los dos puntos, `ad` coincidiría con `adm`; sin `^`, `dm:` también.",
    success="Uno de los cuatro mensajes.",
    tests=[T("usuarios", "Consulta /etc/passwd.", ok(["-u", "root"], val="existe el usuario root"), ok(["-u", "nadie"], val="no existe el usuario nadie"), ok(["-u", "ad"], val="no existe el usuario ad"), ok(["-u", "usuario1"], val="existe el usuario usuario1")),
           T("grupos", "Consulta /etc/group.", ok(["-g", "wheel"], val="existe el grupo wheel"), ok(["-g", "whee"], val="no existe el grupo whee"), ok(["-g", "adm"], val="existe el grupo adm"))],
    errors=[E("uso", 1, "Recibe opción y nombre.", "uso: consulta.sh -u|-g NOMBRE", ["-u"], []),
            E("opcion", 2, "La opción es -u o -g.", "opción no válida", ["-x", "root"])],
    examples=[eg("-u root"), eg("-g nadie")], pages=[13],
    solution=r"""
#!/bin/bash
(($#!=2)) && { echo "uso: consulta.sh -u|-g NOMBRE" >&2; exit 1; }
case $1 in
  -u) fichero=/etc/passwd; tipo=usuario;;
  -g) fichero=/etc/group; tipo=grupo;;
  *) echo "opción no válida" >&2; exit 2;;
esac
if grep -q "^$2:" "$fichero"; then
  echo "existe el $tipo $2"
else
  echo "no existe el $tipo $2"
fi
exit 0
""")

_sec = "getent group p21g >/dev/null || groupadd p21g; gpasswd -M usuario1,usuario2 p21g >/dev/null; getent group p21v >/dev/null || groupadd p21v"
practice.add(
    "secundarios", "Autónomo 4: usuarios secundarios de un grupo",
    """Si el grupo existe, muestra `el grupo existe` y después los usuarios que lo tienen como secundario, uno por línea. Si no tiene ninguno, la segunda línea es `sin usuarios secundarios`.""",
    usage="GRUPO", cmds="`grep`, `cut -d: -f4`, `tr ',' '\\n'`", structs="variable intermedia, `[[ -z ]]`",
    detail="El cuarto campo de `/etc/group` separa los usuarios por comas y **no incluye** a quienes lo tienen como grupo primario.",
    success="La línea de existencia y la lista.",
    tests=[T("grupos", "Muestra la lista real.", ok(["p21g"], val="el grupo existe\nusuario1\nusuario2", prepare=_sec), ok(["p21v"], val="el grupo existe\nsin usuarios secundarios"), ok(["usuario1"], val="el grupo existe\nsin usuarios secundarios"))],
    errors=[E("uso", 1, "Recibe exactamente un grupo.", "uso: secundarios.sh GRUPO", []),
            E("grupo", 4, "El grupo existe.", "el grupo no existe", ["nadie"], ["p21"])],
    examples=[eg("p21g", prepare=_sec)], pages=[13],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: secundarios.sh GRUPO" >&2; exit 1; }
linea=$(grep "^$1:" /etc/group)
[[ -z $linea ]] && { echo "el grupo no existe" >&2; exit 4; }
echo "el grupo existe"
lista=$(echo "$linea" | cut -d: -f4)
if [[ -z $lista ]]; then
  echo "sin usuarios secundarios"
else
  echo "$lista" | tr ',' '\n'
fi
exit 0
""")

practice.add(
    "grupos-de", "Autónomo 5: grupos de un usuario",
    """Si el usuario existe, muestra `el usuario existe` y después sus grupos en una línea `grupos: A B C`, con el grupo primario en primer lugar.""",
    usage="USUARIO", cmds="`id -nG`", structs='`if ! grupos=$(id -nG "$1" 2>/dev/null); then`',
    detail="Puedes asignar y comprobar a la vez: una asignación con `$( )` devuelve el código del comando interior.",
    success="Las dos líneas.",
    tests=[T("usuarios", "Coincide con id.", ok(["root"], ref="""echo 'el usuario existe'; echo "grupos: $(id -nG root)\""""), ok(["usuario1"], ref="""echo 'el usuario existe'; echo "grupos: $(id -nG usuario1)\"""", prepare=_sec), ok(["adm"], ref="""echo 'el usuario existe'; echo "grupos: $(id -nG adm)\""""))],
    errors=[E("uso", 1, "Recibe exactamente un usuario.", "uso: grupos-de.sh USUARIO", []),
            E("usuario", 4, "El usuario existe.", "el usuario no existe", ["nadie"])],
    examples=[eg("root")], pages=[13],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: grupos-de.sh USUARIO" >&2; exit 1; }
if ! grupos=$(id -nG "$1" 2>/dev/null); then
  echo "el usuario no existe" >&2
  exit 4
fi
echo "el usuario existe"
echo "grupos: $grupos"
exit 0
""")

_perfil = """id p21lejos >/dev/null 2>&1 || useradd -M -d /homeless/p21lejos -s /bin/bash p21lejos
id p21sh >/dev/null 2>&1 || useradd -M -d /home/p21sh -s /bin/sh p21sh"""
practice.add(
    "perfil", "Autónomo 6: home y shell de un usuario",
    """Si el usuario existe, muestra tres líneas:

```text
el usuario existe
directorio bajo /home: sí      (o no)
shell /bin/bash: sí            (o no)
```""",
    usage="USUARIO", cmds="`grep`, `cut`", structs='`[[ $home == /home/* ]]`, `IFS=: read`, `<<<`, `&& ... || ...`',
    detail="El comodín de `[[ == ]]` funciona solo **sin comillas** en el patrón. Y `/homeless/x` empieza por `/home` pero no está bajo `/home`: incluye la barra.",
    success="Las tres líneas.",
    tests=[T("usuarios", "Evalúa home y shell.",
             ok(["usuario1"], val="el usuario existe\ndirectorio bajo /home: sí\nshell /bin/bash: sí"),
             ok(["root"], val="el usuario existe\ndirectorio bajo /home: no\nshell /bin/bash: sí"),
             ok(["daemon"], val="el usuario existe\ndirectorio bajo /home: no\nshell /bin/bash: no"),
             ok(["p21lejos"], val="el usuario existe\ndirectorio bajo /home: no\nshell /bin/bash: sí", prepare=_perfil),
             ok(["p21sh"], val="el usuario existe\ndirectorio bajo /home: sí\nshell /bin/bash: no"))],
    errors=[E("uso", 1, "Recibe exactamente un usuario.", "uso: perfil.sh USUARIO", []),
            E("usuario", 4, "El usuario existe.", "el usuario no existe", ["nadie"], ["roo"])],
    examples=[eg("root")], pages=[13],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: perfil.sh USUARIO" >&2; exit 1; }
linea=$(grep "^$1:" /etc/passwd)
[[ -z $linea ]] && { echo "el usuario no existe" >&2; exit 4; }
IFS=: read -r n c u g gecos home shell <<< "$linea"
echo "el usuario existe"
[[ $home == /home/* ]] && echo "directorio bajo /home: sí" || echo "directorio bajo /home: no"
[[ $shell == /bin/bash ]] && echo "shell /bin/bash: sí" || echo "shell /bin/bash: no"
exit 0
""")

_head = lambda f: f"""head -n 1 {f} | sed 's/^#! *//; s/^/interprete: /'; echo 'ejecutable: sí'"""
practice.add(
    "interprete", "Shebang y permiso de ejecución",
    """Apartado 2. Examina un fichero real y muestra su intérprete (lo que sigue a `#!` en la primera línea) y si es ejecutable para quien lanza el script:

```text
interprete: /bin/sh     (ninguno si no hay shebang)
ejecutable: sí          (o no)
```""",
    usage="FICHERO", cmds="`head -n 1`, `file`, `chmod`", structs="`read`, `[[ $linea == '#!'* ]]`, `${linea#\\#!}`, `-x`",
    detail="`./script` obedece al shebang: con `#!/bin/false` no haría nada. Comprueba con `file` cómo cambia la descripción de un fichero según su primera línea.",
    success="Las dos líneas.",
    tests=[T("reales", "Examina scripts del sistema.", ok(["/usr/bin/ldd"], ref=_head("/usr/bin/ldd")), ok(["/usr/bin/gunzip"], ref=_head("/usr/bin/gunzip"))),
           T("sin-shebang", "Reconoce ficheros sin shebang.", ok(["/etc/passwd"], val="interprete: ninguno\nejecutable: no"), ok(["/usr/bin/ls"], val="interprete: ninguno\nejecutable: sí"))],
    errors=[E("uso", 1, "Recibe exactamente un fichero.", "uso: interprete.sh FICHERO", []),
            E("fichero", 4, "El fichero existe y es regular.", "el fichero no existe", ["/nada"], ["/etc"])],
    examples=[eg("/usr/bin/ldd"), eg("/etc/passwd")], pages=[2, 3],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: interprete.sh FICHERO" >&2; exit 1; }
[[ ! -f $1 ]] && { echo "el fichero no existe" >&2; exit 4; }
primera=$(head -c 200 "$1" | head -n 1 | tr -d '\0')
if [[ $primera == '#!'* ]]; then
  interprete=${primera#\#!}
  interprete=${interprete# }
else
  interprete=ninguno
fi
echo "interprete: $interprete"
[[ -x $1 ]] && echo "ejecutable: sí" || echo "ejecutable: no"
exit 0
""")

practice.add(
    "codigo-ls", "Guardar el código de salida",
    """Apartado 3.4. Ejecuta `ls -l` sobre una ruta sin mostrar su salida ni sus errores, y muestra dos líneas: `ls devolvió N` y `la ruta existe` o `la ruta no existe`, según ese código. El script siempre termina con 0.""",
    usage="RUTA", cmds="`ls -l`, `>/dev/null 2>&1`", structs="`$?`, guardar en variable, `(( ))`",
    detail="`$?` es el código del **último** comando: tras un `echo` ya vale 0. Guárdalo en una variable justo después de ejecutar el comando que te interesa.",
    success="Las dos líneas.",
    tests=[T("codigos", "Refleja el código real de ls.", ok(["/etc/passwd"], val="ls devolvió 0\nla ruta existe"), ok(["/nada"], val="ls devolvió 2\nla ruta no existe"))],
    errors=[E("uso", 1, "Recibe exactamente una ruta.", "uso: codigo-ls.sh RUTA", [], ["a", "b"])],
    examples=[eg("/nada")], pages=[7, 8],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: codigo-ls.sh RUTA" >&2; exit 1; }
ls -l "$1" >/dev/null 2>&1
codigo=$?
echo "ls devolvió $codigo"
if ((codigo==0)); then echo "la ruta existe"; else echo "la ruta no existe"; fi
exit 0
""")
