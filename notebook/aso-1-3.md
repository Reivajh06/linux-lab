---
title: 1.3 · Permisos, usuarios y grupos
folder: Prácticas ASO
order: 13
icon: shield
tags: [permisos, usuarios, grupos]
---

Esta práctica enseña a consultar y administrar usuarios, grupos, propietarios y permisos en Linux. Combina cambios con comandos de administración y scripts Bash que validan entradas, consultan el sistema real y preparan un directorio de trabajo compartido.

> [!summary] Lo esencial
> - Los permisos se dividen en propietario, grupo y otros; `r=4`, `w=2`, `x=1`.
> - `chmod` cambia permisos; `chown` y `chgrp` cambian la propiedad.
> - `umask` elimina permisos al crear objetos; no modifica los existentes.
> - SGID favorece la herencia del grupo; sticky restringe el borrado en directorios compartidos.
> - `usermod -aG` añade grupos secundarios; `gpasswd -A` establece administradores.
> - `chage` distingue entre caducidad de contraseña y caducidad de cuenta.

## Identidad, ficheros de cuentas y grupos

El UID identifica al usuario y el GID identifica al grupo. Cada cuenta tiene un grupo primario y puede pertenecer a varios secundarios; para consultar todas sus pertenencias conviene usar `id`.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `whoami` | Muestra el usuario efectivo actual. | `whoami` |
| `id` | Muestra UID, GID y grupos. | `id trabajador1` |
| `id -gn` | Muestra el nombre del grupo primario. | `id -gn trabajador1` |
| `id -nG` | Lista los nombres de todos los grupos. | `id -nG trabajador1` |
| `groups` | Consulta las pertenencias a grupos. | `groups trabajador1` |
| `getent` | Consulta una entrada de la base de cuentas o grupos. | `getent group empresa` |
| `grep -q` | Comprueba una coincidencia sin imprimirla. | `grep -q '^jefe:' /etc/passwd` |
| `man 5 passwd` | Explica el formato del fichero de cuentas. | `man 5 passwd` |

### Qué guarda cada fichero

- `/etc/passwd`: `nombre:clave:UID:GID:comentario:home:shell`; normalmente `x` remite la contraseña a shadow.
- `/etc/shadow`: hash o marca de bloqueo, último cambio y plazos de contraseña/cuenta; requiere privilegios.
- `/etc/group`: `nombre:clave:GID:miembros`; la lista explícita recoge miembros secundarios.
- `/etc/gshadow`: `grupo:clave:administradores:miembros`; permite distinguir administración y pertenencia.

```bash
# Buscar una cuenta completa: jefe no debe coincidir con jefe2.
grep '^jefe:' /etc/passwd
getent group empresa

# Separar los siete campos sin cambiar IFS para toda la sesión.
linea=$(getent passwd jefe)
IFS=: read -r nombre clave uid gid comentario hogar shell <<< "$linea"
printf 'UID=%s GID=%s home=%s shell=%s\n' "$uid" "$gid" "$hogar" "$shell"

# Comprobar pertenencia completa, incluido el grupo primario.
id -nG jefe | tr ' ' '\n' | grep -qx empresa
```

> [!note] Grupo primario
> No deduzcas todos los miembros de un grupo mirando solo el último campo de `/etc/group`. Para encontrar sus miembros primarios, cruza su GID con el cuarto campo de `/etc/passwd`.

## Leer y modificar permisos y propiedad

En `ls -l`, el primer carácter indica el tipo (`-` fichero, `d` directorio, `l` enlace), seguido de tres tríos `rwx`: usuario, grupo y otros. En un fichero, `r/w/x` permiten leer, escribir y ejecutar; en un directorio permiten listar nombres, modificar entradas y atravesarlo, respectivamente.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `ls -ld` | Muestra el directorio mismo, en lugar de su contenido. | `ls -ld /home/trabajo` |
| `cut -c1-10` | Extrae tipo y permisos del listado. | `ls -ld /etc/passwd \| cut -c1-10` |
| `stat -c` | Consulta modo simbólico, octal, propietario y grupo. | `stat -c '%A %a %U:%G' /etc/passwd` |
| `stat -L -c` | Consulta el destino de un enlace. | `stat -L -c '%a' enlace` |
| `chmod 640` | Establece los permisos ordinarios en octal. | `chmod 640 informe.txt` |
| `chmod u+x,go-w` | Añade ejecución al dueño y quita escritura a grupo/otros. | `chmod u+x,go-w tarea.sh` |
| `chmod o-rwx` | Quita todos los permisos de otros. | `chmod o-rwx informe.txt` |
| `chgrp` | Cambia el grupo propietario. | `sudo chgrp empresa informe.txt` |
| `chown usuario:grupo` | Cambia propietario y grupo. | `sudo chown jefe:empresa informe.txt` |

### Octal y notación simbólica

Cada dígito suma los permisos de una clase: `7=rwx`, `6=rw-`, `5=r-x`, `4=r--`, `0=---`. Así, `rwxrw-r--` equivale a `0764`, `640` a `rw-r-----` y `750` a `rwxr-x---`.

En notación simbólica, `u/g/o/a` significan usuario/grupo/otros/todos; `+` añade, `-` elimina y `=` asigna. Usa cambios relativos si el enunciado pide conservar los demás bits.

```bash
touch informe.txt
chmod 640 informe.txt           # Dueño lee/escribe; grupo solo lee.
chmod u+x,go-w informe.txt      # De 640 pasa a 740.
stat -c '%A %a %U:%G' informe.txt

sudo chgrp empresa informe.txt
sudo chown jefe:empresa informe.txt
ls -l informe.txt
```

> [!warning] Permisos de un directorio
> Entrar necesita `x`; crear o borrar entradas suele necesitar `w` y `x` en el directorio. El permiso de escritura del fichero no decide por sí solo si puede borrarse.
> Se aplica la clase correspondiente al usuario: propietario, grupo u otros; sus permisos no se suman.

## Máscara de creación y permisos especiales

`umask` elimina bits de los permisos solicitados al crear un objeto: normalmente se parte de `666` para ficheros y de `777` para directorios. El dígito inicial de un modo de cuatro cifras representa los bits especiales: SUID vale `4`, SGID `2` y sticky `1`.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `umask` | Consulta o establece la máscara de la shell. | `umask 077` |
| `chmod g+s` | Activa SGID; en directorios, los nuevos objetos heredan su grupo. | `sudo chmod g+s /home/equipo` |
| `chmod 2770` | Da acceso completo a dueño/grupo y activa SGID. | `sudo chmod 2770 /home/equipo` |
| `chmod +t` | Añade sticky sin cambiar los permisos ordinarios. | `sudo chmod +t /home/trabajo` |
| `chmod 1770` | Da acceso completo a dueño/grupo y activa sticky. | `sudo chmod 1770 /home/trabajo` |
| `find -perm -4000` | Busca entradas con el bit SUID activo. | `find /usr/bin -maxdepth 1 -type f -perm -4000` |
| `[[ -u/-g/-k ruta ]]` | Comprueba SUID, SGID o sticky, respectivamente. | `[[ -k /tmp ]]` |

```bash
# El subshell limita el cambio de máscara a estas creaciones.
(
    umask 077
    mkdir privado && printf 'hola\n' > privado/nota.txt
)
stat -c '%a %n' privado privado/nota.txt  # 700 y 600, si eran nuevos.

# Calcular quitando bits, no mediante una resta decimal.
m=033
printf 'fichero: %03o\n' "$((8#666 & ~8#$m))"     # 644
printf 'directorio: %03o\n' "$((8#777 & ~8#$m))"  # 744

# Auditar SUID y SGID por separado, sin descender a subdirectorios.
find /usr/bin -maxdepth 1 -type f -perm -4000 | sort
find /usr/bin -maxdepth 1 -type f -perm -2000 | sort
```

### Interpretar los bits especiales

- **SUID en un ejecutable**: al ejecutarlo adopta el UID efectivo de su propietario; ejemplo de la práctica: `/usr/bin/passwd`.
- **SGID en un ejecutable**: adopta el GID efectivo del grupo propietario; en un directorio facilita compartir el grupo de los nuevos objetos.
- **Sticky en un directorio**: restringe borrado y renombrado a quien posee la entrada, al dueño del directorio o a un usuario privilegiado; ejemplo: `/tmp`.

> [!tip] Minúsculas y mayúsculas
> `s` o `t` indican bit especial y ejecución en esa posición; `S` o `T`, bit especial sin ejecución. El modo `1770` se ve como `drwxrwx--T`: sticky está activo aunque otros no tengan `x`.
> SGID no concede escritura al grupo por sí solo; los permisos de creación y la máscara siguen contando.

> [!warning] Dos confusiones habituales
> `umask 033` deja un fichero normal en `644`, no en `633`; `umask` tampoco cambia objetos existentes.
> En `find`, `-perm -4000` exige ese bit; `-perm 4000` exige exactamente ese modo.

## Administrar cuentas, grupos y contraseñas

Las altas y los cambios de cuentas se realizan con privilegios de administrador, usando `sudo` en la terminal del laboratorio. Crear una cuenta no establece una contraseña utilizable: asignarla y configurar su caducidad son operaciones distintas.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `useradd -m -U -s` | Crea home, grupo privado y shell indicada. | `sudo useradd -m -U -s /bin/bash jefe` |
| `passwd` | Asigna o cambia una contraseña de forma interactiva. | `sudo passwd jefe` |
| `chpasswd` | Recibe líneas `usuario:clave` por entrada estándar. | `printf '%s:%s\n' "$usuario" "$clave" \| sudo chpasswd` |
| `usermod -L` | Bloquea la contraseña anteponiendo `!` al hash. | `sudo usermod -L trabajador1` |
| `groupadd` | Crea un grupo. | `sudo groupadd empresa` |
| `usermod -aG` | Añade grupos secundarios conservando los anteriores. | `sudo usermod -aG empresa jefe` |
| `gpasswd -a` | Añade un miembro al grupo. | `sudo gpasswd -a trabajador1 empresa` |
| `gpasswd -A` | Establece la lista de administradores del grupo. | `sudo gpasswd -A jefe empresa` |
| `chage -M -W -I` | Configura máximo, aviso y gracia, en días. | `sudo chage -M 60 -W 4 -I 2 jefe` |
| `chage -E` | Establece caducidad de cuenta; `-1` la elimina. | `sudo chage -E 2026-12-15 trabajador1` |
| `chage -l` | Consulta la política y las fechas de una cuenta. | `sudo chage -l trabajador1` |

```bash
# Alta de una cuenta nueva; las contraseñas se eligen en la variante manual.
sudo useradd -m -U -s /bin/bash jefe
sudo passwd jefe
sudo groupadd empresa
sudo usermod -aG empresa jefe
sudo gpasswd -A jefe empresa
sudo getent gshadow empresa | cut -d: -f3  # Administradores.

# Política de la actividad 8; presupone que las cuatro cuentas existen.
sudo chage -M 60 -W 4 -I 2 -E -1 jefe
for u in trabajador1 trabajador2 trabajador3; do
    sudo chage -M 60 -W 4 -I 2 -E 2026-12-15 "$u"
done
sudo chage -l trabajador1
```

`-M 60` limita la edad de la contraseña; `-W 4` avisa antes de que caduque. `-I 2` permite dos días de gracia después de esa caducidad: no mide los días desde el último inicio de sesión; `-E` fija otra fecha, la de caducidad de la cuenta.

### Leer shadow y convertir fechas

Los campos de `/etc/shadow` son nombre, clave, último cambio, mínimo, máximo, aviso, inactividad, caducidad de cuenta y reservado. Un campo de clave vacío significa sin contraseña; si empieza por `!` o `*`, no permite autenticación mediante esa contraseña.

```bash
# Shadow guarda fechas como días desde 1970-01-01; usar UTC evita desfases.
date -u -d "@$((20802 * 86400))" +%F  # 2026-12-15
segundos=$(date -u -d '2026-12-15' +%s)
printf '%s\n' "$((segundos / 86400))"  # 20802
```

> [!warning] Pertenencia y administración
> `usermod -G` sin `-a` sustituye los grupos secundarios anteriores; `gpasswd -A` sustituye la lista de administradores. Nombrar administrador no sustituye el paso de añadirlo como miembro.
> En una tubería para asignar claves, quien necesita `sudo` es `chpasswd`, no `printf`.

## Scripts verificables y actividad compartida

Los ejercicios Bash combinan parámetros, validaciones y cambios reales del sistema: el resultado debe calcularse, no escribirse a mano. Antes de modificar nada, comprueba argumentos, formato, existencia y privilegios según el enunciado; en altas por lote, valida todos los nombres antes de crear la primera cuenta.

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `chmod u+x` | Hace ejecutable el script para su dueño. | `chmod u+x consulta.sh` |
| `[[ -f/-d/-e ruta ]]` | Comprueba fichero regular, directorio o existencia. | `[[ -d "$1" ]]` |
| `[[ valor =~ patrón ]]` | Valida un formato. | `[[ $modo =~ ^[0-7]{3}$ ]]` |
| `printf ... >&2` | Envía un diagnóstico a stderr. | `printf 'Fichero no valido\n' >&2` |
| `exit` | Devuelve el estado de terminación. | `exit 0` |
| `mkdir -p` | Crea el directorio y los padres que falten. | `sudo mkdir -p /home/trabajo` |

```bash
#!/bin/bash
# Ejemplo de consulta: resultados en stdout y errores en stderr.
if (( $# != 1 )); then
    printf 'Uso: RUTA\n' >&2
    exit 1
fi
if [[ ! -e $1 ]]; then
    printf 'Ruta inexistente\n' >&2
    exit 2
fi
ls -ld -- "$1" | cut -c1-10
exit 0
```

Los códigos y mensajes concretos dependen del ejercicio: éxito es `0`, pero un resultado negativo como `NO EXISTE` o `NO` también puede ser una consulta correcta con salida `0`. Usa comillas en `"$1"` y guarda `$?` inmediatamente si necesitas examinar el estado del comando anterior.

### Estado final de la actividad 8

La variante `aso-p1-3` pide `jefe` y tres trabajadores con home y Bash, contraseñas establecidas, política `60/4/2`, grupo secundario `empresa` y `jefe` como único administrador. Los trabajadores caducan el `2026-12-15`, el jefe no caduca, y cada cuenta conserva su grupo primario individual.

```bash
# Con las cuentas y el grupo ya preparados, terminar el espacio compartido.
sudo mkdir -p /home/trabajo
sudo chown jefe:empresa /home/trabajo
sudo chmod 1770 /home/trabajo
stat -c '%U:%G %a %A' /home/trabajo
# Esperado: jefe:empresa 1770 drwxrwx--T
```

> [!note] Variantes de los ejercicios
> El ejercicio de SGID pide `2770`; el directorio final de empresa pide sticky y `1770`. La integradora reducida usa nombres `aso_p13_*`, dos trabajadores y pide no asignar contraseñas en texto claro; sigue siempre su enunciado.
> Para poder repetir una automatización, comprueba con `id` o `getent` antes de crear cuentas o grupos. Si el ejercicio pide rechazar objetos existentes, devuelve el error indicado.

## Comandos adicionales útiles

Estos comandos amplían las comprobaciones de acceso y permiten practicar con ACL y SELinux en Fedora; sus enlaces llevan a los manuales de referencia.

| Comando | Para qué sirve | Ejemplo |
| --- | --- | --- |
| [`namei -l`](https://man7.org/linux/man-pages/man1/namei.1.html) | Desglosa una ruta mostrando permisos, propietario y grupo de cada componente; ayuda a localizar un directorio sin permiso de paso. | `namei -l /home/trabajo` |
| [`getfacl -p`](https://man7.org/linux/man-pages/man1/getfacl.1.html) | Consulta las listas de control de acceso (ACL), su máscara y las ACL por defecto, conservando las rutas absolutas. | `getfacl -p /home/trabajo` |
| [`setfacl -m`](https://man7.org/linux/man-pages/man1/setfacl.1.html) | Añade o modifica permisos para un usuario o grupo concreto mediante ACL. | `setfacl -m u:trabajador1:r-- informe.txt` |
| [`setfacl -d -m`](https://man7.org/linux/man-pages/man1/setfacl.1.html) | Define una ACL por defecto en un directorio para los objetos nuevos; los permisos solicitados al crearlos limitan lo heredado. | `sudo setfacl -d -m g:empresa:rwx /home/equipo` |
| [`runuser -u`](https://man7.org/linux/man-pages/man1/runuser.1.html) | Ejecuta una comprobación con la identidad de otra cuenta; requiere privilegios de administrador. | `sudo runuser -u trabajador1 -- test -w /home/trabajo` |
| [`install -d -m -g`](https://man7.org/linux/man-pages/man1/install.1.html) | Crea un directorio con modo y grupo explícitos en una sola operación. | `sudo install -d -m 2770 -g empresa /home/equipo-extra` |
| [`mktemp`](https://man7.org/linux/man-pages/man1/mktemp.1.html) | Crea un fichero temporal de nombre impredecible y acceso privado; con `-d`, crea un directorio. | `prueba=$(mktemp)` |
| [`newgrp`](https://man7.org/linux/man-pages/man1/newgrp.1.html) | Abre una shell con otro grupo efectivo, por ejemplo tras añadir la cuenta actual a ese grupo; `exit` vuelve a la anterior. | `newgrp empresa` |
| [`getcap -v`](https://man7.org/linux/man-pages/man8/getcap.8.html) | Consulta las capacidades de un ejecutable, que pueden conceder privilegios sin usar SUID; muestra la ruta aunque no tenga capacidades. | `getcap -v /usr/bin/ping` |
| [`matchpathcon -V`](https://man7.org/linux/man-pages/man8/matchpathcon.8.html) | Comprueba si la etiqueta SELinux de una ruta coincide con la prevista por la política. | `matchpathcon -V /home/trabajo` |
| [`restorecon -n -v`](https://man7.org/linux/man-pages/man8/restorecon.8.html) | Muestra los cambios de etiqueta SELinux propuestos sin aplicarlos; al quitar `-n`, los aplica. | `sudo restorecon -n -v /home/trabajo` |

```bash
# Con trabajador1 ya creado, revisar la ruta y comprobar si puede escribir.
namei -l /home/trabajo && sudo runuser -u trabajador1 -- test -w /home/trabajo && printf 'Puede escribir\n'
```

```bash
# Probar una ACL en un fichero temporal propio y consultar el resultado.
prueba=$(mktemp) && setfacl -m u:trabajador1:r-- "$prueba" && getfacl -p "$prueba"
```

```bash
# Previsualizar la corrección SELinux y verificar la etiqueta actual, aún sin modificarla.
sudo restorecon -n -v /home/trabajo && matchpathcon -V /home/trabajo
```

> [!tip] Cuándo preferir una ACL
> Prefiere `setfacl` cuando necesites dar acceso a una cuenta concreta sin cambiar el grupo propietario ni abrir permisos a otros. Revisa con `getfacl` la entrada `mask::`, que limita los permisos efectivos de usuarios nombrados y grupos; una ACL por defecto solo se hereda en objetos nuevos y no concede acceso al propio directorio.

## Errores frecuentes

- Confundir `ls -l directorio` con `ls -ld directorio`: el segundo consulta el directorio mismo.
- Leer los diez caracteres de `ls` como nueve permisos: el primero es el tipo.
- Usar un modo octal fijo cuando solo se pide añadir `u+x` o quitar `o-rwx`.
- Intentar solucionar un problema de propiedad únicamente con `chmod`.
- Aplicar `chown -R` cuando se pide cambiar un único fichero.
- Confundir grupo propietario, grupo primario, miembro secundario y administrador del grupo.
- Pensar que sticky impide modificar el contenido de un fichero: restringe borrar o renombrar entradas.
- Interpretar `-I` como tiempo sin iniciar sesión o `-M` como fecha de baja de la cuenta.
- Imprimir mensajes auxiliares en stdout o devolver éxito después de un cambio fallido.
- Convertir los límites de validación de un ejercicio en reglas generales de Linux.

## Chuleta rápida

```bash
whoami                                             # Usuario efectivo.
id trabajador1                                     # UID, GID y grupos.
id -nG trabajador1                                 # Nombres de todos sus grupos.
getent passwd trabajador1                          # Datos de la cuenta.
ls -ld /home/trabajo                               # Tipo, permisos y propiedad.
stat -c '%A %a %U:%G' informe.txt                   # Simbólico, octal y dueño:grupo.
chmod 640 informe.txt                              # rw-r-----.
chmod u+x,go-w tarea.sh                            # Cambio relativo.
(umask 077; mkdir privado && touch privado/nota)    # Nuevos objetos: 700 y 600.
sudo useradd -m -U -s /bin/bash nuevo               # Cuenta con home y grupo privado.
sudo usermod -aG empresa trabajador1                # Añadir grupo secundario.
sudo gpasswd -A jefe empresa                       # Establecer administrador.
sudo chown jefe:empresa /home/trabajo               # Propietario y grupo.
sudo chmod 1770 /home/trabajo                       # Acceso u/g y sticky.
sudo chage -M 60 -W 4 -I 2 -E 2026-12-15 trabajador1 # Política y caducidad.
```
