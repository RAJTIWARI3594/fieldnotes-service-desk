import tempfile,unittest
from pathlib import Path
import desk
from app import make_app
class DeskTests(unittest.TestCase):
 def setUp(self):self.d=tempfile.TemporaryDirectory();self.path=str(Path(self.d.name)/'d.db');self.c=desk.connection(self.path)
 def tearDown(self):self.c.close();self.d.cleanup()
 def add(self,**kw):return desk.create(self.c,kw.get('title','Printer jam'),kw.get('description','Synthetic issue.'),kw.get('p','normal'))
 def test_create(self):self.assertEqual(self.add()['status'],'open')
 def test_blank(self):
  with self.assertRaises(ValueError):self.add(title=' ')
 def test_priority(self):
  with self.assertRaises(ValueError):self.add(p='critical')
 def test_length(self):
  with self.assertRaises(ValueError):self.add(title='x'*121)
 def test_history(self):self.assertEqual(len(self.add()['history']),1)
 def test_transition(self):t=self.add();self.assertEqual(desk.update(self.c,t['id'],status='triaged')['status'],'triaged')
 def test_skip_blocked(self):
  t=self.add()
  with self.assertRaises(ValueError):desk.update(self.c,t['id'],status='closed')
  self.assertEqual(desk.get(self.c,t['id'])['status'],'open')
 def test_full_flow(self):
  t=self.add()
  for status in ('triaged','in_progress','resolved','closed'):t=desk.update(self.c,t['id'],status=status)
  self.assertEqual(len(t['history']),5)
 def test_reopen(self):
  t=self.add()
  for s in ('triaged','in_progress','resolved','open'):t=desk.update(self.c,t['id'],status=s)
  self.assertEqual(t['status'],'open')
 def test_edit(self):t=self.add();self.assertEqual(desk.update(self.c,t['id'],p='high')['priority'],'high')
 def test_order(self):self.add();self.add(p='urgent');self.assertEqual(desk.listing(self.c)[0]['priority'],'urgent')
 def test_search(self):self.add();self.assertEqual(len(desk.listing(self.c,'printer')),1)
 def test_literal_search(self):self.add();self.assertEqual(desk.listing(self.c,'%'),[])
 def test_sql_injection(self):self.add();self.assertEqual(desk.listing(self.c,"' OR 1=1 --"),[])
 def test_missing(self):
  with self.assertRaises(LookupError):desk.get(self.c,77)
 def test_persistence(self):self.add();c=desk.connection(self.path);self.assertEqual(len(desk.listing(c)),1);c.close()
 def test_status_filter(self):self.add();self.assertEqual(desk.listing(self.c,status='closed'),[])
 def test_markup_plain(self):self.assertEqual(self.add(title='<script>x</script>')['title'],'<script>x</script>')
class APITests(unittest.TestCase):
 def setUp(self):
  self.d=tempfile.TemporaryDirectory();self.app=make_app(str(Path(self.d.name)/'api.db'));self.client=self.app.test_client();self.client.get('/')
  with self.client.session_transaction() as s:self.token=s['csrf']
 def tearDown(self):self.d.cleanup()
 def headers(self):return {'X-CSRF-Token':self.token}
 def test_csrf(self):self.assertEqual(self.client.post('/api/tickets',json={}).status_code,403)
 def test_origin(self):self.assertEqual(self.client.post('/api/tickets',headers={**self.headers(),'Origin':'https://evil.test'},json={}).status_code,403)
 def test_host(self):self.assertEqual(self.client.get('/',headers={'Host':'evil.test'}).status_code,403)
 def test_json_object(self):self.assertEqual(self.client.post('/api/tickets',json=[],headers=self.headers()).status_code,400)
 def test_create_detail(self):
  r=self.client.post('/api/tickets',json={'title':'SYN demo','description':'Invented'},headers=self.headers());self.assertEqual(r.status_code,201);self.assertEqual(self.client.get('/api/tickets/'+str(r.json['id'])).json['title'],'SYN demo')
 def test_unknown_update(self):self.assertEqual(self.client.patch('/api/tickets/1',json={'admin':True},headers=self.headers()).status_code,400)
 def test_missing(self):self.assertEqual(self.client.get('/api/tickets/999').status_code,404)
 def test_csp(self):self.assertIn("frame-ancestors 'none'",self.client.get('/').headers['Content-Security-Policy'])
if __name__=='__main__':unittest.main()
