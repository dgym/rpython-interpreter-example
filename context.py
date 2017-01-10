from values import Value


class Context:
    '''
    Represents the VM and its entire state.
    '''

    _immutable_fields_ = ['frames', 'stack']
    __slots__ = ['frames', 'fp', 'stack', 'sp']
    _attrs_ = ['frames', 'fp', 'stack', 'sp']

    def __init__(self):
        self.frames = [Frame() for _ in range(1024)]
        self.fp = 0
        self.stack = [Value()] * (1024 * 1024)
        self.sp = -1

    def ended(self):
        if self.fp > 0:
            return False
        frame = self.frames[0]
        return frame.pc >= len(frame.ops)

    def step(self):
        frame = self.frames[self.fp]
        op = frame.ops[frame.pc]
        frame.pc += 1
        op.execute(self)

    def print_stack(self):
        stack_length = self.sp + 1
        print('stack:')
        if stack_length > 0:
            for value in self.stack[:stack_length]:
                print('  ' + value.__repr__())
        print('')

    def print_frame(self, up=0):
        fp = self.fp - up

        print('frame %d ops:' % fp)
        frame = self.frames[fp]
        for idx, op in enumerate(frame.ops):
            if idx == frame.pc:
                print('* ' + op.__repr__())
            else:
                print('  ' + op.__repr__())


class Overload:
    '''
    A function with a specific type signature.
    '''
    _immutable_ = True
    _immutable_fields_ = ['lex_env', 'ret', 'args', 'ops[*]']
    _attrs_ = ['lex_env', 'ret', 'args', 'ops']
    __slots__ = ['lex_env', 'ret', 'args', 'ops']

    def __init__(self, lex_env, ret, args, ops):
        self.lex_env = lex_env
        self.ret = ret
        self.args = args
        self.ops = ops[:]


class LexicalEnv:
    _immutable_ = True
    _immutable_fields_ = ['parent']

    def __init__(self, parent=None):
        assert parent is None or isinstance(parent, LexicalEnv)
        self.parent = parent
        self.procs = {}


class Frame:
    '''
    The execution environment for a function.
    '''
    _immutable_ = True
    _immutable_fields_ = ['lex_env', 'ops[*]']
    _attrs_ = ['lex_env', 'ops', 'pc', 'stack_base']
    __slots__ = ['lex_env', 'ops', 'pc', 'stack_base']

    def __init__(self):
        self.lex_env = None
        self.ops = None
        self.pc = 0
        self.stack_base = 0
