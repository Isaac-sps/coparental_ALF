# Despliegue en un VPS (Hostinger)

Guía para poner CoparentaL ALF en producción. Asume Ubuntu/Debian en el VPS,
con Redis ya instalado y corriendo (según lo configuraste).

## 0. Antes de nada

Estos ajustes ya están hechos en el código (agosto 2026), pero si vienes de
una versión anterior, confírmalos:

- `STORAGES`/whitenoise en `settings.py` (antes `STATICFILES_STORAGE` como
  string, que dejó de funcionar en Django 5 sin avisar).
- `DATABASES` lee de `.env` (antes tenía usuario/contraseña de MySQL
  hardcodeados en el código).
- `SITE_URL` configurable por `.env` (si no, los enlaces de los correos de
  invitación apuntan a `localhost`).
- Ajustes de seguridad (`SECURE_SSL_REDIRECT`, cookies seguras, HSTS) se
  activan solos cuando `DEBUG=False`.

## 1. Paquetes del sistema en el VPS

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential \
  libmysqlclient-dev pkg-config \
  libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0 \
  nginx redis-server mysql-server certbot python3-certbot-nginx
```

(`libpango`/`libcairo`/`libgdk-pixbuf` son para WeasyPrint, que genera los
PDFs de finanzas — sin ellas, la exportación de PDF falla en producción.)

## 2. Base de datos MySQL

```sql
CREATE DATABASE coparental_alf CHARACTER SET utf8mb4;
CREATE USER 'coparental_alf'@'localhost' IDENTIFIED BY 'UNA_CONTRASEÑA_FUERTE_NUEVA';
GRANT ALL PRIVILEGES ON coparental_alf.* TO 'coparental_alf'@'localhost';
FLUSH PRIVILEGES;
```

No reutilices la contraseña de desarrollo local.

## 3. Clonar y preparar el proyecto

```bash
cd /var/www
git clone https://github.com/Isaac-sps/coparental_ALF.git
cd coparental_ALF

python3 -m venv envdjango4.2
source envdjango4.2/bin/activate
pip install -r requirements.txt
```

## 4. Archivo `.env` de producción

Crea `/var/www/coparental_ALF/.env` (nunca lo subas a git — ya está en
`.gitignore`). Genera una `SECRET_KEY` nueva, distinta a la de desarrollo:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Contenido del `.env`:

```ini
SECRET_KEY=<la generada arriba>
DEBUG=False
ALLOWED_HOSTS=leonelwebstudio.com,www.leonelwebstudio.com
SITE_URL=https://leonelwebstudio.com
CSRF_TRUSTED_ORIGINS=https://leonelwebstudio.com,https://www.leonelwebstudio.com

DB_NAME=coparental_alf
DB_USER=coparental_alf
DB_PASSWORD=<la contraseña que pusiste en MySQL>
DB_HOST=127.0.0.1
DB_PORT=3306

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=<la contraseña de tu Redis>

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=<contraseña de aplicación de Gmail>
DEFAULT_FROM_EMAIL=CoparentaL ALF <tu_correo@gmail.com>
```

## 5. Migraciones y estáticos

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser   # opcional, para entrar al /admin/
```

## 6. Gunicorn (systemd)

`/etc/systemd/system/coparental_alf.service`:

```ini
[Unit]
Description=CoparentaL ALF (gunicorn)
After=network.target mysql.service redis-server.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/coparental_ALF
EnvironmentFile=/var/www/coparental_ALF/.env
ExecStart=/var/www/coparental_ALF/envdjango4.2/bin/gunicorn \
  --workers 3 \
  --bind unix:/run/coparental_alf.sock \
  coparental_alf.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## 7. Celery worker + beat (systemd)

`/etc/systemd/system/coparental_alf-worker.service`:

```ini
[Unit]
Description=CoparentaL ALF (celery worker)
After=network.target redis-server.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/coparental_ALF
EnvironmentFile=/var/www/coparental_ALF/.env
ExecStart=/var/www/coparental_ALF/envdjango4.2/bin/celery -A coparental_alf worker --loglevel=INFO
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Sin esto, las invitaciones por correo (padre→madre, padre/madre→profesional)
se quedan encoladas para siempre y nunca se envían — el `.delay()` solo
encola la tarea, un worker corriendo es quien realmente la ejecuta.

`/etc/systemd/system/coparental_alf-beat.service` (solo si usas tareas
periódicas programadas; hoy el proyecto no tiene ninguna configurada, así
que puedes omitir este servicio por ahora):

```ini
[Unit]
Description=CoparentaL ALF (celery beat)
After=network.target redis-server.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/coparental_ALF
EnvironmentFile=/var/www/coparental_ALF/.env
ExecStart=/var/www/coparental_ALF/envdjango4.2/bin/celery -A coparental_alf beat --loglevel=INFO
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Activar todo:

```bash
sudo chown -R www-data:www-data /var/www/coparental_ALF
sudo systemctl daemon-reload
sudo systemctl enable --now coparental_alf coparental_alf-worker
sudo systemctl status coparental_alf coparental_alf-worker
```

## 8. Nginx

`/etc/nginx/sites-available/coparental_alf`:

```nginx
server {
    listen 80;
    server_name leonelwebstudio.com www.leonelwebstudio.com;

    client_max_body_size 20M;  # sube archivos (PDFs, fotos) al Canal ALF

    location /media/ {
        alias /var/www/coparental_ALF/media/;
    }

    location / {
        proxy_pass http://unix:/run/coparental_alf.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Importante:** solo `/media/` necesita esta regla de nginx. Los estáticos
(`/static/...`) los sirve directamente `WhiteNoiseMiddleware` desde
gunicorn — no hace falta (ni conviene) duplicarlos en nginx.

```bash
sudo ln -s /etc/nginx/sites-available/coparental_alf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 9. HTTPS

```bash
sudo certbot --nginx -d leonelwebstudio.com -d www.leonelwebstudio.com
```

Certbot ajusta nginx automáticamente para redirigir a HTTPS y renovar el
certificado solo. Con `SECURE_SSL_REDIRECT=True` (ya activo por defecto
cuando `DEBUG=False`), Django también fuerza HTTPS del lado de la app.

## 10. Verificación final

- `sudo systemctl status coparental_alf coparental_alf-worker nginx redis-server mysql`
  — todos deben decir `active (running)`.
- Entra a `https://leonelwebstudio.com/accounts/login/` — debe cargar con el
  candado verde.
- Envía una invitación de prueba (coparental o profesional) y confirma que
  el enlace del correo apunta a `https://leonelwebstudio.com/...`, no a
  `localhost`.
- Sube un documento en Canal ALF y confirma que `Ver PDF`/descargar
  funciona (pasa por la vista protegida de Django, no por nginx).
- Revisa `sudo journalctl -u coparental_alf-worker -f` mientras envías una
  invitación, para confirmar que el correo realmente sale.

## Actualizaciones futuras

Cada vez que subas cambios nuevos:

```bash
cd /var/www/coparental_ALF
git pull
source envdjango4.2/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart coparental_alf coparental_alf-worker
```
