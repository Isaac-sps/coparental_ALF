# Coparental Alf

Proyecto Django para gestionar funcionalidades de calendario, finanzas, comunicación y notificaciones.

## Tecnologías

- Python 3.10
- Django 4.2.30
- MySQL (configurable desde un archivo .env)
- Django REST/templating básico para las apps del proyecto

## Requisitos previos

- Tener Python 3.10 instalado
- Tener MySQL Workbench o MySQL Server disponible
- Tener acceso a una base de datos MySQL

## 1. Crear y activar el entorno virtual

```bash
python3 -m venv envdjango4.2
source envdjango4.2/bin/activate
```

## 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

## 3. Configurar la base de datos MySQL

1. Crear una base de datos en MySQL Workbench.
2. Editar el archivo .env en la raíz del proyecto con tus datos reales:

```env
SECRET_KEY=tu_secret_key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=nombre_de_tu_base
DB_USER=tu_usuario_mysql
DB_PASSWORD=tu_contraseña
DB_HOST=127.0.0.1
DB_PORT=3306
```

## 4. Ejecutar migraciones

```bash
python manage.py migrate
```

## 5. Iniciar el servidor

```bash
python manage.py runserver
```

## Estructura del proyecto

- core: vista principal y dashboard
- calendario: manejo de eventos
- finanzas: módulo financiero
- comunicacion: módulo de comunicación
- notificaciones: módulo de notificaciones

## Comandos útiles

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

## Notas importantes

- El archivo .env contiene datos sensibles y no debe compartirse públicamente.
- Si cambias dependencias, actualiza requirements.txt.
- Si vuelves a trabajar en el proyecto, activa primero el entorno virtual:

```bash
source envdjango4.2/bin/activate
```
