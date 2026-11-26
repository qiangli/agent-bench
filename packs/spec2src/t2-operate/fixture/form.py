#!/usr/bin/env python3
import sys, os, json, re, time, uuid, socket, subprocess, signal, html, urllib.parse, argparse, datetime, shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

ROOT=Path.home()/'.form'; ROOT.mkdir(mode=0o700,parents=True,exist_ok=True)
STORE=ROOT/'forms.json'; SERVER=ROOT/'server.json'; VERSION='bashy-form-v1'
def read():
    try: return json.loads(STORE.read_text())
    except FileNotFoundError: return {}
def write(data):
    temp=ROOT/('forms.'+str(os.getpid())+'.tmp'); temp.write_text(json.dumps(data)); os.replace(temp,STORE)
def serverinfo():
    try:
        s=json.loads(SERVER.read_text()); sock=socket.create_connection(('127.0.0.1',s['port']),timeout=.3); sock.close(); return s
    except (OSError,ValueError,KeyError): return None
def ensure():
    s=serverinfo()
    if s: return s
    subprocess.Popen([sys.executable,os.path.abspath(__file__),'serve'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    for _ in range(100):
        time.sleep(.05); s=serverinfo()
        if s: return s
    raise ValueError('could not start server')
def url(id):
    s=serverinfo() or ensure(); return 'http://localhost:%s/?id=%s'%(s['port'],urllib.parse.quote(id))
def open_browser(address):
    command = shutil.which('xdg-open') or shutil.which('open')
    if command:
        try: subprocess.Popen([command,address],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        except OSError: pass

def output(obj,args):
    obj=dict(obj); obj['schema_version']=VERSION
    if args.fields is not None: obj={k:obj[k] for k in ['schema_version']+args.fields.split(',') if k in obj}
    if args.json: print(json.dumps(obj,separators=(',',':')))
    else: print(json.dumps(obj,indent=2))
def scalar(s):
    s=s.strip()
    if s in ('true','false'): return s=='true'
    if s.startswith('[') and s.endswith(']'):
        return [scalar(x) for x in s[1:-1].split(',') if x.strip()]
    if len(s)>=2 and s[0] in "\"'" and s[-1]==s[0]:
        return json.loads(s) if s[0]=='"' else s[1:-1].replace("''", "'")
    return s
def yaml_simple(text):
    obj={}; fields=[]; current=None; in_fields=False
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith('#'): continue
        if line=='fields:': in_fields=True; obj['fields']=fields; continue
        if line.startswith('- '): current={}; fields.append(current); line=line[2:]
        if ':' not in line: continue
        k,v=line.split(':',1)
        (current if in_fields and current is not None else obj)[k.strip()]=scalar(v)
    return obj
def definition(args):
    if args.poll:
        return args.poll,[{'id':'vote','label':args.poll,'kind':'choice','options':args.options.split(',') if args.options else [],'required':True}]
    if args.definition: data=json.loads(args.definition)
    elif args.def_file:
        content=Path(args.def_file).read_text(); data=yaml_simple(content) if args.def_file.lower().endswith(('.yaml','.yml')) else json.loads(content)
    else: raise ValueError('a definition is required')
    return (data.get('title',''),data.get('fields',[])) if isinstance(data,dict) else ('',data)
def validate(fields):
    if not isinstance(fields,list): raise ValueError('fields must be an array')
    for f in fields:
        id=f.get('id',''); kind=f.get('kind','')
        if kind=='secret' or re.search(r'password|passwd|secret|credential|api[_-]?key|access[_-]?token|private[_-]?key',id,re.I): raise ValueError('Secret fields are refused here')
        if kind not in ('text','textarea','choice','multi','yes-no','file'): raise ValueError('field "%s": unknown kind "%s"'%(id,kind))
        if not id or not f.get('label'): raise ValueError('field requires id and label')
def update_answers(form, answers, complete):
    fields={f['id']:f for f in form['definition']}
    for k,v in answers.items():
        if k not in fields: raise ValueError('unknown field: '+k)
        f=fields[k]; kind=f['kind']
        if kind=='multi' and isinstance(v,str): v=[x for x in v.split(',') if x]
        if kind in ('choice','multi'):
            for x in (v if isinstance(v,list) else [v]):
                if x and x not in f.get('options',[]): raise ValueError('value is not one of its options')
        if kind=='yes-no' and v not in ('yes','no','',True,False): raise ValueError('expected yes or no')
        form['answers'][k]=v
    if complete:
        for f in fields.values():
            if f.get('required') and form['answers'].get(f['id']) in (None,'',[]): raise ValueError('required field missing: '+f['id'])
        form['status']='answered'
def page(form):
    e=lambda x:html.escape(str(x),quote=True)
    parts=['<!doctype html><html><head><meta charset="utf-8"><title>'+e(form['title'])+'</title></head><body><h1>'+e(form['title'])+'</h1><form method="post" enctype="multipart/form-data">']
    answers=form.get('answers',{})
    for f in form['definition']:
        id=e(f['id']); label=e(f['label']); kind=f['kind']; val=answers.get(f['id'],''); req=' required' if f.get('required') else ''
        parts.append('<div><label for="'+id+'">'+label+'</label> ')
        if kind=='textarea': parts.append('<textarea id="'+id+'" name="'+id+'"'+req+'>'+e(val)+'</textarea>')
        elif kind in ('choice','multi','yes-no'):
            parts.append('<select id="'+id+'" name="'+id+'"'+(' multiple' if kind=='multi' else '')+req+'>')
            if kind!='multi': parts.append('<option value="">Choose…</option>')
            for opt in (['yes','no'] if kind=='yes-no' else f.get('options',[])):
                selected=opt in val if isinstance(val,list) else opt==val
                parts.append('<option value="'+e(opt)+'"'+(' selected' if selected else '')+'>'+e(opt)+'</option>')
            parts.append('</select>')
        else: parts.append('<input id="'+id+'" name="'+id+'" type="'+('file' if kind=='file' else 'text')+'"'+(' value="'+e(val)+'"' if kind!='file' else '')+req+'>')
        if f.get('help'): parts.append('<p>'+e(f['help'])+'</p>')
        parts.append('</div>')
    parts.append('<button type="submit" name="action" value="partial" formnovalidate>Save (partial)</button><button type="submit" name="action" value="complete">Submit answers</button></form></body></html>')
    return ''.join(parts).encode()
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        id=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('id',[''])[0]; form=read().get(id)
        if not form: self.send_error(404); return
        data=page(form); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        import email.parser, email.policy
        id=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('id',[''])[0]; data=read(); form=data.get(id)
        if not form: self.send_error(404); return
        body=self.rfile.read(int(self.headers.get('Content-Length','0'))); ct=self.headers.get('Content-Type',''); values={}
        if ct.startswith('multipart/form-data'):
            msg=email.parser.BytesParser(policy=email.policy.default).parsebytes(('Content-Type: '+ct+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+body)
            for part in msg.iter_parts():
                name=part.get_param('name',header='content-disposition'); filename=part.get_filename(); v=filename if filename is not None else part.get_content()
                if name and v: values.setdefault(name,[]).append(v)
        else: values=urllib.parse.parse_qs(body.decode(),keep_blank_values=True)
        answers={}
        for f in form['definition']:
            k=f['id']; v=values.get(k,[])
            if f['kind']=='multi':
                if v: answers[k]=v
                else: form['answers'].pop(k,None)
            elif v and v[0]!='': answers[k]=v[0]
            elif f['kind']!='file': form['answers'].pop(k,None)
        try: update_answers(form,answers,values.get('action',[''])[0]=='complete'); write(data)
        except ValueError as ex: self.send_error(400,str(ex)); return
        self.send_response(303); self.send_header('Location','/?id='+urllib.parse.quote(id)); self.end_headers()
def serve():
    server=HTTPServer(('127.0.0.1',0),Handler); SERVER.write_text(json.dumps({'pid':os.getpid(),'port':server.server_port}))
    try: server.serve_forever()
    finally:
        try:
            if json.loads(SERVER.read_text())['pid']==os.getpid(): SERVER.unlink()
        except (OSError,ValueError,KeyError): pass
def parser():
    p=argparse.ArgumentParser(prog='form'); sub=p.add_subparsers(dest='cmd',required=True)
    for cmd in ('add','open','show','answer','wait','set','list','serve','stop'):
        q=sub.add_parser(cmd)
        if cmd in ('open','show','answer','wait','set'): q.add_argument('id')
        if cmd=='add':
            for flag in ('id','title','definition','poll','options','close-at'): q.add_argument('--'+flag)
            q.add_argument('--def',dest='def_file'); q.add_argument('--open',action='store_true'); q.add_argument('--group-required',action='store_true')
        if cmd in ('answer','set'):
            q.add_argument('--answer',action='append',default=[]); q.add_argument('--answers'); q.add_argument('--complete',action='store_true'); q.add_argument('--group-required',action='store_true')
        if cmd=='open': q.add_argument('--open',action='store_true')
        if cmd=='wait': q.add_argument('--timeout',default='5m'); q.add_argument('--key')
        if cmd not in ('serve','stop'):
            q.add_argument('--json',action='store_true'); q.add_argument('--fields')
    return p
def main():
    args=parser().parse_args(); cmd=args.cmd
    if cmd=='serve': serve(); return
    if cmd=='stop':
        s=serverinfo()
        if s:
            try: os.kill(s['pid'],signal.SIGTERM)
            except ProcessLookupError: pass
            for _ in range(100):
                if not serverinfo(): break
                time.sleep(.02)
        try: SERVER.unlink()
        except FileNotFoundError: pass
        return
    data=read()
    if cmd=='add':
        title,fields=definition(args); validate(fields); id=args.id or uuid.uuid4().hex
        if id in data: raise ValueError('form already exists')
        if args.close_at: datetime.datetime.fromisoformat(args.close_at.replace('Z','+00:00'))
        if args.group_required: fields=sorted(fields,key=lambda f:not f.get('required',False))
        form={'id':id,'title':args.title or title,'definition':fields,'answers':{},'status':'pending'}
        if args.poll: form['respondents']='many'
        if args.close_at: form['close_at']=args.close_at
        key=uuid.uuid4().hex; data[id]=form; write(data); u=url(id)
        out={**form,'url':u,'inviteURL':u,'ownerKey':key}
        if args.open:
            open_browser(u); out.update(opened=True,openedURL=u)
        output(out,args); return
    if cmd=='list':
        if args.json: output({'forms':list(data.values())},args)
        else:
            for f in data.values(): print(f['id'],f['status'],f['title'])
        return
    if args.id not in data: raise ValueError('form not found: '+args.id)
    form=data[args.id]
    if cmd in ('answer','set'):
        answers={}
        if args.answers: answers=json.load(sys.stdin if args.answers=='-' else open(args.answers))
        for item in args.answer:
            if '=' not in item: raise ValueError('answer must be field=value')
            k,v=item.split('=',1); answers[k]=v
        update_answers(form,answers,args.complete)
        if cmd=='set': form['status']='filled-by-agent'
        if args.group_required: form['definition'].sort(key=lambda f: 0 if f.get('required') and not form['answers'].get(f['id']) else (1 if f.get('required') else 2))
        write(data)
    if cmd=='wait':
        m=re.fullmatch(r'(\d+(?:\.\d+)?)(ms|s|m|h)?',args.timeout)
        if not m: raise ValueError('invalid timeout')
        seconds=float(m[1])*{'ms':.001,'s':1,'m':60,'h':3600,None:1}[m[2]]; end=time.monotonic()+seconds
        while form['status'] not in ('answered','closed') and time.monotonic()<end:
            time.sleep(min(.1,max(0,end-time.monotonic()))); form=read()[args.id]
        if form['status'] not in ('answered','closed'): raise ValueError('timeout waiting for answers')
    u=url(args.id)
    out={'id':args.id,'status':form['status'],'url':u} if cmd=='open' else {**form,'url':u}
    if cmd=='open' and args.open:
        open_browser(u); out.update(opened=True,openedURL=u)
    output(out,args)
if __name__=='__main__':
    try: main()
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError) as e: print('error: '+str(e),file=sys.stderr); sys.exit(1)
