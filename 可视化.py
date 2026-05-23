from pathlib import Path

# from 可视化 import save_graph_diagram
# save_graph_diagram(graph, "记忆检查点.png")

def save_graph_diagram(graph, output_path="graph.png", overwrite=False):
    """
    将 LangGraph 图保存为 PNG 流程图。

    Args:
        graph: 编译后的 LangGraph 图对象
        output_path: 输出文件路径（默认为 "graph.png"）
        overwrite: 是否覆盖已存在的文件
    """
    path = Path(output_path)

    if path.exists() and not overwrite:
        print(f"流程图 {output_path} 已存在。")
        return False

    try:
        png_data = graph.get_graph().draw_mermaid_png()
        with open(path, "wb") as f:
            f.write(png_data)
        print(f"流程图已保存为 {output_path}")
        return True
    except Exception as e:
        print(f"无法生成 PNG 图像：{str(e)}")
        return False