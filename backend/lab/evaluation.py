import asyncio
import base64
import json
import shlex

from .db import now

# Run as a short, isolated Python process INSIDE the learner container. No paths or
# regexes are interpolated into shell syntax; JSON is carried as a base64 argument.
PROBE = r'''
import os,sys,json,base64,stat,pwd,grp,re,subprocess
c=json.loads(base64.b64decode(sys.argv[1])); t=c['type']; ok=False
try:
 if t=='path':
  p=c['path']; k=c['kind']; ok={'file':os.path.isfile,'directory':os.path.isdir,'symlink':os.path.islink,'absent':lambda p:not os.path.lexists(p)}[k](p)
 elif t=='content':
  with open(c['path'],encoding='utf-8') as f: text=f.read(1000001)
  if len(text)>1000000: raise ValueError('File exceeds the 1 MB check limit')
  v=c['value']; m=c['match']; ok=(v in text) if m=='contains' else (text==v if m=='exact' else re.search(v,text) is not None)
 elif t=='permissions': ok=stat.S_IMODE(os.stat(c['path']).st_mode)==int(c['mode'],8)
 elif t=='ownership':
  s=os.stat(c['path']); ok=(not c.get('owner') or pwd.getpwuid(s.st_uid).pw_name==c['owner']) and (not c.get('group') or grp.getgrgid(s.st_gid).gr_name==c['group'])
 elif t=='user':
  try: u=pwd.getpwnam(c['name'])
  except KeyError: u=None
  ok=(u is not None)==c['exists']
  if u and c['exists']: ok=ok and (not c.get('shell') or u.pw_shell==c['shell']) and (not c.get('home') or u.pw_dir==c['home'])
 elif t=='group':
  try: grp.getgrnam(c['name']); found=True
  except KeyError: found=False
  ok=found==c['exists']
 elif t=='membership':
  try:
   u=pwd.getpwnam(c['user']); g=grp.getgrnam(c['group']); ok=u.pw_gid==g.gr_gid or c['user'] in g.gr_mem
  except KeyError: ok=False
 elif t=='package':
  r=subprocess.run(['dpkg-query','-W','-f=${Status}',c['name']],capture_output=True,text=True,timeout=5)
  ok=r.returncode==0 and r.stdout=='install ok installed'
 elif t=='process':
  args=['pgrep','-x',c['name']]
  if c.get('user'): args+=['-u',c['user']]
  r=subprocess.run(args,capture_output=True,timeout=5)
  if r.returncode not in (0,1): raise ValueError('Process lookup failed')
  ok=r.returncode==0
 print(json.dumps({'passed':bool(ok),'message':'Condition satisfied' if ok else 'Condition not satisfied'}))
except FileNotFoundError:
 print(json.dumps({'passed':False,'message':'Required path does not exist'}))
except Exception as e:
 print(json.dumps({'error':str(e)}))
'''


def check_one(runtime, environment_id, check):
    if check.type == "command":
        result = runtime.exec(environment_id, check.script, check.user, check.timeout)
        if result.timed_out:
            return {"status": "error", "message": f"Command timed out after {check.timeout}s", "stdout": result.stdout, "stderr": result.stderr}
        passed = result.code == check.expected_exit and (check.stdout_contains is None or check.stdout_contains in result.stdout)
        return {"status": "pass" if passed else "fail", "message": f"Exit {result.code} (expected {check.expected_exit})", "stdout": result.stdout, "stderr": result.stderr}
    encoded = base64.b64encode(check.model_dump_json().encode()).decode()
    result = runtime.exec(environment_id, f"python3 -c {shlex.quote(PROBE)} {shlex.quote(encoded)}", timeout=10)
    if result.timed_out or result.code != 0:
        return {"status": "error", "message": result.stderr or "Check timed out or could not run"}
    try:
        data = json.loads(result.stdout)
        return {"status": "error" if "error" in data else ("pass" if data["passed"] else "fail"), "message": data.get("error", data.get("message", ""))}
    except (ValueError, KeyError):
        return {"status": "error", "message": "Check returned invalid output"}


async def evaluate(runtime, db, environment_id, exercise_id=None):
    async with runtime.lock(environment_id):
        environment = await asyncio.to_thread(runtime.refresh, environment_id)
        if environment["state"] != "running" or not environment["setup_done"]:
            from .runtime import LabError
            raise LabError("Start a successfully initialized course environment before evaluating")
        if not environment["course_key"]:
            raise ValueError("Free Practice does not have exercises")
        course = db.course(environment["course_key"])
        exercises = [e for e in course.exercises if not exercise_id or e.id == exercise_id]
        if not exercises:
            raise KeyError("Exercise not found in this course")
        output = []
        for exercise in exercises:
            tasks = []
            for task in exercise.tasks:
                checks = []
                for check in task.checks:
                    try:
                        checks.append(await asyncio.to_thread(check_one, runtime, environment_id, check))
                    except Exception as exc:
                        checks.append({"status": "error", "message": str(exc)[:2000]})
                status = "error" if any(c["status"] == "error" for c in checks) else ("pass" if all(c["status"] == "pass" for c in checks) else "fail")
                tasks.append({"id": task.id, "status": status, "earned": task.points if status == "pass" else 0, "available": task.points, "checks": checks})
            result = {"exercise_id": exercise.id, "tasks": tasks, "earned": sum(t["earned"] for t in tasks), "available": sum(t["available"] for t in tasks), "checked_at": now()}
            db.execute("INSERT OR REPLACE INTO results VALUES(?,?,?,?)", (environment_id, exercise.id, json.dumps(result), result["checked_at"]))
            output.append(result)
        return {"results": output}
