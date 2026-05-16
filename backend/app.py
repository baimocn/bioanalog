"""
BioAnalogy — Flask 后端
提供 /api/chat 接口，代理小米 MIMO 2.5 Pro API
集成 SciAgent-Skills 动态技能检索
"""

import os
import json
import math
import requests
import yaml
from pathlib import Path
from typing import List, Dict
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)
CORS(app)

# ---- 配置 ----
BASE_DIR = os.path.dirname(__file__)
PERSONA_PATH = os.path.join(BASE_DIR, "persona.json")
MIMO_API_KEY = os.environ.get("MIMO_API_KEY", "")
MIMO_API_URL = os.environ.get("MIMO_API_URL", "https://api.xiaomimimo.com/v1/chat/completions")
MIMO_MODEL = os.environ.get("MIMO_MODEL", "mimo-v2.5-pro")


# ============================================================
# SciAgentSkillIndexer — 基于注册表的技能检索引擎
# ============================================================

class SciAgentSkillIndexer:
    """加载 skills_library/registry.yaml，提供关键词检索和内容读取"""

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(__file__), "skills_library")
        self.base_dir = Path(base_dir)
        self.registry_path = self.base_dir / "registry.yaml"
        self.registry = self._load_registry()
        self.skills = self._build_index()
        # BM25 参数与文档统计
        self._k1 = 1.5
        self._b = 0.75
        self._doc_texts = []
        self._doc_len = []
        self._avgdl = 0.0
        self._df = {}  # term -> 出现该 term 的文档数
        self._build_bm25_stats()

    def _load_registry(self) -> Dict:
        """加载 registry.yaml 注册表"""
        if not self.registry_path.exists():
            print(f"[SciAgent] 注册表不存在: {self.registry_path}")
            return {"entries": []}
        with open(self.registry_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {"entries": []}
        # 兼容 "entries" 和 "skills" 两种键名
        if "entries" in data:
            data["skills"] = data.pop("entries")
        return data

    def _build_index(self) -> List[Dict]:
        """构建技能索引，解析每个技能的名称、描述、文件路径"""
        index = []
        for entry in self.registry.get("skills", []):
            rel_path = entry.get("path", "")
            full_path = self.base_dir / rel_path
            if not full_path.exists():
                # 尝试去掉前缀 skills/
                alt = rel_path.replace("skills/", "", 1) if rel_path.startswith("skills/") else rel_path
                full_path = self.base_dir / "skills" / alt
            index.append({
                "name": entry.get("name", ""),
                "description": entry.get("description", ""),
                "category": entry.get("category", ""),
                "type": entry.get("type", ""),
                "path": full_path,
            })
        print(f"[SciAgent] 已加载 {len(index)} 个技能")
        return index

    def _build_bm25_stats(self):
        """预计算 BM25 所需的文档统计信息"""
        for skill in self.skills:
            text = (skill["name"] + " " + skill["description"] + " " + skill["category"]).lower()
            tokens = list(self._tokenize(text))
            self._doc_texts.append(tokens)
            self._doc_len.append(len(tokens))
            for t in set(tokens):
                self._df[t] = self._df.get(t, 0) + 1
        total_len = sum(self._doc_len)
        self._avgdl = total_len / len(self._doc_texts) if self._doc_texts else 1.0

    # 中英文同义词映射：中文关键词 → 英文关键词
    _SYNONYMS = {
        "土壤": "soil", "碳": "carbon", "有机": "organic", "分解": "decomposition",
        "微生物": "microb", "酶": "enzyme", "消化": "digest",
        "肾脏": "renal", "肾": "kidney", "湿地": "wetland", "过滤": "filter",
        "净化": "purif", "重吸收": "reabsorb", "泌尿": "urin",
        "呼吸": "respir", "肺": "lung", "气孔": "stomat", "碳平衡": "carbon",
        "气体": "gas", "交换": "exchange", "通量": "flux",
        "统计": "statist", "假设检验": "hypothes", "回归": "regress",
        "可视化": "visual", "画图": "plot", "图表": "chart", "绘图": "plot",
        "机器学习": "machine-learn", "深度学习": "deep-learn",
        "基因": "genom", "转录": "transcript", "蛋白": "protein",
        "分子": "molecular", "细胞": "cell", "序列": "sequence",
        "对接": "dock", "药物": "drug", "筛选": "screen",
        "单细胞": "single-cell", "聚类": "cluster", "降维": "dimension",
        "差异表达": "differential", "富集": "enrichment",
        "系统生物学": "systems-biology", "代谢": "metabol",
        "结构": "structur", "动力学": "kinet", "模型": "model",
        "分析": "analys", "数据": "data", "实验": "lab",
        "文献": "literature", "写作": "writing",
    }

    def _tokenize(self, query: str) -> set:
        """中英文混合分词：空格切分 + 中文同义词扩展"""
        stopwords = {
            "the", "a", "an", "is", "are", "to", "for", "of", "and", "in",
            "on", "at", "with", "by", "it", "this", "that", "can", "how",
            "what", "why", "please", "you", "i", "me", "my", "do", "does",
            "的", "了", "是", "在", "我", "你", "他", "她", "它", "们",
            "和", "与", "对", "请", "怎么", "什么", "为什么", "如何", "可以",
            "吗", "呢", "啊", "吧", "把", "被", "从", "到", "用", "有",
            "一个", "一些", "这个", "那个", "比较", "以及", "或者",
        }
        tokens = set(query.lower().split())
        tokens = {t.strip("？?，,。.!！;；：:（）()") for t in tokens
                  if t.strip("？?，,。.!！;；：:（）()")}
        tokens -= stopwords
        # 中文同义词扩展：将匹配的中文词转为英文关键词
        expanded = set(tokens)
        for token in list(tokens):
            for zh, en in self._SYNONYMS.items():
                if zh in token:
                    expanded.add(en)
        return expanded

    def _bm25_score(self, query_tokens: set, doc_idx: int) -> float:
        """计算单个文档的 BM25 分数"""
        doc = self._doc_texts[doc_idx]
        dl = self._doc_len[doc_idx]
        n = len(self._doc_texts)
        score = 0.0
        # 统计 term 在文档中的出现次数
        tf_map = {}
        for t in doc:
            if t in query_tokens:
                tf_map[t] = tf_map.get(t, 0) + 1
        for term, tf in tf_map.items():
            df = self._df.get(term, 0)
            idf = math.log((n - df + 0.5) / (df + 0.5) + 1.0)
            tf_norm = (tf * (self._k1 + 1)) / (tf + self._k1 * (1 - self._b + self._b * dl / self._avgdl))
            score += idf * tf_norm
        return score

    def retrieve_relevant_skills(self, query: str, top_k: int = 1) -> List[Dict]:
        """基于 BM25 排序检索最相关的技能（支持中英文）"""
        keywords = self._tokenize(query)
        if not keywords:
            return []

        scored = []
        for i in range(len(self.skills)):
            score = self._bm25_score(keywords, i)
            if score > 0:
                scored.append((score, self.skills[i]))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:top_k]]

    def get_skill_content(self, skill: Dict) -> str:
        """读取 SKILL.md 完整内容"""
        try:
            path = skill["path"]
            if path.exists():
                return path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[SciAgent] 读取技能失败: {skill.get('name')} — {e}")
        return ""


# 全局初始化（模块加载时执行一次）
skill_indexer = SciAgentSkillIndexer()


# ---- 辅助函数 ----

def load_persona() -> Dict:
    """读取人格设定文件"""
    try:
        with open(PERSONA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARNING] persona.json 加载失败: {e}")
        return {"system_prompt": "你是一个学术研究助手，请用中文回答问题。"}


# ---- 路由 ----

MAX_HISTORY = 20  # 最多保留的历史消息条数


def _parse_chat_request(body):
    """解析聊天请求，返回 (user_message, history, context) 或错误响应"""
    context = body.get("context", {})
    history = body.get("messages")

    if history and isinstance(history, list):
        user_message = ""
        for msg in reversed(history):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        history = [m for m in history if m.get("role") in ("user", "assistant")]
        history = history[-MAX_HISTORY:]
    else:
        user_message = body.get("message", "")
        if not user_message:
            return None, None, None, (jsonify({
                "error": True,
                "reply": "请求格式错误：需要 message 或 messages 字段。"
            }), 400)

    return user_message, history, context, None


def _build_full_messages(user_message, history, context):
    """构建发送给 MIMO API 的完整 messages 数组，返回 (full_messages, skill_names)"""
    relevant_skills = skill_indexer.retrieve_relevant_skills(user_message, top_k=1)
    skill_names = [s["name"] for s in relevant_skills]

    skill_context = ""
    for skill in relevant_skills:
        content = skill_indexer.get_skill_content(skill)
        if content:
            skill_context += f"\n\n## {skill['name']}\n{content}\n"

    persona = load_persona()
    system_content = persona.get("system_prompt_template", "") or persona.get("system_prompt", "")

    if skill_context:
        system_content += (
            "\n\n【专家技能参考】\n"
            "以下是与用户问题相关的专业技能知识，请优先参考它们来回答：\n"
            + skill_context
        )

    # 强制引用格式要求
    system_content += (
        "\n\n【引用与准确性要求】\n"
        "1. 回答中涉及专业知识时，必须在相关段落末尾标注来源，格式为：[来源: 技能名称]\n"
        "2. 如果引用了专家技能参考中的内容，标注对应的技能名称\n"
        "3. 如果是基于你的通识知识回答，标注 [来源: 通识知识]\n"
        "4. 对于不确定的信息，必须明确标注 [待验证]，不要编造数据或文献\n"
        "5. 涉及具体数值、公式、实验参数时，务必谨慎，宁可说\"不确定\"也不要给出错误数据"
    )

    ctx_parts = []
    if context.get("topic"):
        ctx_parts.append(f"当前话题板块: {context['topic']}")
    if context.get("page"):
        ctx_parts.append(f"当前页面: {context['page']}")
    if ctx_parts:
        system_content += "\n\n[用户上下文]\n" + "\n".join(ctx_parts)

    if history:
        full_messages = [{"role": "system", "content": system_content}] + history
    else:
        full_messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_message},
        ]

    return full_messages, skill_names


@app.route("/api/chat", methods=["POST"])
def chat():
    """AI 聊天接口（非流式），支持多轮对话历史"""
    if not MIMO_API_KEY:
        return jsonify({"error": True, "reply": "AI 服务未配置：环境变量 MIMO_API_KEY 缺失。"}), 503

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": True, "reply": "请求格式错误：需要 JSON body。"}), 400

    user_message, history, context, err = _parse_chat_request(body)
    if err:
        return err

    full_messages, _ = _build_full_messages(user_message, history, context)

    try:
        resp = requests.post(
            MIMO_API_URL,
            headers={"api-key": MIMO_API_KEY, "Content-Type": "application/json"},
            json={
                "model": MIMO_MODEL,
                "messages": full_messages,
                "max_completion_tokens": 2048,
                "temperature": 1.0,
                "top_p": 0.95,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
        reply = msg.get("content") or msg.get("reasoning_content") or "未收到有效回复。"
        return jsonify({"reply": reply})

    except requests.exceptions.Timeout:
        return jsonify({"error": True, "reply": "AI 服务响应超时，请稍后重试。"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": True, "reply": f"AI 服务请求失败: {type(e).__name__}"}), 502
    except (KeyError, IndexError):
        return jsonify({"error": True, "reply": "AI 返回数据格式异常，请稍后重试。"}), 502


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """AI 聊天接口（流式 SSE），支持多轮对话历史"""
    if not MIMO_API_KEY:
        return jsonify({"error": True, "reply": "AI 服务未配置。"}), 503

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": True, "reply": "请求格式错误。"}), 400

    user_message, history, context, err = _parse_chat_request(body)
    if err:
        return err

    full_messages, skill_names = _build_full_messages(user_message, history, context)

    def generate():
        try:
            resp = requests.post(
                MIMO_API_URL,
                headers={"api-key": MIMO_API_KEY, "Content-Type": "application/json"},
                json={
                    "model": MIMO_MODEL,
                    "messages": full_messages,
                    "max_completion_tokens": 2048,
                    "temperature": 1.0,
                    "top_p": 0.95,
                    "stream": True,
                },
                timeout=120,
                stream=True,
            )
            resp.raise_for_status()

            # 发送技能引用元数据
            if skill_names:
                yield f"event: skill_info\ndata: {json.dumps({'skills': skill_names})}\n\n"

            # 流式转发 token
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8", errors="replace")
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield f"data: {json.dumps({'token': token})}\n\n"
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue

            yield "data: [DONE]\n\n"

        except requests.exceptions.Timeout:
            yield f"data: {json.dumps({'error': 'AI 服务响应超时。'})}\n\n"
            yield "data: [DONE]\n\n"
        except requests.exceptions.RequestException as e:
            yield f"data: {json.dumps({'error': f'AI 服务请求失败: {type(e).__name__}'})}\n\n"
            yield "data: [DONE]\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/health", methods=["GET"])
def health():
    """健康检查，返回技能库状态"""
    return jsonify({
        "status": "ok",
        "api_configured": bool(MIMO_API_KEY),
        "skills_loaded": len(skill_indexer.skills),
    })


@app.route("/api/skills", methods=["GET"])
def list_skills():
    """列出所有已注册的技能（调试用）"""
    skills_info = [
        {"name": s["name"], "category": s["category"], "description": s["description"][:80]}
        for s in skill_indexer.skills
    ]
    return jsonify({"count": len(skills_info), "skills": skills_info})


# ---- 启动 ----

if __name__ == "__main__":
    if not MIMO_API_KEY:
        print("[WARNING] 环境变量 MIMO_API_KEY 未设置，AI 功能将不可用。")
    app.run(host="0.0.0.0", port=5000, debug=True)
