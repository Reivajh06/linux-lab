---
title: 2.2 · Lectura, vectores, argumentos y canales
folder: Prácticas ASO
order: 22
icon: brackets
tags: [read, vectores, descriptores]
---

Esta práctica enseña a recorrer ficheros de texto con Bash, separar sus campos y seleccionar datos mediante variables o vectores. También trabaja los argumentos y opciones de un script, la validación de entradas y los descriptores para leer o escribir varios ficheros sin mezclar resultados y errores.

> [!summary] Lo esencial
> - Usa `while IFS= read -r` para conservar el texto y `IFS=:` para separar registros.
> - Redirige el fichero al bucle completo si necesitas conservar su contador después.
> - Los vectores empiezan en cero: el campo 1 corresponde a `${vector[0]}`.
> - Recorre `"$@"` con comillas; `shift` elimina el primer argumento pendiente.
> - Abre canales con `exec`, lee con `read -u` y cierra cada descriptor al terminar.
> - Resultados a stdout, errores a stderr y `exit 0` al terminar correctamente.

## Leer líneas y registros con read

`read` toma una línea de stdin y asigna sus campos a variables. `IFS` decide los separadores; si sobran campos, la última variable recibe el resto, y si faltan, las variables restantes quedan vacías.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `read -r` | Lee sin interpretar barras invertidas | `read -r nombre` |
| `IFS= read -r` | Conserva espacios iniciales y finales | `IFS= read -r linea` |
| `IFS=: read -r` | Divide una línea por dos puntos | `IFS=: read -r nombre clave uid resto` |
| `done < fichero` | Alimenta todo el bucle desde un fichero | `done < /etc/passwd` |
| `printf '%s\n'` | Imprime texto literalmente y añade un salto | `printf '%s\n' "$linea"` |
| `wc -l < fichero` | Cuenta saltos de línea sin imprimir la ruta | `wc -l < "notas clase.txt"` |

### Registros de cuentas y grupos

En `/etc/passwd` los siete campos son `nombre:clave:uid:gid:gecos:directorio:shell`; GECOS contiene información descriptiva. En `/etc/group` el formato es `grupo:clave:gid:usuarios`.

```bash
# Mostrar cuentas cuyo UID coincide con su GID
total=0
while IFS=: read -r nombre clave uid gid gecos casa shell; do
    if (( uid == gid )); then
        printf '%s:%s:%s\n' "$nombre" "$uid" "$gid"
        ((total++))
    fi
done < /etc/passwd
printf 'Total: %d\n' "$total"
```

> [!warning] El contador y la tubería
> En Bash, `cat fichero | while ...` normalmente ejecuta el bucle en un subshell: los cambios del contador no llegan al shell principal. Usa `while ...; do ...; done < fichero` cuando necesites el valor después.

### Conservar el texto y tratar EOF

`read` devuelve un estado distinto de cero al llegar a EOF. Una última línea sin salto puede dejar texto en la variable aunque la lectura no termine correctamente; la condición adicional permite procesarla.

```bash
# Mostrar las líneas pares, incluyendo una última línea sin salto
n=0
while IFS= read -r linea || [[ -n $linea ]]; do
    ((n++))
    if (( n % 2 == 0 )); then
        printf '%s\n' "$linea"
    fi
done < "notas clase.txt"
```

Para impares usa `n % 2 == 1`; la primera línea es la número 1. Para seleccionar una línea concreta, compara el contador con la posición pedida y usa `break` tras imprimirla.

> [!note] Líneas vacías y conteos
> Una línea vacía también se lee correctamente: no confundas texto vacío con EOF. `wc -l` cuenta saltos de línea; el bucle con la condición adicional también procesa un fragmento final sin salto, por lo que los conteos pueden diferir en ese caso.

## Vectores y selección de campos

`read -a` reparte una línea en un vector indexado desde cero. Para seleccionar campos numerados desde 1, resta uno al número solicitado; al pedir varios campos, conserva el orden y las repeticiones de los argumentos.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `read -r -a vector` | Guarda los campos en un vector | `IFS=: read -r -a vector < /etc/passwd` |
| `${vector[i]}` | Obtiene el elemento de índice `i` | `printf '%s\n' "${vector[2]}"` |
| `${#vector[@]}` | Obtiene el número de elementos | `n=${#vector[@]}` |
| `"${vector[@]}"` | Expande cada elemento por separado | `printf '%s\n' "${vector[@]}"` |
| `case ... esac` | Selecciona una rama por patrón | `case $modo in nombre) valor=$nombre;; esac` |

```bash
# Fragmento: los argumentos ya están validados como campos entre 1 y 7
registro=0
while IFS=: read -r -a vector; do
    ((registro++))
    printf 'Registro %d:' "$registro"
    for campo in "$@"; do
        indice=$((10#$campo - 1))
        printf '\t%s' "${vector[indice]}"
    done
    printf '\n'
done < /etc/passwd
printf 'Total de registros: %d\n' "$registro"
```

Para un fichero de una línea con palabras separadas por espacios, `read -r -a vector < "$fichero"` utiliza los separadores habituales. Comprueba que `${#vector[@]}` sea mayor que cero antes de consultar el último elemento, `${vector[n-1]}`.

```bash
# Alternativa con variables con nombre: modo validado previamente
case $modo in
    nombre) valor=$nombre ;;
    uid)    valor=$uid ;;
    shell)  valor=$shell ;;
esac
printf '%s\n' "$valor"
```

> [!warning] Llaves y separadores
> Escribe `${vector[1]}`, no `$vector[1]`: esta última forma expande `$vector` y añade el texto `[1]`. `IFS=:` separa por dos puntos; `IFS=` conserva la línea completa y no sirve para dividirla en campos.

## Argumentos, opciones y validación

Valida la cantidad de argumentos, los formatos y las condiciones del ejercicio antes de producir resultados o abrir una salida que pueda sobrescribirse. Los scripts usan `#!/bin/bash` y permisos de ejecución; cada enunciado concreta sus mensajes, opciones y códigos de error.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `$#`, `$1`, `$2` | Cantidad y posiciones de argumentos | `(( $# == 2 ))` |
| `for f in "$@"` | Recorre argumentos conservando espacios | `for f in "$@"; do printf '%s\n' "$f"; done` |
| `shift` | Descarta `$1` y desplaza los restantes | `directorio=$1; shift` |
| `[[ -f ... && -r ... ]]` | Comprueba fichero regular y legible | `[[ -f $f && -r $f ]]` |
| `[[ -d ... ]]` | Comprueba que es un directorio | `[[ -d $1 ]]` |
| `[[ ... =~ ... ]]` | Valida mediante una expresión regular | `[[ $campo =~ ^[0-9]+$ ]]` |
| `continue`, `break` | Salta una iteración o termina el bucle | `continue` |
| `>&2`, `exit` | Envía errores a stderr y fija el estado | `printf 'Error\n' >&2; exit 2` |
| `chmod u+x` | Da permiso de ejecución al propietario | `chmod u+x lineas.sh` |

### Directorio opcional y errores parciales

```bash
#!/bin/bash
# Variante de lineas.sh con directorio opcional y error parcial 4
directorio=.
if (( $# > 0 )) && [[ -d $1 ]]; then
    directorio=$1
    shift
fi
if (( $# == 0 )); then
    printf 'uso: lineas.sh [DIRECTORIO] FICHERO...\n' >&2
    exit 1
fi
codigo=0
for fichero in "$@"; do
    ruta=$directorio/$fichero
    if [[ ! -f $ruta || ! -r $ruta ]]; then
        printf 'fichero no válido: %s\n' "$fichero" >&2
        codigo=4
        continue
    fi
    printf '%s: %s\n' "$fichero" "$(wc -l < "$ruta")"
done
exit "$codigo"
```

En un recorrido `while (( $# > 0 ))`, guarda `$1` y ejecuta `shift` antes de una posible rama con `continue`; así no procesarás indefinidamente el mismo argumento. Con `for ... in "$@"` no necesitas desplazar los argumentos.

> [!tip] Validaciones habituales
> `^[0-9]+$` admite enteros sin signo, incluido cero; un campo entre 1 y 7 necesita además comprobar su rango. `^[a-z]+$` valida nombres de intérprete y `^[a-z]{3,12}$` el nombre de salida del ejercicio correspondiente. Tras validar dígitos, `10#$valor` fuerza base decimal en aritmética, evitando interpretar un cero inicial como octal.

> [!note] Estados y canales de salida
> El éxito devuelve `0`; los errores llevan el código indicado en cada ejercicio. Por ejemplo, el laboratorio de varios ficheros usa `4` para errores parciales, mientras que las adaptaciones de conteo usan `2`. Un error de validación previo al trabajo deja stdout vacío; en un procesamiento parcial pueden coexistir resultados en stdout y errores en stderr.

## Canales propios con exec

Los descriptores habituales son `0` para stdin, `1` para stdout y `2` para stderr. Con `exec` sin otro comando puedes abrir descriptores adicionales en el shell actual; cada fichero abierto conserva su posición entre lecturas.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `exec 3<` | Abre un fichero para lectura por el canal 3 | `exec 3< "$entrada"` |
| `read -u3` | Lee desde el descriptor 3 | `IFS= read -r -u3 linea` |
| `exec 4>` | Abre una salida y vacía su contenido anterior | `exec 4> "$salida"` |
| `exec 4>>` | Abre una salida para añadir al final | `exec 4>> "$salida"` |
| `>&4` | Envía una escritura al descriptor 4 | `printf '%s\n' "$linea" >&4` |
| `exec 3<&-` | Cierra un descriptor de entrada | `exec 3<&-` |
| `exec 4>&-` | Cierra un descriptor de salida | `exec 4>&-` |

```bash
# Fragmento: entrada y salida ya validadas y distintas
exec 3< "$entrada" || exit 2
exec 4> "$salida" || { exec 3<&-; exit 4; }
n=0
while IFS= read -r -u3 linea || [[ -n $linea ]]; do
    ((n++))
    printf 'Registro %d: %s\n' "$n" "$linea" >&4
done
printf 'Total: %d\n' "$n" >&4
exec 3<&-
exec 4>&-
printf '%d registros escritos\n' "$n"
```

> [!warning] La apertura ya modifica la salida
> `exec 4> "$salida"` trunca el fichero inmediatamente. Valida antes y comprueba los fallos de apertura; para añadir usa `>>`. El cierre de un canal de escritura es `4>&-` en ambos modos. El fragmento deja que Bash informe de los fallos de apertura en stderr; si el ejercicio exige un mensaje exacto, adapta ese tratamiento.

### Entrelazar dos entradas

Abre cada fichero con su propio descriptor y comprueba su fin por separado. El siguiente fragmento conserva líneas vacías y continúa con el fichero más largo.

```bash
# Se supone que ambos ficheros se han validado y abierto correctamente
exec 3< "$fichero1"
exec 4< "$fichero2"
fin1=0; fin2=0
while (( !fin1 || !fin2 )); do
    if (( !fin1 )); then
        if IFS= read -r -u3 a || [[ -n $a ]]; then
            printf '%s\n' "$a"
        else fin1=1; fi
    fi
    if (( !fin2 )); then
        if IFS= read -r -u4 b || [[ -n $b ]]; then
            printf '%s\n' "$b"
        else fin2=1; fi
    fi
done
exec 3<&-
exec 4<&-
```

## Filtros de texto y comparaciones de rutas

Los filtros ayudan a extraer campos, consultar límites y eliminar repeticiones. Distingue siempre una coincidencia literal completa de una subcadena, y compara nombres o rutas según lo que pida el ejercicio.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `cut -d: -f` | Extrae campos separados por `:` | `cut -d: -f1,3 /etc/passwd` |
| `grep -Fxq` | Busca una línea literal completa sin imprimirla | `grep -Fxq -- "$shell" /etc/shells` |
| `grep -c` | Cuenta líneas coincidentes | `grep -c '/bash$' /etc/passwd` |
| `tr -s` | Reduce repeticiones de separadores | `tr -s ' \t' ' '` |
| `sort -u` | Ordena y elimina duplicados | `cut -d: -f7 /etc/passwd \| sort -u` |
| `uniq` | Elimina repeticiones consecutivas | `sort shells.txt \| uniq` |
| `basename`, `${ruta##*/}` | Obtiene el último componente | `nombre=${shell##*/}` |

```bash
# Buscar claves completas: no confundirlas con SYS_UID_MIN o SUB_UID_MIN
minimo=$(grep '^UID_MIN[[:space:]]' /etc/login.defs | tr -s ' \t' ' ' | cut -d' ' -f2)
maximo=$(grep '^UID_MAX[[:space:]]' /etc/login.defs | tr -s ' \t' ' ' | cut -d' ' -f2)
# En el bucle de cuentas, el intervalo incluye ambos extremos
if (( uid >= minimo && uid <= maximo )); then
    printf '%s %s\n' "$nombre" "$uid"
fi
```

Para comprobar intérpretes no admitidos, recorre `/etc/passwd` y muestra `$shell` si `grep -Fxq -- "$shell" /etc/shells` no encuentra coincidencia; ignora comentarios y líneas vacías de la lista de permitidos. Sin `-u`, conserva orden y repeticiones; con `-u`, pasa el resultado por `sort -u`.

```bash
# Descendientes de un directorio validado; también funciona para /
base=${directorio%/}
[[ $casa == "$base"/* ]] && printf '%s\n' "$nombre"
# Nombre exacto del intérprete: sh no debe coincidir con bash
[[ ${shell##*/} == "$interprete" ]] && ((total++))
# Ficheros exclusivos por nombre: repetir intercambiando dir1 y dir2
for ruta in "$dir1"/*; do
    [[ -f $ruta ]] || continue
    [[ -f $dir2/${ruta##*/} ]] || printf '%s\n' "$ruta"
done
```

> [!note] Directorios y variantes
> `"$base"/*` evita que `/home2` coincida con `/home`. El comodín `"$dir"/*` recorre solo entradas directas y omite ocultos; `-f` descarta directorios y coincidencias inexistentes. `-f` sigue enlaces simbólicos: añade `! -L` cuando el enunciado los excluya. La ordenación global o por directorio depende de la variante del ejercicio.

## Comandos adicionales útiles

Estas herramientas amplían la lectura de registros, el manejo de opciones y la comprobación de resultados en scripts Bash de Fedora.

| Comando | Para qué sirve | Ejemplo |
| --- | --- | --- |
| `mapfile -t` | Carga las líneas en un vector y elimina el salto final de cada una; conserva las líneas vacías | `mapfile -t lineas < datos.txt` |
| `declare -A` | Crea un vector asociativo con claves de texto, útil para contadores o búsquedas por nombre | `declare -A visitas; visitas[ana]=1` |
| `getopts` | Analiza opciones cortas; `:` tras una letra indica que requiere un argumento, disponible en `OPTARG` | `while getopts 'f:n:' opcion; do case $opcion in f) fichero=$OPTARG ;; n) limite=$OPTARG ;; *) exit 2 ;; esac; done` |
| `getent passwd` | Consulta las cuentas según NSS, incluidas las de servicios de identidad configurados, además de las locales | `getent passwd root` |
| `awk -F` | Separa campos y permite filtrar registros mediante condiciones numéricas | `awk -F: '$3 == $4 {print $1, $3}' /etc/passwd` |
| `sed -n` | Imprime solo las líneas seleccionadas, útil para comprobar un intervalo sin recorrerlo manualmente | `sed -n '5,10p' datos.txt` |
| `nl -ba` | Numera todas las líneas, incluidas las vacías, para revisar posiciones | `nl -ba datos.txt` |
| `paste -d` | Une entradas por posición de línea con el separador indicado; deja campos vacíos cuando una entrada se agota | `paste -d ':' nombres.txt notas.txt` |
| `comm -23` | Muestra líneas exclusivas de la primera entrada; ambas deben estar ordenadas con la misma configuración regional | `comm -23 lista_a_ordenada.txt lista_b_ordenada.txt` |
| `join -t` | Cruza registros por una clave común; las entradas deben estar ordenadas por el campo de unión, el primero por defecto | `join -t ':' usuarios_ordenados.txt notas_ordenadas.txt` |
| `diff -u` | Compara la salida esperada y la obtenida mostrando las diferencias con contexto | `diff -u esperado.txt obtenido.txt` |
| `bash -n`, `bash -x` | Comprueba la sintaxis sin ejecutar o ejecuta mostrando la traza en stderr; la traza puede revelar valores sensibles | `bash -n script.sh` |

```bash
# Revisar con números de línea las cuentas cuyo UID coincide con su GID
getent passwd | awk -F: '$3 == $4 {print $1 ":" $3}' | nl -ba
```

```bash
# Ver los diez primeros pares nombre:nota, conservando posiciones aunque falten datos
paste -d ':' nombres.txt notas.txt | sed -n '1,10p'
```

```bash
# Comparar conjuntos de nombres; las sustituciones de proceso requieren Bash
LC_ALL=C comm -23 <(LC_ALL=C sort -u lista_a.txt) <(LC_ALL=C sort -u lista_b.txt)
```

```bash
# Comprobar sintaxis y, si es válida, ejecutar guardando resultados y traza por separado
bash -n script.sh && bash -x script.sh datos.txt > obtenido.txt 2> traza.log
```

> [!tip] Leer de una vez o por registros
> Prefiere `mapfile -t` cuando el fichero sea pequeño y necesites consultar sus líneas varias veces por índice; para entradas grandes o procesamiento secuencial, mantén el bucle con `read`, que no carga todo el contenido en memoria.

## Errores frecuentes

- Leer con `for linea in $(cat fichero)`: divide palabras y pierde la estructura de líneas.
- Omitir `IFS=` o `-r` al copiar texto: altera espacios o barras invertidas.
- Usar el número de campo directamente como índice: el campo 7 está en el índice 6.
- Procesar campos antes de validarlos todos: puede dejar una salida parcial indebida.
- Escribir `$@` sin comillas o no entrecomillar rutas: rompe nombres con espacios.
- Usar `break` ante un fichero inválido cuando se pide continuar con los demás.
- Olvidar `shift` o perder un error anterior al decidir el código final.
- Confundir EOF con una línea vacía o detener el entrelazado al terminar la primera entrada.
- Buscar `sh` como subcadena, usar `uniq` sin ordenar o abrir una salida con `>` demasiado pronto.

## Chuleta rápida

```bash
chmod u+x script.sh                         # Hacer ejecutable un script Bash
while IFS= read -r l || [[ -n $l ]]; do printf '%s\n' "$l"; done < "$fichero"
while IFS=: read -r n c u g resto; do printf '%s:%s:%s\n' "$n" "$u" "$g"; done < /etc/passwd
IFS=: read -r -a vector < /etc/passwd       # Primer registro en un vector
printf '%s\n' "${vector[0]}" "${#vector[@]}" # Primer elemento y tamaño
for f in "$@"; do printf '%s\n' "$f"; done  # Un argumento por vuelta
while (( $# > 0 )); do printf '%s\n' "$1"; shift; done
wc -l < "$fichero"                         # Número de saltos de línea
[[ $campo =~ ^[0-9]+$ ]] && (( 10#$campo >= 1 && 10#$campo <= 7 ))
printf 'Error de entrada\n' >&2; exit 2     # Dentro de un script, según su enunciado
exec 3< "$fichero"; IFS= read -r -u3 linea; exec 3<&-
exec 4>> "$salida"; printf '%s\n' "$linea" >&4; exec 4>&-
grep -Fxq -- "$shell" /etc/shells           # Consultar pertenencia exacta
cut -d: -f7 /etc/passwd | sort -u           # Intérpretes sin duplicados
printf '%s\n' "${shell##*/}"                # Nombre del intérprete sin ruta
```
