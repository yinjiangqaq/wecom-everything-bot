# wecom-everything-bot

## wecom-copenhagen-daily-push

通过企业微信 + GitHub Actions，定期发送当前哥本哈根的天气、时间和假期信息。

推荐在 GitHub Actions 中使用企业微信群机器人 webhook：

- 设置 `WECOM_WEBHOOK_KEY` 或完整的 `WECOM_WEBHOOK_URL`
- 脚本会优先走 webhook 发送
- 如果未配置 webhook，脚本会回退到企业微信应用消息接口，需提供 `WECOM_CORP_ID`、`WECOM_CORP_SECRET`、`WECOM_AGENT_ID`、`WECOM_TOUSER`

说明：

- 你遇到的 `errcode: 60020` 表示企业微信接口拒绝当前来源 IP
- GitHub-hosted runner 的出口 IP 不固定，常见做法是改用 webhook，或改为自建固定出口 IP 的 runner
