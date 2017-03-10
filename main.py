import sys

from context import Context, LexicalEnv, Overload, Ops
from ops import (
    PushConstantOp, GetOp, DispatchOp, ReturnOp,
    JumpFalseOp,
)
from values import (
    IntValue, StringValue,
)


def load_bytecode(n=0):
    """
    asm:
      0 push 10
      1 call fib (1)
      2 call print (1)
      3 pop

    fib asm:
      0 get 0
      1 push 2
      2 call < (2)
      3 jump false 6
      4 get 0
      5 return
      6 get 0
      7 push 1
      8 call - (2)
      9 call fib (1)
      10 get 0
      11 push 2
      12 call - (2)
      13 call fib (1)
      14 call + (2)
      15 return
    """

    lex_env = LexicalEnv()

    # Define fib().
    constants = [
        IntValue(2),            # 0
        IntValue(1),            # 1
        IntValue(2),            # 2
        StringValue('<'),       # 3
        StringValue('-'),       # 4
        StringValue('-'),       # 5
        StringValue('fib'),     # 6
        StringValue('+'),       # 7
    ]
    ops = [
        GetOp, 0,           # 0
        PushConstantOp, 0,  # 2
        DispatchOp, 3, 2,   # 4
        JumpFalseOp, 12,    # 7
        GetOp, 0,           # 9
        ReturnOp,           # 11

        GetOp, 0,           # 12
        PushConstantOp, 1,  # 14
        DispatchOp, 4, 2,   # 16
        DispatchOp, 6, 1,   # 19

        GetOp, 0,           # 22
        PushConstantOp, 2,  # 24
        DispatchOp, 4, 2,   # 26
        DispatchOp, 6, 1,   # 29

        DispatchOp, 7, 2,   # 32
        ReturnOp,           # 35
    ]
    inner_lex_env = LexicalEnv(lex_env, constants)
    fib = Overload(inner_lex_env, None, [1], Ops(ops))

    # Define the top level operations.
    constants = [
        IntValue(n),            # 0
        StringValue('fib'),     # 1
        StringValue('print'),   # 2
    ]
    ops = [
        PushConstantOp, 0,
        DispatchOp, 1, 1,
        DispatchOp, 2, 1,
        ReturnOp,
    ]
    lex_env.procs['fib'] = fib
    lex_env.constants = constants
    return (lex_env, Ops(ops), 10)


def entry_point(argv):
    n = 0
    if len(argv) > 1:
        n = int(argv[1])

    lex_env, ops, stack_size = load_bytecode(n)
    ctx = Context()
    ctx.run(lex_env, ops, stack_size)

    return 0


def jitpolicy(driver):
    from rpython.jit.codewriter.policy import JitPolicy
    return JitPolicy()


def target(*args):
    return entry_point, None


if __name__ == '__main__':
    entry_point(sys.argv)
