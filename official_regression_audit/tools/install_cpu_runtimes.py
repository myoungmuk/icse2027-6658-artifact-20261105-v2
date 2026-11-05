"""Isolated CPU scientific/test environments; no models or GPU resources."""
import concurrent.futures,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
UV=ROOT/'runtime_manager/bin/uv'
PYTHON=ROOT/'python_runtimes/cpython-3.9.24-linux-x86_64-gnu/bin/python3.9'
CONFIG={
 'legacy_science':['numpy==1.19.5','scipy==1.5.4','pandas==1.1.5','pytest==5.4.3','Cython==0.29.36','setuptools==59.8.0','wheel==0.41.3','joblib==0.14.1','threadpoolctl==2.2.0','mpmath==1.2.1','hypothesis==6.31.6','packaging==20.9'],
 'modern_science':['numpy==1.23.5','scipy==1.9.3','pandas==1.5.3','pytest==7.4.4','Cython==0.29.36','setuptools==65.5.0','setuptools_scm==6.4.2','wheel==0.41.3','joblib==1.2.0','threadpoolctl==3.1.0','mpmath==1.2.1','hypothesis==6.88.1','pyerfa==2.0.1.4','contourpy==1.0.7','kiwisolver==1.4.5','cycler==0.11.0','fonttools==4.43.1','pillow==9.5.0','pyparsing==3.1.1','python-dateutil==2.8.2','packaging==23.2','pytest-astropy-header==0.2.2','pytest-arraydiff==0.5.0','pytest-doctestplus==0.12.1','pytest-filter-subpackage==0.1.2','pytest-mock==3.12.0','pytest-remotedata==0.4.0','pytest-openfiles==0.5.0'],
 'sphinx_4':['Sphinx==4.3.2','Jinja2==3.0.3','docutils==0.17.1','pytest==7.4.4','sphinxcontrib-applehelp==1.0.2','sphinxcontrib-devhelp==1.0.2','sphinxcontrib-htmlhelp==2.0.0','sphinxcontrib-qthelp==1.0.3','sphinxcontrib-serializinghtml==1.1.5','sphinxcontrib-jsmath==1.0.1','alabaster==0.7.13','snowballstemmer==2.2.0'],
 'sphinx_7':['Sphinx==7.2.6','Jinja2==3.1.6','docutils==0.20.1','pytest==7.4.4','snowballstemmer==2.2.0'],
 'pylint_3':['pylint==3.0.2','astroid==3.0.1','pytest==7.4.4','pytest-benchmark==4.0.0','pytest-timeout==2.2.0'],
 'pytest_self':['pytest==6.0.2','pluggy==0.13.1','py==1.11.0','attrs==21.4.0','more-itertools==8.14.0','packaging==20.9','hypothesis==6.31.6','toml==0.10.2'],
 'requests':['requests==2.27.1','urllib3==1.26.18','idna==3.4','charset-normalizer==2.0.12','certifi==2023.7.22','pytest==7.4.4','pytest-httpbin==2.0.0','Flask==2.2.5','Werkzeug==2.2.3','PySocks==1.7.1','brotli==1.1.0'],
}


def run(item):
    key,requirements=item;env=ROOT/'runtimes'/key;log=ROOT/'evidence'/('runtime_'+key+'.log')
    e=dict(os.environ,UV_CACHE_DIR=str(ROOT/'uv_cache'))
    with log.open('x') as f:
        p=subprocess.run([str(UV),'venv','--python',str(PYTHON),str(env)],env=e,stdout=f,stderr=subprocess.STDOUT)
        if p.returncode:return key,p.returncode
        p=subprocess.run([str(UV),'pip','install','--python',str(env/'bin/python'),*requirements],env=e,stdout=f,stderr=subprocess.STDOUT)
    print('ENV',key,'returncode',p.returncode,flush=True)
    return key,p.returncode


def main():
    (ROOT/'runtimes').mkdir()
    with (ROOT/'experiment_non_django/RUNTIME_REQUIREMENTS.json').open('x') as f:json.dump(CONFIG,f,indent=2)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=dict(pool.map(run,CONFIG.items()))
    with (ROOT/'evidence/runtime_install_results.json').open('x') as f:json.dump(results,f,indent=2)
    assert not any(results.values()),results


if __name__=='__main__':main()
