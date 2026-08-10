# CoparentaL ALF

Proyecto Django para gestionar la coparentalidad entre dos personas (padre y
madre) dentro de un **grupo coparental**: calendario compartido, gastos y
manutención, comunicación interna, y un canal por cada profesional externo
(médico, psicólogo, abogado, dentista, asistenta social, profesor, tutor
legal) con su propia biblioteca de documentos.

## Tecnologías

- Python 3.10
- Django 5.2
- MySQL (configurable desde un archivo `.env`)
- django-allauth (login, registro, restablecimiento de contraseña)
- Celery + Redis (envío asíncrono de correos: invitaciones, notificaciones)
- WeasyPrint (generación de PDFs de resumen financiero)
- Whitenoise (estáticos en producción)

## Requisitos previos

- Python 3.10
- MySQL Workbench o MySQL Server, con una base de datos creada
- Redis (para la cola de Celery)
- Una cuenta de Gmail con verificación en 2 pasos, para generar una
  [contraseña de aplicación](https://myaccount.google.com/apppasswords) y
  poder enviar correos reales (invitaciones, restablecer contraseña)

## 1. Crear y activar el entorno virtual

```bash
python3 -m venv envdjango4.2
source envdjango4.2/bin/activate
```

## 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

> `requirements.txt` está desactualizado respecto al entorno real (falta
> Celery, Redis, WeasyPrint, y fija `Django==4.2.30` mientras el proyecto
> corre sobre Django 5.2). Si preparas un entorno nuevo desde cero, revisa
> qué falta con `pip freeze` contra un entorno que ya funcione.

## 3. Configurar variables de entorno

Edita el archivo `.env` en la raíz del proyecto (nunca se sube a git):

```env
SECRET_KEY=tu_secret_key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Base de datos MySQL
DB_NAME=nombre_de_tu_base
DB_USER=tu_usuario_mysql
DB_PASSWORD=tu_contraseña
DB_HOST=127.0.0.1
DB_PORT=3306

# Envío de correo vía Gmail SMTP (contraseña de aplicación, no la del login normal)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=xxxxxxxxxxxxxxxx
DEFAULT_FROM_EMAIL=CoparentaL ALF <tu_correo@gmail.com>
```

Sin las variables `EMAIL_*`, el proyecto cae por defecto al backend de
consola: los correos (invitaciones, restablecer contraseña) solo se
imprimen en la terminal, no se entregan de verdad.

## 4. Ejecutar migraciones

```bash
python manage.py migrate
```

## 5. Levantar Redis y Celery (necesario para invitaciones y notificaciones)

Las invitaciones (coparental y de profesionales) y las notificaciones de
actividad se envían de forma asíncrona con Celery. Sin esto, el correo
nunca sale.

```bash
redis-server &                                   # broker
celery -A coparental_alf worker --loglevel=INFO & # procesa las tareas
celery -A coparental_alf beat --loglevel=INFO &   # tareas periódicas
```

## 6. Iniciar el servidor

```bash
python manage.py runserver
```

## Modelo de privacidad: cada grupo es un ecosistema cerrado

Regla número uno del proyecto: **ningún grupo coparental puede ver ni
tocar el contenido de otro**. Cada vez que se crea un grupo (un padre y una
madre), todo lo que generan —calendario, pagos, gastos, chat interno, Canal
ALF— queda aislado exclusivamente para ese grupo y sus profesionales
autorizados. Un grupo distinto (otra pareja, otra familia) jamás ve nada de
un grupo ajeno, aunque usen la misma instalación del proyecto.

Esto se aplica mediante:

- Un campo `grupo` (FK a `GrupoCoparental`) en cada modelo con datos
  familiares: `calendario.Evento`, `finanzas.Pago`, `finanzas.Gasto`,
  `comunicacion.Mensaje`, y los canales de `core` (`CanalRol`,
  `MensajeCanal`, `DocumentoCanal`).
- El decorador `core.decorators.solo_padres` (y su equivalente para
  class-based views, `SoloPadresMixin`): exige que el usuario tenga perfil
  de padre/madre y filtra automáticamente todo por `request.grupo`.
- Los profesionales externos (`MiembroExterno`) solo ven el canal de su
  propio rol dentro del grupo al que fueron invitados — ni siquiera ven
  Calendario, Finanzas o Comunicación, que son exclusivos de padre/madre.

## Autenticación y cuentas

Basado en `django-allauth`, con plantillas propias (no las genéricas del
paquete) para mantener el mismo diseño de marca:

- Login: `/accounts/login/`
- Crear cuenta: `/accounts/signup/` (el correo es obligatorio: lo usan las
  invitaciones, el restablecimiento de contraseña y las notificaciones)
- Restablecer contraseña: `/accounts/password/reset/`

Tras iniciar sesión, `LOGIN_REDIRECT_URL` lleva al dashboard del grupo
(`core:dashboard`) — o, si quien entra es un profesional externo, directo a
su propio canal.

## Invitaciones

**Coparental** (`core:invitar`): el padre o la madre invita a la otra
persona por correo con un enlace único (token). Quien recibe el correo
puede abrirlo desde cualquier dispositivo con acceso a ese correo; si no
tiene cuenta, la crea con el email precargado y queda unido al grupo
automáticamente.

**Profesional externo** (`core:invitar_externo`): mismo mecanismo, pero
además de correo se elige un rol (médico, psicólogo, abogado, dentista,
asistenta social, profesor, tutor legal). El acceso del profesional queda
pendiente hasta que **ambos** progenitores lo aprueben (`core:panel_externos`).

## Canal ALF

Panel accesible desde la barra de navegación (`core:canal_alf`, solo para
padre/madre) con una categoría por rol profesional, más "General / Otros"
para lo que no pertenece a ningún profesional en concreto. Cada categoría
es un canal con:

- Historial de mensajes (el "chat interno" de ese rol).
- Biblioteca de documentos/PDFs subidos y clasificados en esa categoría.

Al compartir un archivo se elige a qué rol pertenece, se sube el PDF y se
deja un comentario — ambos quedan juntos en la biblioteca de ese rol. Cada
profesional externo autorizado solo ve el canal de su propio rol; padre y
madre ven los ocho canales completos del grupo.

## Estructura del proyecto

- `core`: usuarios, grupos coparentales, invitaciones, Canal ALF, dashboard
- `calendario`: eventos (visitas, vacaciones)
- `finanzas`: pagos de manutención y gastos compartidos 50/50
- `comunicacion`: chat interno entre padre y madre
- `notificaciones`: módulo de notificaciones

## Comandos útiles

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic   # necesario tras editar CSS/JS/imágenes,
                                  # porque los estáticos se sirven desde
                                  # staticfiles/, no desde static/ directamente
```

## Despliegue en producción

Ver [DEPLOY.md](DEPLOY.md) para la guía completa de despliegue en un VPS
(gunicorn, systemd, nginx, HTTPS, checklist de `.env`).

## Notas importantes

- El archivo `.env` contiene datos sensibles (incluida la contraseña de
  aplicación de Gmail) y nunca debe compartirse ni subirse a git.
- `media/` (comprobantes, fotos de perfil, documentos de Canal ALF) y
  `staticfiles/` están en `.gitignore`: son contenido subido por usuarios o
  archivos generados, no código fuente. Nunca deben versionarse.
- Si cambias dependencias, actualiza `requirements.txt`.
- Si vuelves a trabajar en el proyecto, activa primero el entorno virtual:

```bash
source envdjango4.2/bin/activate
```
