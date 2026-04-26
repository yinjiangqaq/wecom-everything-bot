# wecom-everything-bot

## wecom-copenhagen-daily-push

通过企业微信 + GitHub Actions，定期发送当前哥本哈根的天气、时间、假期信息，以及按类型整理的哥本哈根本地新闻。

推荐在 GitHub Actions 中使用企业微信群机器人 webhook：

- 设置 `WECOM_WEBHOOK_KEY` 或完整的 `WECOM_WEBHOOK_URL`
- 脚本会优先走 webhook 发送
- 如果未配置 webhook，脚本会回退到企业微信应用消息接口，需提供 `WECOM_CORP_ID`、`WECOM_CORP_SECRET`、`WECOM_AGENT_ID`、`WECOM_TOUSER`
- 新闻内容会按 `交通 / 天气 / 节日 / 文化活动 / 本地` 分类抓取哥本哈根优先、丹麦相关次优先的新闻，并自动翻译为中文后追加到消息底部
- 额外推送 `KU 药学院 ↔ Valby 住处` 生活决策助手：先给出今日建议，再附 Too Good To Go、实时生活用品优惠、交通省钱提示等参考情报
- 企业微信消息使用普通文本发送，每条新闻下方会附带原文链接
- 可选环境变量 `NEWS_ITEMS_PER_CATEGORY` 用于控制每个新闻分类输出几条，默认 `1`
- 可选环境变量 `LIFE_INFO_ENABLED=0` 可关闭留学生活情报，默认开启
- 可选环境变量 `LIFE_PRODUCT_QUERIES` 用于配置生活用品实时优惠关键词，格式如 `håndsprit:消毒/免洗洗手液;toiletpapir:厕纸`
- 可选环境变量 `LIFE_DEAL_ITEMS_PER_QUERY` 用于控制每个关键词输出几条实时优惠，默认 `1`
- 可选环境变量 `LIFE_MAX_DEAL_ITEMS` 用于控制生活用品实时优惠总数，默认 `6`
- 可选环境变量 `WECOM_TEXT_MAX_CHARS` 用于控制长消息自动分段阈值，默认 `1800`

说明：

- 你遇到的 `errcode: 60020` 表示企业微信接口拒绝当前来源 IP
- GitHub-hosted runner 的出口 IP 不固定，常见做法是改用 webhook，或改为自建固定出口 IP 的 runner
