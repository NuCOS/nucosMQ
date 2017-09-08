.. _basic_usage:

Basic Usage
===========

.. sidebar:: Short

    - There are two types of connection: server-client and link
    - The principle usage is shown in the tests

.. index:: Basic Usage


Server-Client Connection
------------------------

To work with the server-client connection you should import the following

.. code-block:: python

    from nucosMQ import NucosClient
    from nucosMQ import NucosServer

A usual working example would be

.. code-block:: python

    socketIP = "127.0.0.1"
    socketPort = 4000
    client = NucosClient(socketIP, socketPort, uid="testuser", on_challenge=on_challenge)
    server = NucosServer(socketIP, socketPort, do_auth=Auth, single_server=False)
    server.start()
    client.start()

On server side the Auth class is needed in case of authentication. It implements the methods auth_final and challenge, like in the following simplified example
After creating the key, it can be checked by

.. code-block:: python

    class Auth():
        logger = globalLogger
        def auth_final(self, uid, signature, challenge):
            allowed = signature == "1234"
            if not allowed:
                return False
            else:
                return True
        def auth_challenge(self, uid):
            return "1234"


On client side the function on_challenge returns a signature after digestion of an incoming challenge:

.. code-block:: python

    def on_challenge(challenge):
        #do something interesting with the challenge ...
        return "1234"

Both, the server and the client may be started with the function call start(). This call is non-blocking on both sides. That means, the connections runs in the background and thread-safe.

To interact with the connection one may implement on server side and on client side callbacks via

.. code-block:: python

    def alpha(content):
        #do something with content, an unicode
        pass
    #...
    self.server.add_event_callback("test-event alpha", alpha)

where alpha is an arbitrary own function, which is called by the process automatically whenever the event (here “test-event alpha”) comes in and carries a parameter, which is the content of the message.


Messages
--------

A message contains an event, a content and maybe a room. After the connection is established the client can send messages to the server, the first parameter is always the event, the second is the content.

.. code-block:: python

    client.send("test-event", "hello server")

Also the server may send only to one client, but he has to use the publish-method

.. code-block:: python

    server.publish(client_name, "test-event", "hello server")
    
The client_name is the uid if the client is authenticated. It is also the room-name in which the client is automatically put into. How rooms work otherwise, we will see in the next paragraph.


Publish/Subscripe
-----------------

A client may subscripe to a topic, which is also called room via

.. code-block:: python

    client.subscripe("weather")

From now on every message which is published on that topic will reach also that client. As already mentioned every client is put into a room of its own name, the uid automatically after the authentification.

.. code-block:: python

    server.publish("weather", "today", "sunny")
    another_client.publish("weather", "yesterday", "rain")

A server may publish in all rooms, a client only if he is subscriped in that room. A callback may be related to rooms, events and a combination of both:

.. code-block:: python

    client.add_event_callback(event, handler)
    client.add_room_callback(room, handler)
    client.add_room_event_callback(room, event, handler)


The Server-Client-connection is closed by

.. code-block:: python

    server.close()
    client.close()

Since it is a running background process this call may take time to proceed.

Ping
----

To test a connection you may call

.. code-block:: python

    client.ping()

If everything works fine, the server is answering with a pong in a reasonable time.


Link Connection
---------------

A Link is a one-to-one connection. It works without authentification and it is established as follows

.. code-block:: python

    from nucosMQ import NucosLink
    link_1 = NucosLink()
    link_2 = NucosLink()
    #now connect the two of them ...
    link_1.bind("127.0.0.1",4000)
    link_2.connect("127.0.0.1", 4000)

The connection works via send and callbacks in a fully symmetric way.

.. code-block:: python

    link_2.add_event_callback("test-alpha", alpha)
    link_1.send("test-alpha", "hallo")

The Link-connection is closed by

.. code-block:: python

    link_2.close()
    link_1.close()


