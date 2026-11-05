"""Post-hoc full-package witnesses; observed values are recorded without imputation."""
import argparse,json,traceback,warnings
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--kind',choices=['matplotlib','sklearn']);ap.add_argument('--output',type=Path);args=ap.parse_args()
rows=[];metadata={}
if args.kind=='matplotlib':
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    metadata={'module_path':matplotlib.__file__,'version':matplotlib.__version__,'numpy':np.__version__}
    for name,x,y,c,reduce,kwargs in [
      ('empty_max_default',[],[],[],np.max,{}),
      ('singleton_max_default',[0.5],[0.5],[1.0],np.max,{}),
      ('singleton_min_default',[0.5],[0.5],[1.0],np.min,{}),
      ('singleton_mean_default',[0.5],[0.5],[1.0],np.mean,{}),
      ('singleton_max_explicit_mincnt1',[0.5],[0.5],[1.0],np.max,{'mincnt':1}),
      ('singleton_max_explicit_mincnt0',[0.5],[0.5],[1.0],np.max,{'mincnt':0})]:
        row={'name':name,'reducer':reduce.__name__,'kwargs':kwargs}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always');fig,ax=plt.subplots()
            try:
                result=ax.hexbin(x,y,C=c,gridsize=3,reduce_C_function=reduce,**kwargs)
                row.update(status='returned',bins=len(result.get_array()),values=[float(v) for v in result.get_array()],offsets=result.get_offsets().tolist())
            except Exception as ex:row.update(status='exception',exception_type=type(ex).__name__,message=str(ex),traceback=traceback.format_exc())
            finally:plt.close(fig)
        row['warnings']=[{'type':type(w.message).__name__,'message':str(w.message)} for w in caught];rows.append(row)
else:
    import numpy as np
    import sklearn
    from sklearn.datasets import load_iris,make_classification
    from sklearn.linear_model import LogisticRegressionCV
    import sklearn.linear_model.logistic as logistic
    metadata={'module_path':sklearn.__file__,'version':sklearn.__version__,'numpy':np.__version__}
    iris=load_iris();X,y=iris.data,iris.target
    for fit in [False,True]:
        for multi in ['ovr','multinomial']:
            row={'name':'fit_intercept_'+str(fit)+'_'+multi,'fit_intercept':fit,'multi_class':multi}
            try:
                model=LogisticRegressionCV(Cs=[0.1,1.0],cv=3,scoring='neg_log_loss',fit_intercept=fit,multi_class=multi,solver='lbfgs',max_iter=500,tol=1e-8,n_jobs=1,random_state=6658)
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always');model.fit(X,y)
                row.update(status='returned',probabilities=model.predict_proba(X).tolist(),coefficients=model.coef_.tolist(),intercepts=model.intercept_.tolist(),scores={str(k):v.tolist() for k,v in model.scores_.items()},selected_C=model.C_.tolist(),warnings=[str(w.message) for w in caught])
            except Exception as ex:row.update(status='exception',exception_type=type(ex).__name__,message=str(ex),traceback=traceback.format_exc())
            rows.append(row)
    # Record constructor arguments in a separate instrumentation run. No source edit.
    calls=[];original=logistic.LogisticRegression
    def observed_constructor(*a,**kw):
        calls.append({'fit_intercept_passed':kw.get('fit_intercept','OMITTED'),'multi_class_passed':kw.get('multi_class','OMITTED')})
        return original(*a,**kw)
    logistic.LogisticRegression=observed_constructor
    try:
        model=LogisticRegressionCV(Cs=[0.1],cv=3,scoring='neg_log_loss',fit_intercept=False,multi_class='multinomial',solver='lbfgs',max_iter=500,n_jobs=1)
        with warnings.catch_warnings():warnings.simplefilter('ignore');model.fit(X,y)
        rows.append({'name':'constructor_trace_separate_run','status':'returned','calls':calls})
    except Exception as ex:rows.append({'name':'constructor_trace_separate_run','status':'exception','exception_type':type(ex).__name__,'message':str(ex),'calls':calls})
    finally:logistic.LogisticRegression=original
with args.output.open('x') as f:json.dump({'metadata':metadata,'scenarios':rows,'independent_human_adjudication':False},f,indent=2)
