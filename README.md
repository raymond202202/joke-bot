# 🤣 打工人笑话机器人

定时从公开 API 抓取中文笑话/段子，通过 Hermes cron 发送到飞书群。

## 工作原理

脚本本身不含网络收发逻辑 —— 它只是一个 **stdout 输出器**。  
Hermes cron 每 5 分钟触发一次脚本，脚本判断：

1. 当前是否在上班时间（08:30～12:00 / 14:00～19:30）
2. 是否到了预定的下一次发送时刻
3. 如果是 → 随机抓取一条笑话 → 输出到 stdout → 等待下次

Hermes cron 捕获 stdout 作为消息内容，自动投递到飞书群。

## 数据源（纯公开 API，无需 Key）

| 源 | URL | 风格 |
|----|-----|------|
| 毒鸡汤 | `api.shadiao.pro/du` | 黑色幽默 |
| 彩虹屁 | `api.shadiao.pro/chp` | 无厘头夸奖 |
| 一言 | `api.btstu.cn/yan` | 冷梗/沙雕句子 |

每次随机选一个源，请求失败自动换下一个。

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

## 许可

MIT
