from wss import Server
from wss import Client
import asyncio


def test_server_client():
    loop = asyncio.get_event_loop()

    s = Server(port = 9000, debug = True, useSsl=False)

    to_send = "hello world"
    to_reply = "foo bar"

    received = False
    server_received = False
  
    @asyncio.coroutine
    def sendData():
        while True:
            try:
                print("trying to broadcast to {} clients...".format(len(s.clients)))
                s.broadcast(to_send, False)
                sent = True
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
                traceback.print_exception(exc_type, exc_value, exc_traceback,
                              limit=2, file=sys.stdout)

            yield from asyncio.sleep(0.1)

    loop.create_task(sendData())

    def onMessage(msg, client):
        print("received message: {}".format(msg))
        assert msg == bytes(to_reply, 'utf-8')
        server_received = True

    s.setTextHandler(onMessage)

    s.start()

    client = Client(retry=True, loop=loop)

    def textHandler(msg):
        print(msg)
        assert msg.decode('utf-8') == to_send
        received = True

    def opened():
        print("client connected")
        print(client.connected)
        client.sendTextMsg(to_reply)

    def closed():
        print("connection closed")


    client.debug = True
    
    client.setTextHandler(textHandler)
    client.setOpenHandler(opened)
    client.setCloseHandler(closed)
    
    client.connectTo("localhost", 9000, useSsl=False)

    def stop_loop():
        loop.stop()

    loop.call_later(5, stop_loop)
    loop.run_forever()

    assert client.connected
    assert sent
    assert received
    assert server_received


if __name__ == "__main__":
    test_server_client()
