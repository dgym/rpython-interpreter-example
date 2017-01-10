from context import Context
from values import (
    Value, IntValue, BoolValue,
)


class Op(object):
    _immutable_ = True
    _attrs_ = []
    __slots__ = []

    def __repr__(self):
        return 'nop'

    def execute(self, ctx):
        assert isinstance(ctx, Context)


class PushConstantOp(Op):
    '''
    Pushes a constant value onto the stack.
    '''
    _immutable_ = True
    _immutable_fields_ = ['value']
    _attrs_ = ['value']
    __slots__ = ['value']

    def __init__(self, value=False):
        assert isinstance(value, Value)
        self.value = value

    def __repr__(self):
        return 'push ' + self.value.__repr__()

    def execute(self, ctx):
        ctx.sp += 1
        ctx.stack[ctx.sp] = self.value


class DispatchOp(Op):
    '''
    Calls a builtin function or an Overload.

    The arguments are passed on the stack.
    On return a single value is left on the stack, even
    for functions returning void.
    '''
    _immutable_ = True
    _immutable_fields_ = ['sym', 'argc']
    _attrs_ = ['sym', 'argc']
    __slots__ = ['sym', 'argc']

    def __init__(self, sym, argc):
        assert isinstance(sym, str)
        assert isinstance(argc, int)
        self.sym = sym
        self.argc = argc

    def __repr__(self):
        return 'call ' + self.sym + ' (' + str(self.argc) + ')'

    def execute(self, ctx):
        if self.sym == '+' and self.argc == 2:
            lhs = ctx.stack[ctx.sp-1]
            rhs = ctx.stack[ctx.sp]
            assert isinstance(lhs, IntValue)
            assert isinstance(rhs, IntValue)
            ctx.sp -= 1
            ctx.stack[ctx.sp] = IntValue(lhs.value + rhs.value)
        elif self.sym == '-' and self.argc == 2:
            lhs = ctx.stack[ctx.sp-1]
            rhs = ctx.stack[ctx.sp]
            assert isinstance(lhs, IntValue)
            assert isinstance(rhs, IntValue)
            ctx.sp -= 1
            ctx.stack[ctx.sp] = IntValue(lhs.value - rhs.value)
        elif self.sym == '<' and self.argc == 2:
            lhs = ctx.stack[ctx.sp-1]
            rhs = ctx.stack[ctx.sp]
            assert isinstance(lhs, IntValue)
            assert isinstance(rhs, IntValue)
            ctx.sp -= 1
            ctx.stack[ctx.sp] = BoolValue(lhs.value < rhs.value)
        elif self.sym == 'print' and self.argc == 1:
            arg = ctx.stack[ctx.sp]
            print(arg.__repr__())
            ctx.stack[ctx.sp] = Value()
        else:
            for frame in ctx.frames:
                if self.sym in frame.lex_env.procs:
                    overload = frame.lex_env.procs[self.sym]

                    ctx.fp += 1
                    frame = ctx.frames[ctx.fp]
                    frame.lex_env = overload.lex_env
                    frame.ops = overload.ops
                    frame.pc = 0
                    frame.stack_base = ctx.sp - self.argc + 1
                    break


class ReturnOp(Op):
    '''
    Returns from an Overload call.

    The return value is taken from the top of the stack.
    '''
    _immutable_ = True
    _attrs_ = []
    __slots__ = []

    def __repr__(self):
        return 'return'

    def execute(self, ctx):
        frame = ctx.frames[ctx.fp]
        ctx.stack[frame.stack_base] = ctx.stack[ctx.sp]
        ctx.sp = frame.stack_base
        ctx.fp -= 1


class PopOp(Op):
    '''
    Pops a single value off the stack.
    '''
    _immutable_ = True
    _attrs_ = []
    __slots__ = []

    def __repr__(self):
        return 'pop'

    def execute(self, ctx):
        ctx.sp -= 1


class JumpOp(Op):
    '''
    Unconditional jump.
    '''
    _immutable_ = True
    _immutable_fields_ = ['pc']
    _attrs_ = ['pc']
    __slots__ = ['pc']

    def __init__(self, pc=0):
        self.pc = pc

    def __repr__(self):
        return 'jump ' + str(self.pc)

    def execute(self, ctx):
        frame = ctx.frames[ctx.fp]
        frame.pc = self.pc


class JumpFalseOp(Op):
    '''
    Jumps if the popped value is False.
    '''
    _immutable_ = True
    _immutable_fields_ = ['pc']
    _attrs_ = ['pc']
    __slots__ = ['pc']

    def __init__(self, pc=0):
        self.pc = pc

    def __repr__(self):
        return 'jump false ' + str(self.pc)

    def execute(self, ctx):
        frame = ctx.frames[ctx.fp]
        cnd = ctx.stack[ctx.sp]
        ctx.sp -= 1
        if isinstance(cnd, BoolValue) and not cnd.value:
            frame.pc = self.pc


class GetOp(Op):
    '''
    Retreives a value relative to the frame's stack base.

    This is typically an argument or a local variable.
    '''
    _immutable_ = True
    _immutable_fields_ = ['idx']
    _attrs_ = ['idx']
    __slots__ = ['idx']

    def __init__(self, idx):
        assert isinstance(idx, int)
        self.idx = idx

    def __repr__(self):
        return 'get ' + str(self.idx)

    def execute(self, ctx):
        frame = ctx.frames[ctx.fp]
        ctx.sp += 1
        ctx.stack[ctx.sp] = ctx.stack[frame.stack_base + self.idx]
