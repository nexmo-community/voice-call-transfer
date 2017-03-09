import os
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket
import nexmo
import requests
import json
import phonenumbers

clients = []

MYNUMBER = os.environ['MY_NUMBER'] #Where you want the callers to be connected to
MYLVN = os.environ['MY_LVN'] # Your Nexmo number, used as the CLI to both parties
CC = os.environ['CC']
if os.getenv('NAME'):
    HOSTNAME = os.getenv('NAME') + '.herokuapp.com' 
else:
    HOSTNAME = os.environ['URL']
APP_ID = os.environ['APP_ID'] # Application ID returned by the nexmo cli when you create the applicaiton
try:
    private_key = os.environ['PRIVATE_KEY']
except:
    with open('private.key', 'r') as f:
        PRIVATE_KEY = f.read()
        
        
def transfer(callid):
    payload = {
        "action": "transfer",
           "destination": {
             "type": "ncco",
             "url": ["http://{}/transfer?dest={}".format(HOSTNAME, MYNUMBER)]
        }
    }
    url = "https://api.nexmo.com/v1/calls/{}".format(callid)
    client = nexmo.Client(application_id=APP_ID, private_key=PRIVATE_KEY, key='dummy', secret='dummy')
    headers =  client._Client__headers()
    headers['Content-Type'] = 'application/json'
    response = requests.put(url, headers=headers, data=json.dumps(payload))
    return response


def broadcast(payload):
	for conn in clients:
		conn.write_message(payload)
    
class MainHandler(tornado.web.RequestHandler):
    def get(self):
        x = phonenumbers.parse(MYLVN, CC)
        formatted_number = phonenumbers.format_number(x, phonenumbers.PhoneNumberFormat.NATIONAL)
        t = tornado.template.Loader(".").load("static/index.html")
        self.set_header("Content-Type", 'text/html')
        self.write(t.generate(
            my_lvn = formatted_number,
            hostname = HOSTNAME,
        ))
        self.finish()
		

class CallHandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	def get(self):
        def get(self):
            t = tornado.template.Loader(".").load("ncco.json")
            dest = self.get_argument("dest", None)
            self.set_header("Content-Type", 'application/json')
            self.write(t.generate(
                hostname = HOSTNAME,
            ))
            self.finish()

class TransferHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        t = tornado.template.Loader(".").load("connect.json")
        dest = self.get_argument("dest", None)
        self.set_header("Content-Type", 'application/json')
        self.write(t.generate(
            dest = dest,
            hostname = HOSTNAME,
        ))
        self.finish()


class EventHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def post(self):
        data = json.loads(self.request.body)
        print data
        if data['status'] == "answered" and data['direction'] =='inbound':
            broadcast(data)
        self.content_type = 'text/plain'
        self.write('ok')
        self.finish()
			

class BrowserWSHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print("Browser Client Connected")
        clients.append(self)
    def on_message(self, message):
        print("Browser Client Message Recieved")
        print message
        data = json.loads(message)
        if data['action'] == 'transfer':
            transfer(data['callid'])
    def on_close(self):
        print("Browser Client Disconnected")
        clients.remove(self)


				
def main():
	static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
	print static_path
	application = tornado.web.Application([(r"/", MainHandler),
											(r"/event", EventHandler),
											(r"/ncco", CallHandler),
											(r"/transfer", TransferHandler),
                                            (r"/socket",BrowserWSHandler),
											(r'/static/(.*)', tornado.web.StaticFileHandler, {'path': static_path}),
											])
	http_server = tornado.httpserver.HTTPServer(application)
	port = int(os.environ.get("PORT", 8000))
	http_server.listen(port)
	tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
	main()
	
	

