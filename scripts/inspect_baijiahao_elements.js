/**
 * 百家号首页元素结构爬取脚本
 * 用于获取页面上关键按钮的真实HTML结构和选择器
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// 创建输出目录
const outputDir = path.join(__dirname, '..', 'inspection_results');
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

// 主函数
(async () => {
  console.log('='.repeat(60));
  console.log('百家号首页元素结构爬取脚本');
  console.log('='.repeat(60));

  let browser = null;
  let context = null;
  let page = null;

  try {
    // 启动浏览器
    console.log('\n[1/5] 启动浏览器...');
    browser = await chromium.launch({
      headless: false,
      slowMo: 200,
      args: [
        '--disable-blink-features=AutomationControlled',
        '--start-maximized',
      ]
    });

    context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      locale: 'zh-CN',
      timezoneId: 'Asia/Shanghai',
    });

    page = await context.newPage();

    // 尝试加载保存的cookies
    const authFile = path.join(__dirname, '..', 'baijiahao_auth.json');
    if (fs.existsSync(authFile)) {
      try {
        const cookies = JSON.parse(fs.readFileSync(authFile, 'utf8'));
        await context.addCookies(cookies);
        console.log('✅ 已加载保存的登录状态');
      } catch (e) {
        console.log('⚠️ 加载cookies失败:', e.message);
      }
    }

    console.log('✅ 浏览器启动成功');

    // 访问百家号首页
    console.log('\n[2/5] 访问百家号首页...');
    const targetUrl = 'https://baijiahao.baidu.com/builder/rc/static/edit/index';
    await page.goto(targetUrl, {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    // 等待页面稳定
    await page.waitForTimeout(3000);

    // 检查是否需要登录
    const currentUrl = page.url();
    console.log('当前URL:', currentUrl);

    if (currentUrl.includes('passport.baidu.com') || currentUrl.includes('login')) {
      console.log('\n⚠️ 需要登录，请在浏览器中手动登录...');
      console.log('⏳ 等待登录中（最多等待120秒）...');

      // 等待登录
      for (let i = 0; i < 60; i++) {
        await page.waitForTimeout(2000);
        const url = page.url();
        if (!url.includes('passport.baidu.com') && !url.includes('login')) {
          console.log('✅ 登录成功！');

          // 保存cookies
          const cookies = await context.cookies();
          fs.writeFileSync(authFile, JSON.stringify(cookies, null, 2));
          console.log('💾 登录状态已保存');

          // 重新访问目标页面
          await page.goto(targetUrl, { waitUntil: 'networkidle' });
          await page.waitForTimeout(3000);
          break;
        }
        process.stdout.write(`\r   等待中... ${120 - i * 2}秒`);
      }
      console.log('');
    }

    console.log('✅ 页面加载完成');

    // 截图
    const screenshotPath = path.join(outputDir, '01_homepage.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log('📸 截图已保存:', screenshotPath);

    // 保存完整HTML
    console.log('\n[3/5] 保存页面完整HTML...');
    const htmlContent = await page.content();
    const htmlPath = path.join(outputDir, 'page_source.html');
    fs.writeFileSync(htmlPath, htmlContent, 'utf8');
    console.log('💾 HTML已保存:', htmlPath);

    // 查找关键元素
    console.log('\n[4/5] 查找关键元素...');

    const results = {
      timestamp: new Date().toISOString(),
      url: page.url(),
      elements: {}
    };

    // 1. 查找"+"号按钮
    console.log('\n   查找 "+" 号按钮...');
    const plusButtonSelectors = [
      'button:has-text("+")',
      'span:has-text("+")',
      'a:has-text("+")',
      '[class*="plus"]',
      '[class*="add"]',
      '[class*="create"]',
      'button[class*="icon"]',
      '.add-button',
      '.create-btn',
    ];

    results.elements.plusButtons = [];
    for (const selector of plusButtonSelectors) {
      try {
        const elements = await page.$$(selector);
        for (const el of elements) {
          const isVisible = await el.isVisible().catch(() => false);
          if (isVisible) {
            const html = await el.evaluate((e) => e.outerHTML);
            const box = await el.boundingBox();
            results.elements.plusButtons.push({
              selector,
              html,
              position: box
            });
          }
        }
      } catch (e) {
        // 忽略错误
      }
    }

    // 2. 查找"发布"相关按钮
    console.log('   查找 "发布" 相关按钮...');
    const publishSelectors = [
      'button:has-text("发布")',
      'a:has-text("发布")',
      'span:has-text("发布")',
      '[class*="publish"]',
      '[class*="Publish"]',
      '[class*="submit"]',
    ];

    results.elements.publishButtons = [];
    for (const selector of publishSelectors) {
      try {
        const elements = await page.$$(selector);
        for (const el of elements) {
          const isVisible = await el.isVisible().catch(() => false);
          if (isVisible) {
            const html = await el.evaluate((e) => e.outerHTML);
            const text = await el.evaluate((e) => e.textContent?.trim() || '');
            const box = await el.boundingBox();
            results.elements.publishButtons.push({
              selector,
              text,
              html,
              position: box
            });
          }
        }
      } catch (e) {
        // 忽略错误
      }
    }

    // 3. 查找"作品"、"图文"、"文章"相关按钮
    console.log('   查找 "作品/图文/文章" 相关按钮...');
    const contentSelectors = [
      'button:has-text("作品")',
      'a:has-text("作品")',
      'button:has-text("图文")',
      'a:has-text("图文")',
      'button:has-text("文章")',
      'a:has-text("文章")',
      'button:has-text("写文章")',
      'a:has-text("写文章")',
      '[class*="article"]',
      '[class*="Article"]',
      '[class*="content"]',
    ];

    results.elements.contentButtons = [];
    for (const selector of contentSelectors) {
      try {
        const elements = await page.$$(selector);
        for (const el of elements) {
          const isVisible = await el.isVisible().catch(() => false);
          if (isVisible) {
            const html = await el.evaluate((e) => e.outerHTML);
            const text = await el.evaluate((e) => e.textContent?.trim() || '');
            const box = await el.boundingBox();
            results.elements.contentButtons.push({
              selector,
              text,
              html,
              position: box
            });
          }
        }
      } catch (e) {
        // 忽略错误
      }
    }

    // 4. 查找弹窗/引导层
    console.log('   查找弹窗/引导层...');
    const modalSelectors = [
      '[class*="modal"]',
      '[class*="Modal"]',
      '[class*="dialog"]',
      '[class*="Dialog"]',
      '[class*="popup"]',
      '[class*="Popup"]',
      '[class*="overlay"]',
      '[class*="mask"]',
      '[role="dialog"]',
      '.ant-modal',
      '.el-dialog',
      '.van-popup',
    ];

    results.elements.modals = [];
    for (const selector of modalSelectors) {
      try {
        const elements = await page.$$(selector);
        for (const el of elements) {
          const isVisible = await el.isVisible().catch(() => false);
          if (isVisible) {
            const html = await el.evaluate((e) => e.outerHTML);
            const box = await el.boundingBox();
            results.elements.modals.push({
              selector,
              html,
              position: box
            });
          }
        }
      } catch (e) {
        // 忽略错误
      }
    }

    // 5. 使用JavaScript获取所有可见按钮
    console.log('   获取所有可见按钮...');
    const allButtons = await page.evaluate(() => {
      const buttons = [];

      // 获取所有button元素
      document.querySelectorAll('button').forEach(btn => {
        const rect = btn.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          buttons.push({
            tag: 'button',
            text: btn.textContent?.trim().substring(0, 50) || '',
            class: btn.className,
            id: btn.id,
            html: btn.outerHTML.substring(0, 200)
          });
        }
      });

      // 获取所有a标签
      document.querySelectorAll('a').forEach(link => {
        const rect = link.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          buttons.push({
            tag: 'a',
            text: link.textContent?.trim().substring(0, 50) || '',
            class: link.className,
            id: link.id,
            href: link.getAttribute('href'),
            html: link.outerHTML.substring(0, 200)
          });
        }
      });

      return buttons;
    });

    results.elements.allButtons = allButtons;

    // 保存结果
    console.log('\n[5/5] 保存爬取结果...');
    const resultsPath = path.join(outputDir, 'element_inspection_results.json');
    fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2), 'utf8');
    console.log('💾 结果已保存:', resultsPath);

    // 打印关键发现
    console.log('\n' + '='.repeat(60));
    console.log('爬取结果汇总:');
    console.log('='.repeat(60));

    console.log(`\n✅ "+"号按钮: ${results.elements.plusButtons.length} 个`);
    results.elements.plusButtons.forEach((btn, i) => {
      console.log(`   [${i + 1}] selector: ${btn.selector}`);
      console.log(`       HTML: ${btn.html.substring(0, 100)}...`);
    });

    console.log(`\n✅ "发布"相关按钮: ${results.elements.publishButtons.length} 个`);
    results.elements.publishButtons.forEach((btn, i) => {
      console.log(`   [${i + 1}] text: "${btn.text}"`);
      console.log(`       selector: ${btn.selector}`);
      console.log(`       HTML: ${btn.html.substring(0, 100)}...`);
    });

    console.log(`\n✅ "作品/图文/文章"相关按钮: ${results.elements.contentButtons.length} 个`);
    results.elements.contentButtons.forEach((btn, i) => {
      console.log(`   [${i + 1}] text: "${btn.text}"`);
      console.log(`       selector: ${btn.selector}`);
    });

    console.log(`\n✅ 弹窗/引导层: ${results.elements.modals.length} 个`);
    results.elements.modals.forEach((modal, i) => {
      console.log(`   [${i + 1}] selector: ${modal.selector}`);
    });

    console.log(`\n✅ 所有可见按钮: ${allButtons.length} 个`);

    // 打印推荐的选择器
    console.log('\n' + '='.repeat(60));
    console.log('推荐的选择器:');
    console.log('='.repeat(60));

    // 找出包含"发布"的按钮
    const publishBtns = allButtons.filter(b =>
      b.text.includes('发布') || b.text.includes('作品') || b.text.includes('图文') || b.text.includes('文章')
    );

    if (publishBtns.length > 0) {
      console.log('\n推荐使用以下选择器定位发布按钮:');
      publishBtns.forEach(btn => {
        if (btn.class) {
          console.log(`   - button.${btn.class.split(' ')[0]}`);
        }
        console.log(`   - button:has-text("${btn.text.substring(0, 20)}")`);
      });
    }

    console.log('\n' + '='.repeat(60));
    console.log('✅ 爬取完成！');
    console.log('='.repeat(60));
    console.log('\n文件保存位置:');
    console.log(`   截图: ${screenshotPath}`);
    console.log(`   HTML: ${htmlPath}`);
    console.log(`   JSON: ${resultsPath}`);
    console.log('\n按 Ctrl+C 关闭浏览器...');

    // 保持浏览器打开
    await new Promise(() => {});

  } catch (error) {
    console.error('\n❌ 发生错误:', error.message);
    console.error(error.stack);

    // 错误截图
    if (page) {
      const errorScreenshotPath = path.join(outputDir, 'error.png');
      await page.screenshot({ path: errorScreenshotPath, fullPage: true });
      console.log('📸 错误截图已保存:', errorScreenshotPath);
    }
  } finally {
    // 关闭浏览器
    if (browser) {
      await browser.close();
      console.log('\n✅ 浏览器已关闭');
    }
  }
})();
