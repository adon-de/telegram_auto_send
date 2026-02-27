import os
import requests
import sys

# -----------------------------------------------------------------------------
# 👇👇👇 用户配置区域 (请在这里直接修改) 👇👇👇
# -----------------------------------------------------------------------------

# 1. 批量发送列表 (推荐)
# 在下面的三引号中直接填写发送任务，每行一个。
# 格式: 目标  空格  消息内容
# 如果这里填了内容，环境变量 TG_SEND_LIST 将会被忽略。
MANUAL_SEND_LIST = """
# 示例 (去掉前面的 # 号即可生效):
# @username1  你好，这是一条测试消息
# -100123456789  这是发给群组的消息
# +8613800000000  这是发给手机号的消息
"""

# 2. 单一目标发送 (备用)
# 如果上面的 MANUAL_SEND_LIST 为空，可以在这里填写单一目标和消息。
# 如果这里也为空，则尝试读取环境变量 TG_TARGET 和 TG_MESSAGE。
MANUAL_TARGET = ""   # 例如: "@username" 或 "-100123456"
MANUAL_MESSAGE = ""  # 例如: "你好，世界"

# 3. TG 服务地址
# 默认使用 Docker 内部网络地址。如果脚本在容器外运行，请改为 "http://127.0.0.1:8080/api/call"
TG_SERVICE_URL = os.getenv("TG_SERVICE_URL", "http://tg-service:8080/api/call")


# -----------------------------------------------------------------------------
# 环境变量配置 (通常不需要修改，除非你在青龙面板中使用环境变量)
# -----------------------------------------------------------------------------
ENV_TARGET_KEY = "TG_TARGET"
ENV_MESSAGE_KEY = "TG_MESSAGE"
ENV_SEND_LIST_KEY = "TG_SEND_LIST"

def send_telegram_message(target, message):
    """
    调用 Docker 内部的 TG 服务发送消息
    :param target: 目标 (用户名/ID)
    :param message: 消息内容
    """
    if not target or not message:
        print("❌ 错误: 目标(target)或消息(message)为空")
        return False

    payload = {
        "method": "send_message",
        "params": {
            "entity": target,
            "message": message
        }
    }

    try:
        # 如果 target 是纯数字字符串，尝试转换为整数 (Telethon 对 ID 的要求)
        # 但如果是用户名 (@开头) 或手机号 (+开头)，则保持字符串
        final_target = target
        if isinstance(target, str):
             if target.isdigit() or (target.startswith("-") and target[1:].isdigit()):
                 try:
                     final_target = int(target)
                     payload["params"]["entity"] = final_target
                 except ValueError:
                     pass

        print(f"⏳ 正在向 {final_target} 发送消息...")

        response = requests.post(TG_SERVICE_URL, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                print(f"✅ 发送成功 -> {final_target}")
                return True
            else:
                print(f"❌ 发送失败 -> {final_target}: {result.get('error')}")
                return False
        else:
            print(f"❌ HTTP 请求失败: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败: 无法连接到 TG 服务 ({TG_SERVICE_URL})")
        return False
    except Exception as e:
        print(f"❌ 发生异常: {str(e)}")
        return False

def parse_send_list(raw_list):
    """
    解析多行配置字符串
    每行格式: 目标  消息内容
    """
    tasks = []
    if not raw_list:
        return tasks
    
    # 去除首尾的空白字符和注释行（针对 MANUAL_SEND_LIST）
    lines = []
    for line in raw_list.splitlines():
        line = line.strip()
        # 跳过空行和以 # 开头的注释行
        if not line or line.startswith("#"):
            continue
        lines.append(line)

    for line in lines:
        # 使用 split(None, 1) 只分割第一个空格，保留后续空格作为消息一部分
        parts = line.split(None, 1)
        if len(parts) >= 2:
            target, msg = parts[0], parts[1]
            tasks.append((target, msg))
        elif len(parts) == 1:
            # 只有目标没有消息，尝试使用默认消息
            # 优先使用手动配置的默认消息，其次是环境变量
            default_msg = MANUAL_MESSAGE if MANUAL_MESSAGE else os.getenv(ENV_MESSAGE_KEY)
            if default_msg:
                tasks.append((parts[0], default_msg))
            else:
                print(f"⚠️ 跳过无效行 (缺少消息且无默认消息): {line}")
    return tasks

def main():
    # 1. 尝试获取批量发送列表 (优先使用手动配置)
    # 如果 MANUAL_SEND_LIST 有有效内容，优先使用它
    send_list_raw = MANUAL_SEND_LIST if MANUAL_SEND_LIST and MANUAL_SEND_LIST.strip() else os.getenv(ENV_SEND_LIST_KEY)
    tasks = parse_send_list(send_list_raw)

    # 2. 如果没有批量列表，尝试使用单/多目标配置 (优先手动配置)
    if not tasks:
        # 优先读取手动配置
        target_raw = MANUAL_TARGET if MANUAL_TARGET else os.getenv(ENV_TARGET_KEY)
        default_message = MANUAL_MESSAGE if MANUAL_MESSAGE else os.getenv(ENV_MESSAGE_KEY)

        if target_raw and default_message:
            # 支持旧格式的多目标 (逗号或换行分隔)，但共用同一条消息
            targets = [t.strip() for t in target_raw.replace(",", "\n").splitlines() if t.strip()]
            for t in targets:
                tasks.append((t, default_message))
        elif len(sys.argv) > 2:
            # 命令行参数支持
            tasks.append((sys.argv[1], sys.argv[2]))

    # 3. 执行发送任务
    if not tasks:
        print("⚠️ 警告: 未找到有效的发送任务配置")
        print("请在脚本开头的 '用户配置区域' 填写配置，或者设置环境变量。")
        return

    print(f"📋 共解析到 {len(tasks)} 个发送任务")
    success_count = 0
    
    for target, message in tasks:
        if send_telegram_message(target, message):
            success_count += 1
            
    print(f"\n🎉 任务完成: 成功 {success_count}/{len(tasks)}")

if __name__ == "__main__":
    main()
