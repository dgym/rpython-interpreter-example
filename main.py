import sys

from context import Context, LexicalEnv, Overload
from ops import (
    PushConstantOp, GetOp, PopOp, DispatchOp, ReturnOp,
    JumpFalseOp,
)
from values import IntValue

try:
    from rpython.rlib.jit import JitDriver
    rpython = True
except:
    rpython = False


def get_location(pc, ops):
    return "%d %d" % (len(ops), pc)


if rpython:
    jitdriver = JitDriver(
        greens=['pc', 'ops'],
        reds=['sp', 'fp', 'stack_base', 'ctx', 'stack', 'frames'],
        get_printable_location=get_location,
    )


def load_bytecode(n=0):
    """
    asm:
      0 push 10
      1 call fib (1)
      2 call print (1)
      3 pop

    fib asm:
      0 get 0 0
      1 push 2
      2 call < (2)
      3 jump false 6
      4 get 0 0
      5 return
      6 get 0 0
      7 push 1
      8 call - (2)
      9 call fib (1)
      10 get 0 0
      11 push 2
      12 call - (2)
      13 call fib (1)
      14 call + (2)
      15 return
    """

    ctx = Context()
    lex_env = LexicalEnv()

    # Define int fib(int n).
    ops = [
        GetOp(0),
        PushConstantOp(IntValue(2)),
        DispatchOp('<', 2),
        JumpFalseOp(6),
        GetOp(0),
        ReturnOp(),

        GetOp(0),
        PushConstantOp(IntValue(1)),
        DispatchOp('-', 2),
        DispatchOp('fib', 1),

        GetOp(0),
        PushConstantOp(IntValue(2)),
        DispatchOp('-', 2),
        DispatchOp('fib', 1),

        DispatchOp('+', 2),
        ReturnOp(),
    ]
    inner_lex_env = LexicalEnv(lex_env)
    fib = Overload(inner_lex_env, None, [1], ops[:])

    # Define the top level operations.
    ops = [
        PushConstantOp(IntValue(n)),
        DispatchOp('fib', 1),
        DispatchOp('print', 1),
        PopOp(),
    ]
    lex_env.procs['fib'] = fib
    ctx.frames[0].lex_env = lex_env
    ctx.frames[0].ops = ops
    return ctx


def entry_point(argv):
    n = 0
    if len(argv) > 1:
        n = int(argv[1])

    ctx = load_bytecode(n)

    while not ctx.ended():
        if rpython:
            frame = ctx.frames[ctx.fp]
            jitdriver.jit_merge_point(
                pc=frame.pc, ctx=ctx, ops=frame.ops,
                sp=ctx.sp, fp=ctx.fp, stack_base=frame.stack_base,
                stack=ctx.stack,
                frames=ctx.frames,
            )
        #ctx.print_frame()
        #ctx.print_stack()
        ctx.step()


    return 0


def jitpolicy(driver):
    from rpython.jit.codewriter.policy import JitPolicy
    return JitPolicy()


def target(*args):
    return entry_point, None


if __name__ == '__main__':
    entry_point(sys.argv)
