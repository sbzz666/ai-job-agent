# 职途智配：AI 求职助手

一个面向中文求职场景的端到端 AI 应用：解析简历与职位描述，输出可解释的岗位匹配报告，并使用 DeepSeek 生成简历建议、30 秒自我介绍、面试题和有依据的问答。

## 在线能力

- 支持 PDF、DOCX、TXT 简历，覆盖 Word 表格与文本框；
- 识别岗位技能、经验年限和学历要求；
- 输出匹配度、缺失项和可定位的简历原文证据；
- 可选调用 DeepSeek，生成个性化建议、自我介绍和面试问答；
- 对模型输出进行技能和年限事实检查；
- DeepSeek 失败时自动保留离线分析结果；
- 简历发送模型前隐藏手机号、邮箱和微信号；
- 支持会话隔离、调用限流、可选 OIDC 登录和邮箱白名单。

## 技术栈

Python 3.11+、Streamlit、FastAPI、OpenAI Python SDK / Responses API、DeepSeek、Pydantic、SQLite、PyMuPDF、python-docx、pytest。

## Windows 桌面版

GitHub Releases 提供 `Setup.exe` 安装版和 `Portable.zip` 便携版。便携版解压后运行 `AIJobAssistant.exe`，不需要另装 Python。用户数据保存在 Windows 的本地应用数据目录，不会写入安装目录。

安装包不包含任何 API 密钥。没有配置 DeepSeek 密钥时，软件仍可使用本地岗位匹配功能。发布维护者推送 `v*` 标签后，GitHub Actions 会自动构建并发布两个安装产物。

## 数据流

```text
简历 + JD
   ↓
格式与安全校验
   ↓
本地解析、要求识别、证据定位、可解释评分
   ↓
用户授权 → 隐私脱敏 → DeepSeek 结构化生成
   ↓
事实检查 → 中文报告 / 面试准备 / 有依据问答
```

## 本地运行

```powershell
cd job-agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:DEEPSEEK_API_KEY="你的密钥"
.\.venv\Scripts\python.exe -m streamlit run app\streamlit_app.py
```

访问 `http://localhost:8501`。没有 DeepSeek Key 时，离线匹配仍然可用。

## 测试

```powershell
cd job-agent
.\.venv\Scripts\python.exe -m pytest
```

测试覆盖 TXT、DOCX、PDF 解析、伪装文件拒绝、岗位匹配、证据定位、隐私脱敏、SQLite、API、DeepSeek Mock 和调用限流。

仓库内提供完全虚构的演示材料：

- `job-agent/data/samples/demo_resume.txt`
- `job-agent/data/samples/demo_job_description.txt`

## Streamlit Community Cloud 部署

1. 在 Streamlit Community Cloud 选择此 GitHub 仓库；
2. 入口文件填写 `streamlit_app.py`；
3. Python 选择仍接受安全更新的版本；
4. 在 Advanced settings → Secrets 中参考 `.streamlit/secrets.toml.example` 配置；
5. 优先将应用设置为私有，通过邮箱邀请访问者。

禁止把真实 API Key、真实简历、`.env`、`secrets.toml` 或本地数据库提交到 Git。

## 安全设计

- 最大文件 10MB、PDF 50 页、提取文本 50,000 字符；
- 检查 PDF/DOCX 文件签名与 DOCX 解压大小；
- 用户主动授权后才调用外部模型；
- 单用户小时、每日和全局每日三层 AI 调用限额；
- UI 历史只保存在当前会话，不跨用户共享；
- 生产模式关闭 Swagger 和历史查询接口；
- Secrets、真实文档、虚拟环境和数据库均被 Git 忽略。

详细说明见 [`docs/architecture/security-hardening.md`](docs/architecture/security-hardening.md)。

## 项目状态

当前为可部署的求职作品集版本。下一阶段将增加离线评估集、量化指标、Docker 和持续集成。
