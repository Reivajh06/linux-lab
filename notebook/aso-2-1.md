---
title: 2.1 · Scripts en Bash
folder: Prácticas ASO
order: 21
icon: code
tags: [bash, scripts, control de flujo]
---

Esta práctica enseña a construir scripts de Bash que validan argumentos, toman decisiones, repiten operaciones y organizan cálculos en funciones. Aplica esas herramientas a ficheros de texto, directorios, usuarios y grupos, cuidando el formato de salida y los códigos de terminación.

> [!summary] Lo esencial
> - Empieza con `#!/bin/bash` y concede permiso de ejecución con `chmod u+x`.
> - Valida cantidad de argumentos, formato y rango antes de operar o crear ficheros.
> - Usa `[[ ]]` para pruebas y patrones, `(( ))` para condiciones aritméticas y `$(( ))` para obtener valores.
> - Separa resultados en stdout y errores en stderr; termina con `exit 0` cuando corresponda.
> - Una función comunica datos por stdout y estado con `return`; captura datos con `$(...)`.
> - Consulta los datos reales con filtros y comprueba los requisitos concretos de cada variante.

## Preparar el script y validar argumentos

El shebang selecciona el intérprete al ejecutar `./script.sh`; `bash script.sh` invoca Bash explícitamente y no necesita permiso de ejecución sobre el fichero. Una asignación se escribe sin espacios alrededor de `=` y conviene entrecomillar las expansiones que se pasan como argumentos.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `chmod u+x` | Añade ejecución para el propietario | `chmod u+x hola.sh` |
| `head -n 1`, `file` | Inspeccionan la primera línea y el tipo de fichero | `head -n 1 hola.sh` |
| `$0`, `$#`, `$1`, `$2` | Nombre del script, cantidad y argumentos posicionales | `printf 'Uso: %s N\n' "$0"` |
| `${3:-/etc/passwd}` | Usa un valor por defecto si el tercero falta o está vacío | `fichero=${3:-/etc/passwd}` |
| `[[ cadena =~ regex ]]` | Comprueba una expresión regular | `[[ $1 =~ ^[0-9]+$ ]]` |
| `${#cadena}` | Obtiene la longitud del texto | `cadena=007; echo "${#cadena}"` |

### Plantilla: repetir entre 2 y 20 veces

Este ejemplo sigue el rango de `hola` en la colección ASO Bash; el ejercicio 03 de la colección de veinte ejercicios usa de 1 a 8. Los extremos son inclusivos en ambos casos.

```bash
#!/bin/bash
if (( $# != 1 )); then
    printf 'uso: hola.sh iteraciones\n' >&2
    exit 1
elif [[ ! $1 =~ ^[0-9]+$ ]]; then
    printf 'el argumento debe ser un entero positivo\n' >&2
    exit 2
fi
n=$((10#$1))  # Interpreta los dígitos en base decimal
if (( n < 2 || n > 20 )); then
    printf 'el argumento debe estar entre 2 y 20\n' >&2
    exit 3
fi
k=1
while (( k <= n )); do
    printf '%s: hola, mundo\n' "$k"
    ((k++))
done
exit 0
```

> [!warning] Formato, valor y longitud son cosas distintas
> `^[0-9]+$` acepta uno o más dígitos, incluido `0`; no garantiza un valor mayor que cero. `007` tiene tres caracteres aunque su valor decimal sea 7; usa `${#cadena}` para clasificar por dígitos y valida el rango por separado.

## Condiciones, bucles y funciones

`if` ejecuta una rama cuando su condición devuelve estado 0; en `(( expresión ))`, una expresión distinta de cero produce ese estado de éxito. `while` repite mientras se cumpla la condición y necesita actualizar el contador.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `if`, `elif`, `else`, `fi` | Seleccionan una rama | `if (( a > b )); then echo "$a"; fi` |
| `[[ -e ]]`, `[[ -f ]]`, `[[ -d ]]` | Prueban existencia, fichero regular o directorio | `[[ -f "$ruta" ]]` |
| `[[ -r ]]`, `[[ -x ]]`, `[[ -z ]]` | Prueban lectura, ejecución o cadena vacía | `[[ -r "$fichero" ]]` |
| `[ ]`, `-eq`, `-lt`, `-le`, `-gt`, `-ge` | Pruebas clásicas y comparaciones de enteros | `[ "$n" -le 20 ]` |
| `(( ))`, `$(( ))` | Evalúan aritmética u obtienen su resultado | `suma=$((a + b))` |
| `while`, `do`, `done` | Repiten un bloque | `while (( i <= n )); do ((i++)); done` |
| `&&`, `\|\|`, `!` | Encadenan por éxito, por fallo o niegan el estado | `[[ -f "$ruta" ]] && echo EXISTE` |
| `case`, `esac` | Seleccionan según una opción o patrón | `case $opcion in -u) base=passwd ;; esac` |
| `return`, `exit` | Terminan una función o el script | `return 1` |
| `$(...)` | Captura stdout, quitando saltos finales | `resultado=$(sumar 200 100)` |

### Acumuladores: suma y factorial

```bash
# Fragmento después de validar N entre 1 y 20
n=5; i=1; suma=0
while (( i <= n )); do
    ((suma += i))
    ((i++))
done
printf 'Suma: %s\n' "$suma"  # 15

# Para el factorial se valida N entre 0 y 8
n=0; i=1; factorial=1
while (( i <= n )); do
    ((factorial *= i))
    ((i++))
done
printf 'Factorial: %s\n' "$factorial"  # 0! = 1
```

### Funciones: datos frente a estado

Dentro de una función, `$1`, `$2` y `$#` corresponden a los argumentos de esa llamada. `local` permite que una variable pertenezca a la función.

```bash
sumar() {
    printf '%s\n' "$((10#$1 + 10#$2))"
}
resultado=$(sumar 200 100)  # Argumentos numéricos ya validados
printf 'Resultado: %s\n' "$resultado"

es_par() {
    local numero=$1
    if (( numero % 2 == 0 )); then
        return 0
    else
        return 1
    fi
}
if es_par 7; then echo PAR; else echo IMPAR; fi
```

> [!warning] `return` no transporta una suma
> Los estados de salida están entre 0 y 255: `return 300` se observa como 44. Imprime `300` y captura stdout; para una pregunta como «¿es par?», sí tiene sentido usar el estado de la función.

## Salidas, errores y creación de ficheros

stdout lleva los resultados pedidos; stderr lleva los errores, sin contaminar la salida útil con mensajes auxiliares. El éxito del script es `exit 0`; cada ejercicio fija los demás códigos y sus mensajes, por lo que no hay que trasladarlos automáticamente entre variantes.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `printf`, `echo` | Imprimen resultados | `printf 'Resultado: %s\n' "$resultado"` |
| `>&2` | Envía stdout de ese comando a stderr | `echo 'Uso: RUTA' >&2` |
| `>`, `>>` | Sobrescriben o añaden a un fichero | `echo 'otra línea' >> "$dir/salida.txt"` |
| `<` | Toma stdin de un fichero | `wc -l < "$fichero"` |
| `2>/dev/null` | Descarta solo stderr | `mkdir "$dir" 2>/dev/null` |
| `>/dev/null 2>&1` | Descarta stdout y después dirige stderr al mismo destino | `ls -l "$ruta" >/dev/null 2>&1` |
| `$?` | Estado del último comando ejecutado | `codigo=$?` |
| `mkdir`, `mkdir -p` | Crean un directorio; `-p` también crea padres | `mkdir -p "$dir"` |

```bash
# Guarda el estado antes de imprimir nada
ruta=/etc/passwd
ls -l "$ruta" >/dev/null 2>&1
codigo=$?
printf 'ls devolvió %s\n' "$codigo"
```

```bash
# Fragmento tras validar las iteraciones y el directorio
n=3; dir='./salidas/ejemplo'
if ! mkdir -p "$dir" 2>/dev/null; then
    echo 'no se ha podido crear el directorio' >&2
    exit 4
fi
k=1
while (( k <= n )); do
    if ! printf '%s: hola, mundo\n' "$k" >> "$dir/salida.txt"; then
        exit 4  # Un fallo al escribir tampoco es un éxito
    fi
    ((k++))
done
printf '%s líneas añadidas\n' "$n"
exit 0
```

> [!tip] Comprueba el comando directamente
> `if ! mkdir ...; then` permite tratar su fallo sin consultar `$?`. Dentro de esa rama, `$?` refleja la negación; si necesitas el código original, guárdalo inmediatamente después del comando sin `!`.
> Con `mkdir` sin `-p`, distingue un directorio ya existente (`[[ -d "$dir" ]]`) de un destino que es un fichero o cuyo padre no existe.

## Filtros de texto y campos

`grep` selecciona líneas y `cut` extrae campos; una tubería conecta stdout de un comando con stdin del siguiente. Para contar iniciales hay que anclar la letra con `^`, no buscarla en cualquier posición.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `grep -i` | Ignora diferencias de mayúsculas | `grep -i '^a' diccionario.txt` |
| `grep -c` | Cuenta líneas coincidentes, no apariciones | `grep -c '^ERROR:' mensajes.txt` |
| `grep -q` | Consulta sin imprimir coincidencias | `grep -q '^root:' /etc/passwd` |
| `wc -l` | Cuenta saltos de línea | `wc -l < mensajes.txt` |
| `cut -d: -fN` | Extrae el campo N usando `:` | `cut -d: -f6 /etc/passwd` |
| `IFS=: read -r` | Separa una línea en variables sin interpretar barras inversas | `IFS=: read -r nombre clave uid gid datos casa shell` |
| `tr ',' '\n'` | Convierte comas en saltos de línea | `printf '%s\n' "$lista" \| tr ',' '\n'` |

```bash
# Fragmento tras validar el fichero y una única letra ASCII
letra=a; fichero=/usr/share/dict/words
grep -ic "^$letra" "$fichero"
codigo=$?
if (( codigo > 1 )); then exit 2; fi
exit 0  # Cero coincidencias es un resultado válido
```

> [!note] El estado de `grep` tiene tres significados
> Devuelve 0 si encuentra coincidencias, 1 si no encuentra y normalmente 2 ante un error. `grep -c` imprime `0` y devuelve 1 cuando no hay coincidencias; un script que cuenta debe convertir ese caso normal en éxito.

### Respetar el orden de los campos

En los cursos, `campos.sh` admite campos repetidos y debe conservar el orden solicitado. El ejercicio 05 de la colección de veinte exige campos distintos y conserva el orden del fichero: allí sí encaja directamente `cut -d: -f7,1`.

```bash
# Fragmento para la variante de los cursos: campos ya validados (1..7)
campo1=7; campo2=1; fichero=/etc/passwd
while IFS= read -r linea; do
    primero=$(printf '%s\n' "$linea" | cut -d: -f"$campo1")
    segundo=$(printf '%s\n' "$linea" | cut -d: -f"$campo2")
    printf '%s:%s\n' "$primero" "$segundo"
done < "$fichero"
```

> [!warning] `cut` conserva el orden original
> `cut -d: -f7,1` produce lo mismo que `-f1,7`, y `-f3,3` no duplica el campo. Dos extracciones separadas permiten ordenar y repetir según los argumentos.

## Usuarios, grupos y patrones

En `/etc/passwd`, los campos 1, 6 y 7 son nombre, directorio personal y shell; en `/etc/group`, el cuarto campo contiene miembros secundarios separados por comas. `getent` consulta las bases de cuentas configuradas, mientras que leer esos ficheros consulta sus registros locales.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `getent passwd`, `getent group` | Buscan una cuenta o un grupo | `getent passwd root` |
| `id -nG` | Obtiene nombres de grupos, incluido el primario | `id -nG root` |
| `grep '^nombre:'` | Busca el nombre completo en el primer campo | `grep '^adm:' /etc/group` |
| `[[ texto == patrón ]]` | Compara con un patrón de Bash | `[[ $casa == /home/* ]]` |
| `<<<` | Entrega una cadena como stdin | `IFS=: read -r a b c <<< "$linea"` |

```bash
# Ejemplo de perfil; en un script, valida antes la cantidad de argumentos
usuario=root
if ! linea=$(getent passwd "$usuario"); then
    echo 'el usuario no existe' >&2
    exit 4
fi
IFS=: read -r nombre clave uid gid datos casa shell <<< "$linea"
[[ $casa == /home/* ]] && echo 'HOME=SI' || echo 'HOME=NO'
[[ $shell == /bin/bash ]] && echo 'SHELL=SI' || echo 'SHELL=NO'
id -nG "$usuario"
```

```bash
# Grupo local conocido: no confundir lista vacía con grupo inexistente
if ! linea=$(grep '^adm:' /etc/group); then
    echo 'el grupo no existe' >&2
    exit 4
fi
lista=$(printf '%s\n' "$linea" | cut -d: -f4)
if [[ -z $lista ]]; then
    echo 'sin usuarios secundarios'
else
    printf '%s\n' "$lista" | tr ',' '\n'
fi
```

> [!note] Patrones y alcance de las comprobaciones
> En `[[ $casa == /home/* ]]`, deja el patrón sin comillas: `/home` y `/homeless/ana` no cumplen. Para una búsqueda con `grep`, `^ana:` evita coincidencias parciales; valida el nombre antes de insertarlo en una regex.
> El formato `^[a-z][a-z0-9_]{2,11}$` es la regla del ejercicio 18, no una regla universal de Linux. Los miembros secundarios de `/etc/group` no enumeran a todos los usuarios cuyo grupo primario sea ese grupo.

## Comandos adicionales útiles

Estas herramientas complementan la práctica para depurar scripts, procesar argumentos y resumir datos de usuarios y ficheros en Fedora.

| Comando | Para qué sirve | Ejemplo |
| --- | --- | --- |
| `bash -n` | Comprueba la sintaxis sin ejecutar el script; no detecta errores de lógica | `bash -n ./script.sh` |
| `bash -x` | Ejecuta el script mostrando en stderr los comandos con sus expansiones para seguir el flujo | `bash -x ./script.sh 3` |
| `shellcheck` | Analiza errores habituales de comillas, expansiones y otras construcciones; requiere tener instalado el paquete `ShellCheck` en Fedora | `shellcheck ./script.sh` |
| `help` | Consulta la ayuda de los comandos internos de Bash | `help read` |
| `command -v` | Comprueba si Bash puede localizar un comando antes de usarlo | `command -v shellcheck` |
| `getopts` | Procesa opciones cortas; `:` indica que la opción necesita un argumento, disponible en `OPTARG` | `while getopts 'f:' opcion; do case $opcion in f) fichero=$OPTARG ;; *) exit 2 ;; esac; done` |
| `shift` | Retira argumentos posicionales ya procesados; tras el bucle de `getopts`, deja los operandos en `$1`, `$2`, etc. | `shift "$((OPTIND - 1))"` |
| `awk -F:` | Separa campos por dos puntos y permite filtrarlos, reordenarlos o repetirlos | `awk -F: '{print $7 ":" $1 ":" $7}' /etc/passwd` |
| `sort -n`, `sort -u` | Ordenan números por su valor o eliminan líneas duplicadas al ordenar | `sort -n numeros.txt` |
| `uniq -c` | Cuenta repeticiones consecutivas; ordena antes si quieres agrupar todas las líneas iguales | `uniq -c datos_ordenados.txt` |
| `mktemp` | Crea un fichero temporal con nombre único y permisos restringidos al usuario | `tmp=$(mktemp)` |
| `trap ... EXIT` | Ejecuta una limpieza al salir del shell; permite retirar el temporal creado previamente | `trap 'rm -f -- "$tmp"' EXIT` |

```bash
# Revisa sintaxis y avisos antes de ejecutar con traza; requiere ShellCheck instalado
bash -n ./script.sh && shellcheck ./script.sh && bash -x ./script.sh 3
```

```bash
# Cuenta usuarios locales por shell y muestra primero los grupos más numerosos
awk -F: '{print $7}' /etc/passwd | sort | uniq -c | sort -nr
```

```bash
# Guarda una salida y elimina duplicados; el subshell limpia su temporal al terminar
(tmp=$(mktemp) || exit 1; trap 'rm -f -- "$tmp"' EXIT; bash ./script.sh 3 > "$tmp" && sort -u "$tmp")
```

> [!tip] Elige `awk` para campos con orden o repeticiones
> Cuando se pide mostrar el campo 7 antes del 1 o repetir un campo, `awk -F:` permite hacerlo en una sola pasada; también resulta útil para combinar extracción y condiciones sobre otros campos.

## Errores frecuentes

- Escribir `mensaje = hola`: Bash intenta ejecutar un comando; usa `mensaje=hola`.
- Ejecutar un script con sintaxis Bash mediante `sh`, o lanzar `./script.sh` sin permiso de ejecución.
- Usar `-e` cuando se pide un fichero regular: emplea `-f`; añade `-r` si debe poder leerse.
- Comparar números sin validar el texto o tratar ceros iniciales como octales; usa base decimal para calcular.
- Excluir los extremos con `<=` o `>=` al rechazar un rango inclusivo; rechaza con `<` y `>`.
- Olvidar incrementar el contador o iniciar el factorial en cero.
- Sobrescribir con `>` cuando se pide añadir con `>>`, o crear salidas antes de validar todo.
- Consultar `$?` después de `echo`, o usar `return` para transportar un resultado numérico grande.
- Convertir toda respuesta negativa en error: las variantes de clasificación y consulta pueden exigir stdout y estado 0; otras exigen stderr y un código concreto.
- Añadir cabeceras, mensajes o líneas vacías que no pide el enunciado, o confundir las rutas de datos de las distintas colecciones.

## Chuleta rápida

```bash
chmod u+x script.sh                                  # Dar permiso al propietario
./script.sh 3                                        # Ejecutar con su shebang
(( $# == 1 ))                                       # Comprobar un argumento
[[ $1 =~ ^[0-9]+$ ]]                                # Validar dígitos antes de calcular
fichero=${3:-/etc/passwd}                            # Tercer argumento opcional
[[ -f "$fichero" && -r "$fichero" ]]                  # Fichero regular y legible
printf '%s\n' 'Error de entrada' >&2                  # Mensaje por stderr
ls -l "$ruta" >/dev/null 2>&1; codigo=$?             # Guardar estado inmediatamente
mkdir -p "$dir"                                     # Crear también los padres
printf '%s\n' 'hola, mundo' >> "$dir/salida.txt"       # Añadir una línea
i=1; while (( i <= 3 )); do echo "$i"; ((i++)); done  # Bucle inclusivo
grep -ic '^a' /usr/share/dict/words                  # Contar inicial sin distinguir caja
cut -d: -f1,7 /etc/passwd                            # Nombre y shell
getent group adm                                    # Consultar un grupo
id -nG root                                         # Mostrar todos los grupos
```
