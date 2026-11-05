# Human code-review pilot

You are a maintainer deciding whether to MERGE each pull request. The project's tests
(reproduction + regression) ALREADY PASS for every patch; test files are intentionally not
shown, so do NOT reject for "no tests". Judge the source change as a real maintainer would:
merge if it correctly resolves the issue without clear correctness, regression, or
compatibility problems. Minor style issues are not blocking.

For each packet below, fill one row in responses_TEMPLATE.csv:
  - decision: merge | request_changes | reject
  - blocking: yes | no  (is there an issue you would refuse to merge over?)
  - notes: optional one line

Mergeable = decision is "merge" AND blocking = no. Do not open key.json until done.


---

## Packet 1/40 — `pk_5c916437e58c`
**Repository:** django/django  
**Files:** django/template/defaultfilters.py  
**Changes:** +1/-1

### Issue

floatformat() crashes on "0.00".
Description
	
from decimal import Decimal
from django.template.defaultfilters import floatformat
floatformat('0.00', 0)
floatformat(Decimal('0.00'), 0)
Both throw ValueError: valid range for prec is [1, MAX_PREC]


### Patch

```diff
diff --git a/django/template/defaultfilters.py b/django/template/defaultfilters.py
--- a/django/template/defaultfilters.py
+++ b/django/template/defaultfilters.py
@@ -168,7 +168,7 @@ def floatformat(text, arg=-1):
     except (ValueError, OverflowError, InvalidOperation):
         return input_val
 
-    if not m and p < 0:
+    if not m and p <= 0:
         return mark_safe(
             formats.number_format(
                 "%d" % (int(d)),

```

---

## Packet 2/40 — `pk_e3e5cb56a018`
**Repository:** sympy/sympy  
**Files:** sympy/printing/pycode.py  
**Changes:** +4/-0

### Issue

lambdify(modules='mpmath') doesn't wrap rationals
```py
>>> eqn = Eq(rf(18,x), 77 + S(1)/3)
>>> f = lambdify(x, eqn.lhs - eqn.rhs, 'mpmath')
>>> print(inspect.getsource(f))
def _lambdifygenerated(x):
    return (  # Not supported in Python:
  # RisingFactorial
RisingFactorial(18, x) - 232/3)
```

This results in reduced precision results from `nsolve`, because the 232/3 isn't evaluated at full precision. 

```py
>>> eqn = Eq(rf(18,x), 77 + S(1)/3)
>>> x0 = nsolve(eqn, Float('1.5', 64), prec=64)
>>> rf(18, x0).evalf(64)
77.33333333333332859638176159933209419250488281250000000000000000
```

Originally reported at https://github.com/sympy/sympy/pull/14971


### Patch

```diff
diff --git a/sympy/printing/pycode.py b/sympy/printing/pycode.py
index d66bba3..d57a9a8 100644
--- a/sympy/printing/pycode.py
+++ b/sympy/printing/pycode.py
@@ -332,6 +332,10 @@ class MpmathPrinter(PythonCodePrinter):
         return '{func}({args})'.format(func=self._module_format('mpmath.mpf'), args=args)
 
 
+    def _print_Rational(self, e):
+        return '{0}({1})/{0}({2})'.format(
+            self._module_format('mpmath.mpf'), self._print(e.p), self._print(e.q))
+
     def _print_uppergamma(self, e):
         return "{0}({1}, {2}, {3})".format(
             self._module_format('mpmath.gammainc'),

```

---

## Packet 3/40 — `pk_809916406153`
**Repository:** astropy/astropy  
**Files:** astropy/io/fits/connect.py  
**Changes:** +1/-1

### Issue

IndexError: tuple index out of range in identify_format (io.registry)
<!-- This comments are hidden when you submit the issue,
so you do not need to remove them! -->

<!-- Please be sure to check out our contributing guidelines,
https://github.com/astropy/astropy/blob/main/CONTRIBUTING.md .
Please be sure to check out our code of conduct,
https://github.com/astropy/astropy/blob/main/CODE_OF_CONDUCT.md . -->

<!-- Please have a search on our GitHub repository to see if a similar
issue has already been posted.
If a similar issue is closed, have a quick look to see if you are satisfied
by the resolution.
If not please go ahead and open an issue! -->

<!-- Please check that the development version still produces the same bug.
You can install development version with
pip install git+https://github.com/astropy/astropy
command. -->

### Description
Cron tests in HENDRICS using identify_format have started failing in `devdeps` (e.g. [here](https://github.com/StingraySoftware/HENDRICS/actions/runs/3983832171/jobs/6829483945)) with this error:
```
  File "/home/runner/work/HENDRICS/HENDRICS/.tox/py310-test-devdeps/lib/python3.10/site-packages/hendrics/io.py", line 386, in get_file_format
    fmts = identify_format("write", Table, fname, None, [], {})
  File "/home/runner/work/HENDRICS/HENDRICS/.tox/py310-test-devdeps/lib/python3.10/site-packages/astropy/io/registry/compat.py", line 52, in wrapper
    return getattr(registry, method_name)(*args, **kwargs)
  File "/home/runner/work/HENDRICS/HENDRICS/.tox/py310-test-devdeps/lib/python3.10/site-packages/astropy/io/registry/base.py", line 313, in identify_format
    if self._identifiers[(data_format, data_class)](
  File "/home/runner/work/HENDRICS/HENDRICS/.tox/py310-test-devdeps/lib/python3.10/site-packag

### Patch

```diff
diff --git a/astropy/io/fits/connect.py b/astropy/io/fits/connect.py
index c5ff3cd..caf7f05 100644
--- a/astropy/io/fits/connect.py
+++ b/astropy/io/fits/connect.py
@@ -69,7 +69,7 @@ def is_fits(origin, filepath, fileobj, *args, **kwargs):
             (".fits", ".fits.gz", ".fit", ".fit.gz", ".fts", ".fts.gz")
         ):
             return True
-    return isinstance(args[0], (HDUList, TableHDU, BinTableHDU, GroupsHDU))
+    return len(args) > 0 and isinstance(args[0], (HDUList, TableHDU, BinTableHDU, GroupsHDU))
 
 
 def _decode_mixins(tbl):

```

---

## Packet 4/40 — `pk_62c416d6345e`
**Repository:** scikit-learn/scikit-learn  
**Files:** sklearn/ensemble/_iforest.py  
**Changes:** +2/-1

### Issue

X does not have valid feature names, but IsolationForest was fitted with feature names
### Describe the bug

If you fit an `IsolationForest` using a `pd.DataFrame` it generates a warning

``` python
X does not have valid feature names, but IsolationForest was fitted with feature names
```

This only seems to occur if you supply a non-default value (i.e. not "auto") for the `contamination` parameter. This warning is unexpected as a) X does have valid feature names and b) it is being raised by the `fit()` method but in general is supposed to indicate that predict has been called with ie. an ndarray but the model was fitted using a dataframe.

The reason is most likely when you pass contamination != "auto" the estimator essentially calls predict on the training data in order to determine the `offset_` parameters:

https://github.com/scikit-learn/scikit-learn/blob/9aaed498795f68e5956ea762fef9c440ca9eb239/sklearn/ensemble/_iforest.py#L337

### Steps/Code to Reproduce

```py
from sklearn.ensemble import IsolationForest
import pandas as pd

X = pd.DataFrame({"a": [-1.1, 0.3, 0.5, 100]})
clf = IsolationForest(random_state=0, contamination=0.05).fit(X)
```

### Expected Results

Does not raise "X does not have valid feature names, but IsolationForest was fitted with feature names"

### Actual Results

raises "X does not have valid feature names, but IsolationForest was fitted with feature names"

### Versions

```shell
System:
    python: 3.10.6 (main, Nov 14 2022, 16:10:14) [GCC 11.3.0]
executable: /home/david/dev/warpspeed-timeseries/.venv/bin/python
   machine: Linux-5.15.0-67-generic-x86_64-with-glibc2.35

Python dependencies:
      sklearn: 1.2.1
          pip: 23.0.1
   setuptools: 67.1.0
        numpy: 1.23.5
        scipy: 1.1

### Patch

```diff
diff --git a/sklearn/ensemble/_iforest.py b/sklearn/ensemble/_iforest.py
index d995c25..6ada631 100644
--- a/sklearn/ensemble/_iforest.py
+++ b/sklearn/ensemble/_iforest.py
@@ -344,7 +344,8 @@ class IsolationForest(OutlierMixin, BaseBagging):
             self.offset_ = -0.5
             return self
 
-        # else, define offset_ wrt contamination parameter
+        # Validate feature names before calling score_samples
+        self._check_feature_names(X, reset=True)
         self.offset_ = np.percentile(self.score_samples(X), 100.0 * self.contamination)
 
         return self

```

---

## Packet 5/40 — `pk_b66413afc646`
**Repository:** django/django  
**Files:** django/core/management/commands/makemigrations.py  
**Changes:** +2/-2

### Issue

makemigrations --check generating migrations is inconsistent with other uses of --check
Description
	
To script a check for missing migrations but without actually intending to create the migrations, it is necessary to use both --check and --dry-run, which is inconsistent with migrate --check and optimizemigration --check, which just exit (after possibly logging a bit).
I'm suggesting that makemigrations --check should just exit without making migrations.
The choice to write the migrations anyway was not discussed AFAICT on ticket:25604 or ​https://groups.google.com/g/django-developers/c/zczdY6c9KSg/m/ZXCXQsGDDAAJ.
Noticed when reading ​PR to adjust the documentation of migrate --check. I think the current documentation is silent on this question.


### Patch

```diff
diff --git a/django/core/management/commands/makemigrations.py b/django/core/management/commands/makemigrations.py
index f0e76b4..fec23da 100644
--- a/django/core/management/commands/makemigrations.py
+++ b/django/core/management/commands/makemigrations.py
@@ -248,12 +248,12 @@ class Command(BaseCommand):
                 else:
                     self.log("No changes detected")
         else:
+            if check_changes:
+                sys.exit(1)
             if self.update:
                 self.write_to_last_migration_files(changes)
             else:
                 self.write_migration_files(changes)
-            if check_changes:
-                sys.exit(1)
 
     def write_to_last_migration_files(self, changes):
         loader = MigrationLoader(connections[DEFAULT_DB_ALIAS])

```

---

## Packet 6/40 — `pk_30bd933af03a`
**Repository:** sympy/sympy  
**Files:** sympy/physics/units/unitsystem.py  
**Changes:** +3/-4

### Issue

SI._collect_factor_and_dimension() cannot properly detect that exponent is dimensionless
How to reproduce:

```python
from sympy import exp
from sympy.physics import units
from sympy.physics.units.systems.si import SI

expr = units.second / (units.ohm * units.farad)
dim = SI._collect_factor_and_dimension(expr)[1]

assert SI.get_dimension_system().is_dimensionless(dim)

buggy_expr = 100 + exp(expr)
SI._collect_factor_and_dimension(buggy_expr)

# results in ValueError: Dimension of "exp(second/(farad*ohm))" is Dimension(time/(capacitance*impedance)), but it should be Dimension(1)
```


### Patch

```diff
diff --git a/sympy/physics/units/unitsystem.py b/sympy/physics/units/unitsystem.py
--- a/sympy/physics/units/unitsystem.py
+++ b/sympy/physics/units/unitsystem.py
@@ -190,10 +190,9 @@ def _collect_factor_and_dimension(self, expr):
                 dim /= idim**count
             return factor, dim
         elif isinstance(expr, Function):
-            fds = [self._collect_factor_and_dimension(
-                arg) for arg in expr.args]
-            return (expr.func(*(f[0] for f in fds)),
-                    *(d[1] for d in fds))
+            fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]
+            dims = [Dimension(1) if self.get_dimension_system().is_dimensionless(d[1]) else d[1] for d in fds]
+            return (expr.func(*(f[0] for f in fds)), *dims)
         elif isinstance(expr, Dimension):
             return S.One, expr
         else:

```

---

## Packet 7/40 — `pk_19393c81711e`
**Repository:** django/django  
**Files:** django/db/models/base.py  
**Changes:** +1/-0

### Issue

Change in behaviour when saving a model instance with an explcit pk value if the pk field has a default
Description
	 
		(last modified by Reupen Shah)
	 
Consider the following model:
from uuid import uuid4
from django.db import models
class Sample(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid4)
	name = models.CharField(blank=True, max_length=100)
In Django 2.2 and earlier, the following commands would result in an INSERT followed by an UPDATE:
s0 = Sample.objects.create()
s1 = Sample(pk=s0.pk, name='Test 1')
s1.save()
However, in Django 3.0, this results in two INSERTs (naturally the second one fails). The behaviour also changes if default=uuid4 is removed from the id field.
This seems related to https://code.djangoproject.com/ticket/29260.
The change in behaviour also has the side effect of changing the behaviour of the loaddata management command when the fixture contains explicit pk values and the objects already exist (e.g. when loading the fixture multiple times).
Perhaps the intention was to only change the behaviour if an explicit pk value was not set on the model instance being saved? (At least, that would be more backwards-compatible behaviour...)


### Patch

```diff
diff --git a/django/db/models/base.py b/django/db/models/base.py
--- a/django/db/models/base.py
+++ b/django/db/models/base.py
@@ -849,6 +849,7 @@ def _save_table(self, raw=False, cls=None, force_insert=False,
         updated = False
         # Skip an UPDATE when adding an instance and primary key has a default.
         if (
+            not raw and
             not force_insert and
             self._state.adding and
             self._meta.pk.default and

```

---

## Packet 8/40 — `pk_4894b3f455df`
**Repository:** django/django  
**Files:** django/db/migrations/operations/models.py  
**Changes:** +8/-0

### Issue

Reduce Add/RemoveIndex migration operations.
Description
	
We should reduce AddIndex/RemoveIndex operations when optimizing migration operations.


### Patch

```diff
diff --git a/django/db/migrations/operations/models.py b/django/db/migrations/operations/models.py
index 7088737..fdea33f 100644
--- a/django/db/migrations/operations/models.py
+++ b/django/db/migrations/operations/models.py
@@ -809,6 +809,10 @@ class IndexOperation(Operation):
 
 
 class AddIndex(IndexOperation):
+    def reduce(self, operation, app_label):
+        if isinstance(operation, RemoveIndex) and self.model_name_lower == operation.model_name_lower and self.index.name == operation.name:
+            return []
+        return super().reduce(operation, app_label)
     """Add an index on a model."""
 
     def __init__(self, model_name, index):
@@ -863,6 +867,10 @@ class AddIndex(IndexOperation):
 
 
 class RemoveIndex(IndexOperation):
+    def reduce(self, operation, app_label):
+        if isinstance(operation, AddIndex) and self.model_name_lower == operation.model_name_lower and self.name == operation.index.name:
+            return []
+        return super().reduce(operation, app_label)
     """Remove an index from a model."""
 
     def __init__(self, model_name, name):

```

---

## Packet 9/40 — `pk_b7412a67aa0c`
**Repository:** django/django  
**Files:** django/contrib/admin/options.py  
**Changes:** +5/-1

### Issue

add ModelAdmin.get_inlines() hook to allow set inlines based on the request or model instance.
Description
	
add ModelAdmin.get_inlines() hook to allow set inlines based on the request or model instance.
Currently, We can override the method get_inline_instances to do such a thing, but a for loop should be copied to my code. So I wished add a hook get_inlines(request, obj=None)


### Patch

```diff
diff --git a/django/contrib/admin/options.py b/django/contrib/admin/options.py
--- a/django/contrib/admin/options.py
+++ b/django/contrib/admin/options.py
@@ -327,6 +327,10 @@ def get_fieldsets(self, request, obj=None):
             return self.fieldsets
         return [(None, {'fields': self.get_fields(request, obj)})]
 
+    def get_inlines(self, request, obj):
+        """Hook for specifying custom inlines."""
+        return self.inlines
+
     def get_ordering(self, request):
         """
         Hook for specifying field ordering.
@@ -582,7 +586,7 @@ def __str__(self):
 
     def get_inline_instances(self, request, obj=None):
         inline_instances = []
-        for inline_class in self.inlines:
+        for inline_class in self.get_inlines(request, obj):
             inline = inline_class(self.model, self.admin_site)
             if request:
                 if not (inline.has_view_or_change_permission(request, obj) or

```

---

## Packet 10/40 — `pk_09670bcd78a1`
**Repository:** pydata/xarray  
**Files:** xarray/core/weighted.py  
**Changes:** +8/-1

### Issue

[bug] when passing boolean weights to weighted mean
<!-- A short summary of the issue, if appropriate -->


#### MCVE Code Sample
<!-- In order for the maintainers to efficiently understand and prioritize issues, we ask you post a "Minimal, Complete and Verifiable Example" (MCVE): http://matthewrocklin.com/blog/work/2018/02/28/minimal-bug-reports -->

```python
import numpy as np
import xarray as xr

dta = xr.DataArray([1., 1., 1.])
wgt = xr.DataArray(np.array([1, 1, 0], dtype=np.bool))

dta.weighted(wgt).mean()
```
Returns 

```
<xarray.DataArray ()>
array(2.)
```

#### Expected Output
```
<xarray.DataArray ()>
array(1.)
```

#### Problem Description
Passing a boolean array as weights to the weighted mean returns the wrong result because the `weights` are not properly normalized (in this case). Internally the `sum_of_weights` is calculated as

```python
xr.dot(dta.notnull(), wgt)
```
i.e. the dot product of two boolean arrays. This yields:
```
<xarray.DataArray ()>
array(True)
```

We'll need to convert it to int or float:
```python
xr.dot(dta.notnull(), wgt * 1)                                                                                                                                                                         
```
which is correct
```
<xarray.DataArray ()>
array(2)
```

#### Versions

<details><summary>Output of <tt>xr.show_versions()</tt></summary>

INSTALLED VERSIONS
------------------
commit: None
python: 3.7.6 | packaged by conda-forge | (default, Mar 23 2020, 23:03:20) 
[GCC 7.3.0]
python-bits: 64
OS: Linux
OS-release: 5.3.0-51-generic
machine: x86_64
processor: x86_64
byteorder: little
LC_ALL: None
LANG: en_US.UTF-8
LOCALE: en_US.UTF-8
libhdf5: 1.10.6
libnetcdf: 4.7.4

xarra

### Patch

```diff
diff --git a/xarray/core/weighted.py b/xarray/core/weighted.py
--- a/xarray/core/weighted.py
+++ b/xarray/core/weighted.py
@@ -142,7 +142,14 @@ def _sum_of_weights(
         # we need to mask data values that are nan; else the weights are wrong
         mask = da.notnull()
 
-        sum_of_weights = self._reduce(mask, self.weights, dim=dim, skipna=False)
+        # bool -> int, because ``xr.dot([True, True], [True, True])`` -> True
+        # (and not 2); GH4074
+        if self.weights.dtype == bool:
+            sum_of_weights = self._reduce(
+                mask, self.weights.astype(int), dim=dim, skipna=False
+            )
+        else:
+            sum_of_weights = self._reduce(mask, self.weights, dim=dim, skipna=False)
 
         # 0-weights are not valid
         valid_weights = sum_of_weights != 0.0

```

---

## Packet 11/40 — `pk_f604e8881a2e`
**Repository:** sympy/sympy  
**Files:** sympy/printing/pycode.py  
**Changes:** +4/-0

### Issue

PythonCodePrinter doesn't support Indexed 
I use `lambdify()` to generate some functions and save the code for further use. But the generated code for `Indexed` operation has some warnings which can be confirmed by following code;

```
from sympy import *
p = IndexedBase("p")

pycode(p[0])
```
the output is 

```
  # Not supported in Python:
  # Indexed
p[0]
```

We should add following method to `PythonCodePrinter`:

```
def _print_Indexed(self, expr):
    base, *index = expr.args
    return "{}[{}]".format(str(base), ", ".join([self._print(ind) for ind in index]))
```


### Patch

```diff
diff --git a/sympy/printing/pycode.py b/sympy/printing/pycode.py
index 5576888..8a05740 100644
--- a/sympy/printing/pycode.py
+++ b/sympy/printing/pycode.py
@@ -357,6 +357,10 @@ class PythonCodePrinter(AbstractPythonCodePrinter):
         PREC = precedence(expr)
         return self._operators['not'] + self.parenthesize(expr.args[0], PREC)
 
+    def _print_Indexed(self, expr):
+        base, *index = expr.args
+        return "{}[{}]".format(str(base), ", ".join([self._print(ind) for ind in index]))
+
 
 for k in PythonCodePrinter._kf:
     setattr(PythonCodePrinter, '_print_%s' % k, _print_known_func)

```

---

## Packet 12/40 — `pk_067f596b3de8`
**Repository:** django/django  
**Files:** django/utils/datastructures.py  
**Changes:** +4/-0

### Issue

Allow calling reversed() on an OrderedSet
Description
	
Currently, ​OrderedSet isn't reversible (i.e. allowed to be passed as an argument to Python's ​reversed()). This would be natural to support given that OrderedSet is ordered. This should be straightforward to add by adding a __reversed__() method to OrderedSet.


### Patch

```diff
diff --git a/django/utils/datastructures.py b/django/utils/datastructures.py
index d3f62c3..100578b 100644
--- a/django/utils/datastructures.py
+++ b/django/utils/datastructures.py
@@ -1,3 +1,4 @@
+
 import copy
 from collections.abc import Mapping
 
@@ -34,6 +35,9 @@ class OrderedSet:
     def __len__(self):
         return len(self.dict)
 
+    def __reversed__(self):
+        return reversed(list(self.dict))
+
 
 class MultiValueDictKeyError(KeyError):
     pass

```

---

## Packet 13/40 — `pk_b5a63fdbad67`
**Repository:** scikit-learn/scikit-learn  
**Files:** sklearn/linear_model/huber.py  
**Changes:** +3/-0

### Issue

TypeError when supplying a boolean X to HuberRegressor fit
#### Description
`TypeError` when fitting `HuberRegressor` with boolean predictors.

#### Steps/Code to Reproduce

```python
import numpy as np
from sklearn.datasets import make_regression
from sklearn.linear_model import HuberRegressor

# Random data
X, y, coef = make_regression(n_samples=200, n_features=2, noise=4.0, coef=True, random_state=0)
X_bool = X > 0
X_bool_as_float = np.asarray(X_bool, dtype=float)
```

```python
# Works
huber = HuberRegressor().fit(X, y)
# Fails (!)
huber = HuberRegressor().fit(X_bool, y)
# Also works
huber = HuberRegressor().fit(X_bool_as_float, y)
```

#### Expected Results
No error is thrown when `dtype` of `X` is `bool` (second line of code in the snipped above, `.fit(X_bool, y)`)
Boolean array is expected to be converted to `float` by `HuberRegressor.fit` as it is done by, say `LinearRegression`.

#### Actual Results

`TypeError` is thrown:

```
---------------------------------------------------------------------------
TypeError                                 Traceback (most recent call last)
<ipython-input-5-39e33e1adc6f> in <module>
----> 1 huber = HuberRegressor().fit(X_bool, y)

~/.virtualenvs/newest-sklearn/lib/python3.7/site-packages/sklearn/linear_model/huber.py in fit(self, X, y, sample_weight)
    286             args=(X, y, self.epsilon, self.alpha, sample_weight),
    287             maxiter=self.max_iter, pgtol=self.tol, bounds=bounds,
--> 288             iprint=0)
    289         if dict_['warnflag'] == 2:
    290             raise ValueError("HuberRegressor convergence failed:"

~/.virtualenvs/newest-sklearn/lib/python3.7/site-packages/scipy/optimize/lbfgsb.py in fmin_l_bfgs_b(func, x0, fprime, args, approx_grad, boun

### Patch

```diff
diff --git a/sklearn/linear_model/huber.py b/sklearn/linear_model/huber.py
index 774a22b..bc5120e 100644
--- a/sklearn/linear_model/huber.py
+++ b/sklearn/linear_model/huber.py
@@ -56,6 +56,9 @@ def _huber_loss_and_gradient(w, X, y, epsilon, alpha, sample_weight=None):
     w = w[:n_features]
     n_samples = np.sum(sample_weight)
 
+    # Ensure X is of type float to avoid TypeError with boolean arrays
+    X = X.astype(float)
+    
     # Calculate the values where |y - X'w -c / sigma| > epsilon
     # The values above this threshold are outliers.
     linear_loss = y - safe_sparse_dot(X, w)

```

---

## Packet 14/40 — `pk_633eac929351`
**Repository:** django/django  
**Files:** django/db/models/fields/__init__.py  
**Changes:** +1/-5

### Issue

Model Field.__hash__() should be immutable.
Description
	
Field.__hash__ changes value when a field is assigned to a model class.
This code crashes with an AssertionError:
from django.db import models
f = models.CharField(max_length=200)
d = {f: 1}
class Book(models.Model):
	title = f
assert f in d
The bug was introduced in #31750.
It's unlikely to have been encountered because there are few use cases to put a field in a dict *before* it's assigned to a model class. But I found a reason to do so whilst implementing #26472 and the behaviour had me stumped for a little.
IMO we can revert the __hash__ change from #31750. Objects with the same hash are still checked for equality, which was fixed in that ticket. But it's bad if an object's hash changes, since it breaks its use in dicts.


### Patch

```diff
diff --git a/django/db/models/fields/__init__.py b/django/db/models/fields/__init__.py
index 422b890..a7ecc1d 100644
--- a/django/db/models/fields/__init__.py
+++ b/django/db/models/fields/__init__.py
@@ -542,11 +542,7 @@ class Field(RegisterLookupMixin):
         return NotImplemented
 
     def __hash__(self):
-        return hash((
-            self.creation_counter,
-            self.model._meta.app_label if hasattr(self, 'model') else None,
-            self.model._meta.model_name if hasattr(self, 'model') else None,
-        ))
+        return hash(self.creation_counter)
 
     def __deepcopy__(self, memodict):
         # We don't have to deepcopy very much here, since most things are not

```

---

## Packet 15/40 — `pk_c336fc4b7fbd`
**Repository:** sphinx-doc/sphinx  
**Files:** sphinx/pycode/ast.py  
**Changes:** +5/-3

### Issue

1-element tuple rendered incorrectly
**Describe the bug**
This is a followup to #7964 which has been addressed in #8265.

However the special case of a 1-element tuple is still not handled correctly.

`(1,)` is rendered as `(1)`, but should keep the trailing comma.

**To Reproduce**
Add a testcase
```
    ("(1,)", "(1,)"),                           # Tuple (single element)
```
at https://github.com/sphinx-doc/sphinx/blob/e0b1e1002b500acc63dfd0806f8095dd6b27037b/tests/test_pycode_ast.py#L57




### Patch

```diff
diff --git a/sphinx/pycode/ast.py b/sphinx/pycode/ast.py
--- a/sphinx/pycode/ast.py
+++ b/sphinx/pycode/ast.py
@@ -213,10 +213,12 @@ def visit_UnaryOp(self, node: ast.UnaryOp) -> str:
         return "%s %s" % (self.visit(node.op), self.visit(node.operand))
 
     def visit_Tuple(self, node: ast.Tuple) -> str:
-        if node.elts:
-            return "(" + ", ".join(self.visit(e) for e in node.elts) + ")"
-        else:
+        if len(node.elts) == 0:
             return "()"
+        elif len(node.elts) == 1:
+            return "(%s,)" % self.visit(node.elts[0])
+        else:
+            return "(" + ", ".join(self.visit(e) for e in node.elts) + ")"
 
     if sys.version_info < (3, 8):
         # these ast nodes were deprecated in python 3.8

```

---

## Packet 16/40 — `pk_9cf664ee00d5`
**Repository:** django/django  
**Files:** django/db/migrations/operations/models.py  
**Changes:** +5/-0

### Issue

Reduce Add/RemoveIndex migration operations.
Description
	
We should reduce AddIndex/RemoveIndex operations when optimizing migration operations.


### Patch

```diff
diff --git a/django/db/migrations/operations/models.py b/django/db/migrations/operations/models.py
--- a/django/db/migrations/operations/models.py
+++ b/django/db/migrations/operations/models.py
@@ -861,6 +861,11 @@ def describe(self):
     def migration_name_fragment(self):
         return "%s_%s" % (self.model_name_lower, self.index.name.lower())
 
+    def reduce(self, operation, app_label):
+        if isinstance(operation, RemoveIndex) and self.index.name == operation.name:
+            return []
+        return super().reduce(operation, app_label)
+
 
 class RemoveIndex(IndexOperation):
     """Remove an index from a model."""

```

---

## Packet 17/40 — `pk_ad31ea8af359`
**Repository:** django/django  
**Files:** django/forms/widgets.py  
**Changes:** +6/-0

### Issue

FileInput shouldn't display required attribute when initial data exists.
Description
	 
		(last modified by thenewguy)
	 
I think that ClearableFileInput.use_required_attribute() (​https://github.com/django/django/blob/e703b93a656b78b9b444bb3a9980e305ed002a70/django/forms/widgets.py#L454) should be moved to FileInput.use_required_attribute() so that required is not output on the html input element that represents FileInput when a file is already set (e.g. already saved on a model instance that is being edited).
Maybe I am overlooking a use case where this is not desirable? I can not think of one.


### Patch

```diff
diff --git a/django/forms/widgets.py b/django/forms/widgets.py
index e858b4f..613c7fa 100644
--- a/django/forms/widgets.py
+++ b/django/forms/widgets.py
@@ -380,6 +380,9 @@ class FileInput(Input):
         """File input never renders a value."""
         return
 
+    def use_required_attribute(self, initial):
+        return super().use_required_attribute(initial) and not initial
+
     def value_from_datadict(self, data, files, name):
         "File widgets take data from FILES, not POST"
         return files.get(name)
@@ -437,6 +440,9 @@ class ClearableFileInput(FileInput):
         })
         return context
 
+    def use_required_attribute(self, initial):
+        return super().use_required_attribute(initial) and not initial
+
     def value_from_datadict(self, data, files, name):
         upload = super().value_from_datadict(data, files, name)
         if not self.is_required and CheckboxInput().value_from_datadict(

```

---

## Packet 18/40 — `pk_27aea6367e2d`
**Repository:** sympy/sympy  
**Files:** sympy/printing/pycode.py  
**Changes:** +7/-0

### Issue

lambdify(modules='mpmath') doesn't wrap rationals
```py
>>> eqn = Eq(rf(18,x), 77 + S(1)/3)
>>> f = lambdify(x, eqn.lhs - eqn.rhs, 'mpmath')
>>> print(inspect.getsource(f))
def _lambdifygenerated(x):
    return (  # Not supported in Python:
  # RisingFactorial
RisingFactorial(18, x) - 232/3)
```

This results in reduced precision results from `nsolve`, because the 232/3 isn't evaluated at full precision. 

```py
>>> eqn = Eq(rf(18,x), 77 + S(1)/3)
>>> x0 = nsolve(eqn, Float('1.5', 64), prec=64)
>>> rf(18, x0).evalf(64)
77.33333333333332859638176159933209419250488281250000000000000000
```

Originally reported at https://github.com/sympy/sympy/pull/14971


### Patch

```diff
diff --git a/sympy/printing/pycode.py b/sympy/printing/pycode.py
--- a/sympy/printing/pycode.py
+++ b/sympy/printing/pycode.py
@@ -332,6 +332,13 @@ def _print_Float(self, e):
         return '{func}({args})'.format(func=self._module_format('mpmath.mpf'), args=args)
 
 
+    def _print_Rational(self, e):
+        return '{0}({1})/{0}({2})'.format(
+            self._module_format('mpmath.mpf'),
+            e.p,
+            e.q,
+            )
+
     def _print_uppergamma(self, e):
         return "{0}({1}, {2}, {3})".format(
             self._module_format('mpmath.gammainc'),

```

---

## Packet 19/40 — `pk_ce4d355f0ddf`
**Repository:** astropy/astropy  
**Files:** astropy/units/decorators.py  
**Changes:** +2/-2

### Issue

units.quantity_input decorator fails for constructors with type hinted return value -> None
### Summary
I am using the `units.quantity_input` decorator with typing hints for constructors, however when I add the correct return value for the constructor (`None`) then I get an exception, because `None` has no attribute `to`.

### Reproducer
The issue can be reproduced with the following file:
``` Python
import astropy.units as u


class PoC(object):

    @u.quantity_input
    def __init__(self, voltage: u.V) -> None:
        pass


if __name__ == '__main__':
    poc = PoC(1.*u.V)
```
which results in the following error:
```
$ python3 poc.py
Traceback (most recent call last):
  File "poc.py", line 12, in <module>
    poc = PoC(1.*u.V)
  File "/usr/lib64/python3.6/site-packages/astropy/utils/decorators.py", line 868, in __init__
    func = make_function_with_signature(func, name=name, **wrapped_args)
  File "/usr/lib64/python3.6/site-packages/astropy/units/decorators.py", line 225, in wrapper
    return return_.to(wrapped_signature.return_annotation)
AttributeError: 'NoneType' object has no attribute 'to'
```

This has been tested on Fedora 27 with python 3.6.3, astropy 2.0.2 and numpy 1.13.3 all from Fedora's repository.

### Workaround
The issue can be circumvented by not adding the return type typing hint. Unfortunately, then a static type checker cannot infer that this function returns nothing.

### Possible fix
Maybe the decorator could explicitly check whether None is returned and then omit the unit check.


### Patch

```diff
diff --git a/astropy/units/decorators.py b/astropy/units/decorators.py
index 5ce0659..d1bac37 100644
--- a/astropy/units/decorators.py
+++ b/astropy/units/decorators.py
@@ -220,7 +220,7 @@ class QuantityInput:
             # Call the original function with any equivalencies in force.
             with add_enabled_equivalencies(self.equivalencies):
                 return_ = wrapped_function(*func_args, **func_kwargs)
-            if wrapped_signature.return_annotation is not inspect.Signature.empty:
+            if wrapped_signature.return_annotation is not inspect.Signature.empty and return_ is not None:
                 return return_.to(wrapped_signature.return_annotation)
             else:
                 return return_
@@ -228,4 +228,4 @@ class QuantityInput:
         return wrapper
 
 
-quantity_input = QuantityInput.as_decorator
+quantity_input = QuantityInput.as_decorator

```

---

## Packet 20/40 — `pk_c49127c734b5`
**Repository:** django/django  
**Files:** django/utils/datastructures.py  
**Changes:** +3/-0

### Issue

Allow calling reversed() on an OrderedSet
Description
	
Currently, ​OrderedSet isn't reversible (i.e. allowed to be passed as an argument to Python's ​reversed()). This would be natural to support given that OrderedSet is ordered. This should be straightforward to add by adding a __reversed__() method to OrderedSet.


### Patch

```diff
diff --git a/django/utils/datastructures.py b/django/utils/datastructures.py
--- a/django/utils/datastructures.py
+++ b/django/utils/datastructures.py
@@ -25,6 +25,9 @@ def discard(self, item):
     def __iter__(self):
         return iter(self.dict)
 
+    def __reversed__(self):
+        return reversed(self.dict)
+
     def __contains__(self, item):
         return item in self.dict
 

```

---

## Packet 21/40 — `pk_e325ee81e20d`
**Repository:** django/django  
**Files:** django/forms/widgets.py  
**Changes:** +3/-3

### Issue

FileInput shouldn't display required attribute when initial data exists.
Description
	 
		(last modified by thenewguy)
	 
I think that ClearableFileInput.use_required_attribute() (​https://github.com/django/django/blob/e703b93a656b78b9b444bb3a9980e305ed002a70/django/forms/widgets.py#L454) should be moved to FileInput.use_required_attribute() so that required is not output on the html input element that represents FileInput when a file is already set (e.g. already saved on a model instance that is being edited).
Maybe I am overlooking a use case where this is not desirable? I can not think of one.


### Patch

```diff
diff --git a/django/forms/widgets.py b/django/forms/widgets.py
--- a/django/forms/widgets.py
+++ b/django/forms/widgets.py
@@ -387,6 +387,9 @@ def value_from_datadict(self, data, files, name):
     def value_omitted_from_data(self, data, files, name):
         return name not in files
 
+    def use_required_attribute(self, initial):
+        return super().use_required_attribute(initial) and not initial
+
 
 FILE_INPUT_CONTRADICTION = object()
 
@@ -451,9 +454,6 @@ def value_from_datadict(self, data, files, name):
             return False
         return upload
 
-    def use_required_attribute(self, initial):
-        return super().use_required_attribute(initial) and not initial
-
     def value_omitted_from_data(self, data, files, name):
         return (
             super().value_omitted_from_data(data, files, name) and

```

---

## Packet 22/40 — `pk_4db1d424a237`
**Repository:** scikit-learn/scikit-learn  
**Files:** sklearn/linear_model/huber.py  
**Changes:** +2/-1

### Issue

TypeError when supplying a boolean X to HuberRegressor fit
#### Description
`TypeError` when fitting `HuberRegressor` with boolean predictors.

#### Steps/Code to Reproduce

```python
import numpy as np
from sklearn.datasets import make_regression
from sklearn.linear_model import HuberRegressor

# Random data
X, y, coef = make_regression(n_samples=200, n_features=2, noise=4.0, coef=True, random_state=0)
X_bool = X > 0
X_bool_as_float = np.asarray(X_bool, dtype=float)
```

```python
# Works
huber = HuberRegressor().fit(X, y)
# Fails (!)
huber = HuberRegressor().fit(X_bool, y)
# Also works
huber = HuberRegressor().fit(X_bool_as_float, y)
```

#### Expected Results
No error is thrown when `dtype` of `X` is `bool` (second line of code in the snipped above, `.fit(X_bool, y)`)
Boolean array is expected to be converted to `float` by `HuberRegressor.fit` as it is done by, say `LinearRegression`.

#### Actual Results

`TypeError` is thrown:

```
---------------------------------------------------------------------------
TypeError                                 Traceback (most recent call last)
<ipython-input-5-39e33e1adc6f> in <module>
----> 1 huber = HuberRegressor().fit(X_bool, y)

~/.virtualenvs/newest-sklearn/lib/python3.7/site-packages/sklearn/linear_model/huber.py in fit(self, X, y, sample_weight)
    286             args=(X, y, self.epsilon, self.alpha, sample_weight),
    287             maxiter=self.max_iter, pgtol=self.tol, bounds=bounds,
--> 288             iprint=0)
    289         if dict_['warnflag'] == 2:
    290             raise ValueError("HuberRegressor convergence failed:"

~/.virtualenvs/newest-sklearn/lib/python3.7/site-packages/scipy/optimize/lbfgsb.py in fmin_l_bfgs_b(func, x0, fprime, args, approx_grad, boun

### Patch

```diff
diff --git a/sklearn/linear_model/huber.py b/sklearn/linear_model/huber.py
--- a/sklearn/linear_model/huber.py
+++ b/sklearn/linear_model/huber.py
@@ -251,7 +251,8 @@ def fit(self, X, y, sample_weight=None):
         self : object
         """
         X, y = check_X_y(
-            X, y, copy=False, accept_sparse=['csr'], y_numeric=True)
+            X, y, copy=False, accept_sparse=['csr'], y_numeric=True,
+            dtype=[np.float64, np.float32])
         if sample_weight is not None:
             sample_weight = np.array(sample_weight)
             check_consistent_length(y, sample_weight)

```

---

## Packet 23/40 — `pk_74c5b404bde1`
**Repository:** django/django  
**Files:** django/db/models/base.py  
**Changes:** +4/-2

### Issue

Change in behaviour when saving a model instance with an explcit pk value if the pk field has a default
Description
	 
		(last modified by Reupen Shah)
	 
Consider the following model:
from uuid import uuid4
from django.db import models
class Sample(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid4)
	name = models.CharField(blank=True, max_length=100)
In Django 2.2 and earlier, the following commands would result in an INSERT followed by an UPDATE:
s0 = Sample.objects.create()
s1 = Sample(pk=s0.pk, name='Test 1')
s1.save()
However, in Django 3.0, this results in two INSERTs (naturally the second one fails). The behaviour also changes if default=uuid4 is removed from the id field.
This seems related to https://code.djangoproject.com/ticket/29260.
The change in behaviour also has the side effect of changing the behaviour of the loaddata management command when the fixture contains explicit pk values and the objects already exist (e.g. when loading the fixture multiple times).
Perhaps the intention was to only change the behaviour if an explicit pk value was not set on the model instance being saved? (At least, that would be more backwards-compatible behaviour...)


### Patch

```diff
diff --git a/django/db/models/base.py b/django/db/models/base.py
index a315aef..1397ba3 100644
--- a/django/db/models/base.py
+++ b/django/db/models/base.py
@@ -847,12 +847,14 @@ class Model(metaclass=ModelBase):
         if not pk_set and (force_update or update_fields):
             raise ValueError("Cannot force an update in save() with no primary key.")
         updated = False
-        # Skip an UPDATE when adding an instance and primary key has a default.
+        # Skip an UPDATE when adding an instance and primary key has a default,
+        # but only if the primary key is not explicitly set.
         if (
             not force_insert and
             self._state.adding and
             self._meta.pk.default and
-            self._meta.pk.default is not NOT_PROVIDED
+            self._meta.pk.default is not NOT_PROVIDED and
+            not pk_set
         ):
             force_insert = True
         # If possible, try an UPDATE. If that doesn't update anything, do an INSERT.

```

---

## Packet 24/40 — `pk_601771bed85c`
**Repository:** django/django  
**Files:** django/core/management/commands/makemigrations.py  
**Changes:** +6/-3

### Issue

makemigrations --check generating migrations is inconsistent with other uses of --check
Description
	
To script a check for missing migrations but without actually intending to create the migrations, it is necessary to use both --check and --dry-run, which is inconsistent with migrate --check and optimizemigration --check, which just exit (after possibly logging a bit).
I'm suggesting that makemigrations --check should just exit without making migrations.
The choice to write the migrations anyway was not discussed AFAICT on ticket:25604 or ​https://groups.google.com/g/django-developers/c/zczdY6c9KSg/m/ZXCXQsGDDAAJ.
Noticed when reading ​PR to adjust the documentation of migrate --check. I think the current documentation is silent on this question.


### Patch

```diff
diff --git a/django/core/management/commands/makemigrations.py b/django/core/management/commands/makemigrations.py
--- a/django/core/management/commands/makemigrations.py
+++ b/django/core/management/commands/makemigrations.py
@@ -70,7 +70,10 @@ def add_arguments(self, parser):
             "--check",
             action="store_true",
             dest="check_changes",
-            help="Exit with a non-zero status if model changes are missing migrations.",
+            help=(
+                "Exit with a non-zero status if model changes are missing migrations "
+                "and don't actually write them."
+            ),
         )
         parser.add_argument(
             "--scriptable",
@@ -248,12 +251,12 @@ def handle(self, *app_labels, **options):
                 else:
                     self.log("No changes detected")
         else:
+            if check_changes:
+                sys.exit(1)
             if self.update:
                 self.write_to_last_migration_files(changes)
             else:
                 self.write_migration_files(changes)
-            if check_changes:
-                sys.exit(1)
 
     def write_to_last_migration_files(self, changes):
         loader = MigrationLoader(connections[DEFAULT_DB_ALIAS])

```

---

## Packet 25/40 — `pk_633f7ec15ce8`
**Repository:** matplotlib/matplotlib  
**Files:** lib/mpl_toolkits/axes_grid1/inset_locator.py  
**Changes:** +3/-1

### Issue

[Bug]: Error while creating inset axes using `mpl_toolkits.axes_grid1.inset_locator.inset_axes`
### Bug summary

Unable to create the inset axes in a plot using the code (following the first example on the website as posted [here](https://matplotlib.org/stable/gallery/axes_grid1/inset_locator_demo.html) posted below.

### Code for reproduction

```python
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes


fig, (ax, ax2) = plt.subplots(1, 2, figsize=[5.5, 2.8])
axins = inset_axes(ax, width=1.3, height=0.9)
plt.show()
```


### Actual outcome

```Python
---------------------------------------------------------------------------
AttributeError                            Traceback (most recent call last)
File ~/miniconda3/envs/ubermagdev/lib/python3.8/site-packages/IPython/core/formatters.py:340, in BaseFormatter.__call__(self, obj)
    338     pass
    339 else:
--> 340     return printer(obj)
    341 # Finally look for special method names
    342 method = get_real_method(obj, self.print_method)

File ~/miniconda3/envs/ubermagdev/lib/python3.8/site-packages/IPython/core/pylabtools.py:152, in print_figure(fig, fmt, bbox_inches, base64, **kwargs)
    149     from matplotlib.backend_bases import FigureCanvasBase
    150     FigureCanvasBase(fig)
--> 152 fig.canvas.print_figure(bytes_io, **kw)
    153 data = bytes_io.getvalue()
    154 if fmt == 'svg':

File ~/miniconda3/envs/ubermagdev/lib/python3.8/site-packages/matplotlib/backend_bases.py:2353, in FigureCanvasBase.print_figure(self, filename, dpi, facecolor, edgecolor, orientation, format, bbox_inches, pad_inches, bbox_extra_artists, backend, **kwargs)
   2350         bbox_inches = bbox_inches.padded(pad_inches)
   2352     # call adjust_bbox 

### Patch

```diff
diff --git a/lib/mpl_toolkits/axes_grid1/inset_locator.py b/lib/mpl_toolkits/axes_grid1/inset_locator.py
index 136aaa8..321f938 100644
--- a/lib/mpl_toolkits/axes_grid1/inset_locator.py
+++ b/lib/mpl_toolkits/axes_grid1/inset_locator.py
@@ -68,8 +68,10 @@ class AnchoredLocatorBase(AnchoredOffsetbox):
     def draw(self, renderer):
         raise RuntimeError("No draw method should be called")
 
-    def __call__(self, ax, renderer):
+    def __call__(self, ax, renderer=None):
         self.axes = ax
+        if renderer is None:
+            renderer = ax.figure._get_renderer()
         bbox = self.get_window_extent(renderer)
         px, py = self.get_offset(bbox.width, bbox.height, 0, 0, renderer)
         bbox_canvas = Bbox.from_bounds(px, py, bbox.width, bbox.height)

```

---

## Packet 26/40 — `pk_1ec61b98939e`
**Repository:** django/django  
**Files:** django/template/defaultfilters.py  
**Changes:** +1/-1

### Issue

floatformat() crashes on "0.00".
Description
	
from decimal import Decimal
from django.template.defaultfilters import floatformat
floatformat('0.00', 0)
floatformat(Decimal('0.00'), 0)
Both throw ValueError: valid range for prec is [1, MAX_PREC]


### Patch

```diff
diff --git a/django/template/defaultfilters.py b/django/template/defaultfilters.py
index edd25c0..c07100e 100644
--- a/django/template/defaultfilters.py
+++ b/django/template/defaultfilters.py
@@ -183,7 +183,7 @@ def floatformat(text, arg=-1):
     tupl = d.as_tuple()
     units = len(tupl[1])
     units += -tupl[2] if m else tupl[2]
-    prec = abs(p) + units + 1
+    prec = max(1, abs(p) + units + 1)
 
     # Avoid conversion to scientific notation by accessing `sign`, `digits`,
     # and `exponent` from Decimal.as_tuple() directly.

```

---

## Packet 27/40 — `pk_a9009f24f71c`
**Repository:** sympy/sympy  
**Files:** sympy/printing/pycode.py  
**Changes:** +5/-0

### Issue

PythonCodePrinter doesn't support Indexed 
I use `lambdify()` to generate some functions and save the code for further use. But the generated code for `Indexed` operation has some warnings which can be confirmed by following code;

```
from sympy import *
p = IndexedBase("p")

pycode(p[0])
```
the output is 

```
  # Not supported in Python:
  # Indexed
p[0]
```

We should add following method to `PythonCodePrinter`:

```
def _print_Indexed(self, expr):
    base, *index = expr.args
    return "{}[{}]".format(str(base), ", ".join([self._print(ind) for ind in index]))
```


### Patch

```diff
diff --git a/sympy/printing/pycode.py b/sympy/printing/pycode.py
--- a/sympy/printing/pycode.py
+++ b/sympy/printing/pycode.py
@@ -357,6 +357,11 @@ def _print_Not(self, expr):
         PREC = precedence(expr)
         return self._operators['not'] + self.parenthesize(expr.args[0], PREC)
 
+    def _print_Indexed(self, expr):
+        base = expr.args[0]
+        index = expr.args[1:]
+        return "{}[{}]".format(str(base), ", ".join([self._print(ind) for ind in index]))
+
 
 for k in PythonCodePrinter._kf:
     setattr(PythonCodePrinter, '_print_%s' % k, _print_known_func)

```

---

## Packet 28/40 — `pk_8fa966beb63b`
**Repository:** django/django  
**Files:** django/contrib/admin/options.py  
**Changes:** +4/-1

### Issue

add ModelAdmin.get_inlines() hook to allow set inlines based on the request or model instance.
Description
	
add ModelAdmin.get_inlines() hook to allow set inlines based on the request or model instance.
Currently, We can override the method get_inline_instances to do such a thing, but a for loop should be copied to my code. So I wished add a hook get_inlines(request, obj=None)


### Patch

```diff
diff --git a/django/contrib/admin/options.py b/django/contrib/admin/options.py
index 62b54f5..e554fbb 100644
--- a/django/contrib/admin/options.py
+++ b/django/contrib/admin/options.py
@@ -580,9 +580,12 @@ class ModelAdmin(BaseModelAdmin):
     def __str__(self):
         return "%s.%s" % (self.model._meta.app_label, self.__class__.__name__)
 
+    def get_inlines(self, request, obj=None):
+        return self.inlines
+
     def get_inline_instances(self, request, obj=None):
         inline_instances = []
-        for inline_class in self.inlines:
+        for inline_class in self.get_inlines(request, obj):
             inline = inline_class(self.model, self.admin_site)
             if request:
                 if not (inline.has_view_or_change_permission(request, obj) or

```

---

## Packet 29/40 — `pk_253f869a6ec6`
**Repository:** astropy/astropy  
**Files:** astropy/io/fits/connect.py  
**Changes:** +2/-3

### Issue

IndexError: tuple index out of range in identify_format (io.registry)
<!-- This comments are hidden when you submit the issue,
so you do not need to remove them! -->

<!-- Please be sure to check out our contributing guidelines,
https://github.com/astropy/astropy/blob/main/CONTRIBUTING.md .
Please be sure to check out our code of conduct,
https://github.com/astropy/astropy/blob/main/CODE_OF_CONDUCT.md . -->

<!-- Please have a search on our GitHub repository to see if a similar
issue has already been posted.
If a similar issue is closed, have a quick look to see if you are satisfied
by the resolution.
If not please go ahead and open an issue! -->

<!-- Please check that the development version still produces the same bug.
You can install development version with
pip install git+https://github.com/astropy/astropy
command. -->

### Description
Cron tests in HENDRICS using identify_format have started failing in `devdeps` (e.g. [here](https://github.com/StingraySoftware/HENDRICS/actions/runs/3983832171/jobs/6829483945)) with this error:
```
  File "/home/runner/work/HENDRICS/HENDRICS/.tox/py310-test-devdeps/lib/python3.10/site-packages/hendrics/io.py", line 386, in get_file_format
    fmts = identify_format("write", Table, fname, None, [], {})
  File "/home/runner/work/HENDRICS/HENDRICS/.tox/py310-test-devdeps/lib/python3.10/site-packages/astropy/io/registry/compat.py", line 52, in wrapper
    return getattr(registry, method_name)(*args, **kwargs)
  File "/home/runner/work/HENDRICS/HENDRICS/.tox/py310-test-devdeps/lib/python3.10/site-packages/astropy/io/registry/base.py", line 313, in identify_format
    if self._identifiers[(data_format, data_class)](
  File "/home/runner/work/HENDRICS/HENDRICS/.tox/py310-test-devdeps/lib/python3.10/site-packag

### Patch

```diff
diff --git a/astropy/io/fits/connect.py b/astropy/io/fits/connect.py
--- a/astropy/io/fits/connect.py
+++ b/astropy/io/fits/connect.py
@@ -65,10 +65,9 @@ def is_fits(origin, filepath, fileobj, *args, **kwargs):
         fileobj.seek(pos)
         return sig == FITS_SIGNATURE
     elif filepath is not None:
-        if filepath.lower().endswith(
+        return filepath.lower().endswith(
             (".fits", ".fits.gz", ".fit", ".fit.gz", ".fts", ".fts.gz")
-        ):
-            return True
+        )
     return isinstance(args[0], (HDUList, TableHDU, BinTableHDU, GroupsHDU))
 
 

```

---

## Packet 30/40 — `pk_73bad00420c6`
**Repository:** django/django  
**Files:** django/db/models/enums.py  
**Changes:** +7/-1

### Issue

The value of a TextChoices/IntegerChoices field has a differing type
Description
	
If we create an instance of a model having a CharField or IntegerField with the keyword choices pointing to IntegerChoices or TextChoices, the value returned by the getter of the field will be of the same type as the one created by enum.Enum (enum value).
For example, this model:
from django.db import models
from django.utils.translation import gettext_lazy as _
class MyChoice(models.TextChoices):
	FIRST_CHOICE = "first", _("The first choice, it is")
	SECOND_CHOICE = "second", _("The second choice, it is")
class MyObject(models.Model):
	my_str_value = models.CharField(max_length=10, choices=MyChoice.choices)
Then this test:
from django.test import TestCase
from testing.pkg.models import MyObject, MyChoice
class EnumTest(TestCase):
	def setUp(self) -> None:
		self.my_object = MyObject.objects.create(my_str_value=MyChoice.FIRST_CHOICE)
	def test_created_object_is_str(self):
		my_object = self.my_object
		self.assertIsInstance(my_object.my_str_value, str)
		self.assertEqual(str(my_object.my_str_value), "first")
	def test_retrieved_object_is_str(self):
		my_object = MyObject.objects.last()
		self.assertIsInstance(my_object.my_str_value, str)
		self.assertEqual(str(my_object.my_str_value), "first")
And then the results:
(django30-venv) ➜ django30 ./manage.py test
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
F.
======================================================================
FAIL: test_created_object_is_str (testing.tests.EnumTest)
----------------------------------------------------------------------
Traceback (most recent call last):
 File "/Users/mikailkocak/Development/django30/testing/tests.py", line 14, in test_created_object_is_str
	

### Patch

```diff
diff --git a/django/db/models/enums.py b/django/db/models/enums.py
--- a/django/db/models/enums.py
+++ b/django/db/models/enums.py
@@ -60,7 +60,13 @@ def values(cls):
 
 class Choices(enum.Enum, metaclass=ChoicesMeta):
     """Class for creating enumerated choices."""
-    pass
+
+    def __str__(self):
+        """
+        Use value when cast to str, so that Choices set as model instance
+        attributes are rendered as expected in templates and similar contexts.
+        """
+        return str(self.value)
 
 
 class IntegerChoices(int, Choices):

```

---

## Packet 31/40 — `pk_21d37d82f196`
**Repository:** django/django  
**Files:** django/db/models/fields/__init__.py  
**Changes:** +1/-5

### Issue

Model Field.__hash__() should be immutable.
Description
	
Field.__hash__ changes value when a field is assigned to a model class.
This code crashes with an AssertionError:
from django.db import models
f = models.CharField(max_length=200)
d = {f: 1}
class Book(models.Model):
	title = f
assert f in d
The bug was introduced in #31750.
It's unlikely to have been encountered because there are few use cases to put a field in a dict *before* it's assigned to a model class. But I found a reason to do so whilst implementing #26472 and the behaviour had me stumped for a little.
IMO we can revert the __hash__ change from #31750. Objects with the same hash are still checked for equality, which was fixed in that ticket. But it's bad if an object's hash changes, since it breaks its use in dicts.


### Patch

```diff
diff --git a/django/db/models/fields/__init__.py b/django/db/models/fields/__init__.py
--- a/django/db/models/fields/__init__.py
+++ b/django/db/models/fields/__init__.py
@@ -542,11 +542,7 @@ def __lt__(self, other):
         return NotImplemented
 
     def __hash__(self):
-        return hash((
-            self.creation_counter,
-            self.model._meta.app_label if hasattr(self, 'model') else None,
-            self.model._meta.model_name if hasattr(self, 'model') else None,
-        ))
+        return hash(self.creation_counter)
 
     def __deepcopy__(self, memodict):
         # We don't have to deepcopy very much here, since most things are not

```

---

## Packet 32/40 — `pk_8ce88ae21cad`
**Repository:** pydata/xarray  
**Files:** xarray/core/weighted.py  
**Changes:** +1/-1

### Issue

[bug] when passing boolean weights to weighted mean
<!-- A short summary of the issue, if appropriate -->


#### MCVE Code Sample
<!-- In order for the maintainers to efficiently understand and prioritize issues, we ask you post a "Minimal, Complete and Verifiable Example" (MCVE): http://matthewrocklin.com/blog/work/2018/02/28/minimal-bug-reports -->

```python
import numpy as np
import xarray as xr

dta = xr.DataArray([1., 1., 1.])
wgt = xr.DataArray(np.array([1, 1, 0], dtype=np.bool))

dta.weighted(wgt).mean()
```
Returns 

```
<xarray.DataArray ()>
array(2.)
```

#### Expected Output
```
<xarray.DataArray ()>
array(1.)
```

#### Problem Description
Passing a boolean array as weights to the weighted mean returns the wrong result because the `weights` are not properly normalized (in this case). Internally the `sum_of_weights` is calculated as

```python
xr.dot(dta.notnull(), wgt)
```
i.e. the dot product of two boolean arrays. This yields:
```
<xarray.DataArray ()>
array(True)
```

We'll need to convert it to int or float:
```python
xr.dot(dta.notnull(), wgt * 1)                                                                                                                                                                         
```
which is correct
```
<xarray.DataArray ()>
array(2)
```

#### Versions

<details><summary>Output of <tt>xr.show_versions()</tt></summary>

INSTALLED VERSIONS
------------------
commit: None
python: 3.7.6 | packaged by conda-forge | (default, Mar 23 2020, 23:03:20) 
[GCC 7.3.0]
python-bits: 64
OS: Linux
OS-release: 5.3.0-51-generic
machine: x86_64
processor: x86_64
byteorder: little
LC_ALL: None
LANG: en_US.UTF-8
LOCALE: en_US.UTF-8
libhdf5: 1.10.6
libnetcdf: 4.7.4

xarra

### Patch

```diff
diff --git a/xarray/core/weighted.py b/xarray/core/weighted.py
index 8119fa7..a07bbbd 100644
--- a/xarray/core/weighted.py
+++ b/xarray/core/weighted.py
@@ -142,7 +142,7 @@ class Weighted:
         # we need to mask data values that are nan; else the weights are wrong
         mask = da.notnull()
 
-        sum_of_weights = self._reduce(mask, self.weights, dim=dim, skipna=False)
+        sum_of_weights = self._reduce(mask, self.weights.astype(float), dim=dim, skipna=False)
 
         # 0-weights are not valid
         valid_weights = sum_of_weights != 0.0

```

---

## Packet 33/40 — `pk_d34cfde1a898`
**Repository:** psf/requests  
**Files:** requests/sessions.py  
**Changes:** +2/-0

### Issue

Removing a default header of a session
[The docs](http://docs.python-requests.org/en/latest/user/advanced/#session-objects) say that you can prevent sending a session header by setting the headers value to None in the method's arguments. You would expect (as [discussed on IRC](https://botbot.me/freenode/python-requests/msg/10788170/)) that this would work for session's default headers, too:

``` python
session = requests.Session()
# Do not send Accept-Encoding
session.headers['Accept-Encoding'] = None
```

What happens is that "None"  gets sent as the value of header.

```
Accept-Encoding: None
```

For the reference, here is a way that works:

``` python
del session.headers['Accept-Encoding']
```



### Patch

```diff
diff --git a/requests/sessions.py b/requests/sessions.py
--- a/requests/sessions.py
+++ b/requests/sessions.py
@@ -59,6 +59,8 @@ def merge_setting(request_setting, session_setting, dict_class=OrderedDict):
         if v is None:
             del merged_setting[k]
 
+    merged_setting = dict((k, v) for (k, v) in merged_setting.items() if v is not None)
+
     return merged_setting
 
 

```

---

## Packet 34/40 — `pk_5a72342d8c08`
**Repository:** astropy/astropy  
**Files:** astropy/units/decorators.py  
**Changes:** +1/-1

### Issue

units.quantity_input decorator fails for constructors with type hinted return value -> None
### Summary
I am using the `units.quantity_input` decorator with typing hints for constructors, however when I add the correct return value for the constructor (`None`) then I get an exception, because `None` has no attribute `to`.

### Reproducer
The issue can be reproduced with the following file:
``` Python
import astropy.units as u


class PoC(object):

    @u.quantity_input
    def __init__(self, voltage: u.V) -> None:
        pass


if __name__ == '__main__':
    poc = PoC(1.*u.V)
```
which results in the following error:
```
$ python3 poc.py
Traceback (most recent call last):
  File "poc.py", line 12, in <module>
    poc = PoC(1.*u.V)
  File "/usr/lib64/python3.6/site-packages/astropy/utils/decorators.py", line 868, in __init__
    func = make_function_with_signature(func, name=name, **wrapped_args)
  File "/usr/lib64/python3.6/site-packages/astropy/units/decorators.py", line 225, in wrapper
    return return_.to(wrapped_signature.return_annotation)
AttributeError: 'NoneType' object has no attribute 'to'
```

This has been tested on Fedora 27 with python 3.6.3, astropy 2.0.2 and numpy 1.13.3 all from Fedora's repository.

### Workaround
The issue can be circumvented by not adding the return type typing hint. Unfortunately, then a static type checker cannot infer that this function returns nothing.

### Possible fix
Maybe the decorator could explicitly check whether None is returned and then omit the unit check.


### Patch

```diff
diff --git a/astropy/units/decorators.py b/astropy/units/decorators.py
--- a/astropy/units/decorators.py
+++ b/astropy/units/decorators.py
@@ -220,7 +220,7 @@ def wrapper(*func_args, **func_kwargs):
             # Call the original function with any equivalencies in force.
             with add_enabled_equivalencies(self.equivalencies):
                 return_ = wrapped_function(*func_args, **func_kwargs)
-            if wrapped_signature.return_annotation is not inspect.Signature.empty:
+            if wrapped_signature.return_annotation not in (inspect.Signature.empty, None):
                 return return_.to(wrapped_signature.return_annotation)
             else:
                 return return_

```

---

## Packet 35/40 — `pk_e32f224c66d7`
**Repository:** scikit-learn/scikit-learn  
**Files:** sklearn/ensemble/_iforest.py  
**Changes:** +16/-8

### Issue

X does not have valid feature names, but IsolationForest was fitted with feature names
### Describe the bug

If you fit an `IsolationForest` using a `pd.DataFrame` it generates a warning

``` python
X does not have valid feature names, but IsolationForest was fitted with feature names
```

This only seems to occur if you supply a non-default value (i.e. not "auto") for the `contamination` parameter. This warning is unexpected as a) X does have valid feature names and b) it is being raised by the `fit()` method but in general is supposed to indicate that predict has been called with ie. an ndarray but the model was fitted using a dataframe.

The reason is most likely when you pass contamination != "auto" the estimator essentially calls predict on the training data in order to determine the `offset_` parameters:

https://github.com/scikit-learn/scikit-learn/blob/9aaed498795f68e5956ea762fef9c440ca9eb239/sklearn/ensemble/_iforest.py#L337

### Steps/Code to Reproduce

```py
from sklearn.ensemble import IsolationForest
import pandas as pd

X = pd.DataFrame({"a": [-1.1, 0.3, 0.5, 100]})
clf = IsolationForest(random_state=0, contamination=0.05).fit(X)
```

### Expected Results

Does not raise "X does not have valid feature names, but IsolationForest was fitted with feature names"

### Actual Results

raises "X does not have valid feature names, but IsolationForest was fitted with feature names"

### Versions

```shell
System:
    python: 3.10.6 (main, Nov 14 2022, 16:10:14) [GCC 11.3.0]
executable: /home/david/dev/warpspeed-timeseries/.venv/bin/python
   machine: Linux-5.15.0-67-generic-x86_64-with-glibc2.35

Python dependencies:
      sklearn: 1.2.1
          pip: 23.0.1
   setuptools: 67.1.0
        numpy: 1.23.5
        scipy: 1.1

### Patch

```diff
diff --git a/sklearn/ensemble/_iforest.py b/sklearn/ensemble/_iforest.py
--- a/sklearn/ensemble/_iforest.py
+++ b/sklearn/ensemble/_iforest.py
@@ -344,8 +344,10 @@ def fit(self, X, y=None, sample_weight=None):
             self.offset_ = -0.5
             return self
 
-        # else, define offset_ wrt contamination parameter
-        self.offset_ = np.percentile(self.score_samples(X), 100.0 * self.contamination)
+        # Else, define offset_ wrt contamination parameter
+        # To avoid performing input validation a second time we call
+        # _score_samples rather than score_samples
+        self.offset_ = np.percentile(self._score_samples(X), 100.0 * self.contamination)
 
         return self
 
@@ -428,15 +430,21 @@ def score_samples(self, X):
             The anomaly score of the input samples.
             The lower, the more abnormal.
         """
-        # code structure from ForestClassifier/predict_proba
-
-        check_is_fitted(self)
-
         # Check data
         X = self._validate_data(X, accept_sparse="csr", dtype=np.float32, reset=False)
 
-        # Take the opposite of the scores as bigger is better (here less
-        # abnormal)
+        return self._score_samples(X)
+
+    def _score_samples(self, X):
+        """Private version of score_samples without input validation.
+
+        Input validation would remove feature names, so we disable it.
+        """
+        # Code structure from ForestClassifier/predict_proba
+
+        check_is_fitted(self)
+
+        # Take the opposite of the scores as bigger is better (here less abnormal)
         return -self._compute_chunked_score_samples(X)
 
     def _compute_chunked_score_samples(self, X):

```

---

## Packet 36/40 — `pk_583b76fe75c5`
**Repository:** django/django  
**Files:** django/db/models/enums.py  
**Changes:** +3/-1

### Issue

The value of a TextChoices/IntegerChoices field has a differing type
Description
	
If we create an instance of a model having a CharField or IntegerField with the keyword choices pointing to IntegerChoices or TextChoices, the value returned by the getter of the field will be of the same type as the one created by enum.Enum (enum value).
For example, this model:
from django.db import models
from django.utils.translation import gettext_lazy as _
class MyChoice(models.TextChoices):
	FIRST_CHOICE = "first", _("The first choice, it is")
	SECOND_CHOICE = "second", _("The second choice, it is")
class MyObject(models.Model):
	my_str_value = models.CharField(max_length=10, choices=MyChoice.choices)
Then this test:
from django.test import TestCase
from testing.pkg.models import MyObject, MyChoice
class EnumTest(TestCase):
	def setUp(self) -> None:
		self.my_object = MyObject.objects.create(my_str_value=MyChoice.FIRST_CHOICE)
	def test_created_object_is_str(self):
		my_object = self.my_object
		self.assertIsInstance(my_object.my_str_value, str)
		self.assertEqual(str(my_object.my_str_value), "first")
	def test_retrieved_object_is_str(self):
		my_object = MyObject.objects.last()
		self.assertIsInstance(my_object.my_str_value, str)
		self.assertEqual(str(my_object.my_str_value), "first")
And then the results:
(django30-venv) ➜ django30 ./manage.py test
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
F.
======================================================================
FAIL: test_created_object_is_str (testing.tests.EnumTest)
----------------------------------------------------------------------
Traceback (most recent call last):
 File "/Users/mikailkocak/Development/django30/testing/tests.py", line 14, in test_created_object_is_str
	

### Patch

```diff
diff --git a/django/db/models/enums.py b/django/db/models/enums.py
index 2924da3..b028c06 100644
--- a/django/db/models/enums.py
+++ b/django/db/models/enums.py
@@ -60,7 +60,9 @@ class ChoicesMeta(enum.EnumMeta):
 
 class Choices(enum.Enum, metaclass=ChoicesMeta):
     """Class for creating enumerated choices."""
-    pass
+    
+    def __str__(self):
+        return str(self.value)
 
 
 class IntegerChoices(int, Choices):

```

---

## Packet 37/40 — `pk_3152ef187dc9`
**Repository:** matplotlib/matplotlib  
**Files:** lib/mpl_toolkits/axes_grid1/inset_locator.py  
**Changes:** +2/-0

### Issue

[Bug]: Error while creating inset axes using `mpl_toolkits.axes_grid1.inset_locator.inset_axes`
### Bug summary

Unable to create the inset axes in a plot using the code (following the first example on the website as posted [here](https://matplotlib.org/stable/gallery/axes_grid1/inset_locator_demo.html) posted below.

### Code for reproduction

```python
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes


fig, (ax, ax2) = plt.subplots(1, 2, figsize=[5.5, 2.8])
axins = inset_axes(ax, width=1.3, height=0.9)
plt.show()
```


### Actual outcome

```Python
---------------------------------------------------------------------------
AttributeError                            Traceback (most recent call last)
File ~/miniconda3/envs/ubermagdev/lib/python3.8/site-packages/IPython/core/formatters.py:340, in BaseFormatter.__call__(self, obj)
    338     pass
    339 else:
--> 340     return printer(obj)
    341 # Finally look for special method names
    342 method = get_real_method(obj, self.print_method)

File ~/miniconda3/envs/ubermagdev/lib/python3.8/site-packages/IPython/core/pylabtools.py:152, in print_figure(fig, fmt, bbox_inches, base64, **kwargs)
    149     from matplotlib.backend_bases import FigureCanvasBase
    150     FigureCanvasBase(fig)
--> 152 fig.canvas.print_figure(bytes_io, **kw)
    153 data = bytes_io.getvalue()
    154 if fmt == 'svg':

File ~/miniconda3/envs/ubermagdev/lib/python3.8/site-packages/matplotlib/backend_bases.py:2353, in FigureCanvasBase.print_figure(self, filename, dpi, facecolor, edgecolor, orientation, format, bbox_inches, pad_inches, bbox_extra_artists, backend, **kwargs)
   2350         bbox_inches = bbox_inches.padded(pad_inches)
   2352     # call adjust_bbox 

### Patch

```diff
diff --git a/lib/mpl_toolkits/axes_grid1/inset_locator.py b/lib/mpl_toolkits/axes_grid1/inset_locator.py
--- a/lib/mpl_toolkits/axes_grid1/inset_locator.py
+++ b/lib/mpl_toolkits/axes_grid1/inset_locator.py
@@ -69,6 +69,8 @@ def draw(self, renderer):
         raise RuntimeError("No draw method should be called")
 
     def __call__(self, ax, renderer):
+        if renderer is None:
+            renderer = ax.figure._get_renderer()
         self.axes = ax
         bbox = self.get_window_extent(renderer)
         px, py = self.get_offset(bbox.width, bbox.height, 0, 0, renderer)

```

---

## Packet 38/40 — `pk_8629d084aeb7`
**Repository:** sympy/sympy  
**Files:** sympy/physics/units/unitsystem.py  
**Changes:** +5/-5

### Issue

SI._collect_factor_and_dimension() cannot properly detect that exponent is dimensionless
How to reproduce:

```python
from sympy import exp
from sympy.physics import units
from sympy.physics.units.systems.si import SI

expr = units.second / (units.ohm * units.farad)
dim = SI._collect_factor_and_dimension(expr)[1]

assert SI.get_dimension_system().is_dimensionless(dim)

buggy_expr = 100 + exp(expr)
SI._collect_factor_and_dimension(buggy_expr)

# results in ValueError: Dimension of "exp(second/(farad*ohm))" is Dimension(time/(capacitance*impedance)), but it should be Dimension(1)
```


### Patch

```diff
diff --git a/sympy/physics/units/unitsystem.py b/sympy/physics/units/unitsystem.py
index 4413d8e..8818520 100644
--- a/sympy/physics/units/unitsystem.py
+++ b/sympy/physics/units/unitsystem.py
@@ -190,10 +190,10 @@ class UnitSystem(_QuantityMapper):
                 dim /= idim**count
             return factor, dim
         elif isinstance(expr, Function):
-            fds = [self._collect_factor_and_dimension(
-                arg) for arg in expr.args]
-            return (expr.func(*(f[0] for f in fds)),
-                    *(d[1] for d in fds))
+            fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]
+            if all(self.get_dimension_system().is_dimensionless(d[1]) for d in fds):
+                return expr.func(*(f[0] for f in fds)), Dimension(1)
+            return expr.func(*(f[0] for f in fds)), expr.func(*(d[1] for d in fds))
         elif isinstance(expr, Dimension):
             return S.One, expr
         else:
@@ -203,4 +203,4 @@ class UnitSystem(_QuantityMapper):
         """
         Return the units of the system that do not have a prefix.
         """
-        return set(filter(lambda u: not u.is_prefixed and not u.is_physical_constant, self._units))
+        return set(filter(lambda u: not u.is_prefixed and not u.is_physical_constant, self._units))

```

---

## Packet 39/40 — `pk_f9eaf1759bcb`
**Repository:** psf/requests  
**Files:** requests/models.py  
**Changes:** +1/-1

### Issue

Removing a default header of a session
[The docs](http://docs.python-requests.org/en/latest/user/advanced/#session-objects) say that you can prevent sending a session header by setting the headers value to None in the method's arguments. You would expect (as [discussed on IRC](https://botbot.me/freenode/python-requests/msg/10788170/)) that this would work for session's default headers, too:

``` python
session = requests.Session()
# Do not send Accept-Encoding
session.headers['Accept-Encoding'] = None
```

What happens is that "None"  gets sent as the value of header.

```
Accept-Encoding: None
```

For the reference, here is a way that works:

``` python
del session.headers['Accept-Encoding']
```



### Patch

```diff
diff --git a/requests/models.py b/requests/models.py
index 0d0af12..8b62164 100644
--- a/requests/models.py
+++ b/requests/models.py
@@ -391,7 +391,7 @@ class PreparedRequest(RequestEncodingMixin, RequestHooksMixin):
         """Prepares the given HTTP headers."""
 
         if headers:
-            self.headers = CaseInsensitiveDict((to_native_string(name), value) for name, value in headers.items())
+            self.headers = CaseInsensitiveDict((to_native_string(name), value) for name, value in headers.items() if value is not None)
         else:
             self.headers = CaseInsensitiveDict()
 

```

---

## Packet 40/40 — `pk_512722635caa`
**Repository:** sphinx-doc/sphinx  
**Files:** sphinx/pycode/ast.py  
**Changes:** +4/-1

### Issue

1-element tuple rendered incorrectly
**Describe the bug**
This is a followup to #7964 which has been addressed in #8265.

However the special case of a 1-element tuple is still not handled correctly.

`(1,)` is rendered as `(1)`, but should keep the trailing comma.

**To Reproduce**
Add a testcase
```
    ("(1,)", "(1,)"),                           # Tuple (single element)
```
at https://github.com/sphinx-doc/sphinx/blob/e0b1e1002b500acc63dfd0806f8095dd6b27037b/tests/test_pycode_ast.py#L57




### Patch

```diff
diff --git a/sphinx/pycode/ast.py b/sphinx/pycode/ast.py
index 5db5a4a..aaccfa0 100644
--- a/sphinx/pycode/ast.py
+++ b/sphinx/pycode/ast.py
@@ -214,7 +214,10 @@ class _UnparseVisitor(ast.NodeVisitor):
 
     def visit_Tuple(self, node: ast.Tuple) -> str:
         if node.elts:
-            return "(" + ", ".join(self.visit(e) for e in node.elts) + ")"
+            if len(node.elts) == 1:
+                return "(" + self.visit(node.elts[0]) + ",)"
+            else:
+                return "(" + ", ".join(self.visit(e) for e in node.elts) + ")"
         else:
             return "()"
 

```

---
