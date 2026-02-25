"""
浏览器 Stealth 脚本 — 去除 CDP/自动化痕迹

通过 Page.addScriptToEvaluateOnNewDocument 在页面加载前注入，
使 Stripe、Cloudflare 等风控系统无法检测到自动化操作。

参考：puppeteer-extra-plugin-stealth
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================
# 核心 Stealth JS（在每个新文档加载前执行）
# ============================================================
STEALTH_JS = r"""
(function() {
    'use strict';

    // 1. 移除 navigator.webdriver 标记
    // CDP 连接时 Chromium 会自动设置 navigator.webdriver = true
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true,
    });

    // 2. 修复 navigator.plugins（自动化环境下可能为空数组）
    // Stripe 检测 plugins 长度为 0 视为可疑
    if (navigator.plugins.length === 0) {
        const fakePlugins = {
            length: 5,
            item: function(i) { return this[i] || null; },
            namedItem: function(name) {
                for (var k = 0; k < this.length; k++) {
                    if (this[k] && this[k].name === name) return this[k];
                }
                return null;
            },
            refresh: function() {},
        };
        var pluginData = [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
            { name: 'Chromium PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chromium PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
            { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
        ];
        for (var i = 0; i < pluginData.length; i++) {
            fakePlugins[i] = pluginData[i];
        }
        try {
            Object.defineProperty(navigator, 'plugins', {
                get: () => fakePlugins,
                configurable: true,
            });
        } catch(e) {}
    }

    // 3. 修复 navigator.mimeTypes
    if (navigator.mimeTypes.length === 0) {
        var fakeMimeTypes = { length: 2, item: function(i) { return this[i] || null; } };
        fakeMimeTypes[0] = { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' };
        fakeMimeTypes[1] = { type: 'text/pdf', suffixes: 'pdf', description: 'Portable Document Format' };
        try {
            Object.defineProperty(navigator, 'mimeTypes', {
                get: () => fakeMimeTypes,
                configurable: true,
            });
        } catch(e) {}
    }

    // 4. 修复 navigator.languages（自动化环境可能为空）
    if (!navigator.languages || navigator.languages.length === 0) {
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
            configurable: true,
        });
    }

    // 5. 修复 window.chrome 对象
    // 真实 Chrome 浏览器有 window.chrome.runtime 等属性
    if (!window.chrome) {
        window.chrome = {};
    }
    if (!window.chrome.runtime) {
        window.chrome.runtime = {
            connect: function() {},
            sendMessage: function() {},
            onMessage: { addListener: function() {}, removeListener: function() {} },
            id: undefined,
        };
    }

    // 6. 修复 Permissions API
    // 自动化浏览器的 Notification permission 状态异常
    try {
        var originalQuery = navigator.permissions.query;
        navigator.permissions.query = function(parameters) {
            if (parameters.name === 'notifications') {
                return Promise.resolve({ state: Notification.permission });
            }
            return originalQuery.call(this, parameters);
        };
    } catch(e) {}

    // 7. 修复 iframe contentWindow 检测
    // 自动化环境下 iframe.contentWindow 可能暴露异常
    try {
        var iframeProto = HTMLIFrameElement.prototype;
        var origDesc = Object.getOwnPropertyDescriptor(iframeProto, 'contentWindow');
        if (origDesc) {
            Object.defineProperty(iframeProto, 'contentWindow', {
                get: function() {
                    var win = origDesc.get.call(this);
                    if (win) {
                        try {
                            // 确保 iframe 内的 navigator.webdriver 也是 undefined
                            Object.defineProperty(win.navigator, 'webdriver', {
                                get: () => undefined,
                                configurable: true,
                            });
                        } catch(e) {}
                    }
                    return win;
                },
                configurable: true,
            });
        }
    } catch(e) {}

    // 8. 移除 document 上的 cdc_ 前缀属性
    // ChromeDriver / CDP 会在 document 上注入 cdc_ 开头的属性
    try {
        var props = Object.getOwnPropertyNames(document);
        for (var j = 0; j < props.length; j++) {
            if (props[j].match && props[j].match(/^cdc_/)) {
                delete document[props[j]];
            }
        }
    } catch(e) {}

    // 9. 修复 toString() 检测
    // 风控脚本会检查原生函数的 toString 是否被篡改
    var nativeToString = Function.prototype.toString;
    var customFunctions = new WeakSet();

    function maskFunction(fn, nativeName) {
        customFunctions.add(fn);
    }

    try {
        Function.prototype.toString = function() {
            if (customFunctions.has(this)) {
                return 'function ' + (this.name || '') + '() { [native code] }';
            }
            return nativeToString.call(this);
        };
        maskFunction(Function.prototype.toString, 'toString');
    } catch(e) {}

    // 10. 修复 window.outerHeight / outerWidth
    // 自动化环境下 outerHeight 可能为 0（无头模式）或等于 innerHeight（异常）
    if (window.outerHeight === 0) {
        Object.defineProperty(window, 'outerHeight', {
            get: () => window.innerHeight + 85,
            configurable: true,
        });
    }
    if (window.outerWidth === 0) {
        Object.defineProperty(window, 'outerWidth', {
            get: () => window.innerWidth + 16,
            configurable: true,
        });
    }

    // 11. 修复 navigator.connection（部分指纹浏览器缺失此 API）
    if (!navigator.connection) {
        try {
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    downlink: 10,
                    effectiveType: '4g',
                    rtt: 50,
                    saveData: false,
                    onchange: null,
                }),
                configurable: true,
            });
        } catch(e) {}
    }

    // 12. 修复 navigator.hardwareConcurrency（为 0 或 undefined 时异常）
    if (!navigator.hardwareConcurrency || navigator.hardwareConcurrency < 2) {
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8,
            configurable: true,
        });
    }

    // 13. 修复 navigator.deviceMemory（部分环境缺失）
    if (!navigator.deviceMemory) {
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8,
            configurable: true,
        });
    }

    // 14. 修复 navigator.maxTouchPoints（桌面环境应为 0）
    // 部分指纹浏览器错误地设置了 touch 属性
    // 不做修改，保持浏览器默认值

    // 15. 修复 console.debug 检测（Chromium DevTools 打开时的行为差异）
    // 保持原生行为即可

})();
"""


def inject_stealth(page: Any) -> bool:
    """在浏览器页面注入 stealth 脚本，去除自动化痕迹。

    使用 CDP 的 Page.addScriptToEvaluateOnNewDocument 确保：
    - 脚本在每个新页面/iframe 加载前执行
    - 风控脚本无法在 stealth 注入前检测到自动化痕迹

    Args:
        page: DrissionPage 的 ChromiumPage 实例

    Returns:
        bool: 是否注入成功
    """
    try:
        # 1. 注册到所有未来的新文档（包括导航、iframe）
        page.run_cdp(
            "Page.addScriptToEvaluateOnNewDocument",
            source=STEALTH_JS,
        )

        # 2. 立即在当前页面执行一次（当前页面可能已经加载）
        page.run_js(STEALTH_JS, timeout=5)

        logger.info("stealth script injected successfully")
        return True
    except Exception as e:
        logger.warning(f"stealth injection failed: {e}")
        # 降级：至少尝试在当前页面执行
        try:
            page.run_js(STEALTH_JS, timeout=5)
            logger.info("stealth script injected (current page only, no CDP)")
            return True
        except Exception as e2:
            logger.warning(f"stealth fallback also failed: {e2}")
            return False
