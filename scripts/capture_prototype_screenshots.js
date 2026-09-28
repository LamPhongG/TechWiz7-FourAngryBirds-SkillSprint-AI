const puppeteer = require('../frontend/node_modules/puppeteer-core');
const path = require('path');
const fs = require('fs');

const OUT_DIR = path.resolve(__dirname, '..', 'documentation', 'screenshots');
if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const BASE_URL = 'http://localhost:3000';

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function loginAs(page, email, password = 'Demo@123') {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle2' });
  await page.waitForSelector('input[type="email"]');
  
  // Clear and type
  await page.click('input[type="email"]', { clickCount: 3 });
  await page.keyboard.press('Backspace');
  await page.type('input[type="email"]', email);

  await page.click('input[type="password"]', { clickCount: 3 });
  await page.keyboard.press('Backspace');
  await page.type('input[type="password"]', password);

  await Promise.all([
    page.click('button[type="submit"]'),
    page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 10000 }).catch(() => {})
  ]);
  await sleep(1500);
}

async function main() {
  console.log('Launching browser to capture screenshots...');
  const browser = await puppeteer.launch({
    executablePath: EDGE_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1920,1080']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });

  try {
    // 1. Login Screen
    console.log('[1/10] Capturing 01_login_portal.png...');
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle2' });
    await sleep(1000);
    await page.screenshot({ path: path.join(OUT_DIR, '01_login_portal.png'), fullPage: false });

    // 2. HR Documents Repository
    console.log('[2/10] Capturing 02_hr_documents_repository.png...');
    await loginAs(page, 'hr@fourangrybirds.vn');
    await page.goto(`${BASE_URL}/hr/documents`, { waitUntil: 'networkidle2' });
    await sleep(2000);
    await page.screenshot({ path: path.join(OUT_DIR, '02_hr_documents_repository.png'), fullPage: false });

    // 3. HR Paths Studio
    console.log('[3/10] Capturing 03_hr_paths_studio.png...');
    await page.goto(`${BASE_URL}/hr/paths`, { waitUntil: 'networkidle2' });
    await sleep(2000);
    await page.screenshot({ path: path.join(OUT_DIR, '03_hr_paths_studio.png'), fullPage: false });

    // 4. Dual-Pipeline Comparison (Table 1)
    console.log('[4/10] Capturing 04_hr_dual_comparison_table1.png...');
    // Look for first path link or navigate directly to PATH-001
    await page.goto(`${BASE_URL}/hr/paths`, { waitUntil: 'networkidle2' });
    await sleep(1000);
    const pathLinks = await page.$$('a[href*="/hr/paths/"], button[onClick*="paths"]');
    if (pathLinks.length > 0) {
      await pathLinks[0].click().catch(() => {});
      await sleep(2000);
    } else {
      await page.goto(`${BASE_URL}/hr/paths/PATH-001`, { waitUntil: 'networkidle2' });
      await sleep(2000);
    }
    
    // Switch to comparison tab
    const tabs = await page.$$('button');
    for (const tab of tabs) {
      const text = await page.evaluate(el => el.textContent, tab);
      if (text.includes('Đối chiếu') || text.includes('Comparison') || text.includes('Table 1')) {
        await tab.click();
        await sleep(1500);
        break;
      }
    }
    await page.screenshot({ path: path.join(OUT_DIR, '04_hr_dual_comparison_table1.png'), fullPage: false });

    // 5. HR Path Content & Editing
    console.log('[5/10] Capturing 05_hr_path_content_editor.png...');
    for (const tab of tabs) {
      const text = await page.evaluate(el => el.textContent, tab);
      if (text.includes('Nội dung') || text.includes('Content')) {
        await tab.click();
        await sleep(1500);
        break;
      }
    }
    await page.screenshot({ path: path.join(OUT_DIR, '05_hr_path_content_editor.png'), fullPage: false });

    // 6. Reviewer Approval Queue
    console.log('[6/10] Capturing 06_reviewer_approval_queue.png...');
    await loginAs(page, 'reviewer@fourangrybirds.vn');
    await page.goto(`${BASE_URL}/reviewer/dashboard`, { waitUntil: 'networkidle2' });
    await sleep(2000);
    await page.screenshot({ path: path.join(OUT_DIR, '06_reviewer_approval_queue.png'), fullPage: false });

    // 7. Reviewer Path Inspection
    console.log('[7/10] Capturing 07_reviewer_path_inspection.png...');
    await page.goto(`${BASE_URL}/reviewer/paths`, { waitUntil: 'networkidle2' });
    await sleep(1500);
    const revLinks = await page.$$('a[href*="/reviewer/paths/"], button[onClick*="paths"]');
    if (revLinks.length > 0) {
      await revLinks[0].click().catch(() => {});
      await sleep(2000);
    }
    await page.screenshot({ path: path.join(OUT_DIR, '07_reviewer_path_inspection.png'), fullPage: false });

    // 8. Employee Learning Portal
    console.log('[8/10] Capturing 08_employee_learning_portal.png...');
    await loginAs(page, 'alex.morgan@fourangrybirds.vn');
    await page.goto(`${BASE_URL}/employee/dashboard`, { waitUntil: 'networkidle2' });
    await sleep(2000);
    await page.screenshot({ path: path.join(OUT_DIR, '08_employee_learning_portal.png'), fullPage: false });

    // 9. HR Analytics & Reports
    console.log('[9/10] Capturing 09_hr_analytics_reports.png...');
    await loginAs(page, 'hr@fourangrybirds.vn');
    await page.goto(`${BASE_URL}/hr/reports`, { waitUntil: 'networkidle2' });
    await sleep(2000);
    await page.screenshot({ path: path.join(OUT_DIR, '09_hr_analytics_reports.png'), fullPage: false });

    // 10. Admin User Management
    console.log('[10/10] Capturing 10_admin_user_management.png...');
    await loginAs(page, 'admin@fourangrybirds.vn');
    await page.goto(`${BASE_URL}/admin/users`, { waitUntil: 'networkidle2' });
    await sleep(2000);
    await page.screenshot({ path: path.join(OUT_DIR, '10_admin_user_management.png'), fullPage: false });

    console.log('All 10 real prototype screenshots captured successfully!');
  } catch (err) {
    console.error('Error during screenshot capture:', err);
  } finally {
    await browser.close();
  }
}

main();
