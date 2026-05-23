from langchain_core.tools import tool


@tool
def calculator(a: int, b: int, op: str) -> int:
    """
    这是一个计算器工具，支持加法、减法和乘法运算

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
