.PHONY: run clean test collectstatic run-in-prod run-uwsgi-test

run:
	python WeCron/manage.py runserver 0.0.0.0:8000

run-in-prod: syncdb collectstatic
	BLUEWARE_CONFIG_FILE=$(CURDIR)/blueware.ini blueware-admin run-program uwsgi --ini=uwsgi.ini

run-uwsgi-test:
	uwsgi --chdir=WeCron \
		--module=wecron.wsgi:application \
		--env DJANGO_SETTINGS_MODULE=wecron.settings \
		--http :8000 \
		# --home=/path/to/virtual/env \   # optional path to a virtualenv
		--processes=4 

collectstatic:
	python WeCron/manage.py collectstatic --noinput -v0 --clear

clean:
	find . -name '*.pyc' -delete
	rm -rf WeCron/staticfiles

syncdb:
	python WeCron/manage.py migrate --noinput

release:
	ansible-playbook deploy/playbook.yml -v
