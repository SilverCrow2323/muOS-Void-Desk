# -*- coding: utf-8 -*-
"""
Safe evaluator for the calculator: whitelisted AST instead of eval().
The old eval({"__builtins__": {}}) cannot be hacked but it can be frozen:
9**9**9 or factorial(99999) compute huge integers and lock up UI and RAM (1GB).
Here: explicitly allowed nodes, power cap (result <= ~1e300),
factorial cap, maximum depth.
"""
import ast
import math
import operator as op

_BIN = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
        ast.Mod: op.mod, ast.FloorDiv: op.floordiv, ast.Pow: op.pow}
_UN = {ast.UAdd: op.pos, ast.USub: op.neg}
MAX_FACT = 500
MAX_DEPTH = 40


def calc_safe_eval(expr, ns):
    def ev(n, d=0):
        if d > MAX_DEPTH:
            raise ValueError("nested too deeply")
        if isinstance(n, ast.Expression):
            return ev(n.body, d + 1)
        if isinstance(n, ast.Constant):
            if isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
                return n.value
            raise ValueError("constant not allowed")
        if isinstance(n, ast.Name):
            v = ns.get(n.id)
            if v is not None and not callable(v):
                return v
            raise ValueError("invalid name")
        if isinstance(n, ast.UnaryOp) and type(n.op) in _UN:
            return _UN[type(n.op)](ev(n.operand, d + 1))
        if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            a, b = ev(n.left, d + 1), ev(n.right, d + 1)
            if isinstance(n.op, ast.Pow):
                if abs(b) > 100000:
                    raise OverflowError("exponent too large")
                if abs(a) > 1 and abs(b) * math.log10(abs(a)) > 300:
                    raise OverflowError("result too large")
            return _BIN[type(n.op)](a, b)
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and not n.keywords and callable(ns.get(n.func.id))):
            args = [ev(x, d + 1) for x in n.args]
            if n.func.id == "factorial" and args and abs(args[0]) > MAX_FACT:
                raise OverflowError("factorial too large")
            return ns[n.func.id](*args)
        raise ValueError("expression not allowed")

    return ev(ast.parse(expr, mode="eval"))
