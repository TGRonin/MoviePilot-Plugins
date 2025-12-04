from app.plugins import PluginBase
from app.plugins import EventManager, EventType
from app.schemas import NotificationType
from app.helper import BrowserHelper
from app.utils import RequestUtils
from bs4 import BeautifulSoup
import re
import time
import threading
import logging

class GroupChatZone(PluginBase):
    # 插件元信息
    plugin_id = "groupchatzone"
    plugin_name = "群聊区监控"
    plugin_desc = "监控群聊区特定格式的魔法上传信息"
    plugin_icon = "https://raw.githubusercontent.com/jxxghp/MoviePilot-Plugins/main/icons/chat.png"
    plugin_author = "TraeAI"
    plugin_version = "1.0.0"
    plugin_language = "zh"
    
    # 插件配置项
    enable = False
    target_url = ""
    check_interval = 120  # 检查间隔（秒）
    match_pattern = r"完成了一次上传\d+\.\d{2}下载0\.00的魔法, 持续\d+天\d+小时"
    notification_enable = True
    notification_channel = None
    
    # 内部属性
    _monitor_thread = None
    _monitor_running = False
    _detected_contents = set()
    _last_check_time = 0
    
    def __init__(self):
        """初始化插件"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.eventmanager = EventManager()
    
    def init_plugin(self, config: dict = None):
        """初始化插件配置"""
        if config:
            self.enable = config.get("enable", False)
            self.target_url = config.get("target_url", "")
            self.check_interval = config.get("check_interval", 120)
            self.match_pattern = config.get("match_pattern", r"完成了一次上传\d+\.\d{2}下载0\.00的魔法, 持续\d+天\d+小时")
            self.notification_enable = config.get("notification_enable", True)
            self.notification_channel = config.get("notification_channel")
        
        # 启动监控线程
        if self.enable:
            self.start_monitor()
        else:
            self.stop_monitor()
    
    def get_state(self) -> bool:
        """获取插件运行状态"""
        return self._monitor_running
    
    def get_form(self) -> dict:
        """获取插件配置表单"""
        return {
            "enable": {
                "label": "启用插件",
                "type": "switch",
                "value": self.enable
            },
            "target_url": {
                "label": "监控目标URL",
                "type": "input",
                "value": self.target_url,
                "placeholder": "请输入要监控的群聊区URL"
            },
            "check_interval": {
                "label": "检查间隔（秒）",
                "type": "input",
                "value": self.check_interval,
                "placeholder": "请输入检查间隔，单位：秒"
            },
            "match_pattern": {
                "label": "匹配规则",
                "type": "input",
                "value": self.match_pattern,
                "placeholder": "请输入正则表达式"
            },
            "notification_enable": {
                "label": "启用通知",
                "type": "switch",
                "value": self.notification_enable
            },
            "notification_channel": {
                "label": "通知渠道",
                "type": "select",
                "value": self.notification_channel,
                "options": [
                    {"label": "系统通知", "value": "system"},
                    {"label": "邮件通知", "value": "email"}
                ]
            }
        }
    
    def get_page(self) -> dict:
        """获取插件详情页面"""
        return {
            "title": "群聊区监控",
            "content": "监控群聊区特定格式的魔法上传信息，支持自定义匹配规则和通知设置。"
        }
    
    def start_monitor(self):
        """启动监控线程"""
        if self._monitor_running:
            return
        
        self._monitor_running = True
        self._monitor_thread = threading.Thread(target=self.monitor_task, daemon=True)
        self._monitor_thread.start()
        self.logger.info("群聊区监控已启动")
    
    def stop_monitor(self):
        """停止监控线程"""
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
            self._monitor_thread = None
        self.logger.info("群聊区监控已停止")
    
    def monitor_task(self):
        """监控任务"""
        while self._monitor_running:
            try:
                # 检查是否到检查时间
                now = time.time()
                if now - self._last_check_time < self.check_interval:
                    time.sleep(1)
                    continue
                
                self._last_check_time = now
                self.logger.info("开始检查群聊区内容")
                
                # 获取iframe内容
                content = self.fetch_iframe_content()
                if not content:
                    self.logger.error("获取群聊区内容失败")
                    continue
                
                # 检测目标内容
                self.detect_target_content(content)
                
            except Exception as e:
                self.logger.error(f"监控任务执行失败：{str(e)}")
                time.sleep(1)
    
    def fetch_iframe_content(self) -> str:
        """获取iframe内容"""
        try:
            # 使用BrowserHelper访问目标URL
            browser = BrowserHelper()
            html = browser.get(self.target_url)
            if not html:
                return None
            
            # 解析HTML，查找iframe
            soup = BeautifulSoup(html, 'html.parser')
            iframe = soup.find('iframe', id='sbcontent')
            if not iframe:
                self.logger.error("未找到ID为sbcontent的iframe元素")
                return None
            
            # 获取iframe的src属性
            iframe_src = iframe.get('src')
            if not iframe_src:
                self.logger.error("iframe未设置src属性")
                return None
            
            # 如果iframe src是相对路径，转换为绝对路径
            if not iframe_src.startswith('http'):
                from urllib.parse import urljoin
                iframe_src = urljoin(self.target_url, iframe_src)
            
            # 获取iframe内容
            iframe_content = browser.get(iframe_src)
            if not iframe_content:
                self.logger.error("获取iframe内容失败")
                return None
            
            self.logger.info("成功获取iframe内容")
            return iframe_content
            
        except Exception as e:
            self.logger.error(f"获取iframe内容失败：{str(e)}")
            return None
    
    def detect_target_content(self, content: str):
        """检测目标内容"""
        try:
            # 使用正则表达式匹配目标内容
            pattern = re.compile(self.match_pattern, re.IGNORECASE)
            matches = pattern.findall(content)
            
            if not matches:
                self.logger.info("未检测到目标内容")
                return
            
            # 处理匹配结果，去重
            new_matches = []
            for match in matches:
                if match not in self._detected_contents:
                    # 新内容，添加到已检测集合
                    self._detected_contents.add(match)
                    new_matches.append(match)
            
            if not new_matches:
                self.logger.info(f"检测到{len(matches)}条内容，均已处理过")
                return
            
            # 发送通知
            for match in new_matches:
                self.logger.info(f"检测到新内容：{match}")
                self.send_notification(match)
                
        except Exception as e:
            self.logger.error(f"检测目标内容失败：{str(e)}")
    
    def send_notification(self, matched_content: str):
        """发送通知"""
        if not self.notification_enable:
            return
        
        try:
            # 构建通知内容
            title = "群聊区监控通知"
            text = f"检测到特定格式的魔法上传信息：\n{matched_content}"
            
            # 发送通知事件
            self.eventmanager.send_event(
                EventType.NoticeMessage,
                {
                    "channel": self.notification_channel,
                    "type": NotificationType.info,
                    "title": title,
                    "text": text,
                    "userid": None
                }
            )
            
            self.logger.info("通知发送成功")
            
        except Exception as e:
            self.logger.error(f"发送通知失败：{str(e)}")
    
    def stop_service(self):
        """停止插件服务"""
        self.stop_monitor()
        self.logger.info("群聊区监控插件已停止服务")
    
    def get_api(self) -> dict:
        """获取插件API"""
        return {}
