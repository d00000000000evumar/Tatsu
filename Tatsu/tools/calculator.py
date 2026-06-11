"""
Tatsu AI — Calculator Tool
=============================
Safe mathematical evaluation using Python's ast module.
Supports basic arithmetic, percentages, and common math functions.
"""

import ast
import math
import operator
import logging

from tools.base_tool import BaseTool, ToolParameter, ToolResult, RiskLevel

logger = logging.getLogger("tatsu.tools.calculator")

# Safe operators for ast-based evaluation
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Safe math functions available in expressions
SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "pi": math.pi,
    "e": math.e,
    "pow": pow,
    "max": max,
    "min": min,
}


def safe_eval(expression: str) -> float:
    """
    Safely evaluate a mathematical expression using AST parsing.
    Only allows arithmetic operations and whitelisted functions.
    """
    # Pre-process: handle percentage
    expr = expression.replace("%", "/100")
    expr = expr.replace("^", "**")

    # Replace function names
    for name, func in SAFE_FUNCTIONS.items():
        if isinstance(func, (int, float)):
            expr = expr.replace(name, str(func))

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Invalid expression: {e}")

    return _eval_node(tree.body)


def _eval_node(node):
    """Recursively evaluate an AST node."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value}")

    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if op_type == ast.Div and right == 0:
            raise ValueError("Division by zero")
        return SAFE_OPERATORS[op_type](left, right)

    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        return SAFE_OPERATORS[op_type](_eval_node(node.operand))

    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in SAFE_FUNCTIONS and callable(SAFE_FUNCTIONS[func_name]):
                args = [_eval_node(arg) for arg in node.args]
                return SAFE_FUNCTIONS[func_name](*args)
            raise ValueError(f"Unknown function: {func_name}")
        raise ValueError("Complex function calls not supported")

    elif isinstance(node, ast.Name):
        if node.id in SAFE_FUNCTIONS:
            val = SAFE_FUNCTIONS[node.id]
            if isinstance(val, (int, float)):
                return val
        raise ValueError(f"Unknown variable: {node.id}")

    else:
        raise ValueError(f"Unsupported expression type: {type(node).__name__}")


class CalculatorTool(BaseTool):
    """Calculator tool for mathematical computations."""

    name = "calculator"
    description = (
        "Evaluate mathematical expressions. Supports arithmetic (+, -, *, /, ^, %), "
        "functions (sqrt, sin, cos, tan, log, abs, round, ceil, floor), "
        "and constants (pi, e). Use this for any math calculation."
    )
    parameters = [
        ToolParameter(
            name="expression",
            type="string",
            description="The mathematical expression to evaluate, e.g., '(245 * 18.7) + sqrt(144)'",
        ),
    ]
    requires_confirmation = False
    risk_level = RiskLevel.LOW

    async def execute(self, expression: str, **kwargs) -> ToolResult:
        """Evaluate a mathematical expression safely."""
        try:
            result = safe_eval(expression)

            # Format nicely
            if isinstance(result, float) and result == int(result):
                formatted = str(int(result))
            elif isinstance(result, float):
                formatted = f"{result:.10g}"
            else:
                formatted = str(result)

            return ToolResult(
                success=True,
                output=f"{expression} = {formatted}",
                data={"expression": expression, "result": result},
            )

        except ValueError as e:
            return ToolResult(
                success=False,
                output=f"Cannot evaluate: {expression}",
                error=str(e),
            )
        except Exception as e:
            logger.exception(f"Calculator error: {e}")
            return ToolResult(
                success=False,
                output=f"Calculation failed: {expression}",
                error=str(e),
            )
