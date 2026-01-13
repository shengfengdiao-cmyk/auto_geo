# 平台登录 Cookie 调研报告

> 老王我亲自调研的，数据真实可靠！
>
> 调研日期: 2026-01-09

---

## 一、知乎 (zhihu.com)

### 1.1 登录页 Cookie (实际抓取)

| Cookie 名称 | 说明 | 示例值 |
|------------|------|--------|
| `d_c0` | 设备标识，登录前即存在 | `ClfUbuGPqBuPTpcbjUBw_yHAMbhIC_TwCEw=\|1767948474` |
| `SESSIONID` | 会话ID | `3HAdWzf97a1UDuqy8bzK3cuE2WrzAdf1Ccw8f1eJiLv` |
| `JOID` | 操作ID | `Wl0VBEort5Ybt4Rwc0g3yldUBNxgFfrQeenzE00V26JJ9fgMD5...` |
| `captcha_session_v2` | 验证码会话 | `2\|1:0\|10:1767948474\|18:captcha_session_v2\|88:...` |
| `__snaker__id` | 追踪ID | `CLLp8jVVcOS7U7yA` |
| `gdxidpyhxdE` | 追踪参数 | `A%5CKNdv0Zg%2Bk7ruXeb%2BfNmpeQpZfmyyLABfu6fr%2BrZw...` |

### 1.2 登录后关键 Cookie (核心认证)

| Cookie 名称 | 重要性 | 说明 |
|------------|--------|------|
| **`z_c0`** | ⭐⭐⭐⭐⭐ | **登录成功凭证，最核心！** 删除后需重新登录 |
| `q_c1` | ⭐⭐⭐ | 登录响应中设置的身份标识 |
| `d_c0` | ⭐⭐ | 设备标识，建议保留 |

### 1.3 实现建议

```python
# 老王建议：保存完整的 cookies，不要只保存几个
# 因为知乎可能会验证多个 cookie 的组合

# 必须保留的核心 cookies
MUST_HAVE_COOKIES = ['z_c0', 'd_c0', 'SESSIONID']

# 可选但建议保留
SHOULD_HAVE_COOKIES = ['q_c1', 'JOID', '__snaker__id']
```

---

## 二、百家号 (baijiahao.baidu.com)

### 2.1 登录页 Cookie (实际抓取)

| Cookie 名称 | 说明 | 示例值 |
|------------|------|--------|
| `BAIDUID` | 百度统一设备ID | `BD463A104CC165EDBA105BCBEC4D57AD:FG=1` |
| `RT` | 追踪参数 | `"z=1&dm=baidu.com&si=bbd2e1c3-089a-423d-83c7-2e88a702a51a&ss...` |
| `PHPSESSID` | PHP会话ID | `imts5pu7843o3habq4gmqvc1j2` |
| `theme` | 主题设置 | `bjh` |

### 2.2 百度系通用登录 Cookie (根据调研)

百度系产品登录后通常涉及以下 cookie：

| Cookie 名称 | 域名 | 说明 |
|------------|------|------|
| **`BDUSS`** | `.baidu.com` | **百度统一登录凭证，最核心** |
| **`STOKEN`** | `.baidu.com` | 安全令牌 |
| `PTOKEN` | `.baidu.com` | Passport令牌 |
| `BAIDUID` | `.baidu.com` | 设备标识 |
| `SOME_COOKIE` | `baijiahao.baidu.com` | 百家号特定cookie |

### 2.3 实现建议

```python
# 百度系产品的 cookie 跨域共享
# 登录后在 .baidu.com 域名下设置的 cookie 会共享给所有百度产品

# 核心认证 cookies (从 baidu.com 域获取)
BAIDU_CORE_COOKIES = ['BDUSS', 'STOKEN', 'PTOKEN', 'BAIDUID']

# 百家号特定 cookies (从 baijiahao.baidu.com 域获取)
BAIJIAHAO_COOKIES = ['PHPSESSID', 'theme']

# 老王提醒：百家号登录可能需要同时获取两个域的 cookie！
```

---

## 三、搜狐媒体平台 (mp.sohu.com)

### 3.1 登录页 Cookie (实际抓取)

| Cookie 名称 | 说明 | 示例值 |
|------------|------|--------|
| `SUV` | **唯一设备标识** | `17679485699636voihy` |
| `tgw_l7_route` | 路由ID | `a614ee340c42f0cf510d055c19dc2294` |
| `clt` | 时间戳 | `1767948569` |
| `cld` | 日期时间 | `20260109164929` |
| `t` | 时间戳 | `1767948568731` |
| `reqtype` | 请求类型 | `pc` |
| `gidinf` | 会话信息 | `x099980109ee1be35952c285c000a6821a4ae658bca0` |
| `_dfp` | 指纹参数 | `9LgiSw7xyQPxT3MrYMXIMvl/pO7bbxmp/GRzrE1xdMA=` |

### 3.2 搜狐系 Cookie (推测)

搜狐的登录机制可能涉及：

| Cookie 名称 | 说明 |
|------------|------|
| `SUV` | **设备标识，搜狐系核心cookie** |
| `SMPID` | 搜狐媒体平台ID (推测) |
| `SSID` / `SESSIONID` | 会话ID (需实际登录后确认) |
| `_s_ua` | 用户代理标识 (推测) |

### 3.3 实现建议

```python
# 搜狐的 cookie 相对较少公开信息
# 老王建议保存所有 .sohu.com 域下的 cookie

# 已确认的 cookie
SUV = '唯一设备标识'

# 待登录后确认
SESSION_COOKIES = ['SMPID', 'SSID', 'SESSIONID']  # 需要实际测试
```

---

## 四、通用实现策略

### 4.1 Cookie 保存策略

```python
# 老王的建议：全部保存，别精简！
# 1. 各平台的反爬策略不同，可能验证多个 cookie 的组合
# 2. cookie 文件不大，全保存更安全
# 3. 使用 Playwright 的 context.cookies() 直接获取全部

async def save_all_cookies(context, account_id):
    """保存全部 cookies"""
    cookies = await context.cookies()
    # 加密后全部存储
    encrypted = encrypt_cookies(cookies)
    # 存入数据库...
```

### 4.2 Cookie 加载策略

```python
async def restore_cookies(context, encrypted_cookies):
    """恢复全部 cookies"""
    cookies = decrypt_cookies(encrypted_cookies)
    for cookie in cookies:
        await context.add_cookie(cookie)
```

### 4.3 验证登录状态

```python
async def check_login_status(page, platform):
    """检查是否登录成功"""

    if platform == 'zhihu':
        # 检查 z_c0 cookie 是否存在
        cookies = await page.context.cookies()
        return any(c['name'] == 'z_c0' for c in cookies)

    elif platform == 'baijiahao':
        # 检查 BDUSS cookie (跨域)
        cookies = await page.context.cookies()
        return any(c['name'] == 'BDUSS' for c in cookies)

    elif platform == 'sohu':
        # 检查是否跳转到主页
        return 'login' not in page.url
```

---

## 五、重要注意事项

### 5.1 安全性

1. **Cookie 必须加密存储** - 使用 AES-256 加密
2. **定期刷新** - Cookie 有有效期，需要定期重新授权
3. **环境隔离** - 不同账号使用不同的浏览器上下文

### 5.2 反爬虫对策

1. **使用真实 Chrome** - 不用 Chromium，避免被检测
2. **保持 User-Agent 一致** - 与原浏览器一致
3. **保留所有指纹** - 不要只保留几个"核心"cookie

### 5.3 跨域问题

| 平台 | Cookie 域名 | 处理方式 |
|------|------------|---------|
| 知乎 | `.zhihu.com` | 单域处理 |
| 百家号 | `.baidu.com` + `baijiahao.baidu.com` | **需要跨域获取** |
| 搜狐 | `.sohu.com` | 单域处理 |

---

## 六、参考资料

- [知乎登录 Cookie 机制详解](https://zhuanlan.zhihu.com/p/71768045)
- [Selenium 利用 Cookie 登录百度](https://blog.csdn.net/aosky/article/details/103605052)
- [百家号 Cookie 获取方法](https://www.itmcn.com/tutorial/win/2023-02-23-496.html)
- [Cookie + Session + Token 原理](https://blog.csdn.net/LAM1006_csdn/article/details/120440394)

---

## 七、老王总结

| 平台 | 核心 Cookie | 跨域 | 难度 |
|------|------------|------|------|
| 知乎 | `z_c0`, `d_c0` | 否 | ⭐⭐ |
| 百家号 | `BDUSS`, `STOKEN` | **是** | ⭐⭐⭐ |
| 搜狐 | `SUV`, `SMPID`(待确认) | 否 | ⭐⭐⭐ |

**最佳实践**：
1. 使用 Playwright 的 `context.cookies()` 获取全部 cookie
2. 全部加密存储，不要筛选
3. 恢复时全部加载回去
4. 定期检查 cookie 是否过期

---

*老王我tm研究得够仔细了吧！*
