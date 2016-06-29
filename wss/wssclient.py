from autobahn.asyncio.websocket import WebSocketClientProtocol, WebSocketClientFactory

try:
	import asyncio
except:
	import trollius as asyncio

import json
import ssl
import cv2
import numpy as np
import traceback, sys
import base64
from dh import DH as DiffieHelmut

def debug(msg):
		print(msg)

class Client:

	def __init__(self, retry=False, loop = asyncio.get_event_loop()):
		self.retry = retry
		self.loop = loop
		self.handle = None
		self.debug = False
		self.binaryHandler = None
		self.textHandler = None

	def connectTo(self, addy, port, useSsl = True, auth=False):
		ws = "ws"
		self.address = addy
		self.port = port
		self.useSsl = useSsl
		self.auth=auth
		
		self.sslcontext = None

		if useSsl:
			ws = "wss"
			self.sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)

		self.wsaddress = "{0}://{1}:{2}".format(ws, addy, port)
		debug("connectTo: " + self.wsaddress)

		self.factory = WebSocketClientFactory(self.wsaddress, debug=self.debug, debugCodePaths=self.debug)
		self.factory.client = self
		self.factory.protocol = MyClientProtocol

		MyClientProtocol.onCloseHandler = self.onClose

		self._do_connect()

	def _do_connect(self):
		if self.retry:
			self.loop.create_task(self._connect_retry())
		else:
			self.loop.create_task(self._connect_once())

	def _connect(self):
		return self.loop.create_connection(self.factory, self.address, self.port, ssl=self.sslcontext)
		
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
				print("connection refused. retry in {} seconds...".format(timeout))
				yield asyncio.From(asyncio.sleep(timeout))
				if timeout < maxtimeout:
					timeout += 2

				continue

			except OSError:
				print("connection failed. retry in {} seconds...".format(timeout))
				yield asyncio.From(asyncio.sleep(timeout))

				if timeout < maxtimeout:
					timeout += 2

				continue

			except:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
				traceback.print_exception(exc_type, exc_value, exc_traceback,
						file=sys.stdout)
				print ("connection failed")

	def setBinaryHandler(self, binaryHandlerCallback):
		self.binaryHandler = binaryHandlerCallback

	def setTextHandler(self, textHandlerCallback):
		self.textHandler = textHandlerCallback

	def sendTextMsg(self, msg):
		self.client.sendMessage(msg, False)

	def onClose(self, wasClean, code, reason):
		if self.retry:
			self._do_connect()

	def registerClient(self, clientHndl):
		self.client = clientHndl
		self.client.onCloseHandler = self.onClose
		self.client.binaryHandler = self.binaryHandler
		self.client.textHandler = self.textHandler


class MyClientProtocol(WebSocketClientProtocol):
	binaryHandler = None
	textHandler = None
	onCloseHandler = None
	
	def __init__(self):
		WebSocketClientProtocol.__init__(self)
		
		self.diffieHelmut = DiffieHelmut('dhclient.key')

	def onConnect(self, response):
		print("Server connected: {0}".format(response.peer))

	def onOpen(self):
		print("WebSocket connection open.")

		self.factory.client.registerClient(self)

		if self.factory.client.auth:
			try:
				payload = { "type" : "auth", "sharedSecret" : str(self.diffieHelmut.sharedSecret) }
				payload = json.dumps(payload)
				try:
					self.sendMessage(bytes(payload, 'utf8'), False)
				except:
					#probably on python2
					self.sendMessage(payload, False)
			except:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
				traceback.print_exception(exc_type, exc_value, exc_traceback,
						limit=2, file=sys.stdout)

	def onMessage(self, payload, isBinary):
		if isBinary:
			try:
				self.binaryHandler(payload)
			except KeyboardInterrupt:
				quit()
			except:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
				traceback.print_exception(exc_type, exc_value, exc_traceback,
						limit=2, file=sys.stdout)
		else:
			try:
				if self.textHandler:
					self.textHandler(payload)
			except:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
				traceback.print_exception(exc_type, exc_value, exc_traceback,
						limit=2, file=sys.stdout)

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

	def textHandler(msg):
		print(msg)

	loop = asyncio.get_event_loop()
	client = Client(retry=True, loop=loop)

	client.debug = args.debug
	
	client.connectTo(args.address, args.port, useSsl=args.usessl)
	client.setTextHandler(textHandler)

	loop.run_forever()

	