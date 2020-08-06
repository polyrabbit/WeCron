.PHONY: run clean test docs collectstatic run-in-prod run-uwsgi-test

VCAP_APP_PORT ?= 8000
PORT ?= $(VCAP_APP_PORT)

run:
	python WeCron/manage.py runserver 0.0.0.0:$(PORT)

run-in-prod: clean syncdb collectstatic reschedule
	# uwsgi --ini=deploy/conf/uwsgi.ini.j2 --http :$(PORT) 
	exec uwsgi --ini=deploy/conf/uwsgi.ini --http :$(PORT)

run-uwsgi-test:
	uwsgi --chdir=WeCron \
		--module=wecron.wsgi:application \
		--env DJANGO_SETTINGS_MODULE=wecron.settings \
		--strict \
		--http :$(PORT) \
		--worker-reload-mercy=5 \
		--enable-threads \
		--processes=4 \
		--master \
		# --home=/path/to/virtual/env \   # optional path to a virtualenv

docs:
	python -m grip --user-content --wide --export --title="提醒即服务 - Reminder as a Service" WeCron/remind/static/docs/raas.md WeCron/remind/static/docs/raas.html

collectstatic:
	python WeCron/manage.py collectstatic --noinput -v0 --clear

clean:
	find . -name '*.pyc' -delete
	rm -rf WeCron/staticfiles
	rm -rf staticfiles

syncdb:
	python WeCron/manage.py migrate --noinput

reschedule:
	python WeCron/manage.py missing_reschedule

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
