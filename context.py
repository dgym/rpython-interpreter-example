try:
    from rpython.rlib import jit
    from rpython.rlib.jit import JitDriver, elidable, hint
    from rpython.rlib.objectmodel import always_inline
    rpython = True
except:
    rpython = False

from values import Value, BoolValue, IntValue, StringValue
from ops import (
    PushConstantOp, GetOp, PopOp, DispatchOp, ReturnOp,
    JumpFalseOp,
)


if rpython:
    def get_location(pc, ops):
        return "%d %d" % (ops.__repr__(), pc)

    def get_unique_id(pc, ops):
        from rpython.rlib import rvmprof
        return rvmprof.get_unique_id(ops)

    class BareJitDriver(JitDriver):
        reds = ['self', 'frame']
        greens = ['pc', 'ops']
        virtualizables = ['frame']

    jitdriver = BareJitDriver(
        get_printable_location=get_location,
        #get_unique_id=get_unique_id,
        #is_recursive=True,
        should_unroll_one_iteration = lambda _, __: True
    )
else:
    def always_inline(proc):
        return proc

    def elidable(proc):
        return proc

    def hint(item, **kwargs):
        return item

    class JitDriver:
        def can_enter_jit(*args, **kwargs):
            pass

        def jit_merge_point(*args, **kwargs):
            pass

    jitdriver = JitDriver()


class Context(object):
    def __init__(self):
        pass
        #self.topframeref = jit.vref_None

    def enter(self, frame):
        frame.f_backref = self.topframeref
        self.topframeref = jit.virtual_ref(frame)

    def leave(self, frame):
        jit.virtual_ref_finish(self.topframeref, frame)
        self.topframeref = frame.f_backref

    def run(self, lex_env, ops, stack_size, args=None):
        frame = hint(Frame(lex_env, ops, stack_size), access_directly=True)
        if args is not None:
            frame.push(args)
        #self.enter(frame)
        pc = 0
        jitdriver.can_enter_jit(
            pc=pc, ops=frame.ops,
            self=self, frame=frame,
        )
        try:
            while True:
                jitdriver.jit_merge_point(
                    pc=pc, ops=frame.ops,
                    self=self, frame=frame,
                )

                pc = frame.step(self, pc)
                if pc < 0:
                    return frame.pop()
        finally:
            pass #self.leave(frame)


class Overload(object):
    _immutable_ = True
    _immutable_fields_ = ['lex_env', 'ret', 'args', 'ops[*]']
    _attrs_ = ['lex_env', 'ret', 'args', 'ops']
    __slots__ = ['lex_env', 'ret', 'args', 'ops']

    def __init__(self, lex_env, ret, args, ops):
        self.lex_env = lex_env
        self.ret = ret
        self.args = args
        self.ops = ops


class LexicalEnv(object):
    _immutable_ = True
    _immutable_fields_ = ['parent', 'constants[*]']
    _attrs_ = ['parent', 'vars', 'procs', 'constants']
    __slots__ = ['parent', 'vars', 'procs', 'constants']

    def __init__(self, parent=None, constants=[]):
        assert parent is None or isinstance(parent, LexicalEnv)
        self.parent = parent
        self.vars = {}
        self.procs = {}
        self.constants = constants

    @elidable
    def get_proc_env(self, sym):
        lex_env = self
        while lex_env and not sym in lex_env.procs:
            lex_env = lex_env.parent
        return lex_env


class Ops(object):
    _immutable_ = True
    _immutable_fields_ = ['ops[*]']
    _attrs_ = ['ops']
    __slots__ = ['ops']

    def __init__(self, ops):
        self.ops = ops[:]

    def __repr__(self):
        return len(self.ops)


@elidable
def getop(ops, idx):
    return ops.ops[idx]


class Frame(object):
    '''
    The execution environment for a function.
    '''
    _immutable_fields_ = ['lex_env', 'ops']
    _virtualizable_ = [
        'pc', 'values[*]', 'sp', 'lex_env', 'ops',
    ]

    lex_env = None
    ops = None
    pc = 0
    values = None
    sp = 0

    def __init__(self, lex_env, ops, stack_size):
        self = hint(self, access_directly=True, fresh_virtualizable=True)
        self.lex_env = lex_env
        self.ops = ops
        self.pc = 0
        self.values = [None] * stack_size
        self.sp = 0
        #self.f_backref = jit.vref_None

    @always_inline
    def step(self, ctx, pc):
        self = hint(self, access_directly=True)
        ops = hint(self.ops, promote=True)
        lex_env = hint(self.lex_env, promote=True)
        op = getop(ops, pc)

        if op == PushConstantOp:
            idx = getop(ops, pc + 1)
            self.push(lex_env.constants[idx])
            return pc + 2
        elif op == DispatchOp:
            idx = getop(ops, pc + 1)
            argc = getop(ops, pc + 2)
            sym_value = lex_env.constants[idx]
            assert isinstance(sym_value, StringValue)
            sym = sym_value.value
            if sym == '+' and argc == 2:
                rhs = self.pop()
                lhs = self.pop()
                assert isinstance(lhs, IntValue)
                assert isinstance(rhs, IntValue)
                self.push(IntValue(lhs.value + rhs.value))
            elif sym == '-' and argc == 2:
                rhs = self.pop()
                lhs = self.pop()
                assert isinstance(lhs, IntValue)
                assert isinstance(rhs, IntValue)
                self.push(IntValue(lhs.value - rhs.value))
            elif sym == '<' and argc == 2:
                rhs = self.pop()
                lhs = self.pop()
                assert isinstance(lhs, IntValue)
                assert isinstance(rhs, IntValue)
                self.push(BoolValue(lhs.value < rhs.value))
            elif sym == 'print' and argc == 1:
                print(self.pop().__repr__())
                self.push(Value())
            else:
                proc_lex_env = lex_env.get_proc_env(sym)
                if proc_lex_env:
                    overload = proc_lex_env.procs[sym]
                    self.push(ctx.run(
                        overload.lex_env,
                        overload.ops,
                        10,
                        self.pop(),
                    ))
            return pc + 3
        elif op == ReturnOp:
            return -1
        elif op == PopOp:
            self.drop()
            return pc + 1
        elif op == JumpFalseOp:
            cnd = self.pop()
            if isinstance(cnd, BoolValue) and not cnd.value:
                idx = getop(ops, pc + 1)
                return idx
            else:
                return pc + 2
        elif op == GetOp:
            idx = getop(ops, pc + 1)
            self.push(self.get(idx))
            return pc + 2

        return pc

    def debug(self, stack):
        print('frame ops:')
        for idx, op in enumerate(self.ops.ops):
            if idx == self.pc:
                print('* ' + op.__repr__())
            else:
                print('  ' + op.__repr__())

        stack_length = stack.sp
        print('stack:')
        if stack_length > 0:
            for value in stack.values[:stack_length]:
                print('  ' + value.__repr__())
        print('')

    @always_inline
    def push(self, value):
        sp = hint(self.sp, promote=True)
        #sp = self.sp
        assert sp >= 0
        self.values[sp] = value
        self.sp = sp + 1

    @always_inline
    def pop(self):
        sp = hint(self.sp, promote=True) - 1
        #sp = self.sp - 1
        self.sp = sp
        assert sp >= 0
        return self.values[sp]

    @always_inline
    def get(self, idx):
        idx = hint(idx, promote=True)
        assert idx >= 0
        return self.values[idx]

    @always_inline
    def drop(self):
        sp = hint(self.sp, promote=True) - 1
        self.sp = sp
