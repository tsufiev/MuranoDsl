import engine.config
import engine.dsl
from heatclient.client import Client
from keystoneclient.v2_0 import client as ksclient
import heatclient.exc
import engine.dsl.helpers
import eventlet

@engine.dsl.classname('com.mirantis.murano.system.HeatStack')
class HeatStack(engine.dsl.MuranoObject):
    def initialize(self, _context, name):
        self._name = name
        self._template = None
        self._parameters = {}
        self._applied = True
        environment = engine.dsl.helpers.get_environment(_context)
        keystone_settings = engine.config.CONF.keystone
        heat_settings = engine.config.CONF.heat

        client = ksclient.Client(
            endpoint=keystone_settings.auth_url,
            cacert=keystone_settings.ca_file or None,
            cert=keystone_settings.cert_file or None,
            key=keystone_settings.key_file or None,
            insecure=keystone_settings.insecure)

        if not client.authenticate(
                auth_url=keystone_settings.auth_url,
                tenant_id=environment.tenant_id,
                token=environment.token):
            raise heatclient.exc.HTTPUnauthorized()

        heat_url = client.service_catalog.url_for(
            service_type='orchestration',
            endpoint_type=heat_settings.endpoint_type)

        self._heat_client = Client(
            '1',
            heat_url,
            username='badusername',
            password='badpassword',
            token_only=True,
            token=client.auth_token,
            ca_file=heat_settings.ca_file or None,
            cert_file=heat_settings.cert_file or None,
            key_file=heat_settings.key_file or None,
            insecure=heat_settings.insecure)

    def current(self):
        if self._template is not None:
            return self._template
        try:
            stack_info = self._heat_client.stacks.get(stack_id=self._name)
            template = self._heat_client.stacks.template(
                stack_id='{0}/{1}'.format(
                    stack_info.stack_name,
                    stack_info.id))
            self._template.update(template)
            self._parameters.update(stack_info.parameters)
            self._applied = True
            return self._template.copy()
        except heatclient.exc.HTTPNotFound:
            self._template = None
            self._parameters.clear()
            return None

    def parameters(self):
        self.current()
        return self._parameters.copy()

    def reload(self):
        self._template = None
        self._parameters.clear()
        self._load()
        return self._template

    def setTemplate(self, template):
        self._template = template
        self._parameters.clear()
        self._applied = False

    def updateTemplate(self, template):
        self.current()
        self._template = engine.dsl.helpers.merge_dicts(
            self._template, template)
        self._applied = False

    def _get_status(self):
        status = [None]

        def status_func(state_value):
            status[0] = state_value
            return True

        self._wait_state(status_func)
        return status[0]

    def _wait_state(self, status_func):
        tries = 4
        delay = 1
        while tries > 0:
            while True:
                try:
                    stack_info = self._heat_client.stacks.get(
                        stack_id=self._name)
                    status = stack_info.stack_status
                    tries = 4
                    delay = 1
                except heatclient.exc.HTTPNotFound:
                    stack_info = None
                    status = 'NOT_FOUND'
                except Exception:
                    tries -= 1
                    delay *= 2
                    if not tries:
                        raise
                    eventlet.sleep(delay)
                    break

                if 'IN_PROGRESS' in status:
                    eventlet.sleep(2)
                    continue
                if not status_func(status):
                    raise EnvironmentError(
                        "Unexpected stack state {0}".format(status))

                try:
                    return dict([(t['output_key'], t['output_value'])
                                 for t in stack_info.outputs])
                except Exception:
                    return {}
        return {}

    def output(self):
        return self._wait_state(lambda: True)

    def update(self):
        if self._applied:
            return

        current_status = self._get_status()
        if current_status == 'NOT_FOUND':
            self._heat_client.stacks.create(
                stack_name=self._name,
                parameters=self._parameters,
                template=self._template,
                disable_rollback=False)

            outs = self._wait_state(
                lambda status: status == 'CREATE_COMPLETE')
        else:
            self._heat_client.stacks.update(
                stack_id=self._name,
                parameters=self._parameters,
                template=self._template)
            outs = self._wait_state(
                lambda status: status == 'UPDATE_COMPLETE')

        self._applied = True
        return outs

    def delete(self):
        if not self.current():
            return
        self._heat_client.stacks.delete(
            stack_id=self._name)
        self._wait_state(
            lambda status: status in ('DELETE_COMPLETE', 'NOT_FOUND'))
