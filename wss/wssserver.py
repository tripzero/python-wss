from autobahn.asyncio.websocket import WebSocketServerProtocol, WebSocketServerFactory
import ssl

import trollius as asyncio
from .dh import DH
import sys, traceback
from binascii import hexlify
import json

class Client:
	def __init__(self, handle):
		self.handle = handle
		self.closeHandler = None

	def close(self):
		if self.closeHandler:
			self.closeHandler()

	def sendMessage(self, msg, isBinary):
		self.handle.sendMessage(msg, isBinary)

	def setCloseHandler(self, callback):
		self.closeHandler = callback

class Server:

	def __init__(self, port = 9000, usessl = True, sslcert = "server.crt", sslkey= "server.key", auth=None, privateKeyFile = 'dhserver.key', clientsFile = "clients.json"):
		self.clients = []
		self.knownClients = {}
		self.broadcastRate = 10
		self.broadcastMsg = None
		self.throttle = False
		self.encodeMsg = False
		self.debug = False
		self.port = port
		self.sslcert = sslcert
		self.sslkey = sslkey
		self.ssl = usessl
		self.auth = auth

		if self.auth:
			self.diffieHelmut = DH(privateKeyFile)

			try:
				with open(clientsFile) as cf:
					data = cf.read()
					data = json.loads(data)
					if data.__class__ == dict:
						self.knownClients = data
			except:
				print("exception while parsing {0}".format(clientsFile))
				exc_type, exc_value, exc_traceback = sys.exc_info()
				traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
				traceback.print_exception(exc_type, exc_value, exc_traceback,
	                          limit=6, file=sys.stdout)

			self.secret = self.diffieHelmut.secret

	def registerClient(self, client):
		self.clients.append(Client(client))

	def hasClients(self):
		return len(self.clients)

	def client(self, client_handle):
		for c in self.clients:
			if c.handle == client_handle:
				return c

	def broadcast(self, msg):
		try:
			if self.throttle:
				self.broadcastMsg = msg
			else:
				if self.encodeMsg:
					msg = base64.b64encode(self.msg)
				for c in self.clients:
					c.sendMessage(msg, False)
		except:
			print("exception while broadcast()")
			exc_type, exc_value, exc_traceback = sys.exc_info()
			traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
			traceback.print_exception(exc_type, exc_value, exc_traceback,
                          limit=2, file=sys.stdout)


	def unregisterClient(self, client):
		for c in self.clients:
			if c.handle == client:
				c.close()
				self.clients.remove(c)
				return True

	def authenticate(self, client, sharedSecret):
		#TODO: do real authentication
		if not self.auth:
			return

		try:
			for c in self.clients:
				if c.handle == client:
					symmetricKey = self.diffieHelmut.hashedSymmetricKey(sharedSecret)
					symmetricKey = hexlify(symmetricKey)
					
					print("knownClient: {}".format(self.knownClients))
					if str(sharedSecret) in self.knownClients:
						if symmetricKey == self.knownClients[str(sharedSecret)]:
							c.isAuthenticated = True
							print("authentication success!")
						else:
							print("failed attempt to authenticate.  symmetric Key is wrong")
							print("symmetricKey: ", symmetricKey)
					else:
						print("failed attempt at authenticating.  shared secret is not in clients file")
						print("\"{0}\" : \"{1}\",".format(sharedSecret, symmetricKey))
						c.handle.sendClose()
						self.clients.remove(c)
		except:
			print("exception in authenticate()")
			exc_type, exc_value, exc_traceback = sys.exc_info()
			traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
			traceback.print_exception(exc_type, exc_value, exc_traceback,
                          limit=2, file=sys.stdout)

	def onBinaryMessage(self, msg, fromClient):
		pass

	def onMessage(self, msg, fromClient):
		"override this in subclass"
		pass

	def start(self):
		print("start() called... debug = ", self.debug)
		ws = "ws"

		sslcontext = None
		if self.ssl:
			print("using ssl")
			try:
				sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
				sslcontext.load_cert_chain(self.sslcert, self.sslkey)
			except:
				sslcontext = None
				print("failed to use ssl")

			ws = "wss"	

		ResourceProtocol.server = self

		factory = WebSocketServerFactory(u"{0}://127.0.0.1:{1}".format(ws, self.port))
		factory.protocol = ResourceProtocol

		loop = asyncio.get_event_loop()

		coro = loop.create_server(factory, '', self.port, ssl=sslcontext)
		self.server = loop.run_until_complete(coro)

		print("server should be started now")

	def startTwisted(self):
		from twisted.python import log
		log.startLogging(open("wssserver.log", "w"))

		print("startTwisted() started")
		ws = "ws"

		ResourceProtocol.server = self

		sslcontext = None
		if self.ssl:
			print("using wss... and ssl")
			sslcontext = ssl.DefaultOpenSSLContextFactory(self.sslkey, self.sslcert)
			ws = "wss"

		factory = WebSocketServerFactory(u"{0}://127.0.0.1:9001".format(ws))
		factory.protocol = ResourceProtocol

		listenWS(factory, sslcontext)

		reactor.run()

class ResourceProtocol(WebSocketServerProtocol):
	server = None

	def onConnect(self, request):
		print("Client connecting: {0}".format(request.peer))

	def onOpen(self):
		print("WebSocket connection open.")
		ResourceProtocol.server.registerClient(self)
		
		if not ResourceProtocol.server.auth:
			return

		# send our shared secret:
		print("sending auth to client")
		payload = { "type" : "auth", "sharedSecret" : str(ResourceProtocol.server.diffieHelmut.sharedSecret) }
		payload = json.dumps(payload)
		self.sendMessage(payload, False)

	def onMessage(self, payload, isBinary):
		if isBinary:
			print("Binary message received: {0} bytes".format(len(payload)))
			ResourceProtocol.server.onBinaryMessage(payload, ResourceProtocol.server.client(self))
		
		else:

			if ResourceProtocol.server.auth and 'sharedSecret' in msg and 'type' in msg and msg['type'] == 'auth':
				msg = json.loads(payload.decode('utf8'))
				# {'type' : 'auth', 'sharedSecret' : 'key'}
				ResourceProtocol.server.authenticate(self, int(msg['sharedSecret']))
			else:
				ResourceProtocol.server.onMessage(payload, ResourceProtocol.server.client(self))

	def onClose(self, wasClean, code, reason):
		try:
			print("WebSocket connection closed: {0}".format(reason))
			ResourceProtocol.server.unregisterClient(self)
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
			traceback.print_exception(exc_type, exc_value, exc_traceback,
                          limit=2, file=sys.stdout)


def server_main(ServerClass = Server):
	print("starting...")
	import argparse

	parser = argparse.ArgumentParser()
	parser.add_argument('--ssl', dest="usessl", help="use ssl.", action='store_true')
	parser.add_argument('--debug', dest="debug", help="turn on debugging.", action='store_true')
	parser.add_argument('--sslcert', dest="sslcert", default="server.crt", nargs=1, help="ssl certificate")
	parser.add_argument('--sslkey', dest="sslkey", default="server.key", nargs=1, help="ssl key")
	parser.add_argument('--port', help="port of server", default=9000)

	args = parser.parse_args()

	loop = asyncio.get_event_loop()

	s = ServerClass(usessl=args.usessl, port=args.port)
	s.debug = args.debug

	s.start()
	
	return s


if __name__ == "__main__":
	
	loop = asyncio.get_event_loop()

	s = server_main()

	@asyncio.coroutine
	def sendData():
		while True:
			try:
				print("trying to broadcast to {} clients...".format(len(s.clients)))
				s.broadcast("{'hello' : 'world' }")
			except:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
				traceback.print_exception(exc_type, exc_value, exc_traceback,
	                          limit=2, file=sys.stdout)

			yield asyncio.From(asyncio.sleep(30))

	loop.create_task(sendData())

	loop.run_forever()


