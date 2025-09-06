# i18n 国际化管理指南

本目录包含 When.Trade 项目的所有国际化翻译文件和管理工具。

## 📁 目录结构

```
locales/
├── en-US/                  # 英文翻译文件
│   ├── common.json        # 通用组件翻译
│   ├── analysis.json      # 分析功能翻译
│   ├── cost.json         # 成本控制翻译
│   └── ...
├── zh-CN/                  # 中文翻译文件
│   ├── common.json        # 通用组件翻译
│   ├── analysis.json      # 分析功能翻译
│   ├── cost.json         # 成本控制翻译
│   └── ...
├── backup/                 # 已删除文件的备份
├── reports/                # 检查报告目录
├── dynamic-keys.json       # 动态键白名单
├── redundancy-analysis.md  # 冗余分析报告
├── i18n-cleanup-log.md    # 清理工作日志
└── README.md              # 本文档
```

## 🛠️ 开发工具

### 快速检查
```bash
# 运行简单的 i18n 检查
./scripts/i18n-simple-check.sh
```

### 详细分析（需要 Node.js）
```bash
# 运行完整的 i18n 分析（需要安装 glob 包）
node scripts/i18n-check.js
```

### 安装依赖
```bash
# 如果需要运行完整检查脚本
npm install glob
```

## 📝 使用规范

### 1. 翻译键命名规范
```javascript
// ✅ 推荐格式
t('module.category.item')
t('common.button.save')
t('analysis.progress.title')

// ❌ 避免格式
t('saveButton')
t('very.deep.nested.structure.item')
```

### 2. 动态键使用
```javascript
// ✅ 安全的动态键（已在白名单中）
t(`common.colorSchemes.${schemeId}`)
t(`analysis.domains.${domainType}Desc`)

// ⚠️ 需要添加到白名单
t(`newModule.${dynamicKey}`)
```

### 3. 新增翻译的流程
1. 同时在 `en-US` 和 `zh-CN` 中添加翻译
2. 如果使用动态键，添加到 `dynamic-keys.json` 白名单
3. 运行检查脚本验证：`./scripts/i18n-simple-check.sh`
4. 确保构建成功：`npm run build`

## 🚨 注意事项

### 删除翻译键时
1. **先确认未使用**：运行 `./scripts/i18n-simple-check.sh` 检查
2. **检查动态键**：确认不在 `dynamic-keys.json` 白名单中
3. **测试构建**：删除后运行 `npm run build` 确保无错误
4. **备份重要内容**：大批量删除前先备份

### 添加新模块时
1. **同步创建**：同时创建英文和中文版本
2. **更新索引**：在 `en-US/index.ts` 和 `zh-CN/index.ts` 中导入
3. **命名一致**：确保文件名和模块名一致
4. **结构对齐**：保持两种语言的键结构完全一致

## 📊 当前状态

- **支持语言**: 英文 (en-US)、中文 (zh-CN)
- **翻译文件**: 20个（每语言10个）
- **总翻译键**: ~1,500个（已清理约900个冗余键）
- **检查状态**: ✅ 无缺失键、无构建错误

## 🔄 维护计划

### 每月维护
- 运行 `./scripts/i18n-simple-check.sh` 检查状态
- 清理新增的未使用翻译键
- 更新动态键白名单（如有新增）

### 季度维护
- 深度分析各模块内部冗余键
- 整理和优化键的命名结构
- 更新维护文档和工具

## 🆘 故障排除

### 构建错误：找不到翻译键
1. 检查键名拼写是否正确
2. 确认键在两种语言中都存在
3. 运行 `./scripts/i18n-simple-check.sh` 查看详情

### 动态键被误报为未使用
1. 将键模式添加到 `dynamic-keys.json` 白名单
2. 在白名单中添加使用说明和位置信息
3. 重新运行检查脚本验证

### 翻译内容不一致
1. 对比两种语言的对应文件
2. 确保键结构完全一致
3. 使用 JSON 格式化工具检查语法

---

*最后更新: 2025-01-28*  
*维护团队: When.Trade 开发团队*