"""Local fault-injection witnesses, not independent reviewer labels."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

ap = argparse.ArgumentParser()
ap.add_argument('--source', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
args = ap.parse_args()
sys.path.insert(0, str(args.source))
from django.conf import settings
settings.configure(INSTALLED_APPS=[], DATABASES={'default': {
    'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
    SECRET_KEY='public-local-witness-value', USE_I18N=False)
import django
django.setup()
from django.db import connection, models, transaction, IntegrityError
from django.db.models import signals
from django.db.models.deletion import Collector
from django.db.models.sql.subqueries import DeleteQuery


class Item(models.Model):
    name = models.CharField(max_length=20)
    class Meta:
        app_label = 'v18probe'


with connection.schema_editor() as editor:
    editor.create_model(Item)


def fail_signal(**kwargs):
    raise RuntimeError('deliberate signal fault')


rows = []
for scenario in ['fast_success', 'fast_SQL_exception', 'pre_delete_exception',
                 'post_delete_exception', 'outer_rollback_after_return']:
    item = Item.objects.create(name=scenario[:20])
    original_pk = item.pk
    row = {'scenario': scenario, 'pk_before': original_pk,
           'can_fast_delete_before_instrumentation': Collector(using='default').can_fast_delete(item)}
    signal = None
    if scenario in ['pre_delete_exception', 'post_delete_exception']:
        signal = getattr(signals, 'pre_delete' if scenario.startswith('pre') else 'post_delete')
        signal.connect(fail_signal, sender=Item, weak=False)
    row['can_fast_delete_during_scenario'] = Collector(using='default').can_fast_delete(item)
    try:
        if scenario == 'fast_SQL_exception':
            with patch.object(DeleteQuery, 'delete_batch', side_effect=IntegrityError('deliberate SQL fault')):
                item.delete()
        elif scenario == 'outer_rollback_after_return':
            with transaction.atomic():
                item.delete()
                row['delete_returned'] = True
                row['pk_immediately_after_return'] = item.pk
                row['row_exists_before_outer_rollback'] = Item.objects.filter(pk=original_pk).exists()
                raise RuntimeError('deliberate outer rollback after successful return')
        else:
            item.delete()
            row['delete_returned'] = True
    except Exception as error:
        row['exception'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        if signal is not None:
            signal.disconnect(fail_signal, sender=Item)
    row['pk_after'] = item.pk
    row['row_exists_after'] = Item.objects.filter(pk=original_pk).exists()
    rows.append(row)

with args.output.open('x') as f:
    json.dump({'django_version': django.get_version(), 'django_import_path': django.__file__,
               'database': 'SQLite :memory:', 'scenarios': rows,
               'fault_injection': True, 'independent_adjudication': False}, f, indent=2)
