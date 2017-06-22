from autobahn.asyncio.websocket import WebSocketClientProtocol, WebSocketClientFactory

import trollius as asyncio

import json
import ssl
import traceback, sys
import base64

def debug(msg):
		print(msg)

class ReconnectAsyncio:

	def __init__(self, retry = False, loop=None):
		self.retry = retry
		self.loop = loop
		if not loop:
			self.loop = asyncio.get_event_loop()

	def _connect(self):
		raise Exception("_connect() is an abstract class method.  You must implement this")

	def _do_connect(self):
		debug("_do_connect()...")
		if self.retry:
			self.loop.create_task(self._connect_retry())
		else:
			self.loop.create_task(self._connect_once())
		
	@asyncio.coroutine
	def _connect_once(self):
		try:
			yield asyncio.From(self._connect())

		except asyncio.py33_exceptions.ConnectionRefusedError:
			print("connection refused")
 
		except OSError:
			print("connection failed")
			
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
			traceback.print_exception(exc_type, exc_value, exc_traceback,
					file=sys.stdout)
			print ("connection failed")

	@asyncio.coroutine
	def _connect_retry(self):
		timeout = 5
		maxtimeout = 60

		while True:
			try:
				debug("connecting...")
				yield asyncio.From(self._connect())

				debug("connected!")
				return

			except asyncio.py33_exceptions.ConnectionRefusedError:
				debug("connection refused. retry in {} seconds...".format(timeout))
				yield asyncio.From(asyncio.sleep(timeout))
				if timeout < maxtimeout:
					timeout += 2

				continue

			except OSError:
				debug("connection failed. retry in {} seconds...".format(timeout))
				yield asyncio.From(asyncio.sleep(timeout))

				if timeout < maxtimeout:
					timeout += 2

				continue

			except:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
				traceback.print_exception(exc_type, exc_value, exc_traceback,
						file=sys.stdout)
				debug ("connection failed")

class Client(ReconnectAsyncio):

	def __init__(self, retry=False, loop = None):
		ReconnectAsyncio.__init__(self, retry=retry)

		if not loop:
			loop = asyncio.get_event_loop()

		self.retry = retry
		self.loop = loop
		self.handle = None
		self.debug = False
		self.binaryHandler = None
		self.textHandler = None
		self.openHandler = None
		self.closeHandler = None
		self.client = None

	def connectTo(self, addy, port, useSsl = True, url=None, protocols=None):
		ws = "ws"
		self.address = addy
		self.port = port
		self.useSsl = useSsl
		
		self.sslcontext = None

		if useSsl:
			ws = "wss"
			self.sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)

		if url:
			self.wsaddress = url
		else:
			self.wsaddress = "{0}://{1}:{2}".format(ws, addy, port)

		debug("connectTo: " + self.wsaddress)

		self.factory = WebSocketClientFactory(self.wsaddress, protocols=protocols)
		self.factory.client = self
		self.factory.protocol = MyClientProtocol

		MyClientProtocol.onCloseHandler = self.onClose

		self._do_connect()

	def _connect(self):
		return self.loop.create_connection(self.factory, self.address, self.port, ssl=self.sslcontext)

	def setBinaryHandler(self, binaryHandlerCallback):
		self.binaryHandler = binaryHandlerCallback

	def setTextHandler(self, textHandlerCallback):
		self.textHandler = textHandlerCallback

	def setOpenHandler(self, openHandlerCallback):
		self.openHandler = openHandlerCallback

	def setCloseHandler(self, closeHandlerCallback):
		self.closeHandler = closeHandlerCallback

	def sendTextMsg(self, msg):
		self.sendMessage(msg, False)

	def sendBinaryMsg(self, msg):
		self.sendMessage(msg, True)

	def sendMessage(self, msg, isBinary=False):
		if not self.client:
			return
		self.client.sendMessage(msg, isBinary)

	def onClose(self, wasClean, code, reason):
		if self.retry:
			self._do_connect()

	def close(self, code=WebSocketClientProtocol.CLOSE_STATUS_CODE_NORMAL):
		self.client.sendClose(code=code)

	def registerClient(self, clientHndl):
		self.client = clientHndl
		self.client.onCloseHandler = self.onClose
		self.client.binaryHandler = self.binaryHandler
		self.client.textHandler = self.textHandler

		try:
			if self.openHandler:
				self.openHandler()
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
			traceback.print_exception(exc_type, exc_value, exc_traceback,
			      limit=6, file=sys.stdout)


class MyClientProtocol(WebSocketClientProtocol):
	binaryHandler = None
	textHandler = None
	onCloseHandler = None
	
	def __init__(self):
		WebSocketClientProtocol.__init__(self)
		
	def onConnect(self, response):
		print("Server connected: {0}".format(response.peer))

	def onOpen(self):
		print("WebSocket connection open.")

		self.factory.client.registerClient(self)

	def onMessage(self, payload, isBinary):
		if isBinary:
			try:
				self.binaryHandler(payload)
			except KeyboardInterrupt:
				raise KeyboardInterrupt()

			except:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
				traceback.print_exception(exc_type, exc_value, exc_traceback,
						limit=6, file=sys.stdout)
		else:
			try:
				if self.textHandler:
					self.textHandler(payload)
			except KeyboardInterrupt:
				raise KeyboardInterrupt()
			except:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
				traceback.print_exception(exc_type, exc_value, exc_traceback,
						limit=6, file=sys.stdout)

	def onClose(self, wasClean, code, reason):
		if self.onCloseHandler:
			self.onCloseHandler(wasClean, code, reason)


if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('--ssl', dest="usessl", help="use ssl.", action='store_true')
	parser.add_argument('--debug', dest="debug", help="turn on debugging.", action='store_true')
	parser.add_argument('address', help="address", default="localhost", nargs="?")
	parser.add_argument('port', help="port", default=9000, nargs="?")
	args = parser.parse_args()

	loop = asyncio.get_event_loop()
	client = Client(retry=True, loop=loop)

	def textHandler(msg):
		print(msg)

	def opened():
		print("connected")
		client.sendMessage("{'foo' : 'bar'}")

	def closed():
		print("connection closed")


	client.debug = args.debug
	
	client.setTextHandler(textHandler)
	client.setOpenHandler(opened)
	client.setCloseHandler(closed)
	
	client.connectTo(args.address, args.port, useSsl=args.usessl)

	loop.run_forever()

	