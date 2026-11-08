---
title: Sintaxis de Bash
folder: Referencia
order: 1
icon: book
tags: [bash, sintaxis, referencia]
---

Esta guía reúne la sintaxis de Bash necesaria para escribir y revisar scripts de las prácticas 1.2–3.2 de ASO. Los ejemplos siguen el criterio del laboratorio: validar argumentos, enviar resultados a stdout y errores a stderr, y terminar con un código de salida coherente.

> [!summary] Lo esencial
> - Empieza con `#!/bin/bash` y ejecuta con `bash script.sh` o con `./script.sh` tras dar permiso de ejecución.
> - Asigna sin espacios: `nombre="Ana Pérez"`; protege las expansiones: `"$nombre"`.
> - Comprueba `$#` antes de acceder a `$1`; recorre los argumentos con `"$@"`.
> - Un estado `0` significa éxito; un estado distinto de cero indica fallo o una condición falsa.
> - Usa `[[ ... ]]` para condiciones de Bash y `(( ... ))` para operaciones con enteros.
> - Lee ficheros con `while IFS= read -r linea; do ...; done < fichero`.
> - Separa datos y diagnósticos; comprueba sintaxis con `bash -n` antes de probar el comportamiento.

## Estructura de un script

El shebang selecciona el intérprete al ejecutar el fichero directamente. Bash distingue mayúsculas y minúsculas; cada comando termina con un salto de línea o con `;`.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `#!/bin/bash` | Primera línea: ejecutar con Bash | `#!/bin/bash` |
| `# comentario` | Comentario fuera de comillas | `# Validar argumentos` |
| `chmod +x fichero` | Añadir permiso de ejecución | `chmod +x saludo.sh` |
| `./fichero` | Ejecutar por su ruta | `./saludo.sh Ana` |
| `bash fichero` | Ejecutar sin necesitar permiso de ejecución | `bash saludo.sh Ana` |
| `source fichero` o `. fichero` | Ejecutar en la shell actual | `source ./config.sh` |
| `comando1; comando2` | Ejecutar secuencialmente | `pwd; date` |
| `comando &` | Lanzar en segundo plano | `sleep 5 &` |

```bash
#!/bin/bash
# Guardar como saludo.sh, con finales de línea LF.
printf '%s\n' 'Hola, mundo'
exit 0
```

### Opciones de ejecución

Estas opciones ayudan a detectar fallos, pero requieren entender qué estados devuelve cada comando. Se desactivan con `set +e`, `set +u` y `set +o pipefail`.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `set -e` | Salir ante ciertos estados no nulos | `set -e` |
| `set -u` | Error al expandir variables no definidas | `set -u` |
| `set -o pipefail` | Una tubería falla si falla algún componente | `set -o pipefail` |

> [!warning] Las opciones no sustituyen la validación
> `set -e` tiene excepciones: pruebas de `if`, `while`, `until`, órdenes negadas con `!` y ciertas posiciones de listas `&&`/`||` y tuberías. También puede dejar de actuar dentro de funciones invocadas en esos contextos. `grep` sin coincidencias devuelve `1`, y `((contador++))` devuelve `1` si el valor anterior era cero: no siempre representan un error del programa.
> Con `set -u`, valida `$#` antes de leer `$1` y usa `${opcional:-}` cuando corresponda. Con `pipefail`, un productor puede fallar por SIGPIPE si `head` cierra pronto la tubería.

## Variables y comillas

Los nombres habituales siguen la forma `[a-zA-Z_][a-zA-Z0-9_]*`. Las variables guardan texto; `$` se usa para expandir su valor, no al asignar.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `var=valor` | Asignar sin espacios alrededor de `=` | `curso=ASO` |
| `$var` | Expandir el valor | `printf '%s\n' "$curso"` |
| `${var}` | Delimitar el nombre | `printf '%s\n' "${curso}_2026"` |
| `'texto'` | Conservar todo literalmente | `literal='$HOME'` |
| `"texto"` | Expandir variables y comandos sin dividir palabras | `ruta="$HOME/Mis apuntes"` |
| `$var` sin comillas | Puede sufrir división por IFS y expansión de comodines | `printf '%s\n' $var` |
| `readonly var=valor` | Impedir posteriores asignaciones | `readonly MAX=20` |
| `local var=valor` | Variable local de una función | `local total=0` |
| `export var=valor` | Incluir la variable en el entorno de procesos hijos | `export LANG=C` |
| `unset var` | Eliminar una variable | `unset temporal` |

```bash
nombre='Ana Pérez'
saludo="Hola, ${nombre}"
printf '%s\n' "$saludo"  # Un argumento, aunque contenga espacios.
printf '%s\n' '$nombre'  # Imprime el texto literal $nombre.
```

> [!warning] Espacios y comillas
> `nombre = Ana` intenta ejecutar un comando llamado `nombre`. `nombre= Ana` ejecuta `Ana` con una asignación de entorno. Para guardar el texto completo, escribe `nombre="Ana Pérez"`; al pasarlo a otro comando, usa `"$nombre"`.

## Parámetros especiales y argumentos

Los parámetros posicionales representan los argumentos del script o de la función actual. Un argumento puede contener espacios o estar vacío: sus límites importan.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `$0` | Nombre o ruta usados para invocar el script | `echo "uso: $0 FICHERO" >&2` |
| `$1` a `$9` | Argumentos primero a noveno | `fichero=$1` |
| `${10}` | Décimo argumento; `$10` significa `${1}0` | `echo "${10}"` |
| `$#` | Número de argumentos | `[[ $# -eq 2 ]]` |
| `$@` | Todos los argumentos; sin comillas pierden protección | `echo $@` |
| `"$@"` | Un elemento por argumento, conservando vacíos y espacios | `printf '<%s>\n' "$@"` |
| `$*` y `"$*"` | Todos; entre comillas, un texto unido por el primer carácter de IFS | `resumen="$*"` |
| `$?` | Estado del último comando o tubería | `estado=$?` |
| `$$` | PID de la shell que ejecuta el script | `echo "PID: $$"` |
| `$!` | PID del último proceso lanzado en segundo plano | `pid=$!` |
| `shift [n]` | Descartar los primeros `n` argumentos; por defecto uno | `shift 2` |

```bash
# Procesar sin perder argumentos que contienen espacios.
while (( $# > 0 )); do
    printf 'Argumento: <%s>\n' "$1"
    shift  # El antiguo $2 pasa a ser $1; $0 no cambia.
done
sleep 1 &
pid=$!  # Guardarlo antes de lanzar otro proceso en segundo plano.
wait "$pid"
```

> [!tip] Reenviar argumentos
> Usa `otra_funcion "$@"` o `otro_script "$@"`. `"$@"` sin argumentos produce cero palabras; `"$*"` produce una cadena vacía. Comprueba que queden suficientes argumentos antes de `shift n`.

## Expansiones

Bash transforma el texto antes de ejecutar el comando. Las llaves se expanden antes que los parámetros; después de las expansiones de parámetros, comandos y aritmética pueden ocurrir división de palabras y expansión de nombres si faltan comillas.

### Expansión de parámetros

Los patrones de recorte y sustitución son patrones de shell, no expresiones regulares. En la tabla, `var` es una variable y `pat` es un patrón.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `${var:-def}` | Usar `def` si no está definida o está vacía; no asigna | `echo "${nombre:-anónimo}"` |
| `${var:=def}` | Como la anterior, asignando a la variable | `: "${destino:=salida.txt}"` |
| `${#var}` | Longitud del texto | `echo "${#nombre}"` |
| `${var#pat}` | Quitar el prefijo coincidente más corto | `echo "${ruta#*/}"` |
| `${var##pat}` | Quitar el prefijo coincidente más largo | `echo "${ruta##*/}"` |
| `${var%pat}` | Quitar el sufijo coincidente más corto | `echo "${ruta%/*}"` |
| `${var%%pat}` | Quitar el sufijo coincidente más largo | `echo "${ruta%%/*}"` |
| `${var/a/b}` | Sustituir la primera coincidencia de `a` por `b` | `echo "${texto/hola/adiós}"` |
| `${var//a/b}` | Sustituir todas las coincidencias | `echo "${texto// /_}"` |
| `${var^^}` y `${var,,}` | Convertir a mayúsculas o minúsculas | `echo "${nombre^^}"` |
| `${var:off:len}` | Subcadena desde índice cero, con longitud opcional | `echo "${nombre:0:3}"` |

```bash
ruta='/home/learner/datos.txt'
base=${ruta##*/}                 # datos.txt
printf '%s\n' "${base%.txt}"     # datos
printf '%s\n' "${ruta: -3}"      # txt; espacio para un índice negativo.
```

> [!note] Vacío y no definido
> Con `:-` y `:=`, vacío también activa el valor alternativo. Sin los dos puntos (`${var-def}`), solo se comprueba si está definida. `:` es un comando que no hace nada y devuelve éxito; permite ejecutar una expansión de asignación.

### Comandos, aritmética, llaves y comodines

Las comillas dobles mantienen las sustituciones como un solo argumento. Los comodines buscan nombres existentes; las llaves generan texto aunque no exista ningún fichero.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `$(comando)` | Capturar stdout, quitando saltos de línea finales | `fecha=$(date +%F)` |
| `$((expresión))` | Expandir el resultado entero | `total=$((2 + 3))` |
| `{a,b}` | Generar alternativas | `printf '%s\n' copia.{txt,bak}` |
| `{1..5}` | Generar una secuencia literal | `printf '%s\n' {1..5}` |
| `*` | Cero o más caracteres de un nombre | `printf '%s\n' *.sh` |
| `?` | Exactamente un carácter | `printf '%s\n' dato?.txt` |
| `[abc]`, `[0-9]`, `[!abc]` | Un carácter de un conjunto, rango o complemento | `printf '%s\n' dato[0-9].txt` |

```bash
dir='/etc'
for f in "$dir"/*.conf; do
    [[ -f $f ]] || continue  # También evita procesar el patrón sin coincidencias.
    printf '%s\n' "$f"
done
```

> [!warning] Límites de las expansiones
> Por defecto, un comodín sin coincidencias queda literal; `shopt -s nullglob` lo elimina. `*` no incluye nombres que empiezan por punto salvo opciones como `dotglob`. `"*.sh"` es literal y `{1..$n}` no genera un rango dinámico: usa un `for` aritmético. `$(...)` se ejecuta en una subshell; sus asignaciones no modifican la shell llamante.

## Aritmética

Bash calcula con enteros de tamaño limitado, sin decimales ni detección general de desbordamiento. Valida el formato y un rango razonable antes de interpretar datos externos como expresiones aritméticas.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `$((expresión))` | Obtener un valor | `mitad=$((7 / 2))` produce `3` |
| `((expresión))` | Evaluar; estado `0` si el valor es distinto de cero | `(( n >= 2 ))` |
| `let "expresión"` | Evaluación aritmética; mismas reglas de estado | `let "n += 1"` |
| `expr ...` | Herramienta externa tradicional; separar operandos | `expr 2 + 3` |
| `+ - * / % **` | Suma, resta, producto, división, resto, potencia | `resto=$((n % 2))` |
| `= += -= *= /= %= ++ --` | Asignar y modificar | `((n += 2))` |
| `== != < <= > >=` | Comparación numérica | `(( a <= b ))` |
| `&&`, `\|\|`, `!`, `cond ? a : b` | Lógica y operador condicional | `mayor=$((a > b ? a : b))` |
| `&`, `\|`, `^`, `~`, `<<`, `>>` | Operadores de bits | `doble=$((n << 1))` |

```bash
n=7
((n += 1))                # Ahora n vale 8; no necesita $ dentro de (( )).
printf '%s\n' "$((n / 3))" # 2: división entera.
expr 3 \* 4               # 12: proteger * para que no sea un comodín.
```

> [!warning] Ceros iniciales y estados
> Un literal como `010` se interpreta en octal; `08` no es válido. Para dígitos no negativos ya validados, `10#$texto` fuerza base diez. No evita desbordamientos. `((0))`, `let "n=0"` y `expr 1 - 1` devuelven estado `1`, aunque el cálculo sea válido; nunca dividas entre cero.

## Condiciones

`test expresión` y `[ expresión ]` son comandos equivalentes; `]` debe ser un argumento separado. `[[ expresión ]]` es sintaxis de Bash y evita división de palabras y expansión de nombres en sus operandos.

### Ficheros, cadenas y números

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `-e ruta`, `-f ruta`, `-d ruta` | Existe, fichero regular, directorio | `[[ -f $fichero ]]` |
| `-r ruta`, `-w ruta`, `-x ruta` | Acceso de lectura, escritura, ejecución | `[[ -r $fichero ]]` |
| `-s ruta`, `-L ruta` | Tamaño mayor que cero, enlace simbólico | `[[ -L $ruta ]]` |
| `-z cadena`, `-n cadena` | Cadena vacía, no vacía | `[ -n "$nombre" ]` |
| `a = b`, `a != b` | Igualdad y desigualdad textual | `[ "$modo" = lectura ]` |
| `a < b`, `a > b` | Orden lexicográfico; en `[[ ]]`, según locale | `[[ $a < $b ]]` |
| `a -eq b`, `a -ne b` | Igualdad y desigualdad numérica | `[ "$n" -eq 3 ]` |
| `a -lt b`, `a -le b` | Menor, menor o igual | `[[ $n -le 20 ]]` |
| `a -gt b`, `a -ge b` | Mayor, mayor o igual | `[[ $n -ge 2 ]]` |
| `a && b`, `a \|\| b`, `! a` | Y, o, negación; evaluación con cortocircuito | `[[ -f $f && -r $f ]]` |

Los tests de fichero suelen seguir enlaces simbólicos; `-L` examina el enlace y detecta uno roto aunque `-e` sea falso. En directorios, `-x` significa permiso de búsqueda/acceso, no que sean programas.

```bash
# if acepta directamente el estado de cualquier comando.
if [[ -f $fichero && -r $fichero ]]; then
    printf 'Fichero legible: %s\n' "$fichero"
elif [[ -d $fichero ]]; then
    echo 'Se esperaba un fichero, no un directorio' >&2
else
    echo 'El fichero no está disponible' >&2
fi
```

> [!warning] Sintaxis de los tests
> `[ $a = b ]` falla si `a` está vacía o contiene espacios/comodines; escribe `[ "$a" = b ]`. Deja espacios en `[ ... ]` y `[[ ... ]]`. En `[ ... ]`, escapa `<` y `>` para evitar redirecciones, o usa `[[ ... ]]`. Para combinar tests portables, escribe `[ ... ] && [ ... ]`, evitando `-a` y `-o`.

### Patrones y expresiones regulares

En `[[ $texto == patrón ]]`, la derecha sin comillas es un patrón de shell. `=~` usa una expresión regular extendida y busca coincidencias parciales salvo que la ancles con `^` y `$`.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `[[ texto == patrón ]]` | Comparar con un patrón | `[[ $nombre == *.sh ]]` |
| `[[ texto == "$literal" ]]` | Comparar con el texto literal | `[[ $nombre == "$esperado" ]]` |
| `[[ texto =~ regex ]]` | Buscar una expresión regular | `[[ $n =~ ^[0-9]+$ ]]` |
| `${BASH_REMATCH[0]}` | Coincidencia completa | `echo "${BASH_REMATCH[0]}"` |
| `${BASH_REMATCH[1]}` | Primer grupo entre paréntesis | `echo "${BASH_REMATCH[1]}"` |

```bash
registro='uid=1000'
regex='^uid=([0-9]+)$'
if [[ $registro =~ $regex ]]; then  # No entrecomillar $regex: sería literal.
    printf 'UID: %s\n' "${BASH_REMATCH[1]}"
fi
```

## Control de flujo

`if`, `while` y `until` deciden según estados de salida. `then` y `do` van tras un salto de línea o `;`; cierran con `fi` y `done` respectivamente.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `if ...; then ...; elif ...; then ...; else ...; fi` | Elegir una rama | `if (( n > 0 )); then echo positivo; fi` |
| `case palabra in ... esac` | Elegir por patrones, en orden | `case $modo in -h) echo ayuda ;; esac` |
| `pat1\|pat2)` y `*)` | Alternativas y patrón por defecto en `case` | `si\|s) echo aceptado ;;` |
| `;;` | Terminar la rama de `case` | `*) echo desconocido ;;` |
| `for x in lista; do ...; done` | Recorrer palabras o argumentos | `for x in "$@"; do echo "$x"; done` |
| `for ((inicio; prueba; paso)); do ...; done` | Bucle de estilo C | `for ((i=0; i<n; i++)); do echo "$i"; done` |
| `while prueba; do ...; done` | Repetir mientras tenga éxito | `while (( n > 0 )); do ((n--)); done` |
| `until prueba; do ...; done` | Repetir mientras falle | `until [[ -e listo ]]; do sleep 1; done` |
| `break [n]`, `continue [n]` | Salir de bucles o pasar a la siguiente iteración | `[[ -f $f ]] \|\| continue` |

```bash
case ${1:-} in
    -h|--help) echo 'uso: script.sh [--help]' ;;
    '') echo 'Sin opción' ;;
    *) echo 'Opción desconocida' >&2; exit 1 ;;
esac
for palabra in uno 'dos palabras'; do  # Lista explícita.
    printf '%s\n' "$palabra"
done
for i in {1..3}; do echo "$i"; done   # Rango literal.
for ((i=0; i<3; i++)); do             # Límite calculable en ejecución.
    (( i == 1 )) && continue
    printf '%s\n' "$i"
done
```

> [!note] Composición y alcance
> `a && b` ejecuta `b` si `a` tiene éxito; `a || b` lo hace si falla. `a && b || c` también ejecuta `c` si falla `b`, por lo que no sustituye siempre a `if/else`. `( comandos )` crea una subshell; `{ comandos; }` agrupa en la shell actual. `comando &` permite continuar sin esperar; usa `wait` para recoger su estado.

## Funciones

Una función se define antes de invocarla y se llama como un comando. Sus `$1`, `$2`, `$#` y `"$@"` son los de esa llamada; `$0` sigue siendo el del script.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `nombre() { comandos; }` | Definir una función | `saludar() { echo "Hola, $1"; }` |
| `nombre argumentos` | Invocar | `saludar 'Ana Pérez'` |
| `local var=valor` | Evitar modificar la variable del llamante | `local resultado=0` |
| `return N` | Terminar la función con un estado | `return 1` |
| `exit N` | Terminar el script entero | `exit 2` |
| `echo valor` y `$(funcion)` | Producir texto y capturarlo | `resultado=$(sumar 2 3)` |

```bash
sumar() {
    local a=$1 b=$2  # Aquí se presupone que el llamante validó ambos enteros.
    echo "$((a + b))"
    return 0
}
resultado=$(sumar 200 100)
printf 'Resultado: %s\n' "$resultado"  # 300, sin limitarlo a un estado.
```

> [!tip] Valores y estados son canales distintos
> `return` comunica éxito o fallo, no devuelve un resultado numérico general; los estados se reducen al intervalo 0–255. Sin `return`, cuenta el último comando. Envía diagnósticos a stderr para no capturarlos con `$(...)`; para texto arbitrario, prefiere `printf '%s\n' "$valor"` a `echo "$valor"`. Separa `local resultado` de `resultado=$(comando)` si necesitas comprobar el estado del comando.

## Vectores indexados y asociativos

Los vectores indexados usan índices enteros desde cero y pueden tener huecos. Los asociativos usan claves de texto y requieren Bash 4 o posterior, igual que `${var^^}` y `${var,,}`.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `arr=(a b)` | Crear un vector indexado | `arr=(uno 'dos palabras')` |
| `${arr[0]}` | Obtener un elemento | `echo "${arr[0]}"` |
| `"${arr[@]}"` | Expandir cada elemento como una palabra | `printf '%s\n' "${arr[@]}"` |
| `${#arr[@]}` | Número de elementos, no el índice máximo | `echo "${#arr[@]}"` |
| `"${!arr[@]}"` | Índices o claves existentes | `printf '%s\n' "${!arr[@]}"` |
| `arr+=(valor)` | Añadir al final | `arr+=('tres palabras')` |
| `unset 'arr[1]'` | Borrar sin renumerar los demás índices | `unset 'arr[1]'` |
| `declare -A mapa` | Declarar un vector asociativo | `declare -A capital=([España]=Madrid)` |

```bash
arr=(a b)
arr+=('c d')
for i in "${!arr[@]}"; do
    printf '%s: %s\n' "$i" "${arr[$i]}"
done
declare -A estado=([ana]=activo [luis]=inactivo)
printf '%s\n' "${estado[ana]}"  # El recorrido asociativo no garantiza orden.
```

## Lectura de entrada y ficheros

`read` lee de stdin salvo que indiques otro descriptor. `IFS` define los separadores de campos; `-r` evita interpretar barras inversas como escapes.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `IFS= read -r var` | Leer una línea preservando espacios y barras | `IFS= read -r linea` |
| `IFS=: read -r a b` | Separar campos; el último recibe el resto | `IFS=: read -r usuario resto` |
| `read -r -a arr` | Leer campos en un vector indexado | `read -r -a palabras <<< 'uno dos tres'` |
| `read -r -p texto var` | Pregunta interactiva; el aviso se muestra si la entrada es un terminal | `read -r -p 'Nombre: ' nombre` |

```bash
total=0
# Leer campos de /etc/passwd sin una tubería de entrada.
while IFS=: read -r usuario clave uid gid gecos casa shell; do
    printf '%s: %s\n' "$usuario" "$shell"
    ((total += 1))
done < /etc/passwd
printf 'Total: %s\n' "$total"  # La variable sigue disponible fuera del bucle.
```

> [!note] Fin de fichero
> `read` devuelve un estado no nulo al llegar a EOF, incluso si ha recogido una última línea sin salto final. Para conservarla, usa `while IFS= read -r linea || [[ -n $linea ]]; do ...; done < "$fichero"`. La asignación `IFS=:` delante de `read` afecta solo a esa orden. Evita preguntas interactivas cuando el ejercicio exige únicamente salida evaluable.

## Redirecciones, descriptores y tuberías

Los descriptores habituales son `0` (stdin), `1` (stdout) y `2` (stderr). Una tubería conecta stdout del comando izquierdo con stdin del derecho; stderr sigue su propio camino.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `> fichero`, `>> fichero` | Crear/truncar, o añadir stdout | `echo dato >> salida.txt` |
| `< fichero` | Tomar stdin de un fichero | `wc -l < /etc/passwd` |
| `2> fichero`, `2>> fichero` | Redirigir o añadir stderr | `ls /no-existe 2> errores.log` |
| `2>&1` | Duplicar el destino actual de stdout en stderr | `comando > todo.log 2>&1` |
| `&> fichero` | Redirigir stdout y stderr en Bash | `comando &> todo.log` |
| `/dev/null` | Descartar salida, o leer EOF como entrada | `comando > /dev/null 2>&1` |
| `a \| b` | Conectar dos comandos | `cut -d: -f1 /etc/passwd \| sort` |
| `<<EOF` | Entrada multilínea hasta un delimitador | `cat <<EOF` |
| `<<< texto` | Entrada desde una cadena, añadiendo un salto final | `read -r nombre <<< 'Ana'` |
| `exec 3< fichero` | Abrir un descriptor de lectura persistente | `exec 3< /etc/passwd` |
| `read -r -u 3 var` | Leer del descriptor indicado | `IFS= read -r -u 3 linea` |
| `exec 3<&-`, `exec 3>&-` | Cerrar el descriptor indicado; formas de entrada y salida | `exec 3<&-` |

```bash
# Here-doc con expansión; EOF debe ir solo y sin sangría al cerrar.
nombre=Ana
cat <<EOF
Hola, $nombre
EOF
# Con <<'EOF', el contenido sería literal, sin expandir $nombre ni $(...).
if exec 3< /etc/passwd; then
    IFS= read -r -u 3 linea
    printf '%s\n' "$linea"
    exec 3<&-  # Cerrar después de leer; para salida se usa habitualmente 3>&-.
fi
```

> [!warning] El orden cambia el resultado
> `comando > salida.log 2>&1` reúne ambas salidas en el fichero. `comando 2>&1 > salida.log` deja stderr en el destino anterior de stdout. Por defecto, cada componente de una tubería se ejecuta en una subshell: las asignaciones de `cat fichero | while ...` normalmente no persisten. Redirige al bucle con `done < fichero` si necesitas conservar contadores.

## Códigos de salida y errores

El estado es un entero de 0 a 255: `0` significa éxito. En las prácticas, usa códigos distintos para cada clase de error indicada y respeta exactamente los mensajes y canales pedidos.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `exit N` | Terminar con un estado explícito | `exit 2` |
| `$?` | Consultar inmediatamente el último estado | `estado=$?` |
| `echo "..." >&2` | Escribir un diagnóstico en stderr | `echo 'Fichero no válido' >&2` |
| `if comando; then ...; else ...; fi` | Actuar según éxito o fallo | `if mkdir -p -- "$dir"; then echo creado; fi` |
| `${PIPESTATUS[@]}` | Estados individuales de la última tubería de Bash | `estados=("${PIPESTATUS[@]}")` |

```bash
# Patrón mínimo: número de argumentos antes de acceder a $1.
if [[ $# -ne 1 ]]; then
    echo "uso: $0 FICHERO" >&2
    exit 1
fi
if cp -- "$1" "$1.bak"; then
    printf 'Copia creada\n'
else
    estado=$?  # Capturar antes de ejecutar echo, printf u otra orden.
    echo "No se pudo copiar; estado original: $estado" >&2
    exit 4
fi
```

> [!note] Estados de tuberías y negación
> Sin `pipefail`, `$?` tras una tubería corresponde al último comando; con esa opción, al fallo situado más a la derecha, o `0` si todos tuvieron éxito. Guarda `PIPESTATUS` inmediatamente: otra orden lo sustituye. Tras `if ! comando; then`, `$?` refleja la negación, no el fallo original. Los estados `126` y `127` suelen indicar que no se pudo ejecutar una orden o que no se encontró.

## Depuración

Comprueba primero la sintaxis y después ejecuta con entradas válidas, límites y errores. Verifica por separado stdout, stderr y el estado final; `bash -n` no comprueba la lógica ni la existencia de ficheros.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `bash -n fichero` | Analizar sin ejecutar | `bash -n repetir.sh` |
| `bash -x fichero argumentos` | Ejecutar mostrando comandos expandidos en stderr | `bash -x repetir.sh 2 hola` |
| `set -x`, `set +x` | Activar/desactivar trazas dentro del script | `set -x` |
| `shellcheck fichero` | Análisis estático, si está instalado | `shellcheck repetir.sh` |

```bash
bash -n repetir.sh  # Primero, detectar errores de sintaxis.
bash repetir.sh 2 hola > salida.txt 2> errores.txt
estado=$?
printf 'Estado: %s\n' "$estado"
command -v shellcheck >/dev/null && shellcheck repetir.sh
```

> [!tip] Leer las trazas
> `bash -x` permite ver qué valores reciben las órdenes y por qué se entra en una rama. Sus trazas pueden mostrar datos sensibles y alterar el stderr esperado: desactívalas para entregar el script.

## Plantilla de script

Este script completo repite un mensaje entre 2 y 20 veces, incluidos ambos límites. Acepta enteros decimales sin ceros iniciales; valida cantidad, formato, rango y mensaje antes de producir resultados. Usa `-u` y `pipefail`, con comprobaciones explícitas de error.

| Sintaxis | Significado | Ejemplo |
| --- | --- | --- |
| `./repetir.sh N MENSAJE` | Invocación con dos argumentos | `./repetir.sh 3 'Hola, mundo'` |
| `exit 1/2/3/4` | Errores de uso, formato, rango o mensaje | `./repetir.sh tres hola` termina con `2` |

```bash
#!/bin/bash
set -u
set -o pipefail

error() {
    local codigo=$1
    local mensaje=$2
    printf '%s\n' "$mensaje" >&2
    exit "$codigo"
}

# Comprobar cantidad antes de expandir parámetros con set -u.
if [[ $# -ne 2 ]]; then
    error 1 "uso: $0 ITERACIONES MENSAJE"
fi

# No interpretar como aritmética una entrada de formato desconocido.
if [[ ! $1 =~ ^(0|[1-9][0-9]*)$ ]]; then
    error 2 'las iteraciones deben ser un entero sin ceros iniciales'
fi

# Rechazar longitudes grandes antes de calcular, evitando desbordamientos.
if (( ${#1} > 2 )) || (( $1 < 2 || $1 > 20 )); then
    error 3 'las iteraciones deben estar entre 2 y 20'
fi
if [[ -z $2 ]]; then
    error 4 'el mensaje no puede estar vacío'
fi

readonly iteraciones=$1
readonly mensaje=$2
for ((i=1; i<=iteraciones; i++)); do
    printf '%d: %s\n' "$i" "$mensaje"
done
exit 0
```

> [!example] Pruebas de la plantilla
> Guarda el bloque como `repetir.sh` y ejecuta `chmod +x repetir.sh`. `./repetir.sh 2 'Hola, mundo'` imprime dos líneas y termina con `0`; sin argumentos termina con `1`, con `tres hola` con `2`, con `21 hola` con `3` y con `2 ''` con `4`. En los errores, stdout queda vacío y el diagnóstico va a stderr.

## Errores frecuentes

- Escribir `x = 3`: usa `x=3`; los espacios separan palabras del comando.
- Pasar `$ruta`, `$@` o `${arr[@]}` sin comillas: usa `"$ruta"`, `"$@"` y `"${arr[@]}"` para conservar los argumentos.
- Usar `[ $a = b ]`: escribe `[ "$a" = b ]` o `[[ $a == b ]]`, con espacios alrededor de los delimitadores.
- Leer `$1` antes de validar `$#`, especialmente con `set -u`.
- Confundir `=` textual con `-eq` numérico, o escribir `[ "$n" > 2 ]` y crear una redirección.
- Entrecomillar la expresión de `=~` o confundir regex con comodines de `case` y `[[ ... == ... ]]`.
- Devolver una suma mediante `return`: imprime el valor y captura con `$(...)`.
- Ejecutar otra orden antes de guardar `$?` o `PIPESTATUS`; ambos cambian con la ejecución.
- Perder contadores al alimentar un `while` mediante tubería; usa redirección de entrada.
- Hacer `for f in $(ls ...)`: usa comodines o vectores y protege cada nombre.
- Esperar decimales, ignorar el octal de los ceros iniciales o confiar en `set -e` como gestión completa de errores.
- Añadir mensajes de depuración a stdout o entregar trazas `set -x` en stderr.
- Ejecutar con `sh script.sh` un script que necesita Bash, o guardar con CRLF y romper el shebang.

## Chuleta rápida

```bash
#!/bin/bash
# Argumentos, variables y estado de salida.
[[ $# -eq 1 ]] || { echo "uso: $0 FICHERO" >&2; exit 1; }
fichero=$1; nombre=${fichero##*/}
[[ -f $fichero && -r $fichero ]] || { echo 'Fichero inválido' >&2; exit 4; }
printf 'Nombre: %s\n' "$nombre"
for arg in "$@"; do printf '<%s>\n' "$arg"; done
total=0
while IFS= read -r linea || [[ -n $linea ]]; do
    printf '%s\n' "$linea"
    ((total += 1))
done < "$fichero"
printf 'Líneas: %s\n' "$total"
exit 0
```
