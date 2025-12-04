// iframe监控脚本
// 用于实时监控群聊区iframe内容变化并识别特定内容

class IframeMonitor {
    constructor(iframeId, targetContent, options = {}) {
        this.iframeId = iframeId;
        this.targetContent = targetContent;
        this.options = {
            checkInterval: options.checkInterval || 120000, // 默认2分钟检查一次
            notificationType: options.notificationType || 'console', // 通知类型：console, alert, custom
            customNotification: options.customNotification || null, // 自定义通知函数
            ...options
        };
        
        this.iframe = null;
        this.lastContent = '';
        this.monitoring = false;
        this.checkTimer = null;
        this.mutationObserver = null;
        this.lastCheckTime = 0; // 上次检查时间，用于防抖
        this.detectedContents = new Set(); // 存储已检测过的内容，用于去重
        
        this.init();
    }
    
    // 初始化监控
    init() {
        this.iframe = document.getElementById(this.iframeId);
        if (!this.iframe) {
            console.error(`无法找到ID为${this.iframeId}的iframe元素`);
            return;
        }
        
        // 监听iframe加载完成事件
        this.iframe.addEventListener('load', () => {
            console.log('iframe加载完成，开始监控');
            this.startMonitoring();
        });
        
        // 如果iframe已经加载完成，直接开始监控
        if (this.iframe.contentDocument && this.iframe.contentDocument.readyState === 'complete') {
            console.log('iframe已加载，开始监控');
            this.startMonitoring();
        }
    }
    
    // 开始监控
    startMonitoring() {
        if (this.monitoring) return;
        
        this.monitoring = true;
        
        // 使用MutationObserver监控DOM变化
        this.setupMutationObserver();
        
        // 同时使用定时检查作为兜底方案
        this.startPeriodicCheck();
        
        // 初始检查
        this.checkContent();
    }
    
    // 设置MutationObserver
    setupMutationObserver() {
        try {
            const iframeDoc = this.iframe.contentDocument || this.iframe.contentWindow.document;
            
            this.mutationObserver = new MutationObserver((mutations) => {
                // 当检测到DOM变化时，检查内容
                this.checkContent();
            });
            
            // 配置观察选项
            const observerOptions = {
                childList: true,
                subtree: true,
                characterData: true,
                attributes: false
            };
            
            // 开始观察
            this.mutationObserver.observe(iframeDoc.body, observerOptions);
            console.log('MutationObserver已启动');
        } catch (error) {
            console.error('设置MutationObserver失败:', error);
        }
    }
    
    // 开始定期检查
    startPeriodicCheck() {
        this.checkTimer = setInterval(() => {
            this.checkContent();
        }, this.options.checkInterval);
        console.log(`定期检查已启动，间隔: ${this.options.checkInterval}ms`);
    }
    
    // 检查iframe内容
    checkContent() {
        try {
            // 防抖机制：确保在checkInterval时间内只执行一次检查
            const now = Date.now();
            if (now - this.lastCheckTime < this.options.checkInterval) {
                return;
            }
            this.lastCheckTime = now;
            
            const iframeDoc = this.iframe.contentDocument || this.iframe.contentWindow.document;
            const currentContent = iframeDoc.body.innerText || iframeDoc.body.textContent;
            
            // 内容未变化，跳过
            if (currentContent === this.lastContent) return;
            
            this.lastContent = currentContent;
            console.log('检测到内容变化');
            
            // 检查是否包含目标内容
            this.detectTargetContent(currentContent);
        } catch (error) {
            console.error('检查iframe内容失败:', error);
        }
    }
    
    // 检测目标内容
    detectTargetContent(content) {
        // 支持字符串或正则表达式匹配
        let matches = [];
        
        if (typeof this.targetContent === 'string') {
            if (content.includes(this.targetContent)) {
                matches.push(this.targetContent);
            }
        } else if (this.targetContent instanceof RegExp) {
            // 使用matchAll获取所有匹配的内容
            const regexMatches = content.matchAll(this.targetContent);
            for (const match of regexMatches) {
                matches.push(match[0]);
            }
        } else if (Array.isArray(this.targetContent)) {
            // 支持多个目标内容
            for (const target of this.targetContent) {
                if (typeof target === 'string') {
                    if (content.includes(target)) {
                        matches.push(target);
                    }
                } else if (target instanceof RegExp) {
                    const regexMatches = content.matchAll(target);
                    for (const match of regexMatches) {
                        matches.push(match[0]);
                    }
                }
            }
        }
        
        // 处理匹配结果，去重
        for (const match of matches) {
            if (!this.detectedContents.has(match)) {
                // 新内容，触发通知
                this.detectedContents.add(match);
                console.log('检测到目标内容:', match);
                this.triggerNotification(match);
            } else {
                // 已检测过的内容，忽略
                console.log('已检测过的内容，忽略:', match);
            }
        }
    }
    
    // 触发通知
    triggerNotification(matchedContent) {
        switch (this.options.notificationType) {
            case 'alert':
                alert(`检测到目标内容: ${matchedContent}`);
                break;
            case 'custom':
                if (typeof this.options.customNotification === 'function') {
                    this.options.customNotification(matchedContent);
                }
                break;
            case 'console':
            default:
                console.log(`🚨 检测到目标内容: ${matchedContent}`);
                break;
        }
    }
    
    // 停止监控
    stopMonitoring() {
        if (!this.monitoring) return;
        
        this.monitoring = false;
        
        // 停止MutationObserver
        if (this.mutationObserver) {
            this.mutationObserver.disconnect();
            this.mutationObserver = null;
            console.log('MutationObserver已停止');
        }
        
        // 停止定期检查
        if (this.checkTimer) {
            clearInterval(this.checkTimer);
            this.checkTimer = null;
            console.log('定期检查已停止');
        }
        
        console.log('监控已停止');
    }
    
    // 重启监控
    restartMonitoring() {
        this.stopMonitoring();
        this.startMonitoring();
    }
    
    // 获取当前iframe内容
    getCurrentContent() {
        try {
            const iframeDoc = this.iframe.contentDocument || this.iframe.contentWindow.document;
            return iframeDoc.body.innerText || iframeDoc.body.textContent;
        } catch (error) {
            console.error('获取当前内容失败:', error);
            return '';
        }
    }
}

// 使用示例
// 当页面加载完成后初始化监控
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initMonitor();
    });
} else {
    initMonitor();
}

function initMonitor() {
    // 自定义通知函数示例
    const customNotify = (content) => {
        console.log('自定义通知:', content);
        // 可以在这里添加更多自定义逻辑，比如发送请求、更新UI等
    };
    
    // 创建监控实例
    window.iframeMonitor = new IframeMonitor(
        'sbcontent', // iframe的ID
        /完成了一次上传\d+\.\d{2}下载0\.00的魔法, 持续\d+天\d+小时/, // 使用正则表达式匹配特定格式的魔法上传信息
        {
            checkInterval: 120000, // 每2分钟检查一次
            notificationType: 'console', // 使用控制台通知
            // customNotification: customNotify, // 使用自定义通知
        }
    );
    
    console.log('iframe监控脚本已初始化');
}

// 提供全局控制方法
window.IframeMonitor = IframeMonitor;