from engine.dsl import classname, MuranoObject
import eventlet
from . import create_rmq_client

@classname('com.mirantis.murano.system.AgentListener')
class AgentListener(MuranoObject):
    def initialize(self, _context, name):
        self._results_queue = '-execution-results-%s' % name.lower()
        self._subscriptions = {}
        self._receive_thread = None

    def start(self):
        if self._receive_thread is None:
            self._receive_thread = eventlet.spawn(self._receive)

    def stop(self):
        if self._receive_thread is not None:
            self._receive_thread.kill()
            self._receive_thread = None

    def subscribe(self, message_id, event):
        self._subscriptions[message_id] = event

    def _receive(self):
        client = create_rmq_client()
        client.declare(self._results_queue, enable_ha=True, ttl=86400000)
        with client.open(self._results_queue) as subscription:
            while True:
                msg = subscription.get_message()
                if not msg:
                    continue
                msg.ack()
                msg_id = msg.body.get('SourceID', msg.id)
                if msg_id in self._subscriptions:
                    event = self._subscriptions.pop(msg_id)
                    event.send(msg)
