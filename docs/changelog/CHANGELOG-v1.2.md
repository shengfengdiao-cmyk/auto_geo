# AutoGeo v1.2 更新日志

**发布日期**: 2026-01-10
**版本**: v1.2
**主题**: 百家号弹窗关闭修复

---

## 概述

修复了百家号新手教程弹窗关闭逻辑，从错误的"下一步"按钮点击改为精确点击弹窗右上角的×关闭按钮。

---

## 问题分析

### 原始问题
- 用户反馈："fw还是点下一步，没有点到×号"
- 原代码使用通用选择器（如 `*:has-text('×')`）无法准确定位×按钮
- 错误地包含了 `"button:has-text('下一步')"` 选择器

### 根本原因
通过 Playwright MCP 实际分析页面结构，发现新手教程弹窗的实际 DOM 结构：

```
- generic [弹窗容器]:
  - button [ref=e517]:  ← 这是×号关闭按钮！
    - img
  - generic: 图文编辑能力升级
  - generic: 快来试试新增的功能吧
  - generic:
    - generic: 1/4
    - button "下一步":  ← 这是SB按钮，不能点！
```

**关键发现**：
- ×按钮是弹窗容器内的**第一个** button 元素
- "下一步"按钮也在弹窗内，但不是我们想点的
- 弹窗容器包含"图文编辑能力升级"或"快来试试新增的功能吧"文本

---

## 核心改动

### 1. 后端改动

#### `backend/services/playwright/publishers/baijiahao.py`

**修改方法**：`_close_popups(page)`

**新的弹窗关闭逻辑**：

```python
# 核心方法：精确点击新手教程的×按钮
closed = await page.evaluate("""() => {
    const allElements = document.querySelectorAll('*');

    for (let el of allElements) {
        const text = el.textContent?.trim() || '';

        // 找到包含"图文编辑能力升级"或"快来试试新增的功能吧"的容器
        if (text.includes('图文编辑能力升级') || text.includes('快来试试新增的功能吧')) {
            // 在这个容器内找到第一个button（就是×关闭按钮）
            const closeButton = el.querySelector('button');
            if (closeButton && closeButton.offsetParent !== null) {
                closeButton.click();
                return { success: true, method: 'newbie_tutorial_close_button' };
            }
        }
    }
    return { success: false, reason: 'no_newbie_tutorial_found' };
}""")

if closed.get('success'):
    logger.info(f"[百家号] 成功关闭新手教程弹窗: {closed.get('method')}")
    return
```

**改动要点**：
1. 精确查找包含"图文编辑能力升级"文本的弹窗容器
2. 在容器内找到第一个 button 元素（×按钮）
3. 移除了所有可能导致点击"下一步"的选择器
4. 简化了备用方法，只保留必要的通用关闭逻辑

### 2. 测试脚本改动

#### `backend/test_baijiahao_publish.py`

**同样的弹窗关闭逻辑应用到测试脚本**，确保测试环境与生产环境一致。

**移除的选择器**：
- `"button:has-text('下一步')"`  ← 这是罪魁祸首！

**新增的精确 JavaScript**：
```javascript
close_popup_js = """
    () => {
        const allElements = document.querySelectorAll('*');
        for (let el of allElements) {
            const text = el.textContent?.trim() || '';
            // 找到包含新手教程文本的容器
            if (text.includes('图文编辑能力升级') || text.includes('快来试试新增的功能吧')) {
                // 在这个容器内找到第一个button（就是×关闭按钮）
                const closeButton = el.querySelector('button');
                if (closeButton && closeButton.offsetParent !== null) {
                    closeButton.click();
                    return { success: true, method: 'newbie_tutorial_close' };
                }
            }
        }
        return { success: false, reason: 'not_found' };
    }
"""
```

---

## 修复验证

### 测试方法
1. 使用已保存的 cookies 加载百家号编辑页面
2. 等待新手教程弹窗出现
3. 执行新的弹窗关闭逻辑
4. 验证弹窗被正确关闭（不是点击"下一步"）

### 预期结果
- ✅ 弹窗被关闭
- ✅ 没有点击"下一步"按钮
- ✅ 页面可以正常填充标题和正文

---

## 文件修改清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/services/playwright/publishers/baijiahao.py` | 修改 | 重写 `_close_popups` 方法 |
| `backend/test_baijiahao_publish.py` | 修改 | 更新弹窗关闭测试逻辑 |
| `docs/overview/DEV_SUMMARY.md` | 文档 | 版本历史更新到 v1.2 |
| `docs/changelog/CHANGELOG-v1.2.md` | 新增 | 本次更新日志 |

---

## 技术总结

### 经验教训
1. **不要依赖通用选择器**：`*:has-text('×')` 在复杂页面中可能匹配到错误的元素
2. **先分析页面结构**：使用 Playwright MCP 等工具实际查看 DOM 结构后再编写选择器
3. **避免模糊匹配**：`button:has-text('下一步')` 这种选择器在不知道确切结构时非常危险
4. **精确匹配 > 通用匹配**：通过包含特定文本的容器定位，然后在容器内查找目标元素，更可靠

### 最佳实践
```javascript
// ❌ 错误方式：模糊选择器
const buttons = document.querySelectorAll('button');
for (let btn of buttons) {
    if (btn.textContent.includes('×')) btn.click();
}

// ✅ 正确方式：先定位容器，再找目标元素
for (let el of document.querySelectorAll('*')) {
    if (el.textContent.includes('弹窗特征文本')) {
        const closeBtn = el.querySelector('button');  // 第一个button是关闭按钮
        if (closeBtn) closeBtn.click();
        break;
    }
}
```

---

## 已知问题

无

---

## 下一步

- [ ] 完整测试百家号发布流程（标题填充 → 正文填充 → 发布）
- [ ] 验证其他平台是否有类似的弹窗问题
- [ ] 优化弹窗关闭逻辑，使其可复用于其他平台
