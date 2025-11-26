import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

# ============================
#  EMAIL CONFIG (硬编码)
# ============================
EMAIL_HOST = "smtp.qq.com"
EMAIL_PORT = 587
EMAIL_ENABLE_SSL = True
EMAIL_USERNAME = "1790870505@qq.com"
EMAIL_PASSWORD = "。。"
EMAIL_FROM = "1790870505@qq.com"
EMAIL_DISPLAY_NAME = "PaperIgnition 通知"
EMAIL_TO = ""   # 如需其他收件人修改这里即可
# ============================

def send_failure_email():
    msg = MIMEText("脚本失败了", "plain", "utf-8")
    msg["Subject"] = Header("脚本失败提醒", "utf-8")
    msg["From"] = formataddr((str(Header(EMAIL_DISPLAY_NAME, 'utf-8')), EMAIL_FROM))
    msg["To"] = EMAIL_TO

    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        if EMAIL_ENABLE_SSL:
            server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())
        server.quit()
        print("[INFO] Failure email sent OK.")
    except Exception as e:
        print("[ERROR] Failed to send email:", e)

if __name__ == "__main__":
    send_failure_email()