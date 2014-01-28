from muranocommon.messaging import Message
from . import create_rmq_client
from engine.dsl import classname, MuranoObject
import eventlet.event
import os
import uuid
import types


class AgentException(Exception):
    def __init__(self, message_info):
        self.message_info = message_info

@classname('com.mirantis.murano.system.Agent')
class Agent(MuranoObject):
    def initialize(self, host, environment, resource_manager):
        self._queue = ('e%s-h%s' % (environment.id(), host.id())).lower()
        self._resource_manager = resource_manager
        self._listener = environment.agentListener

    def _send(self, template, wait_results):
        client = create_rmq_client()
        final_template, msg_id = self.build_execution_plan(template)

        if wait_results:
            event = eventlet.event.Event()
            self._listener.subscribe(msg_id, event)
            self._listener.start()

        msg = Message()
        msg.body = template
        msg.id = msg_id
        client.declare(self._queue, enable_ha=True, ttl=86400000)
        client.send(message=msg, key=self._queue)

        if wait_results:
            result = event.wait()

            if not result:
                return None

            if result.get('FormatVersion', '1.0.0').startswith('1.'):
                return self._process_v1_result(result)
            else:
                return self._process_v2_result(result)
        else:
            return None

    def call(self, template):
        return self._send(template, True)

    def send(self, template):
        return self._send(template, False)

    def _process_v1_result(self, result):
        if result['IsException']:
            raise AgentException(dict(self._get_exception_info(
                result.get('Result', [])), source='execution_plan'))
        else:
            results = result.get('Result', [])
            if not result:
                return None
            value = results[-1]
            if value['IsException']:
                raise AgentException(dict(self._get_exception_info(
                    value.get('Result', [])), source='command'))
            else:
                return value.get('Result')

    def _process_v2_result(self, result):
        error_code = result.get('ErrorCode', 0)
        if not error_code:
            return result.get('Body')
        else:
            body = result.get('Body') or {}
            err = {
                'message': body.get('Message'),
                'details': body.get('AdditionalInfo'),
                'errorCode': error_code,
                'time': result.get('Time')
            }
            for attr in ('Message', 'AdditionalInfo'):
                if attr in body:
                    del body[attr]
            err['extra'] = body if body else None
            raise AgentException(err)

    def _get_array_item(self, array, index):
        return array[index] if len(array) > index else None

    def _get_exception_info(self, data):
        data = data or []
        return {
            'type': self._get_array_item(data, 0),
            'message': self._get_array_item(data, 1),
            'command': self._get_array_item(data, 2),
            'details': self._get_array_item(data, 3),
            'timestamp': self.datetime.datetime.now().isoformat()
        }

    def build_execution_plan(self, template):
        if not isinstance(template, types.DictionaryType):
            raise ValueError('Incorrect execution plan ')
        format_version = template.get('FormatVersion')
        if not format_version or format_version.startswith('1.'):
            return self._build_v1_execution_plan(template)
        else:
            return self._build_v2_execution_plan(template)

    def _build_v1_execution_plan(self, template):
        scripts_folder = 'scripts'
        script_files = template.get('Scripts', [])
        scripts = []
        for script in script_files:
            script_path = os.path.join(scripts_folder, script)
            scripts.append(self._resource_manager.string(
                script_path).encode('base64'))
        template['Scripts'] = scripts
        return template, uuid.uuid4().hex

    def _build_v2_execution_plan(self, template):
        scripts_folder = 'scripts'
        plan_id = uuid.uuid4().hex
        template['ID'] = plan_id
        if 'Action' not in template:
            template['Action'] = 'Execute'
        if 'Files' not in template:
            template['Files'] = {}

        files = {}
        for file_id, file_descr in template['Files'].items():
            files[file_descr['Name']] = file_id
        for name, script in template.get('Scripts', {}).items():
            if 'EntryPoint' not in script:
                raise ValueError('No entry point in script ' + name)
            script['EntryPoint'] = self._place_file(
                scripts_folder, script['EntryPoint'], template, files)
            if 'Files' in script:
                for i in range(0, len(script['Files'])):
                    script['Files'][i] = self._place_file(
                        scripts_folder, script['Files'][i], template, files)

        return template, plan_id

    def _place_file(self, folder, name, template, files):
        use_base64 = False
        if name.startswith('<') and name.endswith('>'):
            use_base64 = True
            name = name[1:len(name) - 1]
        if name in files:
            return files[name]

        file_id = uuid.uuid4().hex
        body_type = 'Base64' if use_base64 else 'Text'
        body = self._resource_manager.string(os.path.join(folder, name))
        if use_base64:
            body = body.encode('base64')

        template['Files'][file_id] = {
            'Name': name,
            'BodyType': body_type,
            'Body': body
        }
        files[name] = file_id
        return file_id
