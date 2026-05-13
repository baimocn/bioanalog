"""
test_skills.py — 验证 SciAgentSkillIndexer 技能检索功能
用法: cd backend && python test_skills.py
"""

import sys
import os

# Windows 控制台 UTF-8 输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 确保能导入 app 模块
sys.path.insert(0, os.path.dirname(__file__))

from app import skill_indexer


def test_registry_loaded():
    """测试注册表是否成功加载"""
    count = len(skill_indexer.skills)
    print(f"[1] 注册表加载: {count} 个技能")
    ok = count > 0
    print(f"    {'✓' if ok else '✗'} 通过\n")
    return ok


def test_skill_retrieval():
    """测试技能检索：输入关键词应返回相关技能"""
    queries = [
        ("土壤有机碳分解", "应匹配 soil/carbon 相关技能"),
        ("单细胞 RNA-seq 分析", "应匹配 scanpy-scrna-seq"),
        ("统计分析 假设检验", "应匹配 statistical-analysis"),
        ("分子对接 docking", "应匹配 autodock-vina-docking"),
        ("数据可视化 画图", "应匹配 matplotlib 相关技能"),
    ]
    print("[2] 技能检索测试:")
    all_pass = True
    for query, expect in queries:
        results = skill_indexer.retrieve_relevant_skills(query, top_k=2)
        names = [r["name"] for r in results]
        status = "✓" if results else "✗"
        print(f"    {status} 查询: \"{query}\"")
        print(f"      期望: {expect}")
        print(f"      结果: {names}")
        if not results:
            all_pass = False
    print()
    return all_pass


def test_skill_content():
    """测试技能内容读取：检索到的技能应能读取 SKILL.md"""
    print("[3] 技能内容读取测试:")
    results = skill_indexer.retrieve_relevant_skills("RNA-seq 分析", top_k=1)
    if not results:
        print("    ✗ 未检索到技能，跳过内容测试\n")
        return False
    skill = results[0]
    content = skill_indexer.get_skill_content(skill)
    has_content = len(content) > 50
    status = "✓" if has_content else "✗"
    print(f"    {status} 技能: {skill['name']}")
    print(f"      路径: {skill['path']}")
    print(f"      内容长度: {len(content)} 字符")
    if has_content:
        preview = content[:120].replace("\n", " ")
        print(f"      预览: {preview}...")
    print()
    return has_content


def test_empty_query():
    """测试空查询 / 纯停用词查询"""
    print("[4] 边界情况测试:")
    r1 = skill_indexer.retrieve_relevant_skills("", top_k=3)
    r2 = skill_indexer.retrieve_relevant_skills("的 了 是 在", top_k=3)
    ok = len(r1) == 0 and len(r2) == 0
    status = "✓" if ok else "✗"
    print(f"    {status} 空查询返回 {len(r1)} 结果，停用词查询返回 {len(r2)} 结果")
    print()
    return ok


if __name__ == "__main__":
    print("=" * 50)
    print("SciAgentSkillIndexer 测试")
    print("=" * 50 + "\n")

    results = []
    results.append(("注册表加载", test_registry_loaded()))
    results.append(("技能检索", test_skill_retrieval()))
    results.append(("内容读取", test_skill_content()))
    results.append(("边界情况", test_empty_query()))

    print("=" * 50)
    print("测试结果汇总:")
    for name, passed in results:
        print(f"  {'✓' if passed else '✗'} {name}")
    total = sum(1 for _, p in results if p)
    print(f"\n通过: {total}/{len(results)}")
    print("=" * 50)
