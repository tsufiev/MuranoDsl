import expressions
import types
import exceptions
import helpers


class CodeBlock(expressions.DslExpression):
    def __init__(self, body):
        if not isinstance(body, types.ListType):
            body = [body]
        self._block = map(expressions.parse_expression, body)

    def execute(self, context, object_store, murano_class):
        try:
            for expr in self._block:
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


print "$$$$$$$$$$$$$$$$$$$$$$$$"
expressions.register_macro(do_macro)
expressions.register_macro(func_macro)
expressions.register_macro(ReturnMacro)
expressions.register_macro(BreakMacro)