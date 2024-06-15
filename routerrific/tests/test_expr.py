import inspect
from typing import Annotated, TypeAlias

import pytest

from routerrific.expr import Var, X, evaluate


def test_simple_str():
    expr = X + X

    assert str(expr) == "(x + x)"


def test_length():
    expr = X.length() > 10

    assert str(expr) == "(len(x) > 10)"


def test_complex():
    """Some non-sensical expressions to test every operator."""
    Y = Var("y")
    expr_1 = (-X * X) / (X > 0)
    expr_2 = (Y.length() < 1) + (X == X) - (X != Y)
    expr = expr_1 & (expr_2 <= 1) | (expr_2 > 1) | (expr_2 >= 0)

    assert str(expr)
    assert repr(expr)

    assert evaluate(expr, {"x": 1, "y": "abc"}) is not None


def test_unsupported_type():
    with pytest.raises(ValueError):
        evaluate({}, {})


def test_simple_eval():
    expr = X + X
    variables = {"x": 1}

    assert evaluate(expr, variables) == 2


def test_simple_cond():
    expr = X + 1 >= 2
    variables = {"x": 1}

    assert evaluate(expr, variables) is True


def test_annotated():
    def f(x: Annotated[int, (X >= 0) & (X < 10)]): ...

    signature = inspect.signature(f)
    parameters = signature.parameters

    assert "x" in parameters

    meta = parameters["x"].annotation.__metadata__
    assert len(meta) == 1

    expr = meta[0]

    assert str(expr) == "((x >= 0) and (x < 10))"

    # Now for some crazy stuff
    assert eval(f"lambda x: {expr}")(1) is True
    assert eval(f"lambda x: {expr}")(11) is False


def test_positive_int_annotation():
    PositiveInt: TypeAlias = Annotated[int, X >= 0]

    def f(x: PositiveInt): ...

    signature = inspect.signature(f)
    parameters = signature.parameters

    assert "x" in parameters

    meta = parameters["x"].annotation.__metadata__
    assert len(meta) == 1

    expr = meta[0]

    assert str(expr) == "(x >= 0)"


def test_var_name_invalid():
    with pytest.raises(ValueError):
        Var("from os import *; os.system('rm -rf /')")
