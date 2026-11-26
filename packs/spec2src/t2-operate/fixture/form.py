#!/usr/bin/env python3
import argparse, html, http.server, json, os, re, secrets, socket, subprocess, sys, time, urllib.parse, webbrowser
from pathlib import Path

ROOT = Path.home()/'.local/share/form'
ROOT.mkdir(parents=True, exist_ok=True)
VERSION='bashy-form-v1'
def fail(s):
    print('error: '+s, file=sys.stderr); sys.exit(1)
def path(id):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',id) or id in ('.','..'): raise ValueError('invalid id')
    return ROOT/(id+'.json')
def load(id):
    try: return json.loads(path(id).read_text())
    except (OSError, ValueError): raise ValueError('form not found: '+id)
def save(f):
    p=path(f['id']); tmp=p.with_suffix('.tmp.'+str(os.getpid())); tmp.write_text(json.dumps(f)); os.replace(tmp,p)
def port():
    try:
        p=int((ROOT/'port').read_text())
        with socket.create_connection(('127.0.0.1',p),timeout=.2): return p
    except (OSError, ValueError): pass
    with socket.socket() as s:
        s.bind(('127.0.0.1',0)); p=s.getsockname()[1]
    subprocess.Popen([sys.executable,os.path.abspath(__file__),'serve','--port',str(p)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    for _ in range(100):
        try:
            with socket.create_connection(('127.0.0.1',p),timeout=.1): return p
        except OSError: time.sleep(.03)
    raise ValueError('could not start server')
def url(f): return 'http://localhost:%s/?id=%s'%(port(),urllib.parse.quote(f['id']))
def output(f,args,mode='show'):
    d={'schema_version':VERSION,'id':f['id'],'status':f['status'],'url':url(f)}
    if mode != 'open':
        d.update(title=f['title'],definition=f['definition'],answers=f.get('answers',{}),respondents=f.get('respondents','one'))
        if f.get('close_at'): d['close_at']=f['close_at']
    if mode=='add':
        d['ownerKey']=f['ownerKey']; d['inviteURL']=d['url']; d['opened']=bool(args.open)
        if args.open: d['openedURL']=d['url']
    if getattr(args, 'open', False):
        try: webbrowser.open(d['url'], new=2)
        except Exception: pass
    if args.fields:
        d={k:d[k] for k in args.fields.split(',') if k in d and k!='schema_version'} | {'schema_version':VERSION}
    print(json.dumps(d,separators=(',',':')) if args.json else json.dumps(d,indent=2))
def scalar(s):
    s=s.strip()
    if s.startswith('[') and s.endswith(']'):
        return [scalar(x) for x in s[1:-1].split(',') if x.strip()]
    if s in ('true','false'): return s=='true'
    if len(s)>1 and s[0]==s[-1] and s[0] in "\"'": return s[1:-1]
    return s
def definition_file(filename):
    data=Path(filename).read_text()
    if not filename.lower().endswith(('.yaml','.yml')): return json.loads(data)
    result={'fields':[]}; current=None
    for line in data.splitlines():
        line=line.strip()
        if not line or line.startswith('#') or line=='fields:': continue
        if line.startswith('- '): current={}; result['fields'].append(current); line=line[2:]
        if ':' in line:
            k,v=line.split(':',1)
            (current if current is not None else result)[k.strip()]=scalar(v)
    return result
def validate(fields):
    if not isinstance(fields,list): raise ValueError('definition must contain fields')
    for f in fields:
        id=f.get('id',''); kind=f.get('kind','')
        if kind=='secret' or re.search(r'password|passwd|secret|credential|api[_-]?key|access[_-]?token|private[_-]?key',id,re.I): raise ValueError('Secret fields are refused here')
        if kind not in ('text','textarea','choice','multi','yes-no','file'): raise ValueError('field "%s": unknown kind "%s"'%(id,kind))
        if not id or not f.get('label'): raise ValueError('field requires id and label')
def answers_update(f, vals, complete):
    a=f.setdefault('answers',{}); a.update(vals)
    if complete:
        missing=[x['label'] for x in f['definition'] if x.get('required') and not a.get(x['id'])]
        if missing: raise ValueError('required fields missing: '+', '.join(missing))
        f['status']='answered'
    save(f)
def render(f, error=''):
    esc=lambda x:html.escape(str(x),quote=True)
    out=['<!doctype html><html><head><meta charset="utf-8"><title>'+esc(f['title'])+'</title></head><body><h1>'+esc(f['title'])+'</h1>']
    if error: out.append('<p role="alert">'+esc(error)+'</p>')
    out.append('<form method="post" action="/?id='+esc(urllib.parse.quote(f['id']))+'">')
    for x in f['definition']:
        id=esc(x['id']); label=esc(x['label']); k=x['kind']; val=f.get('answers',{}).get(x['id'],''); req=' required' if x.get('required') else ''
        out.append('<div><label for="'+id+'">'+label+'</label>')
        if k=='textarea': out.append('<textarea id="'+id+'" name="'+id+'"'+req+'>'+esc(val)+'</textarea>')
        elif k in ('choice','multi','yes-no'):
            out.append('<select id="'+id+'" name="'+id+'"'+(' multiple' if k=='multi' else '')+req+'>')
            if k!='multi': out.append('<option value=""></option>')
            for opt in (['yes','no'] if k=='yes-no' else x.get('options',[])):
                selected=opt in val if isinstance(val,list) else opt==val
                out.append('<option value="'+esc(opt)+'"'+(' selected' if selected else '')+'>'+esc(opt)+'</option>')
            out.append('</select>')
        else: out.append('<input id="'+id+'" name="'+id+'" type="'+('file' if k=='file' else 'text')+'"'+(' value="'+esc(val)+'"' if k!='file' else '')+req+'>')
        if x.get('help'): out.append('<p>'+esc(x['help'])+'</p>')
        out.append('</div>')
    out.append('<button type="submit" name="action" value="save" formnovalidate>Save (partial)</button><button type="submit" name="action" value="submit">Submit answers</button></form></body></html>')
    return ''.join(out).encode()
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def handle_request(self,post=False):
        try:
            q=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query); f=load(q.get('id',[''])[0]); error=''
            if post:
                data=urllib.parse.parse_qs(self.rfile.read(int(self.headers.get('Content-Length',0))).decode(),keep_blank_values=True)
                vals={}
                for x in f['definition']:
                    v=data.get(x['id'],[])
                    if x['kind']=='multi': vals[x['id']]=[i for i in v if i]
                    elif v and v[0]: vals[x['id']]=v[0]
                    else: f.get('answers',{}).pop(x['id'],None)
                try: answers_update(f,vals,data.get('action',[''])[0]=='submit')
                except ValueError as e: error=str(e)
            body=render(f,error); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        except (ValueError,KeyError): self.send_error(404)
    def do_GET(self): self.handle_request()
    def do_POST(self): self.handle_request(True)
def main():
    p=argparse.ArgumentParser(prog='form'); sub=p.add_subparsers(dest='cmd',required=True)
    def common(s): s.add_argument('--json',action='store_true'); s.add_argument('--fields')
    a=sub.add_parser('add'); common(a)
    for flag in ('id','def','definition','title','poll','options','close-at'): a.add_argument('--'+flag)
    a.add_argument('--open',action='store_true'); a.add_argument('--group-required',action='store_true')
    for cmd in ('open','show','answer','wait','set'):
        s=sub.add_parser(cmd); s.add_argument('id'); common(s)
        if cmd=='open': s.add_argument('--open',action='store_true')
        if cmd in ('answer','set'):
            s.add_argument('--answer',action='append',default=[]); s.add_argument('--answers'); s.add_argument('--complete',action='store_true'); s.add_argument('--group-required',action='store_true')
        if cmd=='wait': s.add_argument('--timeout',default='5m'); s.add_argument('--key')
    sub.add_parser('list'); s=sub.add_parser('serve'); s.add_argument('--port',type=int)
    args=p.parse_args()
    if args.cmd=='serve':
        try: chosen=args.port or int((ROOT/'port').read_text())
        except (OSError,ValueError): chosen=0
        try:
            server=http.server.ThreadingHTTPServer(('127.0.0.1',chosen),Handler)
        except OSError:
            if args.port: raise
            # An existing per-user server already serves these forms.
            while True:
                try:
                    with socket.create_connection(('127.0.0.1',chosen),timeout=1): pass
                except OSError: break
                time.sleep(1)
            server=http.server.ThreadingHTTPServer(('127.0.0.1',chosen),Handler)
        (ROOT/'port').write_text(str(server.server_port)); server.serve_forever(); return
    if args.cmd=='list':
        for file in sorted(ROOT.glob('*.json')):
            try:
                f=json.loads(file.read_text()); print(f['id'],f['status'])
            except (ValueError,KeyError): pass
        return
    if args.cmd=='add':
        if args.poll:
            fields=[{'id':'vote','label':args.poll,'kind':'choice','options':(args.options or '').split(','),'required':True}]; title=args.poll
        else:
            obj=definition_file(getattr(args,'def')) if getattr(args,'def') else json.loads(args.definition or '[]')
            fields=obj if isinstance(obj,list) else obj.get('fields',[]); title='' if isinstance(obj,list) else obj.get('title','')
        validate(fields)
        if args.group_required: fields=sorted(fields,key=lambda x:not x.get('required'))
        id=args.id or secrets.token_hex(8)
        if path(id).exists(): raise ValueError('form already exists: '+id)
        f={'id':id,'title':args.title or title,'definition':fields,'answers':{},'status':'pending','ownerKey':secrets.token_urlsafe(24),'respondents':'many' if args.poll else 'one'}
        if args.close_at: f['close_at']=args.close_at
        save(f); output(f,args,'add'); return
    f=load(args.id)
    if args.cmd in ('answer','set'):
        vals={}
        if args.answers: vals=json.loads(sys.stdin.read() if args.answers=='-' else Path(args.answers).read_text())
        for item in args.answer:
            k,v=item.split('=',1); vals[k]=v
        answers_update(f,vals,args.complete)
        if args.cmd=='set':
            f['status']='filled-by-agent'
            if args.group_required: f['definition'].sort(key=lambda x: 0 if x.get('required') and not f['answers'].get(x['id']) else 1)
            save(f)
    if args.cmd=='wait':
        m=re.fullmatch(r'(\d+(?:\.\d+)?)(ms|s|m|h)?',args.timeout)
        if not m: raise ValueError('invalid timeout')
        end=time.monotonic()+float(m[1])*{'ms':.001,'s':1,'m':60,'h':3600,None:1}[m[2]]
        while f['status'] not in ('answered','closed'):
            if time.monotonic()>=end: raise ValueError('timed out waiting for answers')
            time.sleep(.1); f=load(args.id)
    output(f,args,'open' if args.cmd=='open' else 'show')
if __name__=='__main__':
    try: main()
    except (ValueError,OSError,KeyError,json.JSONDecodeError) as e: fail(str(e))
