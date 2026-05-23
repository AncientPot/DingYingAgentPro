import json
import sqlite3
import uuid
from dotenv import load_dotenv
from typing import Annotated
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessageChunk, ToolMessage, AIMessage
from langchain_tavily import TavilySearch
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, add_messages
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import Optional
from langchain_core.tools import tool
import os
import time
import subprocess
import win32gui
import win32process
from pywinauto import Application

load_dotenv()

# 状态
class State(TypedDict):
    messages: Annotated[list[BaseMessage],add_messages]

# 工具



def get_pid_by_window_class(exe_path: str, class_name: str, wait_time: int = 7) -> int:
    """通过窗口类名获取进程 PID，若程序未运行则启动它。"""
    hwnd = None

    def enum_callback(found_hwnd, extra):
        nonlocal hwnd
        if hwnd is None and win32gui.IsWindowVisible(found_hwnd) and win32gui.GetParent(found_hwnd) == 0:
            try:
                if win32gui.GetClassName(found_hwnd) == class_name:
                    hwnd = found_hwnd
                    return False  # 停止枚举
            except:
                pass
        return True

    win32gui.EnumWindows(enum_callback, None)

    if not hwnd:
        if os.path.exists(exe_path):
            subprocess.Popen(exe_path)
            time.sleep(wait_time)
            win32gui.EnumWindows(enum_callback, None)
        else:
            raise FileNotFoundError(f"程序路径错误: {exe_path}")

    if not hwnd:
        raise RuntimeError("未找到目标窗口，首次启动可能需要重试。")

    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return pid
    except Exception as e:
        raise RuntimeError(f"获取PID失败: {e}")


@tool
def control_netease_cloud_music(operation: str, song_name: Optional[str] = None) -> str:
    """
    控制本地网易云音乐客户端。
    支持的操作有: 'play_pause', 'next', 'previous', 'search_and_play', 'like', 'unlike', 'play_liked', 'switch_mode'。
    对于 'search_and_play' 操作，必须提供 song_name 参数。
    如果用户要求切换到指定模式，若首次切换未成功，请自动重试调用工具，直至切换成功或达到最大尝试次数。

    Args:
        operation (str): 要执行的操作。
        song_name (str, optional): 当 operation 为 'search_and_play' 时，需要搜索的歌曲名称。

    Returns:
        str: 操作执行后的结果描述。
    """
    # 配置网易云音乐路径（请根据实际路径修改）
    exe_path = r"D:\CloudMusic\cloudmusic.exe"
    CLASS_NAME = "OrpheusBrowserHost"

    try:
        pid = get_pid_by_window_class(exe_path, CLASS_NAME)
        app = Application(backend="uia").connect(process=pid)
        dlg = app.window(class_name=CLASS_NAME)

        if operation == "play_pause":
            dlg.wait('exists', timeout=1.0)
            play = dlg.child_window(auto_id="btn_pc_minibar_play", control_type="Button")
            play.invoke()
            return "已执行播放/暂停操作。"

        elif operation == "next":
            dlg.wait('exists', timeout=1.0)
            next_button = dlg.child_window(title="next", control_type="Button")
            next_button.invoke()
            return "已切换到下一首。"

        elif operation == "previous":
            dlg.wait('exists', timeout=1.0)
            prev_button = dlg.child_window(title="pre", control_type="Button")
            prev_button.invoke()
            return "已切换到上一首。"

        elif operation == "search_and_play":
            if not song_name:
                return "搜索并播放操作需要提供 'song_name' 参数。"
            dlg.wait('exists', timeout=1.0)
            edit = dlg.child_window(control_type="Edit", found_index=0)
            edit.type_keys("^a{BACKSPACE}" + song_name + "{ENTER}", with_spaces=True)
            time.sleep(1.5)  # 等待搜索结果加载
            dlg.wait('exists', timeout=2.0)
            play_button = dlg.child_window(title="play 播放", control_type="Button")
            play_button.invoke()
            return f"已搜索并播放歌曲: {song_name}。"

        elif operation == "like":
            dlg.wait('exists', timeout=1.0)
            like_btn = dlg.child_window(title_re=r"^like_number\s.*", control_type="Button")
            like_btn.invoke()
            return "已将当前歌曲添加到“我喜欢的音乐”。"

        elif operation == "unlike":
            dlg.wait('exists', timeout=1.0)
            not_like_btn = dlg.child_window(title_re=r"^likenumber_red\s.*", control_type="Button")
            not_like_btn.invoke()
            return "已将当前歌曲从“我喜欢的音乐”中移除。"

        elif operation == "play_liked":
            dlg.wait('exists', timeout=1.0)
            my_like = dlg.child_window(
                title="sidebar_like 我喜欢的音乐 sidebar_heartbeat",
                control_type="Group"
            )
            my_like.invoke()
            time.sleep(0.5)
            dlg.wait('exists', timeout=1.0)
            play_like = dlg.child_window(
                title="play 播放全部",
                control_type="Button"
            )
            play_like.invoke()
            return "正在播放“我喜欢的音乐”列表。"

        elif operation == "switch_mode":
            dlg.wait('exists', timeout=1.0)
            switch_btn = dlg.child_window(
                title_re=r"^(singleloop|loop|order|shuffle|infinite|heartbeat)$",
                control_type="Button",
            )
            current_title = switch_btn.window_text()
            switch_btn.invoke()

            mode_mapping = {
                "singleloop": "单曲循环",
                "loop": "列表循环",
                "order": "顺序播放",
                "shuffle": "随机播放",
                "infinite": "无限循环",
                "heartbeat": "心动模式"
            }
            new_mode_title = switch_btn.window_text()
            new_mode = mode_mapping.get(new_mode_title, "未知模式")
            old_mode = mode_mapping.get(current_title, "未知模式")
            return f"播放模式已从 '{old_mode}' 切换为 '{new_mode}'。"

        else:
            return (
                f"不支持的操作: {operation}。"
                "支持的操作有: play_pause, next, previous, search_and_play, like, unlike, play_liked, switch_mode。"
            )

    except Exception as e:
        error_msg = str(e)
        if "未找到目标窗口" in error_msg or "首次启动" in error_msg:
            return "网易云音乐正在启动中，请稍后再试，或再次调用本工具。"
        return f"操作执行失败: {error_msg}"



@tool
def calculator(a: int, b: int, op: str):
    """
    这是一个计算器工具，支持加法、减法和乘法运算

    参数:
    - a: 第一个整数
    - b: 第二个整数
    - operation: 运算类型，可选值为 "add"（加法）、"subtract"（减法）、"multiply"（乘法）

    返回:
    - 计算结果
    """
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y
    }
    if op not in operations:
        raise ValueError(f"不支持的操作: {op}")
    return operations[op](a, b)
search = TavilySearch(max_results=2)
tools = [search,calculator,control_netease_cloud_music]

# 模型
llm = ChatDeepSeek(model="deepseek-chat")

# 智能体
def dingyingagent(state: State) -> State:
    """这个节点负责设定系统提示词并对用户的输入进行回应"""
    system_prompt = SystemMessage(content =
        "你是一个AI助手，请尽你所能回答我的问题。"
    )
    llm_with_tools = llm.bind_tools(tools)
    response = llm_with_tools.invoke([system_prompt] + state["messages"])
    return {"messages": [response]}

# 构建图
graph_builder = StateGraph(State)
tool_node = ToolNode(tools=tools)
graph_builder.add_node("Agent", dingyingagent)
graph_builder.add_node("tools", tool_node)


graph_builder.add_conditional_edges(
    "Agent",
    tools_condition,
)
graph_builder.add_edge("tools", "Agent")
graph_builder.add_edge(START, "Agent")
conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)
memory.setup()
graph = graph_builder.compile(checkpointer=memory)



# 流式传输
def stream(human_message, mode, config=None):
    """
    会话传输显示
    mode = messages为流式传输模式
    mode = values为非流式传输模式
    """
    responses = graph.stream(human_message, stream_mode=mode, config=config)
    total_tokens = 0
    if mode == "values":
        for r in responses:
            message = r["messages"][-1]
            if isinstance(message, AIMessage):
                print(f"AI：{message.content}")
                if hasattr(message, 'usage_metadata') and message.usage_metadata:
                    total_tokens += message.usage_metadata.get("total_tokens", 0)
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    for call in message.tool_calls:
                        tool_name = call["name"]
                        args = call["args"]
                        print(f"调用工具: {tool_name}，传入参数: {args}", end='')
            if isinstance(message, ToolMessage):
                print(f",工具返回信息: {message.content}")
    elif mode == "messages":
        print("AI: ",end="")
        for r in responses:
            message = r[0]
            if isinstance(message, AIMessageChunk):
                print(message.content, end="", flush=True)
            if hasattr(message, 'usage_metadata') and message.usage_metadata:
                total_tokens += message.usage_metadata["total_tokens"]
            if isinstance(message, ToolMessage):
                recall = message.content
                name = message.name
                print(f"\n【调用工具: {name}；工具返回信息: {recall}】")
                print("AI: ",end="")
    print(f"\n【总消耗 Token: {total_tokens}】")



def load_sessions(database, session_map_file):
    """
    数据库和json的预加载函数。
    内存中维护三个表：
    数据库ID表：db_tids
    JSON映射表：session_name_to_tid
    会话名称表：session_names
    """

    # 数据库加载
    print("正在加载已有会话...")
    create_db_tids = set()
    for checkpoint_tuple in database.list(None):
        tid = checkpoint_tuple.config["configurable"]["thread_id"]
        create_db_tids.add(tid)
    # JSON 加载
    name_to_tid = {}
    if os.path.exists(session_map_file):
        with open(session_map_file, "r", encoding="utf-8") as f:
            name_to_tid = json.load(f)
    all_session_names = list(name_to_tid.keys())
    return name_to_tid, all_session_names, create_db_tids



def sync_database_and_json(database, name_to_tid, create_db_tids, session_map_file):
    """同步数据库与 JSON 会话映射，确保两者一致"""
    json_tids = set(name_to_tid.values())
    if create_db_tids > json_tids:
        orphan_tids = create_db_tids - json_tids
        for tid in orphan_tids:
            database.delete_thread(tid)
    elif create_db_tids < json_tids:
        orphan_tids = json_tids - create_db_tids
        for tid in orphan_tids:
            name_to_remove = next(k for k, v in name_to_tid.items() if v == tid)
            del name_to_tid[name_to_remove]
        with open(session_map_file, "w", encoding="utf-8") as f:
            json.dump(name_to_tid, f, ensure_ascii=False, indent=2)
    else:
        pass



def show_sessions(all_session_names, need_db_tids):
    """展示会话列表"""
    if need_db_tids:
        print("已有会话:")
        for i, session_name in enumerate(sorted(all_session_names), 1):
            print(f"  {i}. {session_name}")
    else:
        print("暂无历史会话。")



def select_or_create_session(update_db_tids,name_to_tid, session_namespace, session_map_file):
    """选择会话，返回当前的会话名和会话配置(ID)"""
    select_tid = None

    while True:
        print("请选择会话（输入不存在的会话名称会自动创建新会话）: ")
        select_inter_session_name = input(">>> ").strip()

        if not select_inter_session_name:
            print("会话名称不能为空。")
            continue
        elif select_inter_session_name in name_to_tid:
            select_tid = name_to_tid[select_inter_session_name]
            print(f"使用已有会话: {select_inter_session_name}。")
            break
        else:
            # 创建新会话
            select_tid = str(uuid.uuid5(session_namespace, select_inter_session_name))
            update_db_tids.add(select_tid)
            # 更新 json
            name_to_tid[select_inter_session_name] = select_tid
            with open(session_map_file, "w", encoding="utf-8") as fo:
                json.dump(name_to_tid, fo, ensure_ascii=False, indent=2)
            print(f"创建新会话: {select_inter_session_name}。")
            break

    select_name = select_inter_session_name
    config = {"configurable": {"thread_id": select_tid}}
    return config,select_name



def delete_session(delete_name, database, database_tids, name_to_tid, all_session_names, session_map_file):
    """删除会话"""
    delete_tid = name_to_tid[delete_name]
    database.delete_thread(delete_tid)
    database_tids.remove(delete_tid)
    # 更新json
    all_session_names.remove(delete_name)
    del delete_tid
    with open(session_map_file, "w", encoding="utf-8") as f:
        json.dump(name_to_tid, f, ensure_ascii=False, indent=2)
    print(f"会话 '{delete_name}' 已删除")





SESSION_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")
SESSION_MAP_FILE = "sessions.json"

# 会话初始化
session_name_to_tid, session_names, db_tids = load_sessions(memory, SESSION_MAP_FILE)

# 数据一致性检验
sync_database_and_json(memory, session_name_to_tid, db_tids, SESSION_MAP_FILE)

# 会话显示
show_sessions(session_names, db_tids)

# 会话选择
thread_config,current_name = select_or_create_session(db_tids,session_name_to_tid, SESSION_NAMESPACE, SESSION_MAP_FILE)

# 开始多轮会话
print("输入 /delete <会话ID> 删除指定会话，/exit 退出\n开始会话：")
user_input = input("USER: ")
while user_input != "/exit":
    if user_input.startswith("/delete"):
        parts = user_input.split(maxsplit=1)
        if len(parts) < 2:
            print("请按要求输入/delete+空格+会话ID")
        else:
            need_delete_name = parts[1].strip()
            # 删除会话
            delete_session(need_delete_name, memory, db_tids, session_name_to_tid, session_names, SESSION_MAP_FILE)
            # 数据一致性检验
            sync_database_and_json(memory, session_name_to_tid, db_tids, SESSION_MAP_FILE)
            # 删除会话后重新显示现在的会话列表
            show_sessions(session_names, db_tids)
            # 如果删除的是当前的会话，则要求重新选择会话
            if need_delete_name == current_name:
                thread_config, current_name = select_or_create_session(db_tids,session_name_to_tid, SESSION_NAMESPACE,SESSION_MAP_FILE)
    # 核心会话逻辑
    else:
        input_state = {"messages": [HumanMessage(content=user_input)]}
        stream(input_state, "messages", config=thread_config)
    user_input = input("USER: ")
    if user_input == "/exit":
        sync_database_and_json(memory, session_name_to_tid, db_tids, SESSION_MAP_FILE)
# 退出前关闭连接
conn.close()
