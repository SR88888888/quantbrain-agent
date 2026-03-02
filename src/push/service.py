import requests as req_lib
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from src.core.config import settings
from src.core.logger import log
from src.domain.models import FinalReport, PushChannel


def clean_body(text: str) -> str:
    """清理报告正文: 去掉所有Markdown符号和免责声明"""
    if not text:
        return ""
    import re
    # 去掉所有#开头的标记（不管有没有空格）
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    # 去掉加粗/斜体
    text = text.replace("**", "").replace("__", "")
    # 去掉分隔线
    text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\*{3,}$', '', text, flags=re.MULTILINE)
    # 去掉代码块标记
    text = text.replace("```", "")
    # 去掉列表符号开头的 - 和 *
    text = re.sub(r'^[\-\*]\s+', '', text, flags=re.MULTILINE)
    # 去掉免责声明
    text = text.replace("本报告由AI自动生成,仅供参考", "")
    text = text.replace("*本报告由AI自动生成,仅供参考*", "")
    # 去掉"32. 33." 这类行首数字序号（图片序号样式）
    import re as _re
    text = _re.sub(r'^\d{1,3}[.、。]\s*', '', text, flags=_re.MULTILINE)
    # 去掉①②③...⑩及其变体
    for ch in "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳":
        text = text.replace(ch, '')
    # 清理多余空行
    lines = [l for l in text.split("\n") if l.strip()]
    return "\n".join(lines)


class FeishuPusher:
    """飞书群机器人推送"""

    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url

    async def push(self, report: FinalReport) -> bool:
        if not self.webhook_url:
            log.debug("飞书推送未配置webhook")
            return False

        content = self._format(report)
        try:
            resp = req_lib.post(
                self.webhook_url,
                json={
                    "msg_type": "interactive",
                    "card": {
                        "header": {
                            "title": {"tag": "plain_text", "content": report.title},
                            "template": "blue",
                        },
                        "elements": [
                            {"tag": "markdown", "content": content},
                        ],
                    },
                },
                timeout=10,
            )
            if resp.status_code == 200 and resp.json().get("code") == 0:
                log.warning(f"飞书推送成功: {report.title}")
                return True
            log.warning(f"飞书推送失败: {resp.text[:200]}")
        except Exception as e:
            log.error(f"飞书推送异常: {e}")
        return False

    @staticmethod
    def _format(report: FinalReport) -> str:
        lines = []
        if report.highlights:
            lines.append("**要点速览**")
            for h in report.highlights:
                lines.append(f"- {h}")
            lines.append("")
        if report.summary and report.summary != "暂无摘要":
            lines.append(f"**摘要**: {report.summary}")
            lines.append("")
        if report.body:
            body = report.body[:3000]
            body = body.replace("---", "")
            body = body.replace("*本报告由AI自动生成,仅供参考*", "")
            body = body.replace("本报告由AI自动生成,仅供参考", "")
            lines.append(body)
        return "\n".join(lines)


class WechatPusher:
    """企业微信/群机器人推送"""

    def __init__(self):
        self.webhook_url = settings.PUSH_WECHAT_WEBHOOK

    async def push(self, report: FinalReport) -> bool:
        if not self.webhook_url:
            log.debug("微信推送未配置webhook")
            return False

        content = f"{report.title}\n\n{report.summary}\n\n{clean_body(report.body)[:2000]}"
        try:
            resp = req_lib.post(
                self.webhook_url,
                json={"msgtype": "markdown", "markdown": {"content": content}},
                timeout=10,
            )
            if resp.status_code == 200:
                log.warning(f"微信推送成功: {report.title}")
                return True
        except Exception as e:
            log.error(f"微信推送异常: {e}")
        return False


class EmailPusher:
    """SMTP邮件推送"""

    def __init__(self):
        self.host = settings.PUSH_EMAIL_SMTP_HOST
        self.port = settings.PUSH_EMAIL_SMTP_PORT
        self.user = settings.PUSH_EMAIL_USER
        self.password = settings.PUSH_EMAIL_PASSWORD
        self.receivers = settings.PUSH_EMAIL_RECEIVERS

    async def push(self, report: FinalReport) -> bool:
        if not all([self.host, self.user, self.password, self.receivers]):
            log.debug("邮件推送未配置")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = report.title
            msg["From"] = self.user
            msg["To"] = ", ".join(self.receivers)

            body = clean_body(report.body)
            html = f"<html><body><h2>{report.title}</h2><p>{report.summary}</p><pre>{body}</pre></body></html>"
            msg.attach(MIMEText(html, "html", "utf-8"))

            with smtplib.SMTP_SSL(self.host, self.port) as server:
                server.login(self.user, self.password)
                server.sendmail(self.user, self.receivers, msg.as_string())
            log.warning(f"邮件推送成功: {report.title}")
            return True
        except Exception as e:
            log.error(f"邮件推送异常: {e}")
            return False


class WebhookPusher:
    async def push(self, url: str, report: FinalReport) -> bool:
        if not url:
            return False
        try:
            resp = req_lib.post(url, json=report.model_dump(mode="json"), timeout=10)
            return resp.status_code == 200
        except Exception as e:
            log.error(f"Webhook推送异常: {e}")
            return False


class PushService:
    """统一推送服务"""

    def __init__(self):
        self.wechat = WechatPusher()
        self.email = EmailPusher()
        self.webhook = WebhookPusher()
        self.feishu = FeishuPusher(settings.PUSH_FEISHU_WEBHOOK)

    async def push(self, report: FinalReport, channels: List[PushChannel] = None):
        if channels is None:
            channels = [PushChannel.FEISHU]

        results = {}
        for ch in channels:
            if ch == PushChannel.WECHAT:
                results["wechat"] = await self.wechat.push(report)
            elif ch == PushChannel.EMAIL:
                results["email"] = await self.email.push(report)
            elif ch == PushChannel.FEISHU:
                results["feishu"] = await self.feishu.push(report)

        success_count = sum(1 for v in results.values() if v)
        log.debug(f"推送完成: {success_count}/{len(results)} 成功")
        return results

    async def save_local(self, report: FinalReport):
        import os
        os.makedirs("data/reports", exist_ok=True)
        filename = f"data/reports/{report.report_type.value}_{report.generated_at.strftime('%Y%m%d_%H%M%S')}.txt"

        body = clean_body(report.body)

        content = f"{report.title}\n\n"
        if report.summary:
            content += f"{report.summary}\n\n"
        if report.highlights:
            content += "要点速览\n"
            for h in report.highlights:
                content += f"  - {h}\n"
            content += "\n"
        content += body.strip()

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        log.debug(f"报告已保存: {filename}")


push_service = PushService()
