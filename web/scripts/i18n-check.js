#!/usr/bin/env node

/**
 * i18n 键值检查脚本
 * 用于检测缺失键、冗余键和潜在问题
 */

import fs from 'fs';
import path from 'path';
import globPkg from 'glob';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const { glob } = globPkg;

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 配置
const CONFIG = {
  localesDir: path.join(__dirname, '../src/locales'),
  sourceDir: path.join(__dirname, '../src'),
  languages: ['en-US', 'zh-CN'],
  whitelistFile: path.join(__dirname, '../src/locales/dynamic-keys.json'),
  outputDir: path.join(__dirname, '../reports')
};

class I18nChecker {
  constructor() {
    this.translations = {};
    this.usedKeys = new Set();
    this.whitelist = [];
    this.issues = {
      missingKeys: [],
      unusedKeys: [],
      inconsistentKeys: [],
      dynamicKeys: []
    };
  }

  async run() {
    console.log('🔍 Starting i18n check...');
    
    try {
      await this.loadWhitelist();
      await this.loadTranslations();
      await this.scanUsage();
      await this.analyzeIssues();
      await this.generateReport();
      
      console.log('✅ i18n check completed successfully!');
      return this.issues;
    } catch (error) {
      console.error('❌ Error during i18n check:', error);
      process.exit(1);
    }
  }

  async loadWhitelist() {
    try {
      if (fs.existsSync(CONFIG.whitelistFile)) {
        const content = fs.readFileSync(CONFIG.whitelistFile, 'utf8');
        const data = JSON.parse(content);
        this.whitelist = data.whitelist || [];
        console.log(`📝 Loaded ${this.whitelist.length} whitelist patterns`);
      }
    } catch (error) {
      console.warn('⚠️  Could not load whitelist:', error.message);
    }
  }

  async loadTranslations() {
    for (const lang of CONFIG.languages) {
      const langDir = path.join(CONFIG.localesDir, lang);
      if (!fs.existsSync(langDir)) continue;

      this.translations[lang] = {};
      const files = fs.readdirSync(langDir).filter(file => file.endsWith('.json'));

      for (const file of files) {
        const filePath = path.join(langDir, file);
        const namespace = path.basename(file, '.json');
        
        try {
          const content = fs.readFileSync(filePath, 'utf8');
          this.translations[lang][namespace] = JSON.parse(content);
        } catch (error) {
          console.warn(`⚠️  Could not load ${filePath}:`, error.message);
        }
      }
    }

    console.log(`📚 Loaded translations for ${Object.keys(this.translations).length} languages`);
  }

  async scanUsage() {
    const patterns = [
      '**/*.vue',
      '**/*.ts', 
      '**/*.js',
      '**/*.tsx',
      '**/*.jsx'
    ];

    const files = [];
    for (const pattern of patterns) {
      const matches = glob.sync(pattern, { cwd: CONFIG.sourceDir });
      files.push(...matches.map(f => path.join(CONFIG.sourceDir, f)));
    }

    console.log(`🔎 Scanning ${files.length} source files...`);

    for (const file of files) {
      await this.scanFile(file);
    }

    console.log(`🔑 Found ${this.usedKeys.size} used translation keys`);
  }

  async scanFile(filePath) {
    try {
      const content = fs.readFileSync(filePath, 'utf8');
      
      // 匹配 i18n 使用模式 - 精确匹配避免误检测
      const patterns = [
        // Vue模板中的 $t() 用法
        /\$t\s*\(\s*['"`]([^'"`]+)['"`]/g,
        // 导入的 t() 函数用法（前面有空格、制表符或括号等）
        /(?:[\s\(\[\{,]|^)t\s*\(\s*['"`]([^'"`]+)['"`]/gm,
        // i18n实例的t方法
        /i18n\.t\s*\(\s*['"`]([^'"`]+)['"`]/g,
        // 复数形式
        /\$tc\s*\(\s*['"`]([^'"`]+)['"`]/g,
        /(?:[\s\(\[\{,]|^)tc\s*\(\s*['"`]([^'"`]+)['"`]/gm
      ];

      for (const pattern of patterns) {
        let match;
        while ((match = pattern.exec(content)) !== null) {
          // match[1] 是捕获组，但对于某些正则可能是match[2]
          const key = match[1] || match[2];
          if (key && key.length > 0 && !key.includes('{') && !key.includes('$') && key.includes('.')) {
            // 只有包含点号的才是真正的i18n键
            this.usedKeys.add(key);
          } else if (key && (key.includes('${') || key.includes('`'))) {
            // 动态键
            this.issues.dynamicKeys.push({
              file: path.relative(CONFIG.sourceDir, filePath),
              key: key,
              line: this.getLineNumber(content, match.index)
            });
          }
        }
      }
    } catch (error) {
      console.warn(`⚠️  Could not scan ${filePath}:`, error.message);
    }
  }

  getLineNumber(content, index) {
    const lines = content.substring(0, index).split('\n');
    return lines.length;
  }

  async analyzeIssues() {
    console.log('🔬 Analyzing issues...');
    
    // 收集所有定义的键
    const allDefinedKeys = new Set();
    const keysByLanguage = {};

    for (const [lang, namespaces] of Object.entries(this.translations)) {
      keysByLanguage[lang] = new Set();
      
      for (const [namespace, translations] of Object.entries(namespaces)) {
        const keys = this.flattenObject(translations, namespace);
        keys.forEach(key => {
          allDefinedKeys.add(key);
          keysByLanguage[lang].add(key);
        });
      }
    }

    // 检查缺失键
    for (const usedKey of this.usedKeys) {
      const missingIn = [];
      
      for (const lang of CONFIG.languages) {
        if (!keysByLanguage[lang] || !keysByLanguage[lang].has(usedKey)) {
          missingIn.push(lang);
        }
      }
      
      if (missingIn.length > 0) {
        this.issues.missingKeys.push({
          key: usedKey,
          missingIn: missingIn
        });
      }
    }

    // 检查未使用的键
    for (const definedKey of allDefinedKeys) {
      if (!this.usedKeys.has(definedKey) && !this.isWhitelisted(definedKey)) {
        this.issues.unusedKeys.push(definedKey);
      }
    }

    // 检查语言间不一致的键
    if (CONFIG.languages.length > 1) {
      const [lang1, lang2] = CONFIG.languages;
      const keys1 = keysByLanguage[lang1] || new Set();
      const keys2 = keysByLanguage[lang2] || new Set();
      
      for (const key of keys1) {
        if (!keys2.has(key)) {
          this.issues.inconsistentKeys.push({
            key: key,
            presentIn: [lang1],
            missingIn: [lang2]
          });
        }
      }
      
      for (const key of keys2) {
        if (!keys1.has(key)) {
          this.issues.inconsistentKeys.push({
            key: key,
            presentIn: [lang2],
            missingIn: [lang1]
          });
        }
      }
    }

    console.log(`📊 Analysis complete:
    - Missing keys: ${this.issues.missingKeys.length}
    - Unused keys: ${this.issues.unusedKeys.length}
    - Inconsistent keys: ${this.issues.inconsistentKeys.length}
    - Dynamic keys detected: ${this.issues.dynamicKeys.length}`);
  }

  flattenObject(obj, prefix = '', result = []) {
    for (const [key, value] of Object.entries(obj)) {
      const newKey = prefix ? `${prefix}.${key}` : key;
      
      if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        this.flattenObject(value, newKey, result);
      } else {
        result.push(newKey);
      }
    }
    return result;
  }

  isWhitelisted(key) {
    return this.whitelist.some(pattern => {
      const regex = new RegExp(pattern.pattern.replace('*', '.*'));
      return regex.test(key);
    });
  }

  async generateReport() {
    if (!fs.existsSync(CONFIG.outputDir)) {
      fs.mkdirSync(CONFIG.outputDir, { recursive: true });
    }

    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        totalUsedKeys: this.usedKeys.size,
        missingKeys: this.issues.missingKeys.length,
        unusedKeys: this.issues.unusedKeys.length,
        inconsistentKeys: this.issues.inconsistentKeys.length,
        dynamicKeys: this.issues.dynamicKeys.length
      },
      issues: this.issues
    };

    // 生成 JSON 报告
    const jsonPath = path.join(CONFIG.outputDir, `i18n-report-${Date.now()}.json`);
    fs.writeFileSync(jsonPath, JSON.stringify(report, null, 2));

    // 生成人类可读报告
    const mdPath = path.join(CONFIG.outputDir, `i18n-report-${Date.now()}.md`);
    const markdown = this.generateMarkdownReport(report);
    fs.writeFileSync(mdPath, markdown);

    console.log(`📄 Reports generated:
    - JSON: ${path.relative(process.cwd(), jsonPath)}
    - Markdown: ${path.relative(process.cwd(), mdPath)}`);

    // 输出摘要到控制台
    this.printSummary(report);
  }

  generateMarkdownReport(report) {
    return `# i18n 检查报告

**生成时间**: ${new Date(report.timestamp).toLocaleString()}

## 📊 摘要统计

- 使用的键: ${report.summary.totalUsedKeys}
- 缺失的键: ${report.summary.missingKeys}
- 未使用的键: ${report.summary.unusedKeys}
- 不一致的键: ${report.summary.inconsistentKeys}
- 动态键: ${report.summary.dynamicKeys}

## 🚫 缺失的键 (${report.issues.missingKeys.length})

${report.issues.missingKeys.map(item => 
  `- \`${item.key}\` (缺失于: ${item.missingIn.join(', ')})`
).join('\n')}

## 📦 未使用的键 (${report.issues.unusedKeys.length})

${report.issues.unusedKeys.slice(0, 50).map(key => `- \`${key}\``).join('\n')}
${report.issues.unusedKeys.length > 50 ? '\n... 以及其他 ' + (report.issues.unusedKeys.length - 50) + ' 个键\n' : ''}

## ⚠️ 不一致的键 (${report.issues.inconsistentKeys.length})

${report.issues.inconsistentKeys.map(item =>
  `- \`${item.key}\` (存在于: ${item.presentIn.join(', ')}, 缺失于: ${item.missingIn.join(', ')})`
).join('\n')}

## 🔧 动态键 (${report.issues.dynamicKeys.length})

${report.issues.dynamicKeys.slice(0, 20).map(item =>
  `- \`${item.key}\` 在 ${item.file}:${item.line}`
).join('\n')}
${report.issues.dynamicKeys.length > 20 ? '\n... 以及其他 ' + (report.issues.dynamicKeys.length - 20) + ' 个动态键\n' : ''}

---
*自动生成于 ${new Date().toISOString()}*
`;
  }

  printSummary(report) {
    console.log('\n📋 检查结果摘要:');
    console.log('─'.repeat(50));
    
    if (report.issues.missingKeys.length > 0) {
      console.log(`❌ 发现 ${report.issues.missingKeys.length} 个缺失键`);
    }
    
    if (report.issues.unusedKeys.length > 0) {
      console.log(`⚠️  发现 ${report.issues.unusedKeys.length} 个未使用键`);
    }
    
    if (report.issues.inconsistentKeys.length > 0) {
      console.log(`🔄 发现 ${report.issues.inconsistentKeys.length} 个不一致键`);
    }

    if (report.issues.dynamicKeys.length > 0) {
      console.log(`🔧 发现 ${report.issues.dynamicKeys.length} 个动态键使用`);
    }
    
    if (report.issues.missingKeys.length === 0 && 
        report.issues.inconsistentKeys.length === 0) {
      console.log('✅ 没有发现关键问题！');
    }
    
    console.log('─'.repeat(50));
  }
}

// 如果直接运行脚本
if (import.meta.url === `file://${process.argv[1]}`) {
  const checker = new I18nChecker();
  checker.run().catch(console.error);
}

export default I18nChecker;