"""Run original Django test runner and record real unittest outcomes."""
import argparse,atexit,hashlib,importlib.metadata,json,os,platform,runpy,sys,traceback,unittest
from datetime import datetime,timezone
from pathlib import Path

ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('targets',nargs='+');args=ap.parse_args()
source=args.source.resolve();events=[];runs=[]


class RecordingResult(unittest.TextTestResult):
    def addSuccess(self,test):
        events.append({'test_id':test.id(),'outcome':'success'});super().addSuccess(test)
    def addFailure(self,test,err):
        events.append({'test_id':test.id(),'outcome':'failure','exception_type':err[0].__name__,'traceback':''.join(traceback.format_exception(*err))});super().addFailure(test,err)
    def addError(self,test,err):
        events.append({'test_id':test.id(),'outcome':'error','exception_type':err[0].__name__,'traceback':''.join(traceback.format_exception(*err))});super().addError(test,err)
    def addSkip(self,test,reason):
        events.append({'test_id':test.id(),'outcome':'skip','reason':reason});super().addSkip(test,reason)
    def addSubTest(self,test,subtest,err):
        if err is not None:events.append({'test_id':test.id(),'subtest_id':str(subtest),'outcome':'subtest_failure' if issubclass(err[0],test.failureException) else 'subtest_error','exception_type':err[0].__name__,'traceback':''.join(traceback.format_exception(*err))})
        super().addSubTest(test,subtest,err)
    def stopTestRun(self):
        runs.append({'tests_run':self.testsRun,'failures':len(self.failures),'errors':len(self.errors),'skipped':len(self.skipped),'successful':self.wasSuccessful()});super().stopTestRun()


unittest.TextTestRunner.resultclass=RecordingResult
started=datetime.now(timezone.utc).isoformat();top_exception=None


def save():
    dependencies={x.metadata['Name']:x.version for x in importlib.metadata.distributions(path=os.environ.get('PYTHONPATH','').split(os.pathsep))}
    payload={'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),'source':str(source),'targets':args.targets,'events':events,'runner_summaries':runs,'top_exception':top_exception,'dependencies':dependencies}
    with args.output.open('x') as f:json.dump(payload,f,ensure_ascii=False,indent=2);f.write('\n')


atexit.register(save)
try:
    import setuptools  # Real vendored distutils for old Django on Python 3.12.
    os.chdir(source)
    sys.path[:0]=[str(source),str(source/'tests')]
    sys.argv=[str(source/'tests/runtests.py'),'--settings=test_sqlite','--parallel=1','--verbosity=2',*args.targets]
    runpy.run_path(str(source/'tests/runtests.py'),run_name='__main__')
except SystemExit:
    raise
except BaseException as ex:
    top_exception={'type':type(ex).__name__,'traceback':traceback.format_exc()}
    raise
