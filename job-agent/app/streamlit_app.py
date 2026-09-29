"""Chinese Streamlit interface for local resume/JD analysis."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import streamlit as st

from app.models import AICareerGuidance, MatchReport
from app.services.deepseek_service import (
    DeepSeekCareerService,
    DeepSeekServiceError,
    deepseek_is_configured,
)
from app.services.resume_parser import ResumeParseError, parse_resume
from app.services.rate_limiter import RateLimitExceeded, RateLimiter
from app.services.task_repository import TransientTaskRepository
from app.services.workflow import JobAnalysisWorkflow


BASE_DIR = Path(__file__).resolve().parents[1]
repository = TransientTaskRepository()
workflow = JobAnalysisWorkflow(repository)

st.set_page_config(
    page_title="职途智配 · AI 求职助手",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _setting(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, None)
    except FileNotFoundError:
        value = None
    return str(value) if value is not None else os.getenv(name, default)


def _enabled(name: str, default: bool = False) -> bool:
    return _setting(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


for secret_name in ("DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "DEEPSEEK_BASE_URL"):
    secret_value = _setting(secret_name)
    if secret_value and not os.getenv(secret_name):
        os.environ[secret_name] = secret_value


if _enabled("REQUIRE_LOGIN"):
    if not st.user.is_logged_in:
        st.title("职途智配")
        st.info("请先登录后使用求职分析功能。")
        st.button("登录", type="primary", on_click=st.login)
        st.stop()

    allowed_emails = {
        email.strip().casefold()
        for email in _setting("ALLOWED_EMAILS").split(",")
        if email.strip()
    }
    current_email = str(st.user.get("email", "")).casefold()
    if allowed_emails and current_email not in allowed_emails:
        st.error("当前账号没有访问权限。")
        st.button("退出登录", on_click=st.logout)
        st.stop()


@st.cache_resource
def _rate_limiter() -> RateLimiter:
    return RateLimiter(
        per_user_hour=int(_setting("AI_CALLS_PER_USER_HOUR", "6")),
        per_user_day=int(_setting("AI_CALLS_PER_USER_DAY", "20")),
        global_day=int(_setting("AI_CALLS_GLOBAL_DAY", "100")),
    )


def _user_id() -> str:
    if st.user.is_logged_in and st.user.get("email"):
        return str(st.user.email).casefold()
    if "anonymous_session_id" not in st.session_state:
        st.session_state.anonymous_session_id = uuid4().hex
    return st.session_state.anonymous_session_id

st.markdown(
    """
    <style>
    :root { --brand: #2563eb; --ink: #172033; --muted: #64748b; }
    .stApp {
        background:
          radial-gradient(circle at 10% 0%, rgba(37,99,235,.10), transparent 28rem),
          linear-gradient(180deg, #f8faff 0%, #f4f7fb 100%);
    }
    .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem; }
    [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e7ecf3; }
    [data-testid="stSidebar"] .block-container { padding-top: 2rem; }
    .hero {
        padding: 2.2rem 2.4rem; border-radius: 24px; color: white;
        background: linear-gradient(120deg, #173f9f 0%, #2563eb 58%, #38bdf8 120%);
        box-shadow: 0 18px 50px rgba(37, 99, 235, .18); margin-bottom: 1.4rem;
    }
    .hero-kicker { font-size: .84rem; letter-spacing: .12em; opacity: .82; font-weight: 700; }
    .hero h1 { margin: .45rem 0 .55rem; font-size: 2.15rem; line-height: 1.2; }
    .hero p { margin: 0; max-width: 760px; opacity: .9; font-size: 1.02rem; }
    .step-card {
        min-height: 112px; padding: 1rem 1.1rem; border-radius: 16px;
        background: rgba(255,255,255,.88); border: 1px solid #e5eaf2;
        box-shadow: 0 6px 24px rgba(15,23,42,.045);
    }
    .step-num {
        display:inline-flex; width:28px; height:28px; align-items:center; justify-content:center;
        border-radius:9px; background:#e8f0ff; color:#1d4ed8; font-weight:800; margin-right:.45rem;
    }
    .step-title { color: var(--ink); font-weight: 750; }
    .step-desc { color: var(--muted); font-size: .88rem; margin-top: .55rem; line-height: 1.55; }
    .section-title { font-size: 1.12rem; color: var(--ink); font-weight: 800; margin: .2rem 0 .2rem; }
    .section-desc { color: var(--muted); font-size: .9rem; margin-bottom: .7rem; }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255,255,255,.93); border-color: #e3e9f2 !important;
        border-radius: 18px; box-shadow: 0 8px 28px rgba(15,23,42,.045);
    }
    .stButton > button[kind="primary"] {
        min-height: 48px; border: 0; border-radius: 12px; font-weight: 750;
        background: linear-gradient(100deg, #1d4ed8, #2563eb 60%, #0ea5e9);
        box-shadow: 0 8px 20px rgba(37,99,235,.2);
    }
    [data-testid="stFileUploaderDropzone"] { border-radius: 14px; background: #f8faff; }
    [data-testid="stFileUploaderDropzoneInstructions"] span { font-size: 0 !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] span::before {
        content: "拖拽简历到这里"; font-size: .95rem; color: #27364f;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] small { font-size: 0 !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] small::before {
        content: "支持 PDF、Word、TXT，单个文件不超过 10MB"; font-size: .78rem; color: #748198;
    }
    [data-testid="stFileUploaderDropzone"] button { font-size: 0 !important; }
    [data-testid="stFileUploaderDropzone"] button::after { content: "选择文件"; font-size: .86rem; }
    [data-testid="stMetric"] {
        padding: .85rem 1rem; background: #f8faff; border: 1px solid #e5eaf2; border-radius: 14px;
    }
    [data-testid="stMetricValue"] { color: #173f9f; }
    .privacy-note {
        padding: .85rem 1rem; border-radius: 12px; background: #effaf5;
        color: #166534; border: 1px solid #ccebd9; font-size: .85rem; line-height: 1.55;
    }
    .score-copy { color: var(--muted); margin: -.15rem 0 .65rem; }
    .footer { text-align:center; color:#94a3b8; font-size:.78rem; padding-top:2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _score_comment(score: float) -> str:
    if score >= 85:
        return "高度匹配：核心硬性条件覆盖较好，重点优化成果表达。"
    if score >= 65:
        return "较为匹配：已有可用基础，建议针对缺失项补充真实证据。"
    if score >= 40:
        return "部分匹配：建议优先调整项目经历与岗位要求的对应关系。"
    return "匹配偏低：请确认岗位方向，并补充完整、真实的相关经历。"


def _show_report(report: MatchReport) -> None:
    st.markdown("### 分析结果")
    with st.container(border=True):
        score_col, skill_col, exp_col, edu_col = st.columns([1.25, 1, 1, 1])
        score_col.metric("综合匹配度", f"{report.overall_score:.0f}%")
        skill_col.metric("技能覆盖", f"{report.score_breakdown.skills:.0f}%")
        exp_col.metric(
            "经验要求",
            f"{report.detected_experience_years or 0}/{report.required_experience_years} 年"
            if report.required_experience_years
            else "岗位未注明",
        )
        edu_col.metric("学历匹配", "符合" if report.score_breakdown.education == 100 else "待确认")
        st.progress(report.overall_score / 100)
        st.markdown(f'<div class="score-copy">{_score_comment(report.overall_score)}</div>', unsafe_allow_html=True)
        st.caption(f"任务编号：{report.task_id}　·　简历：{report.resume_name}")

    overview_tab, evidence_tab, advice_tab = st.tabs(["核心结论", "证据核验", "优化建议"])
    with overview_tab:
        left, right = st.columns(2)
        with left, st.container(border=True):
            st.markdown("#### 已覆盖的岗位技能")
            st.success("　·　".join(report.matched_skills) if report.matched_skills else "暂未识别到匹配技能")
        with right, st.container(border=True):
            st.markdown("#### 尚缺少的岗位技能")
            if report.missing_skills:
                st.warning("　·　".join(report.missing_skills))
            else:
                st.success("已覆盖当前识别出的技能要求")

    with evidence_tab:
        st.caption("只展示简历中能够定位的文字；未找到证据时不会替你编造经历。")
        if not report.evidence:
            st.info("职位描述中暂未识别到可核验的技能要求。")
        for item in report.evidence:
            status = "已找到" if item.matched else "未找到"
            with st.expander(f"{status}｜{item.requirement}", expanded=item.matched):
                if item.evidence:
                    for line in item.evidence:
                        st.text(line)
                else:
                    st.write("简历中没有找到对应文字证据。")

    with advice_tab:
        for index, suggestion in enumerate(report.recommendations, start=1):
            with st.container(border=True):
                st.markdown(f"**建议 {index}**")
                st.write(suggestion)
        with st.expander("查看评分说明与限制"):
            for limitation in report.limitations:
                st.write(f"- {limitation}")


def _show_ai_guidance(guidance: AICareerGuidance) -> None:
    st.markdown("### DeepSeek 深度分析")
    if guidance.verified:
        st.success("生成内容已通过技能与年限的基础事实检查。")
    else:
        st.warning("生成内容存在待核验表述，请不要直接复制到简历。")
        for warning in guidance.fact_check_warnings:
            st.write(f"- {warning}")

    suggestion_tab, intro_tab, interview_tab = st.tabs(
        ["简历修改建议", "30 秒自我介绍", "面试问题与参考回答"]
    )
    with suggestion_tab:
        for index, suggestion in enumerate(guidance.resume_suggestions, start=1):
            with st.container(border=True):
                st.markdown(f"**建议 {index}**")
                st.write(suggestion)
    with intro_tab:
        with st.container(border=True):
            st.write(guidance.self_introduction)
            st.caption("使用前请根据本人真实经历复核，禁止添加不存在的经历。")
    with interview_tab:
        for index, item in enumerate(guidance.interview_questions, start=1):
            with st.expander(f"问题 {index}｜{item.question}"):
                st.markdown(f"**考察点：** {item.evaluation_focus}")
                st.markdown("**参考回答：**")
                st.write(item.reference_answer)
    st.caption(f"生成模型：{guidance.model}")


def _show_ai_qa() -> None:
    if not deepseek_is_configured() or "resume_text" not in st.session_state:
        return
    st.markdown("### 向求职助手继续提问")
    st.caption("回答仅基于本次简历和职位描述；材料不足时应拒绝猜测。")
    for message in st.session_state.get("qa_messages", []):
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message.get("evidence"):
                with st.expander("查看回答依据"):
                    for evidence in message["evidence"]:
                        st.text(evidence)

    question = st.chat_input("例如：这份简历最需要补强什么？")
    if question:
        st.session_state.setdefault("qa_messages", []).append(
            {"role": "user", "content": question}
        )
        try:
            _rate_limiter().consume(_user_id())
            with st.spinner("DeepSeek 正在基于简历回答……"):
                answer = DeepSeekCareerService().answer_question(
                    question,
                    st.session_state.resume_text,
                    st.session_state.job_description,
                )
            st.session_state.qa_messages.append(
                {
                    "role": "assistant",
                    "content": answer.answer,
                    "evidence": answer.evidence,
                }
            )
        except (DeepSeekServiceError, RateLimitExceeded) as exc:
            st.session_state.qa_messages.append(
                {"role": "assistant", "content": str(exc), "evidence": []}
            )
        st.rerun()


with st.sidebar:
    st.markdown("## 🎯 职途智配")
    st.caption("本地 AI 求职助手")
    st.divider()
    st.markdown("**使用说明**")
    st.markdown("1. 上传当前简历\n2. 粘贴完整职位描述\n3. 查看匹配证据与建议")
    st.divider()
    st.markdown(
        '<div class="privacy-note">🔒 简历文件仅临时解析，不持久化整份正文；发送 DeepSeek 前会隐藏手机号、邮箱和微信号。</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    if st.button("清除本次会话数据", use_container_width=True):
        for key in ("last_report", "resume_text", "job_description", "qa_messages", "ai_guidance", "session_history"):
            st.session_state.pop(key, None)
        st.rerun()
    st.caption("当前版本：安全增强版 · v0.3")

st.markdown(
    """
    <div class="hero">
      <div class="hero-kicker">智能岗位匹配助手</div>
      <h1>让每一次投递，都更有依据</h1>
      <p>上传简历并粘贴目标职位描述，快速获得岗位匹配度、原文证据和可执行的优化建议。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

step_columns = st.columns(3)
steps = [
    ("1", "上传简历", "支持 PDF、Word 和 TXT，自动提取正文与表格内容。"),
    ("2", "粘贴职位描述", "请包含岗位职责、技能、经验和学历要求。"),
    ("3", "查看分析报告", "逐项核验匹配证据，并获得真实可执行的建议。"),
]
for column, (number, title, description) in zip(step_columns, steps):
    column.markdown(
        f'<div class="step-card"><span class="step-num">{number}</span>'
        f'<span class="step-title">{title}</span><div class="step-desc">{description}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")
analysis_tab, history_tab = st.tabs(["开始岗位分析", "历史分析记录"])

with analysis_tab:
    with st.container(border=True):
        st.markdown('<div class="section-title">填写分析材料</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-desc">材料越完整，分析结果越准确。仅在你主动勾选授权后，才会调用外部模型。</div>',
            unsafe_allow_html=True,
        )
        upload_col, jd_col = st.columns([.9, 1.35], gap="large")
        with upload_col:
            resume = st.file_uploader(
                "上传你的简历",
                type=["txt", "docx", "pdf"],
                help="建议使用文字版 PDF 或 DOCX；扫描版 PDF 暂不支持。",
            )
            if resume is not None:
                st.caption(f"已选择：{Path(resume.name).name}")
        with jd_col:
            job_description = st.text_area(
                "目标职位描述（JD）",
                height=205,
                placeholder="请粘贴招聘信息中的岗位职责、任职要求、技术栈、工作年限和学历要求……",
            )

        ai_available = deepseek_is_configured()
        use_deepseek = st.checkbox(
            "使用 DeepSeek 生成个性化建议、自我介绍和面试问答",
            value=False,
            disabled=not ai_available,
            help="勾选后，脱敏的简历文本和职位描述将发送给 DeepSeek API。",
        )
        if ai_available:
            st.caption("已检测到 DEEPSEEK_API_KEY。只有勾选后才会调用外部模型。")
        else:
            st.info("未检测到 DEEPSEEK_API_KEY，当前只运行本地可解释匹配。")

        analyze = st.button("生成岗位匹配报告", type="primary", use_container_width=True)
        if analyze:
            if resume is None or len(job_description.strip()) < 10:
                st.error("请上传简历，并填写至少 10 个字符的职位描述。")
            elif len(resume.getvalue()) > 10 * 1024 * 1024:
                st.error("简历文件不能超过 10MB。")
            else:
                try:
                    with st.spinner("正在解析简历、核验岗位要求……"), TemporaryDirectory(
                        prefix="job-agent-ui-"
                    ) as temp_dir:
                        safe_name = Path(resume.name).name
                        path = Path(temp_dir) / safe_name
                        path.write_bytes(resume.getvalue())
                        parsed = parse_resume(path)
                        report = workflow.run_parsed(parsed, job_description)
                        st.session_state.last_report = report
                        st.session_state.setdefault("session_history", []).insert(0, report)
                        st.session_state.session_history = st.session_state.session_history[:10]
                        st.session_state.resume_text = parsed.text
                        st.session_state.job_description = job_description
                        st.session_state.qa_messages = []
                        st.session_state.pop("ai_guidance", None)
                        if use_deepseek:
                            try:
                                _rate_limiter().consume(_user_id())
                                st.session_state.ai_guidance = DeepSeekCareerService().generate_guidance(
                                    parsed.text, job_description, report
                                )
                            except (DeepSeekServiceError, RateLimitExceeded) as exc:
                                st.warning(f"DeepSeek 增强失败：{exc} 离线匹配报告仍可正常使用。")
                    st.toast("岗位分析已完成", icon="✅")
                except (ResumeParseError, ValueError) as exc:
                    st.error(str(exc))

    if report := st.session_state.get("last_report"):
        _show_report(report)
        if guidance := st.session_state.get("ai_guidance"):
            _show_ai_guidance(guidance)
        _show_ai_qa()

with history_tab:
    st.markdown("### 本次会话记录")
    st.caption("这些记录只存在于当前浏览器会话，不会与其他用户共享，也不会写入云端数据库。")
    session_history = st.session_state.get("session_history", [])
    if not session_history:
        st.info("本次会话还没有分析记录。")
    else:
        for task in session_history:
            with st.container(border=True):
                name_col, score_col, time_col = st.columns([2.1, .8, 1.25])
                name_col.markdown(f"**{task.resume_name}**")
                score_col.markdown(f"**{task.overall_score:.0f}%** 匹配")
                time_col.caption(task.created_at.strftime("%Y-%m-%d %H:%M"))
                st.caption(f"任务编号：{task.task_id}")

st.markdown('<div class="footer">职途智配 · 让求职分析更清晰、更可信</div>', unsafe_allow_html=True)
