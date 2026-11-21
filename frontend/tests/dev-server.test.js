import assert from 'node:assert/strict'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { test } from 'node:test'
import { devServerConfig } from '../vite.config.js'

test('a new frontend session retains the API selected in the repo .env', () => {
  const dir = mkdtempSync(join(tmpdir(), 'sunpower-proxy-'))
  const previous = process.env.API_PROXY_TARGET
  delete process.env.API_PROXY_TARGET
  try {
    writeFileSync(join(dir, '.env'), 'API_PROXY_TARGET=http://127.0.0.1:8102\nPOSTGRES_PASSWORD=private\n')
    for (let restart = 0; restart < 2; restart++) {
      const server = devServerConfig('development', dir)
      assert.equal(server.proxy['/api'].target, 'http://127.0.0.1:8102')
      assert.equal(server.strictPort, true)
      assert.equal(JSON.stringify(server).includes('private'), false)
    }
    process.env.API_PROXY_TARGET = 'http://127.0.0.1:8199'
    assert.equal(devServerConfig('development', dir).proxy['/api'].target, 'http://127.0.0.1:8199')
    delete process.env.API_PROXY_TARGET
    writeFileSync(join(dir, '.env'), '')
    assert.equal(devServerConfig('development', dir).proxy['/api'].target, 'http://127.0.0.1:8000')
  } finally {
    if (previous === undefined) delete process.env.API_PROXY_TARGET
    else process.env.API_PROXY_TARGET = previous
    rmSync(dir, { recursive: true })
  }
})
