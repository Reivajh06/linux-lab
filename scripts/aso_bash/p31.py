"""Práctica 3.1: procesos reales con ps, pgrep, kill, top y trabajos en segundo plano."""
from .framework import E, Practice, T, eg, ok, probe

practice = Practice(
    "3.1", "Procesos",
    """Consulta y controla **procesos reales** del contenedor: `ps` con `-e`, `-o`, `-u`, `--sort` y `--no-headers`, `pgrep`, `top -b`, `kill`, señales, `&`, `wait` y `$!`.
    El evaluador lanza procesos `sleep` reales con las cuentas `p31a`, `p31b`, `p31g1` y `p31g2` antes de cada caso, porque el resto de la lista de procesos cambia de una ejecución a otra.
    En la terminal puedes lanzar los tuyos: `sudo runuser -u p31a -- sleep 900 &`.""",
    setup="""getent group p31g >/dev/null || groupadd -g 23102 p31g
for u in p31a p31b p31c usuario1; do id $u >/dev/null 2>&1 || useradd -m -s /bin/bash $u; done
for u in p31g1 p31g2; do id $u >/dev/null 2>&1 || useradd -m -s /bin/bash -g p31g $u; done
""")


def asuser(user):
    """setpriv execs directly: runuser would stay as a parent and resume stopped children.

    setsid keeps stopped processes alive: the kernel hangs up a stopped group orphaned by its shell.
    """
    return f"setsid setpriv --reuid={user} --regid=$(id -g {user}) --init-groups"


def spawn(*pairs):
    """Leave exactly N real `sleep 900` processes running for each (user, N)."""
    lines = []
    for user, count in pairs:
        lines.append(f"pkill -KILL -u {user} ; for i in {' '.join(str(n) for n in range(count))}; do {asuser(user)} sleep 900 >/dev/null 2>&1 </dev/null & done")
    return "\n".join(lines + ["sleep 0.4"])


_base = spawn(("p31a", 3), ("p31b", 1), ("p31c", 0))
practice.add(
    "procs-usuario", "Actividad 1: procesos por usuario",
    """Actividad de laboratorio 1. Muestra `USUARIO: N` con el número de procesos de cada usuario indicado. Si un nombre no corresponde a un usuario, escribe `no existe: NOMBRE` en stderr, continúa y termina con el código 4.""",
    usage="USUARIO...", cmds="`ps -u`, `--no-headers`, `wc -l`, `id`", structs='`for u in "$@"`, `continue`, sustitución de comandos',
    detail="La cabecera de `ps` contaría como una línea más: usa `--no-headers`. Un usuario sin procesos existe y da 0, aunque `ps -u` devuelva 1 en ese caso.",
    success="Una línea por usuario.",
    tests=[T("cuentas", "Cuenta procesos reales.", ok(["p31a", "p31b"], val="p31a: 3\np31b: 1", prepare=_base), ok(["p31c"], val="p31c: 0"))],
    errors=[E("uso", 1, "Recibe al menos un usuario.", "uso: procs-usuario.sh USUARIO...", []),
            E("parcial", 4, "Cada usuario existe; si no, se avisa y se continúa.", "no existe: nadie", dict(args=["nadie", "p31a"], ref="echo 'p31a: 3'", prepare=_base), partial="stdout con los válidos y stderr con los demás.", eg=False)],
    examples=[eg("p31a p31b", prepare=_base)],
    solution=r"""
#!/bin/bash
(($#<1)) && { echo "uso: procs-usuario.sh USUARIO..." >&2; exit 1; }
codigo=0
for usuario in "$@"; do
  if ! id "$usuario" >/dev/null 2>&1; then
    echo "no existe: $usuario" >&2
    codigo=4
    continue
  fi
  echo "$usuario: $(ps -u "$usuario" --no-headers | wc -l)"
done
exit $codigo
""")

_grupo = spawn(("p31g1", 3), ("p31g2", 1))
practice.add(
    "gid-umbral", "Actividad 2: grupo primario y umbral",
    """Actividad de laboratorio 2. Recibe un GID `G` y un mínimo `P`. Muestra `USUARIO: N` para los usuarios cuyo grupo primario es `G` y que tienen `P` o más procesos.
    Si ningún usuario tiene ese GID como primario, o ninguno llega a `P`, muestra el error correspondiente y termina.""",
    usage="G P", cmds="`ps -u --no-headers`, `wc -l`, `/etc/passwd`", structs="`while IFS=: read`, `(( ))`, banderas `hay_grupo` y `hay_umbral`",
    detail="Son dos situaciones distintas y llevan códigos distintos. El grupo `p31g` tiene GID 23102 y es primario de `p31g1` y `p31g2`.",
    success="Una línea por usuario que cumple.",
    tests=[T("umbral", "Filtra por GID y número de procesos.", ok(["23102", "2"], val="p31g1: 3", prepare=_grupo), ok(["23102", "1"], val="p31g1: 3\np31g2: 1"), ok(["23102", "3"], val="p31g1: 3"))],
    errors=[E("uso", 1, "Recibe G y P.", "uso: gid-umbral.sh G P", ["1"], []),
            E("formato", 2, "G y P son enteros.", "G y P deben ser enteros", ["a", "1"], ["1", "b"]),
            E("sin-grupo", 4, "Algún usuario tiene G como grupo primario.", "ningún usuario tiene ese grupo primario", ["99999", "1"]),
            E("sin-umbral", 5, "Algún usuario llega a P procesos.", "ningún usuario llega a ese número de procesos", dict(args=["23102", "9"], prepare=_grupo), eg=False)],
    examples=[eg("23102 2", prepare=_grupo)],
    solution=r"""
#!/bin/bash
error() { echo "$1" >&2; exit "$2"; }
(($#!=2)) && error "uso: gid-umbral.sh G P" 1
[[ ! $1 =~ ^[0-9]+$ || ! $2 =~ ^[0-9]+$ ]] && error "G y P deben ser enteros" 2
hay_grupo=0
hay_umbral=0
while IFS=: read -r usuario c u gid resto; do
  ((gid!=$1)) && continue
  hay_grupo=1
  procesos=$(ps -u "$usuario" --no-headers | wc -l)
  if ((procesos>=$2)); then
    echo "$usuario: $procesos"
    hay_umbral=1
  fi
done < /etc/passwd
((hay_grupo==0)) && error "ningún usuario tiene ese grupo primario" 4
((hay_umbral==0)) && error "ningún usuario llega a ese número de procesos" 5
exit 0
""")

practice.add(
    "por-usuario", "Autónomo 1: listado ordenado por usuario",
    """Ejercicio autónomo 1. Lista todos los procesos con PID, usuario y línea de comandos completa, ordenados por usuario y sin cabecera.""",
    cmds="`ps -e`, `-o pid,user,cmd`, `--sort user`, `--no-headers`", structs="`(($#!=0))`",
    detail="`comm` es solo el nombre del comando; `cmd` es la línea completa con opciones. No mezcles estilos: `ps -ef` y `ps ef` hacen cosas muy distintas.",
    success="Una línea por proceso.",
    tests=[T("contenido", "Incluye la línea de comandos completa.", ok(rx=r"^\s*[0-9]+\s+p31a\s+sleep 900\s*$", prepare=_base)),
           T("orden", "Agrupa y ordena por usuario.", probe("""$S | awk '{print $2}' | uniq | LC_ALL=C sort -c && [ -z "$($S | awk '{print $2}' | uniq | sort | uniq -d)" ] && [ -n "$($S)" ]""", user="learner"))],
    errors=[E("uso", 1, "No recibe argumentos.", "uso: por-usuario.sh", ["x"])],
    examples=[eg("| tail -n 3", prepare=_base)],
    solution=r"""
#!/bin/bash
(($#!=0)) && { echo "uso: por-usuario.sh" >&2; exit 1; }
ps -eo pid,user,cmd --no-headers --sort user
exit 0
""")

practice.add(
    "mas-cpu", "Autónomo 6: los que más CPU han consumido",
    """Ejercicio autónomo 6, ampliado. Muestra PID, comando y tiempo de CPU de los N procesos que más tiempo de CPU han consumido, de mayor a menor y sin cabecera. Por defecto, N es 5.""",
    usage="[N]", cmds="`ps -eo pid,comm,time`, `--sort -time`, `head -n`", structs="`${1:-5}`, `[[ =~ ]]`",
    detail="El signo de `--sort` indica el sentido: `-time` es decreciente. `time` es el acumulado de CPU; `pcpu` es un porcentaje.",
    success="N líneas.",
    tests=[T("cantidad", "Devuelve N líneas ordenadas.", probe("""[ "$($S | wc -l)" = 5 ] && [ "$($S 2 | wc -l)" = 2 ] && [ "$($S 7 | wc -l)" = 7 ] && $S 7 | awk '{print $3}' | LC_ALL=C sort -rc""", user="learner", prepare=_base),
             ok(["1"], rx=r"^\s*[0-9]+\s+\S+\s+[0-9:-]+\s*$"))],
    errors=[E("uso", 1, "Recibe como mucho un número.", "uso: mas-cpu.sh [N]", ["1", "2"]),
            E("formato", 2, "N es un entero positivo.", "N debe ser un entero positivo", ["x"], ["0"])],
    examples=[eg("2")],
    solution=r"""
#!/bin/bash
(($#>1)) && { echo "uso: mas-cpu.sh [N]" >&2; exit 1; }
n=${1:-5}
[[ ! $n =~ ^0*[1-9][0-9]*$ ]] && { echo "N debe ser un entero positivo" >&2; exit 2; }
ps -eo pid,comm,time --no-headers --sort -time | head -n "$n"
exit 0
""")

practice.add(
    "antiguos", "Autónomo 7: los procesos más antiguos",
    """Ejercicio autónomo 7. Muestra PID, comando, tiempo de CPU y tiempo transcurrido desde su inicio de los N procesos que llevan más tiempo ejecutándose, del más antiguo al más reciente y sin cabecera. Por defecto, N es 10.""",
    usage="[N]", cmds="`ps -eo pid,comm,time,etime`, `--sort start_time`", structs="`${1:-10}`",
    detail="`etime` es el tiempo transcurrido, `time` el de CPU: un proceso que duerme acumula mucho del primero y casi nada del segundo. El más antiguo es el PID 1.",
    success="N líneas, empezando por el PID 1.",
    tests=[T("orden", "Empieza por el PID 1 y devuelve N líneas.", probe("""[ "$($S | wc -l)" = "$(ps -e --no-headers | wc -l | awk '{print ($1<10?$1:10)}')" ] && [ "$($S 3 | wc -l)" = 3 ] && [ "$($S 1 | awk '{print $1}')" = 1 ]""", user="learner", prepare=_base),
             ok(["1"], rx=r"^\s*1\s+\S+\s+[0-9:-]+\s+[0-9:-]+\s*$"))],
    errors=[E("uso", 1, "Recibe como mucho un número.", "uso: antiguos.sh [N]", ["1", "2"]),
            E("formato", 2, "N es un entero positivo.", "N debe ser un entero positivo", ["x"])],
    examples=[eg("2")],
    solution=r"""
#!/bin/bash
(($#>1)) && { echo "uso: antiguos.sh [N]" >&2; exit 1; }
n=${1:-10}
[[ ! $n =~ ^0*[1-9][0-9]*$ ]] && { echo "N debe ser un entero positivo" >&2; exit 2; }
ps -eo pid,comm,time,etime --no-headers --sort start_time | head -n "$n"
exit 0
""")

_cmd = f"""pkill -KILL -f '^sleep 901$' ; {asuser('p31b')} sleep 901 >/dev/null 2>&1 </dev/null &
sleep 0.4"""
practice.add(
    "buscar-cmd", "Autónomos 8 y 10: buscar en la línea de comandos",
    """Muestra los PID, uno por línea, de los procesos cuya línea de comandos contiene una cadena, **excluyendo al propio script**. Con `-c` muestra solo cuántos son.""",
    usage="[-c] CADENA", cmds="`pgrep -f`, `grep -vx`, `wc -l`", structs="`$$`, `shift`",
    detail="`pgrep bash` compara el nombre; `pgrep -f bash` compara la línea completa. El script contiene la cadena en sus propios argumentos, así que se encontraría a sí mismo: descártalo con `$$`. Guarda antes el resultado de `pgrep` en una variable, sin tubería: `$(pgrep ... | grep ...)` crea un sub-shell con tu misma línea de comandos y `pgrep` también lo vería.",
    success="Los PID, o el recuento.",
    tests=[T("encuentra", "Encuentra el proceso real.", probe("""pid=$(pgrep -u p31b -f '^sleep 901$'); [ -n "$pid" ] && $S 'sleep 90[1]' | grep -qx "$pid" """, prepare=_cmd),
             probe("""n=$($S -c 'sleep 901'); [ "$n" -ge 1 ] && [ "$n" -lt 8 ]""")),
           T("no-se-cuenta", "No se incluye a sí mismo.", probe("""c=zzp31; c="${c}zz"; o=$($S "$c"); n=$($S -c "$c"); [ -z "$o" ] && [ "$n" = 0 ]"""))],
    errors=[E("uso", 1, "Recibe la cadena, con -c opcional delante.", "uso: buscar-cmd.sh [-c] CADENA", [], ["-c"])],
    examples=[eg("-c 'sleep 901'", prepare=_cmd)],
    solution=r"""
#!/bin/bash
contar=0
if [[ $1 == -c ]]; then contar=1; shift; fi
(($#!=1)) && { echo "uso: buscar-cmd.sh [-c] CADENA" >&2; exit 1; }
todos=$(pgrep -f -- "$1")
lista=$(echo "$todos" | grep -vx "$$")
if ((contar==1)); then
  if [[ -z $lista ]]; then echo 0; else echo "$lista" | wc -l; fi
else
  [[ -n $lista ]] && echo "$lista"
fi
exit 0
""")

practice.add(
    "no-root", "Autónomo 13: procesos que no son de root",
    """Ejercicio autónomo 13. Muestra PID, usuario, comando y memoria virtual (`vsz`) de los procesos que no pertenecen a `root`, sin cabecera.""",
    cmds="`ps -eo pid,user,comm,vsz`, `ps -N -u root` o `grep -v`", structs="tuberías",
    detail="`ps -u root -N` invierte la selección. Si filtras con `grep -v root`, descartarías también un proceso cuyo comando contenga esa palabra.",
    success="Una línea por proceso.",
    tests=[T("contenido", "Incluye los procesos ajenos.", ok(rx=r"^\s*[0-9]+\s+p31a\s+sleep\s+[0-9]+\s*$", prepare=_base)),
           T("exclusion", "No incluye a root.", probe("""o=$($S); [ -n "$o" ] && ! echo "$o" | awk '{print $2}' | grep -qx root""", user="learner"))],
    errors=[E("uso", 1, "No recibe argumentos.", "uso: no-root.sh", ["x"])],
    examples=[eg("| grep p31a", prepare=_base)],
    solution=r"""
#!/bin/bash
(($#!=0)) && { echo "uso: no-root.sh" >&2; exit 1; }
ps -N -u root -o pid,user,comm,vsz --no-headers
exit 0
""")

_stop = "pkill -KILL -f '^sleep 904$' ;\n" + spawn(("p31b", 2)) + "\npkill -STOP -u p31b -x sleep\nsleep 0.2"
practice.add(
    "estado", "Ejemplo 3: procesos en un estado exacto",
    """Apartado 4.3. Muestra PID, usuario y estado de los procesos cuyo estado es **exactamente** el indicado, sin cabecera. `S` no debe incluir `Ss` ni `S+`, y `T` no debe incluir `Ts`, el estado de un proceso detenido que además es líder de sesión. Si no hay ninguno, muestra `ninguno`.""",
    usage="ESTADO", cmds="`ps -eo pid,user,stat`, `grep -E` o `awk`", structs="`[[ =~ ]]`, variable intermedia, `${var:-ninguno}`",
    detail="La hoja busca `' S +[0-9]'` porque tras el estado hay un número. En una expresión regular el `+` de `S+` es un metacarácter y hay que escaparlo. Los códigos están en la sección *PROCESS STATE CODES* de `man ps`.",
    success="Una línea por proceso, o `ninguno`.",
    tests=[T("detenidos", "Encuentra procesos detenidos reales.", ok(["Ts"], ref="ps -eo pid,user,stat --no-headers | awk '$3==\"Ts\"'", prepare=_stop), ok(["Ts"], has="p31b")),
           T("exacto", "Coincide de forma exacta.", probe("""! $S T | grep -q p31b"""), probe("""o=$($S S); [ -z "$o" ] || ! echo "$o" | awk '{print $3}' | grep -qvx S"""), ok(["Zl"], val="ninguno"))],
    errors=[E("uso", 1, "Recibe exactamente un estado.", "uso: estado.sh ESTADO", [], ["S", "T"]),
            E("formato", 2, "El estado empieza por una letra mayúscula.", "estado no válido", ["1"], ["s"])],
    examples=[eg("Ts", prepare=_stop)],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: estado.sh ESTADO" >&2; exit 1; }
[[ ! $1 =~ ^[A-Z][A-Za-z\<+]*$ ]] && { echo "estado no válido" >&2; exit 2; }
lista=$(ps -eo pid,user,stat --no-headers | awk -v e="$1" '$3==e')
echo "${lista:-ninguno}"
exit 0
""")

practice.add(
    "por-tamano", "Ejemplo 2: ordenar por tamaño",
    """Apartado 4.2. Muestra PID, comando y tamaño (`size`) de todos los procesos, de menor a mayor tamaño, sin cabecera y con un solo espacio entre campos, sin espacio inicial.""",
    cmds="`ps --no-headers -eo pid,comm,size`, `tr -s ' '`, `sort -n`", structs="tuberías",
    detail="`--sort size` no ordena de forma numérica, por eso la hoja recurre a `sort`. `ps` deja un espacio inicial que desplaza la numeración de los campos para `sort -t ' ' -k`.",
    success="Una línea por proceso.",
    tests=[T("orden", "Ordena de forma numérica.", probe("""o=$($S); [ -n "$o" ] && echo "$o" | awk '{print $NF}' | sort -nc && ! echo "$o" | grep -q '^ ' && ! echo "$o" | grep -q '  '""", user="learner", prepare=_base),
             ok(has=" sleep "))],
    errors=[E("uso", 1, "No recibe argumentos.", "uso: por-tamano.sh", ["x"])],
    examples=[eg("| head -n 2")],
    solution=r"""
#!/bin/bash
(($#!=0)) && { echo "uso: por-tamano.sh" >&2; exit 1; }
ps --no-headers -eo pid,comm,size | tr -s ' ' | sed 's/^ //' | sort -t ' ' -k 3 -n
exit 0
""")

_vict = f"""pkill -KILL -f '^sleep 90[34]$' ; pkill -KILL -f '^p31terco -c'
{asuser('learner')} sleep 903 >/dev/null 2>&1 </dev/null &
{asuser('learner')} sleep 904 >/dev/null 2>&1 </dev/null &
{asuser('learner')} bash -c 'exec -a p31terco bash -c "trap \\"\\" TERM; while :; do sleep 1; done"' >/dev/null 2>&1 </dev/null &
sleep 0.4
pkill -STOP -f '^sleep 904$'
sleep 0.2"""
practice.add(
    "matar", "Terminar un proceso de forma ordenada",
    """Apartado 6. Envía `SIGTERM` al PID indicado, espera un segundo y, si sigue vivo, envía `SIGKILL`. Muestra `terminado con SIGTERM` o `terminado con SIGKILL`.""",
    usage="PID", cmds="`kill`, `kill -9`, `kill -0`, `sleep`", structs="`if kill -0 ...; then`, `2>/dev/null`",
    detail="`SIGTERM` pide terminar y se puede ignorar; un proceso **detenido** no lo atiende hasta reanudarse; `SIGKILL` lo elimina el núcleo. `kill -0` no envía nada: solo comprueba si el proceso existe.",
    success="Una línea con la señal que lo terminó.",
    tests=[T("sigterm", "Un proceso normal acaba con SIGTERM.", probe("""p=$(pgrep -u learner -f '^sleep 903$'); [ -n "$p" ] && [ "$($S "$p")" = "terminado con SIGTERM" ] && sleep 0.2 && ! kill -0 "$p" 2>/dev/null""", user="learner", prepare=_vict, timeout=15)),
           T("detenido", "Un proceso detenido necesita SIGKILL.", probe("""p=$(pgrep -u learner -f '^sleep 904$'); [ -n "$p" ] && [ "$($S "$p")" = "terminado con SIGKILL" ] && sleep 0.2 && ! kill -0 "$p" 2>/dev/null""", user="learner", prepare=_vict, timeout=15)),
           T("ignora", "Un proceso que ignora SIGTERM necesita SIGKILL.", probe("""p=$(pgrep -u learner -f '^p31terco -c'); [ -n "$p" ] && [ "$($S "$p")" = "terminado con SIGKILL" ]""", user="learner", prepare=_vict, timeout=15))],
    errors=[E("uso", 1, "Recibe exactamente un PID.", "uso: matar.sh PID", []),
            E("formato", 2, "El PID es un número.", "el PID debe ser un número", ["x"]),
            E("no-existe", 4, "El proceso existe y se le pueden enviar señales.", "no se puede enviar señales a ese proceso", ["999999"], ["1"])],
    examples=[eg("999999")],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: matar.sh PID" >&2; exit 1; }
[[ ! $1 =~ ^[0-9]+$ ]] && { echo "el PID debe ser un número" >&2; exit 2; }
if ! kill -0 "$1" 2>/dev/null; then
  echo "no se puede enviar señales a ese proceso" >&2
  exit 4
fi
kill "$1" 2>/dev/null
sleep 1
if kill -0 "$1" 2>/dev/null; then
  kill -9 "$1" 2>/dev/null
  echo "terminado con SIGKILL"
else
  echo "terminado con SIGTERM"
fi
exit 0
""")

practice.add(
    "senal", "Números y nombres de señales",
    """Convierte entre número y nombre de señal con la orden `kill -l`: `9` da `KILL` y `TERM` da `15`. Acepta también el prefijo: `SIGHUP` da `1`.""",
    usage="NUMERO|NOMBRE", cmds="`kill -l`, `man 7 signal`", structs='`if ! r=$(kill -l "$1" 2>/dev/null); then`',
    detail="`kill` es a la vez una orden interna de Bash y un programa; `kill -l` sin argumentos muestra la lista completa.",
    success="La conversión.",
    tests=[T("conversiones", "Convierte en ambos sentidos.", ok(["9"], val="KILL"), ok(["15"], val="TERM"), ok(["TERM"], val="15"), ok(["KILL"], val="9"), ok(["SIGHUP"], val="1"), ok(["2"], val="INT"))],
    errors=[E("uso", 1, "Recibe exactamente un valor.", "uso: senal.sh NUMERO|NOMBRE", []),
            E("senal", 4, "La señal existe.", "señal desconocida", ["NOEXISTE"], ["999"])],
    examples=[eg("9"), eg("TERM")],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: senal.sh NUMERO|NOMBRE" >&2; exit 1; }
if ! resultado=$(kill -l "$1" 2>/dev/null); then
  echo "señal desconocida" >&2
  exit 4
fi
echo "$resultado"
exit 0
""")

practice.add(
    "lanza", "Procesos en segundo plano y wait",
    """Apartado 7. Lanza N procesos `sleep 0.7` **en segundo plano**, espera a que terminen todos y muestra `lanzados: N` y `terminados: N`, contando los `wait` correctos.""",
    usage="N", cmds="`&`, `wait`, `$!`, `jobs`", structs="`for ((i=0;i<n;i++))`, vector de PID `pids+=($!)`",
    detail="Con `&` todos corren a la vez: 5 procesos tardan unos 0,7 s en total, no 3,5 s. Sin `wait`, el script terminaría dejándolos huérfanos. `$!` es el PID del último proceso lanzado en segundo plano.",
    success="Las dos líneas.",
    tests=[T("concurrente", "Lanza en paralelo y espera.", probe("""i=$(date +%s%N); o=$($S 5); f=$(date +%s%N); ms=$(( (f-i)/1000000 )); [ "$o" = "lanzados: 5
terminados: 5" ] && [ "$ms" -ge 650 ] && [ "$ms" -lt 2500 ]""", user="learner", timeout=20)),
           T("sin-huerfanos", "No deja procesos al terminar.", probe("""[ "$($S 2 | head -n 1)" = "lanzados: 2" ] && ! pgrep -u learner -f '^sleep 0.7$' >/dev/null""", user="learner", timeout=20))],
    errors=[E("uso", 1, "Recibe exactamente un número.", "uso: lanza.sh N", []),
            E("formato", 2, "N es un entero positivo.", "N debe ser un entero positivo", ["x"], ["0"])],
    examples=[eg("3")],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: lanza.sh N" >&2; exit 1; }
[[ ! $1 =~ ^0*[1-9][0-9]*$ ]] && { echo "N debe ser un entero positivo" >&2; exit 2; }
pids=()
for ((i=0;i<$1;i++)); do
  sleep 0.7 &
  pids+=($!)
done
terminados=0
for pid in "${pids[@]}"; do
  wait "$pid" && ((terminados++))
done
echo "lanzados: ${#pids[@]}"
echo "terminados: $terminados"
exit 0
""")

_padre = f"""pkill -KILL -f '^bash -c sleep 905 & sleep 905' ; pkill -KILL -f '^sleep 905$' ; {asuser('learner')} bash -c 'sleep 905 & sleep 905 & wait' >/dev/null 2>&1 </dev/null &
sleep 0.4"""
practice.add(
    "hijos", "Procesos hijos de un PID",
    """Apartado 5. Muestra `PID COMANDO` de los hijos directos de un proceso, ordenados por PID. Si no tiene hijos, muestra `sin hijos`. Es la relación padre-hijo que dibuja `pstree`.""",
    usage="PID", cmds="`ps --ppid`, `-o pid,comm`, `pstree`, `/proc`", structs="`[[ -d /proc/$1 ]]`, variable intermedia",
    detail="`ps --ppid N` devuelve 1 si no hay coincidencias. Comprueba la existencia del proceso aparte: cada proceso tiene su directorio en `/proc`.",
    success="Una línea por hijo, o `sin hijos`.",
    tests=[T("hijos", "Lista los hijos reales.", probe("""p=$(pgrep -u learner -f '^bash -c sleep 905 & sleep 905'); [ -n "$p" ] && [ "$($S "$p" | tr -s ' ' | sed 's/^ //')" = "$(pgrep -P "$p" | sort -n | sed 's/$/ sleep/')" ]""", user="learner", prepare=_padre)),
           T("sin-hijos", "Indica si no tiene hijos.", probe("""p=$(pgrep -u learner -f '^sleep 905$' | head -n 1); [ -n "$p" ] && [ "$($S "$p")" = "sin hijos" ]""", user="learner", prepare=_padre))],
    errors=[E("uso", 1, "Recibe exactamente un PID.", "uso: hijos.sh PID", []),
            E("formato", 2, "El PID es un número.", "el PID debe ser un número", ["x"]),
            E("no-existe", 4, "El proceso existe.", "el proceso no existe", ["999999"])],
    examples=[eg("1")],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: hijos.sh PID" >&2; exit 1; }
[[ ! $1 =~ ^[0-9]+$ ]] && { echo "el PID debe ser un número" >&2; exit 2; }
[[ ! -d /proc/$1 ]] && { echo "el proceso no existe" >&2; exit 4; }
lista=$(ps --ppid "$1" -o pid,comm --no-headers --sort pid)
echo "${lista:-sin hijos}"
exit 0
""")

practice.add(
    "top-lote", "top en modo no interactivo",
    """Apartado 2. Usa `top` en modo por lotes para contar los procesos de un usuario: ejecuta una sola actualización, salta la cabecera y muestra el número de líneas de procesos.""",
    usage="USUARIO", cmds="`top -b -n 1 -u`, `tail -n +8`, `wc -l`, `id`", structs='`if ! id "$1" ...; then`',
    detail="Sin `-b`, `top` espera una terminal interactiva y no termina: en un script necesita `-b` y `-n`. Su cabecera ocupa 7 líneas; compruébalo antes.",
    success="Un número.",
    tests=[T("cuentas", "Coincide con los procesos reales.", ok(["p31a"], val="3", prepare=_base, timeout=20), ok(["p31b"], val="1", timeout=20), ok(["p31c"], val="0", timeout=20))],
    errors=[E("uso", 1, "Recibe exactamente un usuario.", "uso: top-lote.sh USUARIO", []),
            E("usuario", 4, "El usuario existe.", "el usuario no existe", ["nadie"])],
    examples=[eg("p31a", prepare=_base)],
    solution=r"""
#!/bin/bash
(($#!=1)) && { echo "uso: top-lote.sh USUARIO" >&2; exit 1; }
if ! id "$1" >/dev/null 2>&1; then
  echo "el usuario no existe" >&2
  exit 4
fi
top -b -n 1 -u "$1" | tail -n +8 | grep -c .
exit 0
""")
