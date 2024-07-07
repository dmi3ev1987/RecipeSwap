python manage.py makemigrations --no-input
python manage.py migrate --no-input
python manage.py collectstatic --no-input
cp -r /app/collected_static/. /backend_static/static/ 
python manage.py loaddata db.json
gunicorn --bind 0.0.0.0:7000 backend.wsgi

exec "$@"