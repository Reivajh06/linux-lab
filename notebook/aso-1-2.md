---
title: 1.2 · Filtros, tuberías y expresiones regulares
folder: Prácticas ASO
order: 12
icon: filter
tags: [filtros, tuberías, regex]
---

Esta práctica enseña a transformar texto combinando filtros pequeños mediante tuberías y redirecciones. Se trabaja con cuentas de `/etc/passwd`, palabras del diccionario, nombres de ficheros y un CSV de portátiles para seleccionar, ordenar, contar y buscar patrones.

> [!summary] Lo esencial
> - Una tubería conecta la salida estándar de un comando con la entrada del siguiente.
> - `cut` selecciona campos o bytes; `tr` transforma caracteres; `head` y `tail` seleccionan líneas.
> - `sort` ordena y `uniq` compara líneas consecutivas: ordena antes de quitar duplicados.
> - `grep -c` cuenta líneas; `grep -o` permite contar apariciones individuales.
> - Las regex describen texto; los comodines del shell seleccionan nombres de ficheros.
> - Protege los argumentos con comillas y distingue resultados, errores y códigos de salida.

## Ayuda, canales y tuberías

Un filtro suele leer de stdin (entrada estándar) y escribir en stdout (salida estándar); los errores van a stderr. El shell prepara las redirecciones y conecta los comandos antes de ejecutarlos.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `man` | Consulta el manual y una sección concreta | `man 5 passwd` |
| `man -aw` | Muestra todas las rutas del manual de un nombre | `man -aw passwd` |
| `--help`, `help` | Ayuda breve y ayuda de órdenes internas | `ls --help`; `help cd` |
| `<` | Usa un fichero como stdin | `wc -l < texto.txt` |
| `>`, `>>` | Sobrescribe stdout o lo añade al final | `printf 'otra\n' >> texto.txt` |
| `2>` | Guarda stderr por separado | `ls -R /etc 2> errores.txt` |
| `\|` | Envía stdout al siguiente filtro | `cut -d: -f1 /etc/passwd \| sort` |
| `cat` | Copia el contenido a stdout | `cat origen.txt > copia.txt` |
| `chmod u+x` | Da permiso de ejecución al propietario | `chmod u+x filtro.sh` |

```bash
# Crear y después añadir una línea
printf 'primera\n' > canales.txt
printf 'segunda\n' >> canales.txt

# Guardar resultados y errores en ficheros distintos
ls -R /etc > listado.txt 2> errores.txt
wc -l < listado.txt      # Solo el número, sin el nombre del fichero
cat origen.txt > copia.txt
```

> [!warning] Sobrescritura
> `>` vacía el destino antes de ejecutar el comando. Usa `>>` para añadir y nunca hagas `cat texto.txt > texto.txt`: perderías su contenido.

### Ayuda y scripts

`man passwd` describe el comando (sección 1); `man 5 passwd`, el formato del fichero (sección 5). En la terminal, `Ctrl+A` y `Ctrl+E` llevan al inicio y al final de la línea; `Ctrl+R` busca en el historial.

Los scripts Bash empiezan con `#!/bin/bash` y necesitan permiso de ejecución. Las colecciones piden resultados en stdout, errores en stderr y código `0` al completar correctamente; los códigos de error concretos dependen del ejercicio.

```bash
#!/bin/bash
# Ejemplo de filtro con una ruta como argumento
if [[ $# -ne 1 ]]; then
    printf 'Se espera un fichero\n' >&2
    exit 1
fi
if [[ ! -f "$1" || ! -r "$1" ]]; then
    printf 'Fichero no valido\n' >&2
    exit 2
fi
cut -d: -f1 "$1"
```

## Seleccionar líneas, campos y caracteres

En `/etc/passwd`, cada línea tiene siete campos separados por `:`: nombre, contraseña representada, UID, GID, comentario, directorio personal y shell. Las posiciones de campos y bytes empiezan en `1`.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `cut -d -f` | Extrae campos con un delimitador | `cut -d: -f1,5 /etc/passwd` |
| `cut -b` | Extrae posiciones de bytes | `cut -b1-3,5-8 /etc/passwd` |
| `tr` | Sustituye caracteres leídos de stdin | `tr ':' ' ' < /etc/passwd` |
| `head -n N` | Muestra las primeras N líneas | `head -n 3 /etc/passwd` |
| `tail -n N` | Muestra las últimas N líneas | `tail -n 2 /etc/passwd` |
| `tail -n +N` | Muestra desde la línea N hasta el final | `tail -n +2 /etc/passwd` |
| `nl`, `nl -ba` | Numera líneas no vacías o todas las líneas | `nl -ba texto.txt` |
| `wc -l` | Cuenta saltos de línea | `wc -l < texto.txt` |

```bash
# Seleccionar y transformar, sin cambiar /etc/passwd
cut -d: -f1,3,5 /etc/passwd
tr ':' ' ' < /etc/passwd
tr '[:lower:]' '[:upper:]' < mensajes.txt

# Sexta línea: quedarse con seis y tomar la última
head -n 6 /etc/passwd | tail -n 1

# Filtrar primero para numerar únicamente las coincidencias
grep 'bash' /etc/passwd | nl -ba

# Quitar desde # hasta el final, conservando el resto y las líneas
cut -d'#' -f1 /etc/protocols
```

> [!warning] Líneas y bytes
> `tail -n +2` elimina la primera línea; `tail -n 2` conserva las dos últimas. Si N supera la longitud del fichero, `head -n N | tail -n 1` devuelve la última línea disponible: valida N antes.
> `cut -b` cuenta bytes; un carácter con tilde en UTF-8 puede ocupar varios.

## Ordenar, eliminar duplicados y resumir datos

`sort` ordena como texto por defecto; para UID, tamaños o frecuencias hace falta orden numérico. El orden de los filtros determina qué datos se seleccionan y qué campos quedan disponibles.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `sort` | Ordena líneas como texto | `sort frutas.txt` |
| `sort -n`, `sort -nr` | Ordena números ascendente o descendente | `sort -nr cantidades.txt` |
| `sort -t: -k3,3n` | Ordena numéricamente solo por el campo 3 | `sort -t: -k3,3n /etc/passwd` |
| `sort -t: -k1.2,1` | Usa el campo 1 desde su segundo carácter | `sort -t: -k1.2,1 /etc/passwd` |
| `sort -u` | Ordena y elimina líneas repetidas | `sort -u frutas.txt` |
| `uniq` | Reduce cada grupo de líneas iguales consecutivas | `sort frutas.txt \| uniq` |
| `uniq -d` | Muestra una vez cada línea repetida del grupo | `sort frutas.txt \| uniq -d` |
| `uniq -c` | Antecede cada grupo con su frecuencia | `sort frutas.txt \| uniq -c` |

```bash
# Ordenar solo las tres primeras líneas originales
head -n 3 /etc/passwd | sort
# Obtener las tres primeras de todo el fichero ya ordenado
sort /etc/passwd | head -n 3

# Ordenar por UID después de extraer: ahora UID es el campo 2
cut -d: -f1,3,5 /etc/passwd | sort -t: -k2,2n
# Ordenar por el comentario después de extraer nombre y comentario
cut -d: -f1,5 /etc/passwd | sort -t: -k2,2

# GID repetidos y cantidad de shells distintos
cut -d: -f4 /etc/passwd | sort -n | uniq -d
cut -d: -f7 /etc/passwd | sort -u | wc -l
```

> [!tip] Leer una clave de ordenación
> En `-k3,3n`, ambos `3` limitan la clave al tercer campo y `n` activa la comparación numérica. Sin ella, `10` puede quedar antes que `9`; `r` invierte el orden. La ordenación textual depende de la configuración regional.

### Aplicación al CSV de portátiles

La muestra tiene un índice inicial sin nombre y campos sin comas internas: marca en el campo `2`, tipo en el `3`, tamaño en el `4` y CPU en el `6`. Elimina la cabecera antes de contar u ordenar datos; `cut -d,` sirve para esta muestra sencilla, pero no interpreta CSV con comas entrecomilladas.

```bash
csv=/home/learner/aso/p12/laptop_data.csv
# Marcas distintas y frecuencia por marca, de mayor a menor
tail -n +2 "$csv" | cut -d, -f2 | sort -u
tail -n +2 "$csv" | cut -d, -f2 | sort | uniq -c | sort -k1,1nr -k2,2

# Pares marca,tamaño sin repetir; tamaño ordenado como número
tail -n +2 "$csv" | cut -d, -f2,4 | sort -t, -k1,1 -k2,2n | uniq
# CPU Intel: buscar al principio del campo extraído
tail -n +2 "$csv" | cut -d, -f6 | grep -c '^Intel'
```

## Buscar texto y expresiones regulares

`grep` selecciona líneas que contienen una coincidencia; con `-E` admite expresiones regulares extendidas. Escribe los patrones entre comillas simples para que el shell no interprete sus caracteres especiales.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `grep` | Selecciona líneas que coinciden | `grep 'bash' /etc/passwd` |
| `grep -E` | Activa regex extendidas | `grep -E '^[A-Za-z]{5}$' palabras.txt` |
| `grep -i` | Ignora mayúsculas y minúsculas | `grep -i 'error' mensajes.txt` |
| `grep -v` | Selecciona las líneas que no coinciden | `grep -v ':/bin/bash$' /etc/passwd` |
| `grep -F` | Trata el patrón como texto literal | `grep -F 'a.b' texto.txt` |
| `grep -x` | Exige que coincida toda la línea | `grep -Fx '/bin/bash' shells.txt` |
| `grep -c` | Cuenta líneas seleccionadas | `grep -c 'bash' /etc/passwd` |
| `grep -o` | Imprime cada coincidencia por separado | `grep -o 'root' /etc/passwd` |
| `grep -w` | Exige límites de palabra | `grep -owF 'root' /etc/passwd` |

### Piezas de una regex extendida

`^` y `$` anclan el inicio y el final; `.` representa un carácter cualquiera. `[aeiou]` selecciona una vocal y `[^aeiou]` un carácter que no sea vocal; `*` repite cero o más veces, `+` una o más, `{5}` exactamente cinco y `{1,4}` entre una y cuatro.

Los paréntesis agrupan y `|` ofrece alternativas: `(ing|ed)$` exige uno de esos dos sufijos. Dentro de una clase, coloca `-` al final para usarlo literalmente; `\.` representa un punto literal fuera de una clase.

```bash
dic=/usr/share/dict/words
# Mostrar palabras; añadir -c si se pide el número de líneas
grep -iE '^[aeiou]' "$dic"                 # Empiezan por vocal
grep -E '^[A-Za-z]{5}$' "$dic"             # Cinco letras ASCII exactas
grep -E '^[A-Za-z]{1,4}$' "$dic"           # De una a cuatro letras
grep -iE '[aeiou]{2}' "$dic"               # Dos vocales consecutivas
grep -E '(ing|ed)$' "$dic"                 # Uno de los dos sufijos
grep -E '^[AEIOUaeiou].*tion$' "$dic"      # Vocal inicial y sufijo tion
grep -E '^[AEIOUaeiou][A-Za-z]{0,3}tion$' "$dic"  # Hasta ocho letras
grep -E 'sh.*sh' "$dic"                   # Al menos dos apariciones de sh

# Excluir vocales; puede conservar líneas vacías, números o signos
grep -ivE '[aeiou]' "$dic"
# Exigir además una o más consonantes ASCII, sin otros caracteres
grep -iE '^[b-df-hj-np-tv-z]+$' "$dic"
```

> [!note] Ajustar la búsqueda al enunciado
> La variante Bash cuenta con `grep -icE`; otras variantes muestran las palabras y solo ignoran mayúsculas cuando se pide. `[a-z]{5}` sin anclas también coincide dentro de palabras largas; `^[A-Za-z]{5}$` exige que toda la línea tenga cinco letras ASCII.

### Coincidencias exactas y extracción

```bash
# Contar cuentas cuyo campo shell sea exactamente /bin/bash
cut -d: -f7 /etc/passwd | grep -Fxc '/bin/bash'
# Usuarios con otro shell, sin confundir bash en el comentario
grep -v ':/bin/bash$' /etc/passwd | cut -d: -f1 | sort
# Contar apariciones completas, incluso varias en una misma línea
grep -owF 'root' /etc/passwd | wc -l
# Extraer correos habituales; patrón práctico para este ejercicio
grep -oE '[A-Za-z0-9._-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' texto.txt
```

> [!warning] Cero coincidencias también puede ser correcto
> `grep` devuelve `0` si selecciona líneas, `1` si no selecciona ninguna y `2` ante un error. `grep -c` imprime `0` en el segundo caso, pero su estado sigue siendo `1`; un script que deba terminar con éxito sin coincidencias debe tratar ese caso sin ocultar errores reales.

```bash
# Fragmento para un script: después de validar argumentos y fichero
grep -E '^[A-Za-z]{5}$' "$1"
estado=$?
if (( estado == 1 )); then
    exit 0                 # Salida vacía válida para este filtro
fi
exit "$estado"             # Conservar el éxito o el error real
```

## Comodines y expansión de llaves

Los comodines se expanden a nombres existentes antes de ejecutar el comando. Las llaves generan combinaciones de texto aunque todavía no existan esos ficheros.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `*`, `?` | Seleccionan cero o más caracteres, o exactamente uno | `ls /etc/*.conf`; `ls -d /etc/???` |
| `[a-c]*` | Selecciona nombres que empiezan por a, b o c | `ls -d /etc/[a-c]*` |
| `{1..5}`, `{a,b}` | Generan series y alternativas | `touch tema{1..5}.txt` |
| `mkdir -p` | Crea directorios y padres que falten | `mkdir -p trabajo/practica{1..4}` |
| `shopt -s nullglob` | Elimina patrones sin coincidencias | `shopt -s nullglob` |
| `[[ -f ... ]]`, `[[ -d ... ]]` | Comprueban fichero regular o directorio | `[[ -f "$ruta" ]]` |

```bash
# Crear series y combinaciones
touch tema{1..5}.txt
mkdir -p trabajo/{practica,memoria}{1..4}
touch trabajo/{texto,datos}{1..4}.{txt,pdf}

# Recorrer solo ficheros regulares .txt, incluidos nombres con espacios
directorio=/home/learner/lab/aso-fundamentos/extensiones
shopt -s nullglob
for ruta in "$directorio"/*.txt; do
    if [[ -f "$ruta" ]]; then
        printf '%s\n' "$ruta"
    fi
done | sort
```

> [!tip] Comillas y patrones
> `"$directorio"/*.txt` protege la ruta y permite expandir el comodín. `"$directorio/*.txt"` lo convierte en texto literal. En la configuración habitual estos patrones no incluyen nombres ocultos; `nullglob` evita procesar un patrón literal cuando no hay coincidencias.
> `touch` crea ficheros que faltan, pero conserva el contenido de los existentes; `: > fichero` los deja vacíos.

## Comandos adicionales útiles

Estos comandos amplían las posibilidades de los filtros para relacionar datos, consultar cuentas del sistema y comprobar resultados sin modificar los ficheros de entrada.

| Comando | Para qué sirve | Ejemplo |
| --- | --- | --- |
| `awk -F` | Filtra por valores de campos y calcula o compone la salida; `-F` fija el separador | `awk -F: '$3 >= 1000 {print $1, $3}' /etc/passwd` |
| `sed -n`, `sed -E` | Selecciona rangos de líneas o transforma texto con regex extendidas; sin `-i` no modifica el original | `sed -n '5,10p' texto.txt`; `sed -E 's/[[:space:]]+/ /g' texto.txt` |
| `getent passwd` | Consulta cuentas según las fuentes configuradas en el sistema, incluidas las que no proceden de `/etc/passwd` | `getent passwd root` |
| `paste -d`, `paste -s` | Une líneas de varios ficheros por posición o reúne las de uno en una sola línea | `paste -d: usuarios.txt uid.txt`; `paste -sd, marcas.txt` |
| `join -t` | Relaciona dos ficheros por un campo común; ambos deben estar ordenados por esa clave con la misma configuración regional | `join -t: -1 1 -2 1 nombres.txt grupos.txt` |
| `comm -12`, `comm -23` | Obtiene líneas comunes o exclusivas del primer fichero; exige entradas ordenadas con la misma configuración regional | `comm -23 lista-a.txt lista-b.txt` |
| `tee` | Guarda una copia de la salida mientras la envía al siguiente filtro | `tee resultados.txt` |
| `column -t -s` | Alinea campos para leerlos en pantalla; no interpreta CSV con comas entrecomilladas | `column -t -s: /etc/passwd` |
| `diff -u` | Compara la salida esperada y la obtenida mostrando las diferencias con contexto | `diff -u esperado.txt obtenido.txt` |
| `find -type f -name -print0` | Busca ficheros regulares por nombre y separa sus rutas con NUL para conservar espacios y saltos de línea | `find . -type f -name '*.txt' -print0` |
| `xargs -0 -r` | Convierte rutas separadas por NUL en argumentos y evita ejecutar el comando si no recibe ninguna | `xargs -0 -r wc -l` |

```bash
# Guardar las cuentas con UID >= 1000 y shell bash, y mostrar sus campos alineados
getent passwd | awk -F: '$3 >= 1000 && $7 ~ /\/bash$/ {print $1 ":" $3}' | tee usuarios-bash.txt | column -t -s:
```

```bash
# Quitar comentarios y líneas vacías antes de extraer los nombres de protocolos
sed -E 's/#.*$//; /^[[:space:]]*$/d' /etc/protocols | awk '{print $1}' | tee protocolos.txt
```

```bash
# Obtener nombres presentes en ambas listas y reunirlos en una línea separada por comas (Bash)
LC_ALL=C comm -12 <(LC_ALL=C sort -u lista-a.txt) <(LC_ALL=C sort -u lista-b.txt) | paste -sd, -
```

```bash
# Contar líneas de los ficheros .txt encontrados, incluso si sus nombres contienen espacios
find . -type f -name '*.txt' -print0 | xargs -0 -r wc -l
```

> [!tip] Elegir `awk` para condiciones entre campos
> Prefiere `awk` cuando necesites comparar números, combinar condiciones de varias columnas o calcular totales en una misma pasada; `cut` resulta más directo si solo quieres extraer campos con un separador fijo.

## Errores frecuentes

- Usar `uniq` sin ordenar cuando los duplicados están separados.
- Ordenar UID como texto o seguir usando el número de campo original después de `cut`.
- Confundir `head | sort` con `sort | head`: seleccionan conjuntos diferentes.
- Usar `grep -c` para contar apariciones: cuenta líneas, aunque haya varias coincidencias.
- Buscar `bash` en cualquier campo cuando se pide exactamente el shell `/bin/bash`.
- Olvidar las anclas, `-E` o las comillas del patrón; confundir `*.txt` con una regex.
- Quitar comentarios con `grep -v '#'`: también elimina los datos anteriores al comentario.
- Contar la cabecera del CSV o asumir columnas sin comprobar su posición.
- Dejar argumentos sin comillas, mezclar errores con stdout o devolver `1` por una búsqueda vacía válida.

## Chuleta rápida

```bash
cut -d: -f1,5 /etc/passwd                         # Nombre y comentario
cut -b1-3,5-8 /etc/passwd                         # Bytes seleccionados
tr ':' ' ' < /etc/passwd                          # Cambiar separadores
tail -n +2 /etc/passwd                            # Omitir primera línea
head -n 6 /etc/passwd | tail -n 1                 # Sexta línea
cut -d: -f1 /etc/passwd | sort                    # Usuarios ordenados
grep bash /etc/passwd | nl -ba                    # Numerar coincidencias
grep -c bash /etc/passwd                          # Contar líneas
cut -d: -f1,3,5 /etc/passwd | sort -t: -k2,2n      # Ordenar por UID
cut -d: -f4 /etc/passwd | sort -n | uniq -d        # GID repetidos
cut -d: -f7 /etc/passwd | sort -u | wc -l          # Cantidad de shells
sort frutas.txt | uniq -c                        # Frecuencias
grep -E '^[A-Za-z]{5}$' /usr/share/dict/words      # Cinco letras
grep -owF root /etc/passwd | wc -l                # Apariciones completas
ls -R /etc > listado.txt 2> errores.txt           # Separar canales
```
