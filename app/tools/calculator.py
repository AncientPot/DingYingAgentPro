"""计算器工具 —— 支持加、减、乘法运算。"""

from langchain_core.tools import tool


@tool
def calculator(a: int, b: int, op: str) -> int:
    """
    计算器工具，支持加法、减法和乘法运算。

    参数:
    - a: 第一个整数
    - b: 第二个整数
    - op: 运算类型，可选值为 "add"（加法）、"subtract"（减法）、"multiply"（乘法）

    返回:
    - 计算结果
    """
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
    }
    if op not in operations:
        raise ValueError(f"不支持的操作: {op}")
    return operations[op](a, b)


def get_tool():
    """返回 calculator 工具实例。"""
    return calculator


def test_tool() -> dict:
    """自检：执行基本运算验证工具可用。"""
    try:
        r1 = calculator.invoke({"a": 3, "b": 4, "op": "add"})
        r2 = calculator.invoke({"a": 10, "b": 3, "op": "subtract"})
        r3 = calculator.invoke({"a": 3, "b": 3, "op": "multiply"})
        assert str(r1) == "7" and str(r2) == "7" and str(r3) == "9", f"unexpected: {r1}, {r2}, {r3}"
        return {"ok": True, "message": "计算器工具正常（加/减/乘法测试通过）", "details": "3+4=7 10-3=7 3*3=9"}
    except Exception as e:
        return {"ok": False, "message": f"计算器自检失败: {e}", "details": str(e)}
