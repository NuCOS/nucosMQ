.. nucosMQ documentation master file, created by
   sphinx-quickstart on Wed Oct 19 11:56:02 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to nucosMQ's documentation!
===================================

nucosMQ is a python messaging module (in the sense of zeroMQ) written in pure Python. We are aware of other projects like snakeMQ but we were not able to produce reasonable results with that, since we depend in our related projects on massive threading.

The underlying protocoll is tcp and as an alternative udp yet not very far implemented. The Communication is thread safe, so it may be used together with whatever GUI-Library. The module is light-weighted, pure python and ready to use.

The project is in alpha stage: every usage is on your own responsibility.

nucosMQ implements two kind of connections: server-client connection and link-connection. The server accepts many clients, the link is a one-to-one connection. The connections may be established also with your individual authentification method, which can be integrated easily (see examples).

A publish/subscribe logic is implemented, where clients can subscribe to a topic and the server acts as a broker for that topology.

.. toctree::
   :maxdepth: 2

   Install
   Basic_Usage

Links
=====

* :ref:`genindex`
* :ref:`search`

