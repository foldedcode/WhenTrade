#!/usr/bin/env node
/**
 * i18n-report: 生成当前多语言覆盖报告（不修改文件）。
 * - 扫描 web/src 中的 i18n 使用，提取“已使用的 key（字面量）”和“疑似动态 key 前缀）”。
 * - 读取 web/src/locales/{en-US,zh-CN}/*.json，汇总现有 key。
 * - 输出：每种语言缺失的 key、冗余的 key、疑似动态 key 前缀统计。
 */

const fs = require('fs')
const path = require('path')

const ROOT = path.resolve(__dirname, '..')
const SRC_DIR = path.join(ROOT, 'web/src')
const LOCALES_DIR = path.join(SRC_DIR, 'locales')
const LOCALE_NAMES = ['en-US', 'zh-CN']

function walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true })
  let files = []
  for (const e of entries) {
    if (e.name.startsWith('.')) continue
    const p = path.join(dir, e.name)
    if (e.isDirectory()) files = files.concat(walk(p))
    else files.push(p)
  }
  return files
}

function extractKeys(content) {
  const used = new Set()
  const dynamic = new Set()
  // $t('key')、i18n.global.t('key')、t('key')
  const reLiteralCalls = [
    /\$t\(\s*['"]([a-zA-Z0-9_.-]+)['"]\s*\)/g,
    /i18n\.global\.t\(\s*['"]([a-zA-Z0-9_.-]+)['"]\s*\)/g,
    /(?<![A-Za-z0-9_])t\(\s*['"]([a-zA-Z0-9_.-]+)['"]\s*\)/g,
  ]
  // meta: { titleKey: 'ns.xxx' }
  const reTitleKey = /titleKey\s*:\s*['"]([a-zA-Z0-9_.-]+)['"]/g
  // 动态：t('ns.xxx.' + var) 或 t(`ns.xxx.${var}`)
  const reDynamicConcat = /t\(\s*['"]([a-zA-Z0-9_.-]+\.)['"]\s*\+/g
  const reDynamicTpl = /t\(\s*`([a-zA-Z0-9_.-]+\.)\$\{/g

  const collect = (re) => {
    re.lastIndex = 0
    let m
    while ((m = re.exec(content)) !== null) used.add(m[1])
  }
  reLiteralCalls.forEach(collect)
  collect(reTitleKey)

  const collectDyn = (re) => {
    re.lastIndex = 0
    let m
    while ((m = re.exec(content)) !== null) dynamic.add(m[1])
  }
  collectDyn(reDynamicConcat)
  collectDyn(reDynamicTpl)

  return { used, dynamic }
}

function extractAllUsed() {
  const files = walk(SRC_DIR).filter((f) => /\.(vue|ts|js|tsx)$/.test(f))
  const used = new Set()
  const dynamic = new Set()
  for (const f of files) {
    const content = fs.readFileSync(f, 'utf8')
    const r = extractKeys(content)
    r.used.forEach((k) => used.add(k))
    r.dynamic.forEach((k) => dynamic.add(k))
  }
  return { used, dynamic }
}

function flatten(obj, prefix = '') {
  const out = {}
  for (const [k, v] of Object.entries(obj || {})) {
    const key = prefix ? `${prefix}.${k}` : k
    if (v && typeof v === 'object' && !Array.isArray(v)) Object.assign(out, flatten(v, key))
    else out[key] = v
  }
  return out
}

function listLocaleKeys() {
  const byLocale = {}
  for (const locale of LOCALE_NAMES) {
    const dir = path.join(LOCALES_DIR, locale)
    const files = fs.existsSync(dir)
      ? fs.readdirSync(dir).filter((f) => f.endsWith('.json'))
      : []
    const keys = new Set()
    const perNs = {}
    for (const file of files) {
      const ns = path.basename(file, '.json')
      try {
        const data = JSON.parse(fs.readFileSync(path.join(dir, file), 'utf8'))
        const flat = flatten(data)
        perNs[ns] = Object.keys(flat).length
        for (const k of Object.keys(flat)) keys.add(`${ns}.${k}`)
      } catch (e) {
        console.error('JSON parse failed:', path.join(dir, file), e.message)
      }
    }
    byLocale[locale] = { keys, perNs }
  }
  return byLocale
}

function main() {
  const { used, dynamic } = extractAllUsed()
  const locales = listLocaleKeys()

  const usedList = Array.from(used).sort()
  const dynamicList = Array.from(dynamic).sort()

  console.log('= i18n 使用报告（只读） =')
  console.log(`已解析使用中的字面量 key: ${usedList.length} 个`)
  console.log(`检测到疑似动态 key 前缀: ${dynamicList.length} 个`)
  if (dynamicList.length) {
    console.log('\n疑似动态 key 前缀（需人工确认保留子树）：')
    dynamicList.forEach((p) => console.log('  -', p + '*'))
  }

  for (const locale of LOCALE_NAMES) {
    const { keys } = locales[locale]
    const missing = usedList.filter((k) => !keys.has(k))
    const unused = Array.from(keys).filter((k) => !used.has(k) && !dynamicList.some((p) => k.startsWith(p)))

    console.log(`\n--- ${locale} ---`)
    console.log(`缺失: ${missing.length} 个`)
    if (missing.length) missing.forEach((k) => console.log('  +', k))

    console.log(`冗余: ${unused.length} 个`)
    if (unused.length) unused.forEach((k) => console.log('  -', k))
  }
}

if (require.main === module) main()

