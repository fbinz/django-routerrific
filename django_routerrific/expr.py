from typing import Any


class Expr:
    def evaluate(self, variables: dict[str, Any]) -> Any:
        raise NotImplementedError

    def compile(self):
        return eval(f"lambda x: {self}")

    def __str__(self) -> str:
        raise NotImplementedError

    def __add__(self, other):
        return Add(self, other)

    def __sub__(self, other):
        return Sub(self, other)

    def __mul__(self, other):
        return Mul(self, other)

    def __truediv__(self, other):
        return Div(self, other)

    def __neg__(self):
        return Neg(self)

    def length(self):
        return Length(self)

    def __gt__(self, other):
        return Gt(self, other)

    def __ge__(self, other):
        return Ge(self, other)

    def __lt__(self, other):
        return Lt(self, other)

    def __le__(self, other):
        return Le(self, other)

    def __eq__(self, other):
        return Eq(self, other)

    def __ne__(self, other):
        return Ne(self, other)

    def __and__(self, other):
        return And(self, other)

    def __or__(self, other):
        return Or(self, other)


class Add(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Add({self.left!r}, {self.right!r})"

    def __str__(self):
        return f"({self.left} + {self.right})"

    def evaluate(self, variables: dict[str, Any]) -> Any:
        return evaluate(self.left, variables) + evaluate(self.right, variables)


class Sub(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Sub({self.left!r}, {self.right!r})"

    def __str__(self):
        return f"({self.left} - {self.right})"

    def evaluate(self, variables: dict[str, Any]) -> Any:
        return evaluate(self.left, variables) - evaluate(self.right, variables)


class Mul(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Mul({self.left!r}, {self.right!r})"

    def __str__(self):
        return f"({self.left} * {self.right})"

    def evaluate(self, variables: dict[str, Any]) -> Any:
        return evaluate(self.left, variables) * evaluate(self.right, variables)


class Div(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Div({self.left!r}, {self.right!r})"

    def __str__(self):
        return f"({self.left}/{self.right})"

    def evaluate(self, variables: dict[str, Any]) -> Any:
        return evaluate(self.left, variables) / evaluate(self.right, variables)


class Neg(Expr):
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return f"Neg({self.expr!r})"

    def __str__(self) -> str:
        return f"-{self.expr}"

    def evaluate(self, variables: dict[str, Any]) -> Any:
        return -evaluate(self.expr, variables)


class Length(Expr):
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return f"Len({self.expr!r})"

    def __str__(self) -> str:
        return f"len({self.expr})"

    def evaluate(self, variables: dict[str, Any]) -> Any:
        return len(evaluate(self.expr, variables))


class Gt(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Gt({self.left!r}, {self.right!r})"

    def __str__(self) -> str:
        return f"({self.left} > {self.right})"

    def evaluate(self, variables: dict[str, Any]) -> Any:
        return evaluate(self.left, variables) > evaluate(self.right, variables)


class Ge(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Gte({self.left!r}, {self.right!r})"

    def __str__(self) -> str:
        return f"({self.left} >= {self.right})"

    def evaluate(self, variables: dict[str, Any]) -> Any:
        return evaluate(self.left, variables) >= evaluate(self.right, variables)


class Lt(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Lt({self.left!r}, {self.right!r})"

    def __str__(self) -> str:
        return f"({self.left} < {self.right})"

    def evaluate(self, variables: dict[str, Any]) -> Any:
        return evaluate(self.left, variables) < evaluate(self.right, variables)


class Le(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Lte({self.left!r}, {self.right!r})"

    def __str__(self) -> str:
        return f"({self.left} <= {self.right})"

    def evaluate(self, variables: dict[str, Any]) -> Any:
        return evaluate(self.left, variables) <= evaluate(self.right, variables)


class Eq(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Eq({self.left!r}, {self.right!r})"

    def __str__(self) -> str:
        return f"({self.left} == {self.right})"

    def evaluate(self, variables: dict[str, Any]) -> Any:
        return evaluate(self.left, variables) == evaluate(self.right, variables)


class Ne(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Ne({self.left!r}, {self.right!r})"

    def __str__(self) -> str:
        return f"({self.left} != {self.right})"

    def evaluate(self, variables: dict[str, Any]) -> Any:
        return evaluate(self.left, variables) != evaluate(self.right, variables)


class And(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"And({self.left!r}, {self.right!r})"

    def __str__(self) -> str:
        return f"({self.left} and {self.right})"

    def evaluate(self, variables: dict[str, Any]) -> Any:
        return evaluate(self.left, variables) and evaluate(self.right, variables)


class Or(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Or({self.left!r}, {self.right!r})"

    def __str__(self) -> str:
        return f"({self.left} or {self.right})"

    def evaluate(self, variables: dict[str, Any]) -> Any:
        return evaluate(self.left, variables) or evaluate(self.right, variables)


class Var(Expr):
    def __init__(self, name):
        if not str.isidentifier(name):
            raise ValueError(f"Invalid variable name: {name}")
        self.name = name

    def __repr__(self):
        return f"Var({self.name!r})"

    def __str__(self) -> str:
        return self.name

    def evaluate(self, variables: dict[str, Any]) -> Any:
        return variables[self.name]


def evaluate(expr: Any, variables: dict[str, Any]) -> Any:
    if isinstance(expr, Expr):
        return expr.evaluate(variables)
    elif isinstance(expr, (str, int, float, bool, type(None))):
        return expr

    raise ValueError(f"Unsupported expr {type(expr)}")


X = Var("x")
