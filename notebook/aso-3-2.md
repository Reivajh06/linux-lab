---
title: 3.2 · Servicios, systemd y vi
folder: Prácticas ASO
order: 32
icon: server
tags: [systemd, servicios, vi]
---

Esta práctica enseña a consultar y administrar servicios con systemd, personalizar unidades mediante drop-ins y controlar sus recursos. También trabaja la edición con `vi` y la escritura de scripts Bash que validan entradas y separan resultados de errores. Las colecciones distinguen entre edición de ficheros, operaciones reales sobre unidades sin systemd activo y administración de servicios simulada.

> [!summary] Lo esencial
> - Arrancar un servicio y habilitarlo para futuros arranques son operaciones distintas.
> - Los targets agrupan unidades; el target predeterminado no tiene por qué ser el activo.
> - Personaliza mediante `UNIDAD.service.d/*.conf`, respetando las secciones de la unidad.
> - `daemon-reload`, `reload` y `restart` tienen efectos diferentes.
> - En `vi`, vuelve al modo normal con `Esc` antes de ejecutar órdenes.
> - `CPUQuota` limita, `CPUWeight` reparte y `MemoryMax` fija un techo de memoria.

## Entorno, targets y scripts Bash

systemd administra unidades, entre ellas servicios (`.service`) y grupos de unidades (`.target`). Muchos demonios tienen nombres terminados en `d`, como `sshd`, pero el nombre no basta para saber si están funcionando.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `systemctl get-default` | Consulta el target predeterminado. | `systemctl get-default` |
| `systemctl set-default` | Cambia el target de futuros arranques. | `systemctl set-default multi-user.target` |
| `readlink` | Lee el destino de un enlace simbólico. | `readlink /usr/lib/systemd/system/runlevel3.target` |
| `chmod u+x` | Permite al propietario ejecutar un script. | `chmod u+x consulta.sh` |
| `printf` y `>&2` | Escriben resultados o diagnósticos. | `printf '%s\n' 'Uso: SERVICIO' >&2` |
| `exit` | Termina el script con un código. | `exit 0` |

### Elegir el entorno correcto

> [!note] Las tres colecciones no tienen el mismo alcance
> `aso-p3-2` se centra en `vi`. `aso-bash-p3-2` usa unidades reales de Fedora y `systemctl --root=/`, sin systemd como PID 1; utiliza `atd.service` porque no está instalado `httpd`. La colección de 20 ejercicios proporciona simuladores de `systemctl`, `dnf`, `curl` y `firewall-cmd`.

```bash
# Solo en la colección de 20 ejercicios: seleccionar sus simuladores
export PATH="/home/learner/lab/aso-servicios/bin:$PATH"
systemctl get-default
systemctl set-default multi-user.target
```

En esa simulación no uses `sudo` ni rutas absolutas a los comandos: evitarías las herramientas preparadas. Los ejemplos de administración de Apache de esta página corresponden a ese entorno; en una VM con systemd real actúan sobre servicios reales y necesitan los privilegios adecuados.

Los enlaces de compatibilidad relacionan los niveles clásicos con targets: `0 → poweroff`, `1 → rescue`, `2/3/4 → multi-user`, `5 → graphical`, `6 → reboot`, todos con sufijo `.target`.

```bash
# En el entorno de unidades reales: consultar, no fijar la respuesta a mano
for n in {0..6}; do
    destino=$(readlink "/usr/lib/systemd/system/runlevel$n.target")
    printf '%s %s\n' "$n" "${destino##*/}"
done
```

### Contrato de los scripts

Resultados a stdout, errores a stderr y `exit 0` al completar correctamente. En los errores, stdout queda vacío; los códigos concretos dependen del ejercicio: por ejemplo, `1` para uso incorrecto y `2` para un valor no permitido en varios ejercicios simulados.

```bash
#!/bin/bash
# Consulta del ejercicio simulado: un servicio inactivo también es un resultado válido
if (( $# != 1 )); then
    printf '%s\n' 'Uso: SERVICIO' >&2
    exit 1
fi
case "$1" in
    httpd|sshd|cron) ;;
    *) printf '%s\n' 'Servicio no valido' >&2; exit 2 ;;
esac
if systemctl is-active "$1" >/dev/null; then
    printf '%s\n' 'ACTIVO'
else
    printf '%s\n' 'INACTIVO'
fi
exit 0
```

> [!tip] Validar antes de modificar
> Comprueba argumentos, rutas, nombres y valores antes de escribir configuraciones. No imprimas `OK` hasta comprobar que todas las operaciones han terminado correctamente.

## Servicios, Apache y cortafuegos

El estado de ejecución (`active` o `inactive`) es independiente de la habilitación (`enabled` o `disabled`). Una unidad `static` carece de instrucciones de habilitación y puede arrancar mediante dependencias de otras unidades.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `systemctl is-active` | Consulta si el servicio está activo. | `systemctl is-active httpd` |
| `systemctl is-enabled` | Consulta la habilitación. | `systemctl is-enabled httpd` |
| `systemctl start` / `stop` | Arranca o detiene ahora. | `systemctl stop httpd` |
| `systemctl enable` / `disable` | Configura o retira enlaces de habilitación. | `systemctl enable httpd` |
| `systemctl enable --now` | Habilita y arranca. | `systemctl enable --now httpd` |
| `systemctl restart` | Detiene y vuelve a arrancar. | `systemctl restart httpd` |
| `systemctl reload` | Solicita recargar la configuración propia del servicio. | `systemctl reload httpd` |
| `systemctl list-units` | Lista unidades y su estado de ejecución. | `systemctl list-units --type=service --all` |
| `systemctl list-unit-files` | Lista ficheros de unidad y su habilitación. | `systemctl list-unit-files --type=service --state=enabled` |
| `dnf list installed` | Comprueba el paquete instalado. | `dnf list installed httpd` |
| `curl -fsS` | Consulta HTTP y señala fallos. | `curl -fsS http://localhost` |
| `firewall-cmd` | Consulta o modifica servicios permitidos. | `firewall-cmd --list-services` |

```bash
# Simulación: arrancar Apache y comprobar ambas dimensiones
systemctl enable --now httpd
systemctl is-active httpd
systemctl is-enabled httpd
# El simulador devuelve dos columnas: UNIDAD ESTADO
systemctl list-units --type=service --all | awk '$2 == "active" {print $1}' | sort
```

```bash
# Unidades reales, sin contactar con un gestor systemd en ejecución
systemctl --root=/ list-unit-files --type=service --state=enabled \
    --no-legend --no-pager | awk '{print $1}' | sort
# Habilitar crea enlaces según [Install]; no arranca el servicio
# Estas modificaciones requieren root en el entorno de unidades reales
systemctl --root=/ enable atd.service
ls -l /etc/systemd/system/multi-user.target.wants/
```

> [!warning] Estados y columnas
> `is-active` e `is-enabled` pueden imprimir un estado válido aunque devuelvan un código distinto de cero. Además, la salida real de `list-units` tiene más columnas que el simulador: no reutilices su filtro de dos columnas. Evita `grep active`, que también coincide con `inactive`.

```bash
# Simulación: comprobar instalación y respuesta web por separado
if dnf list installed httpd >/dev/null 2>&1; then
    printf '%s\n' 'INSTALADO'
else
    printf '%s\n' 'NO INSTALADO'
fi
if curl -fsS http://localhost 2>/dev/null | grep -Fq 'Enhorabuena'; then
    printf '%s\n' 'WEB OK'
else
    printf '%s\n' 'Apache no disponible' >&2
    exit 3
fi
# Guardar la apertura de HTTP y aplicarla a la configuración activa
firewall-cmd --permanent --add-service=http && firewall-cmd --reload
firewall-cmd --list-services | grep -w 'http'
```

`http` y `https` son servicios distintos del cortafuegos. Que Apache esté instalado, activo o accesible localmente son comprobaciones diferentes; ninguna sustituye la consulta de las reglas.

## Ficheros de unidad y drop-ins

En las rutas trabajadas, una unidad completa en `/etc/systemd/system` tiene prioridad sobre `/run/systemd/system` y esta sobre `/usr/lib/systemd/system`. Usa `/etc` para personalizaciones persistentes del administrador y conserva el original del paquete en `/usr/lib`.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `less` / `cat` | Inspecciona el fichero de unidad. | `less /usr/lib/systemd/system/atd.service` |
| `mkdir -p` | Prepara el directorio de drop-ins. | `mkdir -p "$base/httpd.service.d"` |
| `printf '%s\n'` | Escribe una propiedad por línea. | `printf '%s\n' '[Unit]' 'Description=Mi servicio'` |
| `systemd-delta` | Muestra diferencias y extensiones locales. | `systemd-delta` |
| `systemctl daemon-reload` | Hace releer unidades y dependencias al gestor. | `systemctl daemon-reload` |
| `rm` / `rmdir` | Elimina un drop-in y un directorio vacío. | `rm "$base/httpd.service.d/descripcion.conf"` |
| `man 5 systemd.service` | Consulta propiedades de los servicios. | `man 5 systemd.service` |

### Secciones de una unidad

`[Unit]` contiene la descripción y dependencias; `[Service]`, cómo se ejecuta y controla el proceso; `[Install]`, cómo habilitarlo. `WantedBy=multi-user.target` permite crear el enlace de habilitación en `multi-user.target.wants/`.

```bash
# Fichero local de práctica: no instala ni arranca el servicio
base="$HOME/lab/aso-servicios/config-prueba"
mkdir -p "$base"
cat > "$base/descanso.service" <<'EOF'
[Unit]
Description=Servicio de practica
[Service]
Type=simple
ExecStart=/usr/bin/sleep 30
[Install]
WantedBy=multi-user.target
EOF
```

Al leer una propiedad en Bash, controla en qué sección estás con `while IFS= read -r linea`. Para las claves escalares del ejercicio conserva la última aparición de esa sección; `${linea#*=}` o `cut -d= -f2-` conserva los posibles `=` dentro del valor.

### Añadir y retirar personalizaciones

Un drop-in añade configuración en `UNIDAD.service.d/NOMBRE.conf`: no es necesario copiar toda la unidad. En la simulación se escribe dentro del directorio local recibido; en `aso-bash-p3-2` se trabaja como root sobre `/etc/systemd/system/atd.service.d/`.

```bash
# Continuación del ejemplo local: separar cada motivo de personalización
mkdir -p "$base/httpd.service.d"
printf '%s\n' '[Unit]' 'Description=My Apache HTTP Server' \
    > "$base/httpd.service.d/descripcion.conf"
printf '%s\n' '[Service]' 'Restart=on-failure' 'RestartSec=10' \
    > "$base/httpd.service.d/restart-policy.conf"
# En la simulación registra la recarga; no carga estos ficheros locales
systemctl daemon-reload
```

`Restart=on-failure` solicita un reinicio tras un fallo; `RestartSec=10` fija una espera de diez segundos. En el entorno real, `systemd-delta` identifica la unidad ampliada como `[EXTENDED]`; para deshacer un cambio concreto, elimina su `.conf` y vuelve a ejecutar `daemon-reload`.

> [!warning] Sustituir ExecStart
> Para reemplazar el comando de inicio, escribe en `[Service]` una línea vacía `ExecStart=` y después `ExecStart=COMANDO NUEVO`, conservando la ruta absoluta del ejecutable. Sin vaciarlo puedes añadir un segundo comando no permitido. En una VM real debes ejecutar `daemon-reload` y reiniciar el servicio para ejecutar el nuevo comando.

> [!note] Tres operaciones diferentes
> `daemon-reload` relee la configuración de systemd; `reload httpd` pide a Apache releer su propia configuración, si lo admite; `restart httpd` vuelve a ejecutar el servicio. Editar una unidad no ejecuta automáticamente su nuevo `ExecStart`.

## Edición con vi

`vi` distingue modo normal, inserción y órdenes que empiezan por `:`. Pulsa `Esc` para volver al modo normal; las teclas de edición de la tabla se usan desde ese modo.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `i` / `o` | Inserta o abre una línea debajo. | `o`, escribir `cierre`, `Esc` |
| `:w` / `:x` / `:q!` | Guarda, guarda y sale, o sale descartando cambios. | `:x` y `Enter` |
| `dd` / `3dd` | Borra una línea o tres desde el cursor. | `3dd` |
| `yy` / `p` | Copia una línea y pega debajo. | `yy` seguido de `p` |
| `x` / `r` | Borra un carácter o reemplaza uno. | `rE` |
| `cw` / `dw` | Cambia o borra una palabra desde el cursor. | `cwactivo`, `Esc` |
| `/texto`, `n`, `N` | Busca y repite hacia delante o atrás. | `/parado` y `Enter` |
| `u` / `Ctrl+R` | Deshace o rehace en Vim. | `u` |
| `:%s/origen/destino/g` | Sustituye en todo el fichero y todas las apariciones por línea. | `:%s/viejo/nuevo/g` |
| `:2,4d` | Borra las líneas 2 a 4, incluidas. | `:2,4d` |
| `vi -es -c` | Ejecuta órdenes sin interacción. | `vi -es -c '2,4d' -c x borrar.txt` |

```bash
# Abrir el fichero; dentro: i, escribir, Esc, :x y Enter
vi "$HOME/aso/p32/nota.txt"
# Automatizar una sustitución y guardar; e tolera que no haya coincidencias
vi -es -c '%s#viejo#nuevo#ge' -c x "$HOME/aso/p32/sustituir.txt"
# Usar # evita escapar las barras de estas rutas
vi -es -c '%s#/bin/#/sbin/#ge' -c x rutas.txt
# Contar las líneas restantes después de borrar un rango
vi -es -c '2,4d' -c x "$HOME/aso/p32/borrar.txt"
wc -l < "$HOME/aso/p32/borrar.txt"
```

> [!tip] Alcance de la sustitución
> `%` selecciona todas las líneas y `g` todas las coincidencias de cada línea. `grep -c` cuenta líneas coincidentes, no apariciones. Consulta `man vi`, `vimtutor` o `:help :substitute` para practicar.

## Recursos y cgroups

systemd aplica controles a grupos de procesos mediante cgroups. Una cuota es un techo; un peso solo influye en el reparto cuando los grupos compiten por CPU.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `systemctl set-property --runtime` | Aplica propiedades sin persistencia tras reiniciar el sistema. | `systemctl set-property --runtime httpd CPUQuota=25% MemoryMax=300M` |
| `systemctl set-property` | Aplica y guarda propiedades de forma persistente. | `systemctl set-property httpd CPUQuota=25% MemoryMax=300M` |
| `systemctl show` | Consulta propiedades del servicio. | `systemctl show httpd` |
| `cat /sys/fs/cgroup/memory.max` | Lee el techo de memoria del cgroup en bytes o `max`. | `cat /sys/fs/cgroup/memory.max` |
| `cat /sys/fs/cgroup/pids.max` | Lee el límite de tareas del cgroup o `max`. | `cat /sys/fs/cgroup/pids.max` |
| `read cuota periodo` | Lee cuota y período de CPU. | `read cuota periodo < /sys/fs/cgroup/cpu.max` |
| `man 5 systemd.resource-control` | Consulta controles de recursos. | `man 5 systemd.resource-control` |

`MemoryMin=1G` protege memoria frente a reclamación dentro de los límites de la jerarquía; no reserva ni asigna 1 GiB por adelantado. `MemoryMax=2G` fija un máximo; `CPUQuota=25%` limita al equivalente del 25 % de una CPU, no al 25 % de toda una máquina multinúcleo.

```bash
# Drop-in local de la actividad; base se definió en el ejemplo anterior
printf '%s\n' '[Service]' 'MemoryMin=1G' 'MemoryMax=2G' 'CPUWeight=50' \
    > "$base/httpd.service.d/recursos.conf"
# Simulación: aplicar una cuota temporal y consultar las propiedades guardadas
systemctl set-property --runtime httpd CPUQuota=25% MemoryMax=300M
systemctl show httpd
```

`CPUWeight` admite de 1 a 10000 y vale 100 por defecto. Con pesos 50 y 100, dos servicios que compiten en el mismo nivel reciben aproximadamente 1/3 y 2/3 de la CPU disponible; 50 no significa un límite del 50 %.

```bash
# Entorno de cgroups reales: calcular porcentajes sin suponer valores fijos
read cuota periodo < /sys/fs/cgroup/cpu.max
if [[ "$cuota" == max ]]; then
    printf '%s\n' 'cpu: sin límite de cuota en este cgroup'
else
    printf 'cpu: %s%%\n' "$((cuota * 100 / periodo))"
fi
# memory.max se convierte a MiB dividiendo entre 1024*1024, salvo si vale max
cat /sys/fs/cgroup/memory.max /sys/fs/cgroup/pids.max
```

## Comandos adicionales útiles

Estos comandos amplían el diagnóstico de servicios y scripts en Fedora; para consultar o administrar servicios en ejecución, usa una VM con systemd real y fuera del `PATH` de los simuladores.

| Comando | Para qué sirve | Ejemplo |
| --- | --- | --- |
| `systemctl status` | Resume el estado, los procesos y los mensajes recientes de una unidad. | `systemctl status httpd.service --no-pager -l` |
| `systemctl cat` | Muestra el fichero de unidad y sus drop-ins, indicando sus rutas de origen. | `systemctl cat httpd.service` |
| `systemctl edit` | Abre un drop-in para personalizar la unidad y recarga la configuración del gestor al guardar. | `sudo systemctl edit httpd.service` |
| `systemctl list-dependencies --reverse` | Consulta dependencias inversas entre las unidades cargadas para investigar qué unidades dependen de otra. | `systemctl list-dependencies --reverse httpd.service` |
| `systemctl reset-failed` | Limpia el estado de fallo y los contadores de reinicio y límite de arranques; no corrige la causa ni arranca el servicio. | `sudo systemctl reset-failed httpd.service` |
| `journalctl -u -b -n` | Filtra el registro por unidad, arranque actual y número de mensajes recientes. | `sudo journalctl -u httpd.service -b -n 50 --no-pager` |
| `systemd-analyze verify` | Detecta directivas desconocidas y problemas de unidades y dependencias sin arrancar el servicio. | `systemd-analyze verify ./descanso.service` |
| `systemd-cgtop` | Observa consumo de CPU, memoria y tareas por cgroup; la disponibilidad de métricas depende de la contabilidad habilitada. | `systemd-cgtop` |
| `ss -ltnp` | Lista sockets TCP en escucha con puertos numéricos y procesos asociados; root permite ver los de otros usuarios. | `sudo ss -ltnp 'sport = :80'` |
| `bash -n` | Comprueba la sintaxis de un script sin ejecutarlo; no detecta errores de lógica. | `bash -n ./consulta.sh` |
| `bash -x` | Ejecuta el script y escribe en stderr una traza de los comandos con sus argumentos expandidos. | `bash -x ./consulta.sh httpd` |
| `rpm -qf` | Identifica el paquete instalado al que pertenece un fichero de unidad. | `rpm -qf /usr/lib/systemd/system/httpd.service` |

```bash
# VM real: ver el estado y después el registro, aunque status indique un fallo
systemctl status httpd.service --no-pager -l; sudo journalctl -u httpd.service -b -n 50 --no-pager
```

```bash
# VM real: inspeccionar la unidad y sus drop-ins antes de verificar su configuración
systemctl cat httpd.service && systemd-analyze verify httpd.service
```

```bash
# Ejecutar con traza solo si la sintaxis es válida; guardar la traza y los errores juntos
bash -n ./consulta.sh && bash -x ./consulta.sh httpd 2>depuracion.log
```

> [!tip] Elegir la comprobación adecuada
> Prefiere `systemd-analyze verify` para revisar una unidad antes de arrancarla y `journalctl -u` para investigar fallos durante su ejecución; para un script Bash, empieza por `bash -n` y usa `bash -x` cuando necesites seguir lo que ejecuta.

## Errores frecuentes

- Confundir `enabled` con `active`, o usar `enable` esperando que arranque el proceso.
- Suponer que `set-default` cambia inmediatamente el target activo.
- Ejecutar operaciones de servicios reales en un contenedor sin systemd como PID 1.
- Usar `sudo` o rutas absolutas a comandos en la simulación y saltarse su `PATH`.
- Dejar creado `/run/systemd/system` en el contenedor de unidades reales: puede hacer que `systemctl` crea que hay un gestor activo.
- Poner `Description` en `[Service]`, olvidar el sufijo `.service.d` o modificar el fichero del paquete en vez de un drop-in.
- Omitir `daemon-reload`, confundirlo con `reload` o cambiar `ExecStart` sin vaciarlo antes.
- Buscar `active` o `http` como subcadenas y aceptar por error `inactive` o `https`.
- Salir de `vi` con `:q!` después de editar y esperar que se hayan guardado los cambios.
- Confundir peso con cuota de CPU, o copiar valores de cgroups en vez de leerlos.
- Mezclar diagnósticos con stdout, imponer códigos de otro ejercicio o anunciar éxito tras un fallo.

## Chuleta rápida

```bash
export PATH="/home/learner/lab/aso-servicios/bin:$PATH" # Solo colección simulada
systemctl get-default # Consultar target predeterminado
systemctl set-default multi-user.target # Configurar futuros arranques
systemctl is-active httpd # Estado de ejecución; puede devolver no cero
systemctl is-enabled httpd # Habilitación; independiente de active
systemctl enable --now httpd # Habilitar y arrancar en la simulación
systemctl restart httpd # Reiniciar el proceso
systemctl reload httpd # Recargar configuración propia de Apache
systemctl list-unit-files --type=service --state=enabled # Listar habilitados
systemctl daemon-reload # Releer unidades y drop-ins
systemctl set-property --runtime httpd CPUQuota=25% MemoryMax=300M # Temporal
firewall-cmd --permanent --add-service=http && firewall-cmd --reload # Abrir HTTP
curl -fsS http://localhost # Probar respuesta web
vi -es -c '%s#viejo#nuevo#ge' -c x fichero.txt # Sustituir y guardar
cat /sys/fs/cgroup/cpu.max # Cgroup real; leer fuera del simulador
```
