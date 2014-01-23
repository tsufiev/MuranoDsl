import engine.dsl

@engine.dsl.classname('com.mirantis.murano.system.Heat')
class HeatApi(engine.dsl.MuranoObject):
    def initialize(self, a=None, b=None):
        print 'Create HEatApi', a, b

    def createStack(self, name=None, name2=None):
        print 'Create stack', name, name2
