import json
import os
import platform
import subprocess
import time
from urllib.parse import parse_qs, urlparse

import qrcode
import requests

HEADERS = {
    "Origin": "https://www.bilibili.com",
    "Referer": "https://www.bilibili.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
}


class Request:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch(self, url, params=None, cookies=None):
        response = self.session.get(url=url, params=params, cookies=cookies)
        response.raise_for_status()
        if response.json().get("code", -1) == 0:
            return response.json().get("data", {})
        raise


class Login(Request):
    api = {
        "generate": "https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
        "poll": "https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
    }
    config_path = "cookies.json"

    max_retries = 75
    retry_delay = 1

    def __init__(self):
        super().__init__()
        self.qrcode_key = None
        self.qrcode_url = None

    def _generate_qrcode(self):
        """生成二维码并保存到本地文件"""
        data = self.fetch(self.api["generate"], {"source": "main-fe-header", "go_url": "https://www.bilibili.com/"})
        self.qrcode_key = data.get("qrcode_key")
        self.qrcode_url = data.get("url")

        qrcode_image = qrcode.make(self.qrcode_url)
        qrcode_image.save("qrcode.png")

    def _poll_for_cookies(self):
        """轮询获取登录后的cookies"""
        for _ in range(self.max_retries):
            time.sleep(self.retry_delay)
            data = self.fetch(self.api["poll"], {"qrcode_key": self.qrcode_key, "source": "main-fe-header"})
            if data.get("code", -1) == 0:
                return {key: value[0] for key, value in parse_qs(urlparse(data.get("url")).query).items()}
        raise TimeoutError("Failed to get cookie after maximum retries.")

    def _read_cookies(self):
        """从配置文件中读取cookies"""
        with open(self.config_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _write_cookies(self, cookies):
        """将cookies写入配置文件"""
        with open(self.config_path, "w", encoding="utf-8") as file:
            json.dump(cookies, file)

    def _open_qrcode(self):
        """打开二维码"""
        commands = {
            "Windows": ["start", "qrcode.png"],
            "Darwin": ["open", "qrcode.png"],
            "Linux": ["xdg-open", "qrcode.png"],
        }
        subprocess.run(commands.get(platform.system()), shell=True)

    def get_cookies(self):
        """获取cookies"""
        if os.path.exists(self.config_path):
            return self._read_cookies()
        self._generate_qrcode()
        self._open_qrcode()

        try:
            cookies = self._poll_for_cookies()
        finally:
            if os.path.exists("qrcode.png"):
                os.remove("qrcode.png")
        self._write_cookies(cookies)
        return cookies


def main():
    cookies = Login().get_cookies()


if __name__ == '__main__':
    main()
