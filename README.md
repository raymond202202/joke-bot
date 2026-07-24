This project was created with assistance from the AI agent Hermes. Human review and additional development were performed by the repository maintainer.

# 🤣 打工人笑话机器人

> 🤖 **本项目的 AI 背景**
>
> 本项目由 [Hermes Agent](https://hermes-agent.nousresearch.com)（Nous Research 开发的 AI 编程助手）
> **全程 AI 辅助完成**：需求分析、代码编写、文档撰写均由 AI 完成。
> 人工仅做需求提出、验证和最终发布。

> ⚠️ **数据源声明**
>
> 本项目使用的笑话/段子 API 均来自互联网公开的免费接口，并非项目自身提供的内容。
> 接口来源：
> - [api.shadiao.pro](https://api.shadiao.pro) — 毒鸡汤 / 彩虹屁
> - [api.btstu.cn](https://api.btstu.cn) — 一言冷梗
>
> 如果这些接口的内容涉及侵权，请联系我（通过 GitHub Issues），**我会立即删除相关引用**。
> 你也可以替换为自建或其他来源的笑话源（见下方说明）。

---

定时从公开 API 抓取中文笑话/段子，通过 Hermes cron 发送到飞书群。

## 工作原理

脚本本身不含网络收发逻辑 —— 它只是一个 **stdout 输出器**。  
Hermes cron 每 5 分钟触发一次脚本，脚本判断：

1. 当前是否在上班时间（08:30～12:00 / 14:00～19:30）
2. 是否到了预定的下一次发送时刻
3. 如果是 → 随机抓取一条笑话 → 输出到 stdout → 等待下次

Hermes cron 捕获 stdout 作为消息内容，自动投递到飞书群。

## 自定义笑话源

你完全可以替换为自己的笑话源。在 `joke_bot.py` 的 `JOKE_SOURCES` 列表中添加或修改：

```python
JOKE_SOURCES = [
    {
        "name": "我的笑话源",       # 显示名称
        "url": "https://你的接口",   # API 地址
        "headers": {"User-Agent": "JokeBot/1.0"},
        "parser": lambda data: json.loads(data).get("data", {}).get("text", ""),
    },
]
```

每个源的 `parser` 是一个 lambda 函数，接收 HTTP 响应正文并返回笑话文本。你可以自己写接口，也可以指向其他公开免费 API。

> 💡 **推荐方案**：如果你想完全自己控制笑话内容，可以自己部署一个简单的 API（比如 Flask 服务），甚至直接准备一个 `jokes.json` 本地文件，修改 [...]

## 配置参数

```python
MORNING_START  = 8:30   # 上午开始时间
MORNING_END    = 12:00  # 上午结束（午休）
AFTERNOON_START= 14:00  # 下午开始
AFTERNOON_END  = 19:30  # 下午结束
MIN_INTERVAL   = 15     # 最小发送间隔（分钟）
MAX_INTERVAL   = 60     # 最大发送间隔（分钟）
```

## 使用方式

```bash
# 手动测试
python3 joke_bot.py
# 输出示例：
# 🤣 打工人的快乐源泉 🤣
#
# [毒鸡汤]
# 钱对你真的就那么重要吗？讲了3个多小时了，一分钱都不降。
```

配合 Hermes cron：

```bash
# 创建定时任务（每5分钟轮询）
hermes cron create \
  --name "打工人笑话机器人" \
  --script joke_bot.py \
  --schedule "*/5 * * * *" \
  --no-agent
```

脚本内部通过 `~/.hermes/scripts/joke_state.json` 状态文件追踪下次发送时间，跨天自动重置。

## 致谢

- [shadiao.pro](https://shadiao.pro) — 毒鸡汤 & 彩虹屁 公开 API
- [api.btstu.cn](https://api.btstu.cn) — 一言冷梗 公开 API
- [Hermes Agent](https://hermes-agent.nousresearch.com) — AI 开发助手

## 许可

MIT
