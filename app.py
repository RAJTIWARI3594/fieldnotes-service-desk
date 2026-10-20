from flask import Flask,request,jsonify,render_template,session
from pathlib import Path
import secrets,hmac,sqlite3
import desk
from contextlib import closing

def make_app(database=None):
 app=Flask(__name__);app.secret_key=secrets.token_bytes(32);app.config.update(MAX_CONTENT_LENGTH=16384,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict')
 if database is None:
  Path(app.instance_path).mkdir(exist_ok=True);database=str(Path(app.instance_path)/'desk.db')
 app.config['DATABASE']=database
 with closing(desk.connection(database)):pass
 @app.before_request
 def guard():
  if request.host not in ('127.0.0.1:8082','localhost:8082','127.0.0.1','localhost'):return jsonify(error='Local access only'),403
  if request.method in ('POST','PATCH','DELETE'):
   origin=request.headers.get('Origin');expected=request.host_url.rstrip('/')
   if origin and origin!=expected:return jsonify(error='Origin refused'),403
   expected_token=session.get('csrf','');actual=request.headers.get('X-CSRF-Token','')
   if not expected_token or not hmac.compare_digest(expected_token,actual):return jsonify(error='Refresh the page before editing'),403
   if not request.is_json:return jsonify(error='JSON required'),415
 @app.after_request
 def headers(response):
  response.headers.update({'X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; style-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'",'Cache-Control':'no-store'})
  return response
 @app.errorhandler(ValueError)
 def bad(e):return jsonify(error=str(e)),400
 @app.errorhandler(LookupError)
 def missing(e):return jsonify(error=str(e)),404
 @app.errorhandler(sqlite3.Error)
 def db_error(e):return jsonify(error='Database operation failed'),409
 @app.get('/')
 def index():
  session.setdefault('csrf',secrets.token_hex(32));return render_template('index.html',csrf=session['csrf'])
 @app.get('/api/tickets')
 def tickets():
  with closing(desk.connection(database)) as c:return jsonify(tickets=desk.listing(c,request.args.get('q',''),request.args.get('status','all')))
 @app.get('/api/tickets/<int:i>')
 def detail(i):
  with closing(desk.connection(database)) as c:return jsonify(desk.get(c,i))
 @app.post('/api/tickets')
 def add():
  x=request.get_json();
  if not isinstance(x,dict):raise ValueError('JSON object required')
  with closing(desk.connection(database)) as c:return jsonify(desk.create(c,x.get('title'),x.get('description'),x.get('priority','normal'))),201
 @app.patch('/api/tickets/<int:i>')
 def edit(i):
  x=request.get_json()
  if not isinstance(x,dict) or not x or set(x)-{'title','description','priority','status'}:raise ValueError('Unknown or empty update')
  with closing(desk.connection(database)) as c:return jsonify(desk.update(c,i,title=x.get('title'),description=x.get('description'),p=x.get('priority'),status=x.get('status')))
 return app
if __name__=='__main__':make_app().run(host='127.0.0.1',port=8082,debug=False)
