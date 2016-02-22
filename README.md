# python-wss
Simple python secure websocket server/client with optional authentication built in.

This is just a simple wrapper around autobahn that removes the need to write a bunch of
boiler plate code if you just want a simple and secure server client to send messages 
back and forth.  It has optional diffie-helman-based authentication (what? dh isn't for 
authentication?).

You still need to create your own ssl certs and keys.  You can follow this guide on how to
create a locally signed cert/key combo: 

https://tripzero.io/general/secure-websocket-server-using-autobahn-and-trollius-asyncio/

You can also use letsencrypt.org to create cert/keys.

basic usage:

```python
import wss
import trollius as asyncio

loop = asyncio.get_event_loop()

server =  wss.Server(port=1234, usessl=True, sslcert="path/to/cert.crt", 
                     sslkey="path/to/server.key", auth=None)

def onTextMessage(server, msg, client):
	print("got message from client:", msg)

def onBinaryMessage(server, msg, client):
	print("got binary message")

server.onMessage = onTextMessage
server.onBinaryMessage = onBinaryMessage

@asyncio.coroutine
	def sendData():
		while True:
			try:
				print("trying to broadcast...")
				s.broadcast("{'hello' : 'world' }")
			except:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
				traceback.print_exception(exc_type, exc_value, exc_traceback,
	                          limit=2, file=sys.stdout)

			yield asyncio.From(asyncio.sleep(30))

loop.create_task(sendData())

server.start()
loop.run_forever()
```

