from autobahn.asyncio.websocket import WebSocketClientProtocol, WebSocketClientFactory

import asyncio

import json
import ssl
import traceback, sys
import base64

class DebugPrinter:
	def __init__(self, debug = False):
		self.debug = debug

	def print_debug(self, msg):
		if self.debug:
			print(msg)

class ReconnectAsyncio(DebugPrinter):

	def __init__(self, retry = False, loop=None, debug = False):
		DebugPrinter.__init__(self, debug)
		self.address = None
		self.retry = retry
		self.loop = loop

		if not loop:
			self.loop = asyncio.get_event_loop()

	def _connect(self):
		raise Exception("_connect() is an abstract class method.  You must implement this")

	def _do_connect(self):		
		if self.retry:
			self.loop.create_task(self._connect_retry())
		else:
			self.loop.create_task(self._connect_once())
		
	@asyncio.coroutine
	def _connect_once(self):
		try:
			yield from self._connect()

		except ConnectionRefusedError:
			self.print_debug("connection refused ({})".format(self.address))
 
		except OSError:
			self.print_debug("connection failed ({})".format(self.address))
			
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
			traceback.print_exception(exc_type, exc_value, exc_traceback,
					file=sys.stdout)
			self.print_debug("connection failed ({})".format(self.address))

	@asyncio.coroutine
	def _connect_retry(self):
		timeout = 5
		maxtimeout = 60

		while True:
			try:
				self.print_debug("connecting...")
				yield from self._connect()

				self.print_debug("connected!")
				return

			except ConnectionRefusedError:
				self.print_debug("connection refused ({}). retry in {} seconds...".format(self.address, timeout))
				yield from asyncio.sleep(timeout)
				if timeout < maxtimeout:
					timeout += 2

				continue

			except OSError:
				self.print_debug("connection failed ({}). retry in {} seconds...".format(self.address, timeout))
				yield from asyncio.sleep(timeout)

				if timeout < maxtimeout:
					timeout += 2

				continue

			except:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
				traceback.print_exception(exc_type, exc_value, exc_traceback,
						file=sys.stdout)
				self.print_debug("connection failed ({})".format(self.address))

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

		self.print_debug("connectTo: " + self.wsaddress)

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

	def sendTextMsg(self, msg, encoding='utf-8'):
		self.sendMessage(msg.encode(encoding), False)

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
		if self.client:
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
	
	def __init__(self):
		WebSocketClientProtocol.__init__(self)
		self.binaryHandler = None
		self.textHandler = None
		self.onCloseHandler = None
		
	def onConnect(self, response):
		self.factory.client.print_debug("Server connected: {0}".format(response.peer))

	def onOpen(self):
		self.factory.client.print_debug("WebSocket connection open.")

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
		client.sendTextMsg("{'foo' : 'bar'}")

	def closed():
		print("connection closed")


	client.debug = args.debug
	
	client.setTextHandler(textHandler)
	client.setOpenHandler(opened)
	client.setCloseHandler(closed)
	
	client.connectTo(args.address, args.port, useSsl=args.usessl)

	loop.run_forever()

