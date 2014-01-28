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