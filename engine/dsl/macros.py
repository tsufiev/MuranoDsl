from yaql_expression import YaqlExpression
import expressions
import types
import exceptions
import helpers
from eventlet.greenpool import GreenPool


class CodeBlock(expressions.DslExpression):
    def __init__(self, body):
        if not isinstance(body, types.ListType):
            body = [body]
        self.code_block = map(expressions.parse_expression, body)

    def execute(self, context, object_store, murano_class):
        try:
            for expr in self.code_block:
                expr.execute(context, object_store, murano_class)
        except exceptions.BreakException:
            return


class MethodBlock(CodeBlock):
    def execute(self, context, object_store, murano_class):
        try:
            super(MethodBlock, self).execute(
                context, object_store, murano_class)
        except exceptions.ReturnException as e:
            return e.value
        else:
            return None


class ReturnMacro(expressions.DslExpression):
    def __init__(self, Return):
        e, body = Return
        if e:
            raise SyntaxError()
        self._value = body

    def execute(self, context, object_store, murano_class):
        raise exceptions.ReturnException(
            helpers.evaluate(self._value, context))


class BreakMacro(expressions.DslExpression):
    def __init__(self, Break):
        e, body = Break
        if e or body:
            raise SyntaxError()

    def execute(self, context, object_store, murano_class):
        raise exceptions.BreakException()


class ParallelMacro(CodeBlock):
    def __init__(self, Parallel, Limit=(None, None)):
        e, body = Parallel
        if e:
            raise SyntaxError()
        super(ParallelMacro, self).__init__(body)
        e, limit = Limit
        if e:
            raise SyntaxError()
        if limit:
            self._limit = YaqlExpression(limit)
        else:
            self._limit = len(self.code_block)

    def execute(self, context, object_store, murano_class):
        if not self.code_block:
            return
        gp = GreenPool(helpers.evaluate(self._limit, context))
        for expr in self.code_block:
            gp.spawn_n(expr.execute, context, object_store, murano_class)
        gp.waitall()


class OnChangedMacro(CodeBlock):
    def __init__(self, OnChanged, Do):
        _, parameters = OnChanged
        _, body = Do
        if not isinstance(parameters, types.DictType) or not body:
            raise SyntaxError()

        super(OnChangedMacro, self).__init__(body)
        self._parameters = parameters

    @property
    def parameters(self):
        return self._parameters

    def _parameters_changed(self, context, object_store):
        changed = False
        obj = context.get_data()
        for p_name, p_value in self.parameters.iteritems():
            if obj.diff(p_name, p_value, context=context,
                        object_store=object_store):
                changed = True
                break

        return changed

    def _commit_history(self, context):
        obj = context.get_data()
        for p_name, p_value in self.parameters.iteritems():
            obj.set_history(p_name, p_value, context)

    def execute(self, context, object_store, murano_class):
        if self._parameters_changed(context, object_store):
            print 'One of the {parameters} parameters has changed, running ' \
                  'the main code body'.format(parameters=self.parameters)
            try:
                super(OnChangedMacro, self).execute(
                    context, object_store, murano_class)
            # update changed variables only if no errors occurred
            except exceptions.BreakException:
                self._commit_history(context)
            except exceptions.ReturnException:
                self._commit_history(context)
                raise
            else:
                self._commit_history(context)
        else:
            print 'None of the parameters has changed, skipping main code ' \
                  'body'


def do_macro(Do):
    e, body = Do
    if e:
        raise SyntaxError()
    return CodeBlock(body)


def func_macro(Func):
    e, body = Func
    if e:
        raise SyntaxError()
    return MethodBlock(body)


expressions.register_macro(do_macro)
expressions.register_macro(func_macro)
expressions.register_macro(ReturnMacro)
expressions.register_macro(BreakMacro)
expressions.register_macro(ParallelMacro)
expressions.register_macro(OnChangedMacro)
