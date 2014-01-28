from muranocommon.messaging import MqClient
import inspect
from engine.dsl import classname
from engine.system import heat_stack, resource_manager
from engine import config as cfg


def _auto_register(class_loader):
    globs = globals().copy()
    for module_name, value in globs.iteritems():
        if inspect.ismodule(value):
            for class_name in dir(value):
                class_def = getattr(value, class_name)
                if inspect.isclass(class_def) and hasattr(
                        class_def, '_murano_class_name'):
                    class_loader.import_class(class_def)


def register(class_loader, path):
    _auto_register(class_loader)

    @classname('com.mirantis.murano.system.Resources')
    class ResolurceManagerWrapper(resource_manager.ResourceManager):
        def initialize(self, _context, _class=None):
            super(ResolurceManagerWrapper, self).initialize(
                path, _context, _class)

    class_loader.import_class(ResolurceManagerWrapper)

def create_rmq_client():
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
