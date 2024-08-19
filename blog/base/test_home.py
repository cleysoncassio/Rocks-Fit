import os
import sys
import django
from django.test import Client
from django.conf import settings
from django.test.utils import get_runner


def test_status_code(client:Client):
    resp=client.get('/')
    assert resp.status_code == 200

os.environ['DJANGO_SETTINGS_MODULE'] = 'sitio.settings'
django.setup()

TestRunner = get_runner(settings)
test_runner = TestRunner()
failures = test_runner.run_tests(['blog'])
sys.exit(failures)