// Run against a disposable seeded demo with Playwright on Node's module path.
// QA_UI_URL and QA_SEED_PASSWORD select the UI and its seeded users.
const assert = require('node:assert/strict')
const { chromium } = require('playwright')

async function run() {
  const baseURL = process.env.QA_UI_URL
  const password = process.env.QA_SEED_PASSWORD
  assert(baseURL && password, 'Set QA_UI_URL and QA_SEED_PASSWORD for the disposable demo')
  const browser = await chromium.launch({ channel: process.env.QA_CHROME_CHANNEL || 'chrome' })
  try {
    const context = await browser.newContext({ baseURL, viewport: { width: 375, height: 812 } })
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', (error) => errors.push(error.message))
    page.on('console', (message) => {
      if (message.type() === 'error') errors.push(message.text())
    })
    async function login(role) {
      const response = await context.request.post('/api/v1/auth/login', {
        data: { email: role + '@sunpower.test', password },
      })
      assert.equal(response.status(), 200)
    }
    await login('sales')
    for (const path of ['/', '/thank-you', '/enquiry']) {
      await page.goto(path, { waitUntil: 'networkidle' })
      await page.evaluate(() => document.fonts.ready)
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), path)
    }
    const name = 'Survey QA ' + Date.now()
    const enquiry = await context.request.post('/api/v1/public/enquiries', {
      data: { name, phone: '9' + Date.now().toString().slice(-9), address: 'QA roof',
        pincode: '560001', system_type: 'ON_GRID', requested_kw: 3 },
    })
    assert.equal(enquiry.status(), 201)
    const { lead_id } = (await enquiry.json()).data
    await page.goto('/surveys')
    await page.getByRole('button', { name: 'Schedule survey' }).click()
    const dialog = page.getByRole('dialog')
    await dialog.getByText(/No leads are ready|Choose lead/).first().waitFor({ state: 'attached' })
    assert.equal(await dialog.getByRole('option', { name: new RegExp(name) }).count(), 0)
    await page.goto('/leads/' + lead_id)
    await page.getByRole('button', { name: 'Ready for a survey', exact: true }).click()
    await page.getByRole('button', { name: 'Log Call', exact: true }).click()
    await page.getByRole('button', { name: 'Schedule survey' }).click()
    const lead = dialog.getByLabel('Lead', { exact: true })
    await lead.waitFor()
    assert.equal(await lead.inputValue(), String(lead_id))
    assert((await lead.locator('option:checked').innerText()).includes(name))
    const surveyor = dialog.getByLabel('Surveyor', { exact: true })
    const assigned = await surveyor.getByRole('option', { name: /Demo Surveyor/i }).getAttribute('value')
    await surveyor.selectOption(assigned)
    const tomorrow = new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 10)
    await dialog.getByLabel('Visit time').fill(tomorrow + 'T10:30')
    await dialog.getByRole('button', { name: 'Schedule survey' }).click()
    await page.waitForURL(/\/surveys\/\d+$/)
    const visitId = new URL(page.url()).pathname.split('/').at(-1)
    await login('surveyor')
    await page.goto('/surveys')
    await page.getByRole('link', { name: 'Survey #' + visitId, exact: true }).waitFor()
    await login('crew')
    await page.goto('/dashboard')
    await page.waitForURL(/\/installs$/)
    assert.deepEqual(errors, [])
    console.log('PASS mobile public pages, named survey scheduling, assigned visit and role redirect')
  } finally {
    await browser.close()
  }
}

run().catch((error) => { console.error(error); process.exitCode = 1 })
