# AI 求职助手 Agent

## 当前可运行 MVP

- 解析 `.txt`、`.docx` 和 `.pdf` 简历；
- 返回统一的文档类型、页/段落数量、字符数和纯文本；
- 对路径不存在、空文件、不支持格式、加密/损坏 PDF、缺失依赖给出明确异常；
- 浏览器上传简历、粘贴 JD 并生成匹配报告；
- 展示技能命中、缺失项、简历原文证据、经验/学历判断和改进建议；
- FastAPI 提供分析、历史列表和单任务查询接口；
- SQLite 保存任务报告和脱敏后的命中证据，不保存整份简历正文；
- 可选接入 DeepSeek，生成简历建议、30 秒自我介绍、面试题和基于材料的问答；
- DeepSeek 内容经过技能与年限基础事实检查，模型异常时自动保留离线报告；
- 不把真实简历或个人隐私写入仓库。

## 运行

```powershell
python -m pip install -e ".[dev]"
pytest
python -m app.cli parse path\to\resume.pdf
uvicorn app.api:app --reload
# 另开终端
streamlit run app/streamlit_app.py
```

启用 DeepSeek 前，在启动 Streamlit 的同一个终端配置：

```powershell
$env:DEEPSEEK_API_KEY="你的密钥"
# 可选；默认 deepseek-flash
$env:DEEPSEEK_MODEL="deepseek-flash"
```

页面只有在用户勾选授权后，才会把脱敏简历文本和 JD 发送给 DeepSeek。

命令行默认只输出摘要；添加 `--show-text` 才会显示简历正文，避免终端日志意外泄露隐私。
