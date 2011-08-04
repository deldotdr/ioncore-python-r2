"""
"""

from pika import BasicProperties

from gevent import queue as gqueue
from gevent import event

class BaseChannel(object):
    """
    TODO: for synchronous method callbacks, the frame abstraction should
    not show up in this class. The layer below needs to unpack the frames
    and call these methods with a specified signature. 
    """

    amq_chan = None
    endpoint_name = None # (exchange, routing_key)

    # AMQP options
    exchange_type = 'direct'
    exchange_auto_delete = False
    exchange_durable = False
    queue_auto_delete = True
    queue_durable = False

    consumer_no_ack = True
    consumer_exclusive = True
    prefetch_size = 1
    prefetch_count = 1

    immediate = False # don't use
    mandatory = False # don't use

    queue = None
    exchange = None

    def __init__(self):
        """
        """
        self._channel_bind_cb = None

        self._consuming = 0

    def on_channel_open(self, amq_chan):
        """
        """
        print 'channel open'
        amq_chan.add_on_close_callback(self.on_channel_close)
        self.amq_chan = amq_chan
        self.do_config() # doesn't jive with blocking interface

    def on_channel_close(self, *a):
        """
        """
        print 'channel close'

    def do_config(self):
        """
        configure amqp
        implement in subclass 

        XXX only use existing exchange now
        """

    def do_queue(self, callback=None):
        if callback:
            self._channel_bind_cb = callback
        self.amq_chan.queue_declare(callback=self._on_queue_declare_ok,
                                    queue=self.queue,
                                    auto_delete=self.queue_auto_delete,
                                    durable=self.queue_durable)

    def _on_queue_declare_ok(self, frame):
        """
        reply contains queue name, number of messages and number of
        consumers

        when binding unique queues, get the name from here.
        """
        self.queue = frame.method.queue #XXX who really defines queue!!
        print 'queue ', self.queue
        self.amq_chan.queue_bind(callback=self._on_queue_bind_ok,
                                queue=self.queue,
                                exchange=self.endpoint_name[0],
                                routing_key=self.endpoint_name[1])

    def _on_queue_bind_ok(self, frame):
        """
        or queue_bind can be called with no wait, and we handle a channel
        exception in the case of an error

        nowait with consumer raises channel exception on error
        """
        if self._channel_bind_cb:
            self._channel_bind_cb()
        else:
            self._start_consumer()

    def _start_consumer(self):
        if self._consuming:
            raise #?
        self.amq_chan.basic_consume(self._on_basic_deliver,
                                    queue=self.queue,
                                    no_ack=self.consumer_no_ack,
                                    exclusive=self.consumer_exclusive)
        self._consuming = True # XXX ?

    def _on_exchange_declare_ok(self, frame):
        """
        """

    def _on_basic_deliver(self, chan, method_frame, header_frame, body):
        """
        delivery comes with the channel context, so this can easily be
        intercepted before it gets here
        """
        self.message_received(body)

    def message_received(self, body):
        """
        implement
        """
        print 'message received'
        print body

    def send(self, data):
        """
        use when 'connected' to an endpoint (sending end of a channel)
        """
        self._send(self.endpoint_name, data)

    def sendto(self, name, data):
        """
        """

    def _send(self, name, data, headers={},
                                content_type=None,
                                content_encoding=None,
                                message_type=None,
                                reply_to=None,
                                correlation_id=None,
                                message_id=None):
        """
        TODO: redo without intermediate props dict
        how expensive is constructing the BasicProperties for each send?
        """
        exchange, routing_key = name
        props = BasicProperties(headers=headers,
                            content_type=content_type,
                            content_encoding=content_encoding,
                            type=message_type,
                            reply_to=reply_to,
                            correlation_id=correlation_id,
                            message_id=message_id)
        # data is assumed to be properly encoded 
        print 'sending'
        print exchange, routing_key
        self.amq_chan.basic_publish(exchange=exchange, #todo  
                                routing_key=routing_key, #todo 
                                body=data,
                                properties=props,
                                immediate=False, #todo 
                                mandatory=False) #todo

class PointToPointClient(BaseChannel):
    """
    """

class PointToPointServer(BaseChannel):
    """
    """

    def do_config(self):
        self.queue = self.endpoint_name[1]
        self.do_queue()


class PubSubChannel(BaseChannel):
    """
    Endpoints do not directly interact.

    use a topic amqp exchange
    """


class SocketInterface(object):
    """
    Adapts an amqp channel.
    Adds a blocking layer using gevent Async Events to achieve a socket/0mq like behavior.
    """

    def __init__(self, amq_chan, ch_type):
        #amq_chan.add_on_close_callback(self.on_channel_close)
        self.amq_chan = amq_chan
        ch_proto = ch_type()
        ch_proto.message_received = self.message_received
        ch_proto.on_channel_open(amq_chan)
        self.ch_proto = ch_proto

        self.exchange = None
        self.routing_key = None
        self.queue = None

        self._bound = 0
        self._receive_queue = gqueue.Queue()

        self._connected = 0

    def on_channel_close(self, *a):
        print 'channel close'

    def message_received(self, msg):
        self._receive_queue.put(msg)

    def accept(self):
        """
        """

    def bind(self, name):
        """
        """
        if self._bound:
            raise #?
        self._bound = 1
        self._bind_name = name
        self.ch_proto.endpoint_name = name
        self.ch_proto.queue = name[1]

        # not sure if we need this here?
        self.exchange = name[0]
        self.routing_key = name[1]
        self.queue = name[1] # XXX for prototype, assume p2p

        result = event.AsyncResult()
        def channel_bound_ok():
            result.set()

        self.ch_proto.do_queue(channel_bound_ok) # XXX 
        result.wait()
        return


    def close(self):
        """
        """

    def connect(self, name):
        """
        """
        self._connect_name = name
        self.ch_proto.endpoint_name = name
        self.ch_proto.queue = name[1]
        self._connected = 1 #?


    def listen(self, n):
        """
        """
        if self._bound:
            self.ch_proto._start_consumer()
        else:
            raise #?

    def recv(self, *args):
        """
        """
        return self._receive_queue.get()

    def recv_into(self, callback):
        """
        """

    def send(self, data):
        """
        """
        self.ch_proto.send(data)

    def sendto(self, data, name):
        """
        """

