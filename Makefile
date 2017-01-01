.PHONY: run clean test collectstatic run-in-prod run-uwsgi-test

VCAP_APP_PORT ?= 8000

run:
	python WeCron/manage.py runserver 0.0.0.0:$(VCAP_APP_PORT)

run-in-prod: clean syncdb collectstatic
	uwsgi --ini=deploy/conf/uwsgi.ini.j2 --http :$(VCAP_APP_PORT) 

run-uwsgi-test:
	uwsgi --chdir=WeCron \
		--module=wecron.wsgi:application \
		--env DJANGO_SETTINGS_MODULE=wecron.settings \
		--strict \
		--http :$(VCAP_APP_PORT) \
		--worker-reload-mercy=5 \
		--enable-threads \
		--processes=4 \
		--master \
		# --home=/path/to/virtual/env \   # optional path to a virtualenv

collectstatic:
	python WeCron/manage.py collectstatic --noinput -v0 --clear

clean:
	find . -name '*.pyc' -delete
	rm -rf WeCron/staticfiles
	rm -rf staticfiles

syncdb:
	python WeCron/manage.py migrate --noinput

release: test
	ansible-playbook deploy/playbook.yml -v

test:
	cd WeCron && \
		python -Wall manage.py test && \
		python manage.py check

test-coverage:
	cd WeCron && \
		coverage run manage.py test && \
		python manage.py check