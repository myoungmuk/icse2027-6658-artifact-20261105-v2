"""Targeted real ORM/SQLite checks; imported Django must be the selected full tree."""
import argparse
import hashlib
import json
import platform
import sqlite3
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--case', choices=['django__django-11179', 'django__django-13028'], required=True)
ap.add_argument('--source', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
args = ap.parse_args()
sys.path.insert(0, str(args.source))

# Python 3.12 removed stdlib distutils, imported by these historical Django
# packages. Setuptools supplies its real vendored implementation. Tested Django
# source and ORM/database logic remain unchanged.
import setuptools

from django.conf import settings
settings.configure(INSTALLED_APPS=['probeapp'], DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
                   SECRET_KEY='targeted-local-sqlite-check', USE_I18N=False, DEBUG=True)
import django
django.setup()
from django.db import connection, models
from django.db.models.deletion import Collector


def observe(call):
    try:
        return {'outcome': 'returned', 'value': call()}
    except Exception as error:
        return {'outcome': 'raised', 'exception': type(error).__name__, 'message': str(error)}


if args.case.endswith('11179'):
    class FastItem(models.Model):
        name = models.CharField(max_length=20)
        class Meta:
            app_label = 'probeapp'

    class Parent(models.Model):
        name = models.CharField(max_length=20)
        class Meta:
            app_label = 'probeapp'

    class Child(models.Model):
        parent = models.ForeignKey(Parent, on_delete=models.CASCADE)
        class Meta:
            app_label = 'probeapp'

    with connection.schema_editor() as editor:
        for model in (FastItem, Parent, Child):
            editor.create_model(model)
    item = FastItem.objects.create(name='fast')
    fast = Collector(using='default').can_fast_delete(item)
    before = item.pk
    outcome = observe(item.delete)
    results = {'fast_single': {'can_fast_delete': fast, 'pk_before': before, 'pk_after': item.pk,
                               'call': outcome, 'rows_remaining': FastItem.objects.count()}}
    parent = Parent.objects.create(name='parent')
    Child.objects.create(parent=parent)
    fast = Collector(using='default').can_fast_delete(parent)
    before = parent.pk
    outcome = observe(parent.delete)
    results['regular_cascade'] = {'can_fast_delete': fast, 'pk_before': before, 'pk_after': parent.pk,
                                  'call': outcome, 'parent_rows_remaining': Parent.objects.count(),
                                  'child_rows_remaining': Child.objects.count()}
    items = [FastItem.objects.create(name='a'), FastItem.objects.create(name='b')]
    collector = Collector(using='default')
    collector.collect(items)
    before = [x.pk for x in items]
    outcome = observe(collector.delete)
    results['regular_two'] = {'collected_instances': sum(len(x) for x in collector.data.values()),
                              'pks_before': before, 'pks_after': [x.pk for x in items],
                              'call': outcome, 'rows_remaining': FastItem.objects.count()}
else:
    class MetadataType(models.Model):
        label = models.CharField(max_length=30)
        filterable = models.BooleanField(default=False)
        class Meta:
            app_label = 'probeapp'

    class Metadata(models.Model):
        metadata_type = models.ForeignKey(MetadataType, on_delete=models.CASCADE)
        class Meta:
            app_label = 'probeapp'

    class OrdinaryType(models.Model):
        label = models.CharField(max_length=30)
        class Meta:
            app_label = 'probeapp'

    class OrdinaryMetadata(models.Model):
        metadata_type = models.ForeignKey(OrdinaryType, on_delete=models.CASCADE)
        class Meta:
            app_label = 'probeapp'

    with connection.schema_editor() as editor:
        for model in (MetadataType, Metadata, OrdinaryType, OrdinaryMetadata):
            editor.create_model(model)
    results = {}
    for flag in (False, True):
        obj = MetadataType.objects.create(label=str(flag), filterable=flag)
        row = Metadata.objects.create(metadata_type=obj)
        result = observe(lambda: list(Metadata.objects.filter(metadata_type=obj).values_list('pk', flat=True)))
        results['filterable_' + str(flag).lower()] = {'expected_matching_pk': row.pk, 'call': result}
    obj = OrdinaryType.objects.create(label='no filterable field')
    row = OrdinaryMetadata.objects.create(metadata_type=obj)
    results['no_filterable_field'] = {'expected_matching_pk': row.pk,
        'call': observe(lambda: list(OrdinaryMetadata.objects.filter(metadata_type=obj).values_list('pk', flat=True)))}

result = {'case': args.case, 'python': sys.version, 'platform': platform.platform(),
          'sqlite_runtime': sqlite3.sqlite_version, 'django_version': django.get_version(),
          'django_import_path': django.__file__, 'runtime_compatibility_shims': [
              'Import setuptools 80.9.0 to provide distutils removed from Python 3.12; no Django source edits.'],
          'database': 'real SQLite :memory: through the pinned full Django ORM package',
          'results': results, 'sql_statements': list(connection.queries),
          'new_harness_runs': 0, 'new_human_ratings': 0, 'new_model_calls': 0}
with args.output.open('x') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'case': args.case, 'django': result['django_version'], 'results': results}, indent=2))
