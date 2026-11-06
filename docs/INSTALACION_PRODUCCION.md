# Instalación en producción

Guía paso a paso para instalar Lexi Compliance en un servidor nuevo, con HTTPS, respaldos
nocturnos y una prueba de restauración. Está pensada para un servidor virtual (VPS) pequeño
con Docker; un consultorio o comercio no necesita más.

> Para trabajar en tu equipo usa el [arranque rápido del README](../README.md). Esta guía es
> solo para el servidor donde lo usará el cliente.

## Cómo queda instalado

```
Internet ──443/80──▶ Caddy ──▶ web (Next.js) ──▶ api (FastAPI) ──▶ postgres
                    (HTTPS)                                    └──▶ qdrant
                                                               └──▶ /data/storage (evidencias)
```

- **Solo Caddy publica puertos** (80 y 443). Postgres, Qdrant, la API y la web solo se ven
  dentro de la red interna de Docker. El navegador nunca habla con la API: lo hace la web.
- **Caddy consigue y renueva el certificado HTTPS solo** (Let's Encrypt) y redirige
  `http://` a `https://`.
- **La sesión** va en una cookie `Secure; HttpOnly; SameSite=Lax`: solo viaja por HTTPS y
  ningún script del navegador puede leerla.
- **La API se niega a arrancar** si falta algo crítico (ver [Revisión de arranque](#revisión-de-arranque)).
- **Respaldos** cada noche de la base, las evidencias y el índice del asistente, con una
  prueba semanal de que se pueden restaurar.

Archivos involucrados:

| Archivo | Para qué |
|---|---|
| `docker-compose.prod.yml` | La pila de producción |
| `.env.prod.example` | Plantilla de ajustes y secretos del servidor |
| `deploy/Caddyfile` | HTTPS, cabeceras de seguridad y proxy |
| `apps/web/Dockerfile.prod` | Compilación de producción de la web y contenedor de migraciones |
| `scripts/backup.sh` | Respaldo completo |
| `scripts/restore-test.sh` | Prueba que un respaldo se puede restaurar (sin tocar producción) |
| `scripts/restore.sh` | Restaura un respaldo sobre producción |

## Antes de empezar

Necesitas:

1. **Un servidor virtual** con Ubuntu 24.04 LTS, 2 GB de RAM y 25 GB de disco como mínimo
   (DigitalOcean, Hetzner, Vultr, Linode o similar; unos 5–10 USD al mes). Con 1 GB de RAM la
   compilación de la web puede quedarse sin memoria.
2. **Un dominio o subdominio**, por ejemplo `cumplimiento.consultorio.mx`.
3. **Una clave de OpenAI** (o un servidor Ollama propio) para el asistente.
4. Acceso SSH al servidor como un usuario con `sudo`.

## 1. Apuntar el dominio al servidor

En el panel de tu proveedor de dominio crea un **registro A** con el subdominio apuntando a la
IP pública del servidor. Comprueba desde tu equipo que ya resuelve (puede tardar unos minutos):

```bash
nslookup cumplimiento.consultorio.mx
```

Debe responder con la IP del servidor. **No sigas hasta que resuelva**: Caddy necesita que el
dominio apunte al servidor para obtener el certificado.

## 2. Preparar el servidor

Conéctate por SSH y actualiza el sistema:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git ufw
```

Firewall: solo SSH, HTTP y HTTPS.

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
sudo ufw enable
```

> Docker publica sus puertos por fuera de ufw. Por eso la pila de producción **no publica**
> los puertos de Postgres, Qdrant ni la API: aunque el firewall fallara, no están expuestos.

Instala Docker (script oficial) y permite usarlo sin `sudo`:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
```

Cierra la sesión SSH y vuelve a entrar para que el grupo surta efecto. Comprueba:

```bash
docker run --rm hello-world
```

## 3. Descargar el proyecto

```bash
sudo mkdir -p /opt/lexi && sudo chown "$USER" /opt/lexi
git clone https://github.com/Luiss11/lexi-compliance-platform.git /opt/lexi
cd /opt/lexi
```

## 4. Configurar `.env.prod`

```bash
cp .env.prod.example .env.prod
chmod 600 .env.prod
```

Genera los secretos (ejecuta el comando una vez por secreto y copia el resultado):

```bash
openssl rand -base64 48 | tr -d '/+=' | cut -c1-48
```

Edita el archivo (`nano .env.prod`) y rellena como mínimo:

| Variable | Valor |
|---|---|
| `DOMAIN` | Tu subdominio, sin `https://` |
| `ACME_EMAIL` | Correo para avisos de Let's Encrypt |
| `POSTGRES_PASSWORD` | Un secreto generado (solo letras y números) |
| `JWT_SECRET` | Otro secreto generado, distinto |
| `OPENAI_API_KEY` | Tu clave de OpenAI (o `LLM_PROVIDER=ollama`) |

Guarda una copia de `.env.prod` **fuera del servidor** (en un gestor de contraseñas). Sin la
contraseña de la base no podrás usar los respaldos en otro servidor.

## 5. Arrancar

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

O con make, si está instalado (`sudo apt install -y make`): `make prod-up`.

La primera vez tarda varios minutos (compila la web). El orden de arranque es automático:
Postgres → migraciones de la base → API (pasa la revisión de arranque) → web → Caddy.

Comprueba que todo está arriba:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
```

Deben aparecer `postgres`, `qdrant`, `api` y `web` en `Up` (la API y Postgres en `healthy`) y
`caddy` en `Up`. El servicio `migrate` aparece como terminado (`Exited (0)`): es normal, solo
corre al arrancar.

Abre `https://tu-dominio` en el navegador: debe mostrar la pantalla de inicio de sesión con
el candado de conexión segura.

## 6. Crear la primera organización

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -it api \
  python -m app.tools.create_tenant \
  --name "Clínica Dental Sonrisa" --slug clinica-sonrisa --sector clinica \
  --admin-name "Dra. Ana López" --admin-email ana@clinica.mx
```

Te pedirá la contraseña del administrador (mínimo 10 caracteres, con letras y números). Para
entrar en la web se usan el identificador (`clinica-sonrisa`), el correo y esa contraseña.
Desde ahí, el administrador da de alta al resto del equipo en **Usuarios**.

> En producción **no** corras `make seed`: crea usuarios de demostración con una contraseña
> pública.

## 7. Respaldos nocturnos

Crea la carpeta de respaldos y prueba un respaldo manual:

```bash
sudo mkdir -p /var/backups/lexi && sudo chown "$USER" /var/backups/lexi
scripts/backup.sh
scripts/restore-test.sh --latest
```

El segundo comando debe terminar con `RESTAURACIÓN PROBADA`. Qué comprueba:

1. Que los archivos del respaldo no están dañados (sumas SHA-256).
2. Que la base se restaura en un Postgres temporal y desechable.
3. Que **cada evidencia y cada PDF** registrados existen en el respaldo y su SHA-256 coincide
   con el que se selló al subirlos.
4. Que el índice del asistente (Qdrant) se puede leer.

Programa el respaldo cada noche y la prueba cada domingo (`crontab -e`):

```cron
0 3 * * *  /opt/lexi/scripts/backup.sh >> /var/log/lexi-backup.log 2>&1
30 4 * * 0 /opt/lexi/scripts/restore-test.sh --latest >> /var/log/lexi-backup.log 2>&1
```

Y crea el archivo de registro con permisos para tu usuario:

```bash
sudo touch /var/log/lexi-backup.log && sudo chown "$USER" /var/log/lexi-backup.log
```

Durante el respaldo Qdrant se detiene unos segundos para copiarlo de forma consistente; a las
3 a. m. nadie lo nota. Se conservan los últimos `BACKUP_KEEP_DAYS` días (14 por defecto).

### Copia fuera del servidor (muy recomendada)

Un respaldo que vive en el mismo servidor no sirve si el servidor se pierde. Dos opciones que
se pueden combinar:

- **Copias de seguridad del proveedor** (snapshots semanales del servidor completo). Se
  activan en su panel por ~1 USD/mes.
- **rclone** a un almacenamiento externo (Backblaze B2, Google Drive, S3…):

  ```bash
  sudo apt install -y rclone
  rclone config            # crea un "remote", por ejemplo llamado b2
  ```

  y en `.env.prod`: `BACKUP_REMOTE=b2:lexi-respaldos`. `backup.sh` copiará cada respaldo ahí.

## 8. Restaurar un respaldo

**Primero pruébalo** (no toca producción):

```bash
scripts/restore-test.sh /var/backups/lexi/20261106-030000
```

Si pasa, restaura. Esto **borra** los datos actuales y los reemplaza por los del respaldo:

```bash
scripts/restore.sh /var/backups/lexi/20261106-030000
```

Pide escribir `RESTAURAR` para confirmar. Detiene la web y la API, restaura base, archivos e
índice, y vuelve a levantar todo.

**En un servidor nuevo** (el anterior se perdió): sigue los pasos 1 a 5 de esta guía usando
el **mismo `.env.prod`** que guardaste, copia la carpeta del respaldo al servidor (o
descárgala con `rclone copy`) y ejecuta `scripts/restore.sh` sobre ella. No crees la
organización del paso 6: viene en el respaldo.

## 9. Actualizar a una versión nueva

```bash
cd /opt/lexi
scripts/backup.sh                       # siempre, antes de actualizar
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Las migraciones de la base se aplican solas al arrancar.

## Revisión de arranque

En producción (`APP_ENV=production`, que `docker-compose.prod.yml` pone siempre) la API se
niega a iniciar y explica qué corregir si:

- `JWT_SECRET` es un valor de ejemplo o tiene menos de 32 caracteres;
- `ALLOW_INSECURE_JWT_SECRET` está activo;
- la base usa la contraseña de desarrollo (`lexi_dev`), ninguna, o apunta a `localhost`;
- `LLM_PROVIDER=openai` y falta `OPENAI_API_KEY`, o `LLM_PROVIDER` no es válido;
- no se puede escribir en la carpeta de evidencias.

Además, `docker compose` no arranca si falta `DOMAIN`, `ACME_EMAIL` o algún dato de la base
en `.env.prod`.

## Problemas frecuentes

| Síntoma | Causa probable y solución |
|---|---|
| El navegador dice que el certificado no es válido | El dominio aún no apuntaba al servidor cuando arrancó Caddy, o el puerto 80 está cerrado. Revisa el paso 1 y el firewall y reinicia Caddy: `docker compose -f docker-compose.prod.yml --env-file .env.prod restart caddy`. Mira `logs caddy`. |
| `api` reinicia una y otra vez | No pasó la revisión de arranque. `docker compose -f docker-compose.prod.yml --env-file .env.prod logs api` dice qué falta en `.env.prod`. |
| `web` no arranca y `migrate` aparece con error | Una migración falló. Revisa `logs migrate`. |
| La compilación se detiene sin error claro | Poca memoria. Usa un servidor de 2 GB o añade swap: `sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile`. |
| `required variable ... is missing` al arrancar | Falta esa variable en `.env.prod`. |

Comandos útiles (desde `/opt/lexi`):

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod ps         # estado
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f api web caddy
docker compose -f docker-compose.prod.yml --env-file .env.prod restart web
tail -n 50 /var/log/lexi-backup.log                                       # respaldos
```

## Probar la pila de producción en tu equipo

Con `DOMAIN=localhost` en `.env.prod` y `LLM_PROVIDER=ollama` (para no necesitar clave),
`docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build` levanta la
pila en `https://localhost`. Caddy usa un certificado propio no público, así que el navegador
avisará de que no es de confianza: es lo esperado en local. Necesita los puertos 80 y 443
libres. Para apagarla: `docker compose -f docker-compose.prod.yml --env-file .env.prod down`
(los datos se conservan en volúmenes; `down -v` los borra).
