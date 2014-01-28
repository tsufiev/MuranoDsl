# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import eventlet
from muranocommon.messaging import MqClient

from engine import system
from engine.dsl import ObjectStore
from engine.enviroment import Environment
from openstack.common import service
from openstack.common import log as logging
import config as cfg
from dsl.executor import MuranoDslExecutor
import class_loader


log = logging.getLogger(__name__)


class EngineService(service.Service):
    def __init__(self):
        super(EngineService, self).__init__()

    def start(self):
        #super(EngineService, self).start()
        #self.tg.add_thread(self._start_rabbitmq)
        self.test()

    def stop(self):
        super(EngineService, self).stop()

    def _task_received(self, message):
        task = message.body or {}
        message_id = message.id
        message.ack()

    def create_rmq_client(self):
        rabbitmq = cfg.CONF.rabbitmq
        connection_params = {
            'login': rabbitmq.login,
            'password': rabbitmq.password,
            'host': rabbitmq.host,
            'port': rabbitmq.port,
            'virtual_host': rabbitmq.virtual_host,
            'ssl': rabbitmq.ssl,
            'ca_certs': rabbitmq.ca_certs.strip() or None
        }
        return MqClient(**connection_params)

    def _start_rabbitmq(self):
        reconnect_delay = 1
        while True:
            try:
                with self.create_rmq_client() as mq:
                    mq.declare('tasks', 'tasks')
                    mq.declare('task-results')
                    with mq.open('tasks', prefetch_count=1) as subscription:
                        reconnect_delay = 1
                        while True:
                            msg = subscription.get_message(timeout=2)
                            if msg is not None:
                                eventlet.spawn(self._task_received, msg)
            except Exception as ex:
                log.exception(ex)

                eventlet.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60)

    def debug_print(self, x, y=5):
        print "It works!", x, y
        return 14

    def test(self):

        environment = Environment()
        environment.tenant_id = ''
        environment.token = ''

        base_path = './meta'
        cl = class_loader.ClassLoader(base_path)
        system.register(cl, base_path)
        executor = MuranoDslExecutor(cl, environment)
        objects = executor.load({
            '123': {'?': {'type': 'com.mirantis.murano.examples.Test'},
                     'p1': 88, 'pt': '345' },
            '345': {'?': {'type': 'com.mirantis.murano.examples.Test2'},
                    'p2': 777}
        })
        # objects = object_store.load({
        #     '123': {'?': {'type': 'com.mirantis.murano.examples.Test'}},
        # })

        obj = [t for t in objects if t.object_id == '123'][0]
        print obj
        print '---------------------------------------------------------'
        print



        object_class = cl.get_class("com.mirantis.murano.Object")
        object_class.add_method('debugPrint', self.debug_print)
#        print test_class.name
        print "=", obj.type.invoke('method1', executor, obj, {'t': 17})
        print
        print '---------------------------------------------------------'
        print obj
        exit()





