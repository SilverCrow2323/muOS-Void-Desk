import math
import pytest
from desk.utils.safe_calc import calc_safe_eval

NS = {"factorial": math.factorial}

def test_add():
    assert calc_safe_eval("1+2", NS) == 3

def test_pow():
    assert calc_safe_eval("2**10", NS) == 1024

def test_fact():
    assert calc_safe_eval("factorial(5)", NS) == 120

def test_huge_pow():
    with pytest.raises(OverflowError):
        calc_safe_eval("9**9**9", NS)

def test_huge_fact():
    with pytest.raises(OverflowError):
        calc_safe_eval("factorial(99999)", NS)

def test_reject_dunder():
    with pytest.raises((ValueError, SyntaxError)):
        calc_safe_eval("__import__('os').system('ls')", NS)
