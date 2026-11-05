"""Run full-package observations; no independent labels or imputed decisions."""
import argparse,json,math,sys,traceback,warnings
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--case',required=True);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
rows=[];metadata={}
def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    if hasattr(x,'tolist'):return clean(x.tolist())
    if isinstance(x,float) and not math.isfinite(x):return None
    return x
def observe(name,fn):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        try:r={'name':name,'status':'returned','result':clean(fn())}
        except Exception as ex:r={'name':name,'status':'exception','exception_type':type(ex).__name__,'message':str(ex),'traceback':traceback.format_exc()}
        r['warnings']=[{'type':type(w.message).__name__,'message':str(w.message)} for w in caught]
    rows.append(r)

if a.case.startswith('django'):
    import setuptools
    import django
    from django.conf import settings
    sys.path.insert(0,str(a.source/'tests'))
    settings.configure(INSTALLED_APPS=['django.contrib.auth','django.contrib.contenttypes'],DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':':memory:'}},SECRET_KEY='diagnostic-no-service',USE_TZ=False)
    django.setup()
    from django.contrib.auth.models import AbstractBaseUser
    from django.contrib.auth.checks import check_user_model
    from django.db import models
    from django.test.utils import isolate_apps,override_settings
    metadata={'module_path':django.__file__,'version':django.get_version()}
    def constraint_case(kind,backend):
        with isolate_apps('auth_tests') as apps:
            if kind=='single':constraint=models.UniqueConstraint(fields=['username'],name='diag_single')
            elif kind=='multi':constraint=models.UniqueConstraint(fields=['username','email'],name='diag_multi')
            else:constraint=models.UniqueConstraint(fields=['username'],condition=models.Q(active=True),name='diag_partial')
            class DiagnosticUser(AbstractBaseUser):
                username=models.CharField(max_length=30);email=models.CharField(max_length=50);active=models.BooleanField(default=True)
                USERNAME_FIELD='username'
                class Meta:app_label='auth_tests';constraints=[constraint]
            with override_settings(AUTH_USER_MODEL='auth_tests.DiagnosticUser',AUTHENTICATION_BACKENDS=[backend]):
                errors=check_user_model(app_configs=apps.get_app_configs())
                return {'check_ids':[e.id for e in errors],'messages':[e.msg for e in errors]}
    for kind in ['single','multi','conditional']:
        for backend in ['django.contrib.auth.backends.ModelBackend','my.custom.backend']:
            observe(kind+'_'+('default' if backend.startswith('django') else 'custom'),lambda k=kind,b=backend:constraint_case(k,b))
elif a.case.startswith('scikit'):
    import numpy as np,pandas as pd,sklearn
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    metadata={'module_path':sklearn.__file__,'version':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__}
    def scale(pandas_output):
        frame=pd.DataFrame({'a':[0,1,2]},dtype='int64')
        m=StandardScaler().set_output(transform='pandas' if pandas_output else 'default');out=m.fit_transform(frame)
        vals=np.asarray(out)
        return {'values':vals,'dtype':str(vals.dtype),'input_values':frame.values,'expected_analytic_values':(frame.values-frame.values.mean(axis=0))/frame.values.std(axis=0)}
    def pca():
        frame=pd.DataFrame({'a':[0,1,2,3],'b':[2,0,1,2]},dtype='int64')
        out=PCA(n_components=1).set_output(transform='pandas').fit_transform(frame)
        return {'values':out.values,'columns':list(out.columns),'dtypes':list(map(str,out.dtypes))}
    observe('standard_scaler_default',lambda:scale(False));observe('standard_scaler_pandas_integer',lambda:scale(True));observe('pca_pandas_renamed_columns',pca)
elif a.case.startswith('astropy'):
    import io,numpy as np,astropy
    from astropy.table import Table
    metadata={'module_path':astropy.__file__,'version':astropy.__version__,'numpy':np.__version__}
    def structured(masked):
        data=np.array([(1,2.5),(3,4.5)],dtype=[('x','i4'),('y','f8')])
        if masked:data=np.ma.array(data,mask=[(False,True),(True,False)])
        t=Table();t['value']=data;col=t['value'];stream=io.StringIO()
        result={'column_type':type(col).__name__,'column_module':type(col).__module__,'dtype':str(col.dtype),'values':col.tolist(),'has_mask':hasattr(col,'mask')}
        try:
            t.write(stream,format='ascii.ecsv');encoded=stream.getvalue();rt=Table.read(encoded,format='ascii.ecsv')
            result.update(ecsv_write_status='returned',ecsv_roundtrip_column_type=type(rt['value']).__name__,ecsv_text=encoded)
        except Exception as ex:result.update(ecsv_write_status='exception',ecsv_exception_type=type(ex).__name__,ecsv_message=str(ex))
        return result
    observe('structured_unmasked',lambda:structured(False));observe('structured_masked',lambda:structured(True))
else:
    import numpy as np,xarray as xr,dask
    metadata={'module_path':xr.__file__,'version':xr.__version__,'dask':dask.__version__,'dask_path':dask.__file__}
    def rolling(backend,minp):
        arr=xr.DataArray(np.arange(1,10,dtype=float),dims=['time'],coords={'time':np.arange(9)})
        if backend=='dask':arr=arr.chunk({'time':3})
        r=arr.rolling(time=3,center=True,min_periods=minp)
        windows=[{'label':int(label.item()),'values':window.values,'mean':float(window.mean().compute().item())} for label,window in r]
        return {'labels':[x['label'] for x in windows],'manual_means':[x['mean'] for x in windows],'windows':windows,'vectorized_means':r.mean().values}
    for backend in ['numpy','dask']:
        for minp in [None,1]:observe(backend+'_minp_'+str(minp),lambda b=backend,m=minp:rolling(b,m))
with a.output.open('x') as f:json.dump({'metadata':metadata,'scenarios':rows,'independent_human_adjudication':False},f,indent=2,allow_nan=False)
