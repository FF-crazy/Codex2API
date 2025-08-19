#!/usr/bin/env python3
"""
获取token的脚本 - 从多个位置按优先级获取token
"""

import json
import os
from pathlib import Path
from typing import Any


def get_auth_file_paths() -> list[Path]:
    """获取认证文件的搜索路径，按优先级排序"""
    paths = []

    # 优先级1: $CHATGPT_LOCAL_HOME/auth.json
    chatgpt_home = os.getenv("CHATGPT_LOCAL_HOME")
    if chatgpt_home:
        paths.append(Path(chatgpt_home) / "auth.json")

    # 优先级2: $CODEX_HOME/auth.json
    codex_home = os.getenv("CODEX_HOME")
    if codex_home:
        paths.append(Path(codex_home) / "auth.json")

    # 优先级3: ~/.chatgpt-local/auth.json (默认路径)
    paths.append(Path.home() / ".chatgpt-local" / "auth.json")

    # 优先级4: ~/.codex/auth.json (备用路径)
    paths.append(Path.home() / ".codex" / "auth.json")

    return paths


def find_auth_files() -> list[tuple[Path, dict[str, Any]]]:
    """查找所有存在的认证文件并返回路径和内容"""
    found_files = []
    paths = get_auth_file_paths()

    for path in paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    found_files.append((path, data))
                    print(f"✅ 找到认证文件: {path}")
            except Exception as e:
                print(f"❌ 读取文件失败 {path}: {e}")

    return found_files


def extract_tokens_from_auth_data(auth_data: dict[str, Any]) -> list[str]:
    """从认证数据中提取所有可能的token"""
    tokens = []

    # 检查OPENAI_API_KEY
    api_key = auth_data.get("OPENAI_API_KEY")
    if api_key and isinstance(api_key, str):
        tokens.append(api_key)

    # 检查tokens字段中的access_token
    tokens_dict = auth_data.get("tokens", {})
    if isinstance(tokens_dict, dict):
        access_token = tokens_dict.get("access_token")
        if access_token and isinstance(access_token, str):
            tokens.append(access_token)

        # 检查id_token
        id_token = tokens_dict.get("id_token")
        if id_token and isinstance(id_token, str):
            tokens.append(id_token)

        # 检查refresh_token
        refresh_token = tokens_dict.get("refresh_token")
        if refresh_token and isinstance(refresh_token, str):
            tokens.append(refresh_token)

    return tokens


def get_all_tokens() -> list[str]:
    """获取所有找到的token，按优先级排序"""
    all_tokens = []
    found_files = find_auth_files()

    if not found_files:
        print("❌ 未找到任何认证文件")
        return []

    print(f"\n📋 处理 {len(found_files)} 个认证文件:")

    for i, (path, auth_data) in enumerate(found_files, 1):
        print(f"\n{i}. 文件: {path}")
        tokens = extract_tokens_from_auth_data(auth_data)

        if tokens:
            print(f"   找到 {len(tokens)} 个token:")
            for j, token in enumerate(tokens, 1):
                # 显示token的前缀和后缀
                if len(token) > 20:
                    display_token = f"{token[:10]}...{token[-10:]}"
                else:
                    display_token = token
                print(f"   {j}. {display_token}")
                all_tokens.append(token)
        else:
            print("   未找到token")

    return all_tokens


def get_default_auth_file_path() -> Path:
    """获取默认的auth.json保存路径"""
    # 按优先级选择保存位置
    chatgpt_home = os.getenv("CHATGPT_LOCAL_HOME")
    if chatgpt_home:
        return Path(chatgpt_home) / "auth.json"

    codex_home = os.getenv("CODEX_HOME")
    if codex_home:
        return Path(codex_home) / "auth.json"

    # 默认使用 ~/.chatgpt-local/auth.json
    return Path.home() / ".chatgpt-local" / "auth.json"


def save_token_to_auth_file(token: str) -> bool:
    """将token保存到auth.json文件"""
    auth_file_path = get_default_auth_file_path()

    # 创建目录（如果不存在）
    auth_file_path.parent.mkdir(parents=True, exist_ok=True)

    # 准备auth数据
    auth_data = {
        "OPENAI_API_KEY": token,
        "tokens": {"access_token": token, "token_type": "Bearer"},
        "created_at": __import__("datetime").datetime.now().isoformat(),
        "source": "get_token.py",
    }

    try:
        # 保存到文件
        with open(auth_file_path, "w", encoding="utf-8") as f:
            json.dump(auth_data, f, indent=2, ensure_ascii=False)

        # 设置文件权限为600 (仅所有者可读写)
        auth_file_path.chmod(0o600)

        print(f"\n💾 Token已保存到: {auth_file_path}")
        return True

    except Exception as e:
        print(f"\n❌ 保存失败: {e}")
        return False


def print_separator(title: str):
    """打印分隔符"""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


def main():
    """主函数"""
    print("🔑 Token获取脚本")
    print("从多个位置按优先级获取token")

    print_separator("搜索路径")
    paths = get_auth_file_paths()
    for i, path in enumerate(paths, 1):
        status = "✅ 存在" if path.exists() else "❌ 不存在"
        print(f"{i}. {path} - {status}")

    print_separator("获取Token")
    all_tokens = get_all_tokens()

    if not all_tokens:
        print("\n❌ 未找到任何token")
        print("\n💡 请确保:")
        print("1. 已完成OAuth认证")
        print("2. 认证文件存在于以下位置之一:")
        for path in paths:
            print(f"   - {path}")
        return

    print_separator("结果")
    print(f"🎉 总共找到 {len(all_tokens)} 个token")

    if len(all_tokens) > 1:
        print(f"\n📌 按优先级，使用最后一个token:")
        last_token = all_tokens[-1]
    else:
        print(f"\n📌 使用找到的token:")
        last_token = all_tokens[0]

    print(f"📋 Token: {last_token}")

    # 保存token到auth.json文件
    save_token_to_auth_file(last_token)

    print(f"\n💡 使用方法:")
    print(f"export OPENAI_API_KEY='{last_token}'")

    print(f"\n📝 或者在代码中使用:")
    print(f"import os")
    print(f'os.environ["OPENAI_API_KEY"] = "{last_token}"')


if __name__ == "__main__":
    main()
