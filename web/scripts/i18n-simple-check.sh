#!/bin/bash

# i18n 简单检查脚本
# 用于快速检测基本的 i18n 问题

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$(dirname "$SCRIPT_DIR")"
LOCALES_DIR="$WEB_DIR/src/locales"
SRC_DIR="$WEB_DIR/src"

echo "🔍 i18n 快速检查工具"
echo "=================================="

# 检查语言目录是否存在
check_directories() {
    echo "📁 检查目录结构..."
    
    if [[ ! -d "$LOCALES_DIR" ]]; then
        echo "❌ 错误: locales 目录不存在: $LOCALES_DIR"
        exit 1
    fi
    
    languages=("en-US" "zh-CN")
    for lang in "${languages[@]}"; do
        if [[ ! -d "$LOCALES_DIR/$lang" ]]; then
            echo "⚠️  警告: 语言目录不存在: $lang"
        else
            file_count=$(find "$LOCALES_DIR/$lang" -name "*.json" | wc -l)
            echo "✅ $lang: $file_count 个翻译文件"
        fi
    done
    echo
}

# 检查文件同步性
check_file_sync() {
    echo "🔄 检查文件同步性..."
    
    en_files=($(find "$LOCALES_DIR/en-US" -name "*.json" -exec basename {} \; | sort))
    cn_files=($(find "$LOCALES_DIR/zh-CN" -name "*.json" -exec basename {} \; | sort))
    
    # 检查 en-US 中有但 zh-CN 中没有的文件
    for file in "${en_files[@]}"; do
        if [[ ! -f "$LOCALES_DIR/zh-CN/$file" ]]; then
            echo "⚠️  zh-CN 缺少文件: $file"
        fi
    done
    
    # 检查 zh-CN 中有但 en-US 中没有的文件
    for file in "${cn_files[@]}"; do
        if [[ ! -f "$LOCALES_DIR/en-US/$file" ]]; then
            echo "⚠️  en-US 缺少文件: $file"
        fi
    done
    
    common_files_count=0
    for file in "${en_files[@]}"; do
        if [[ -f "$LOCALES_DIR/zh-CN/$file" ]]; then
            ((common_files_count++))
        fi
    done
    
    echo "✅ 公共文件数量: $common_files_count"
    echo
}

# 检查 JSON 语法
check_json_syntax() {
    echo "📝 检查 JSON 语法..."
    
    syntax_errors=0
    while IFS= read -r -d '' file; do
        if ! python3 -m json.tool "$file" > /dev/null 2>&1; then
            echo "❌ JSON 语法错误: $(basename "$(dirname "$file")")/$(basename "$file")"
            ((syntax_errors++))
        fi
    done < <(find "$LOCALES_DIR" -name "*.json" -print0)
    
    if [[ $syntax_errors -eq 0 ]]; then
        echo "✅ 所有 JSON 文件语法正确"
    else
        echo "❌ 发现 $syntax_errors 个 JSON 语法错误"
    fi
    echo
}

# 查找常见的 i18n 使用模式
check_usage_patterns() {
    echo "🔎 检查 i18n 使用模式..."
    
    # 统计各种使用模式
    dollar_t_count=$(grep -r "\$t(" "$SRC_DIR" --include="*.vue" --include="*.ts" --include="*.js" | wc -l)
    t_func_count=$(grep -r "[^$]t(" "$SRC_DIR" --include="*.vue" --include="*.ts" --include="*.js" | wc -l)
    i18n_t_count=$(grep -r "i18n\.t(" "$SRC_DIR" --include="*.vue" --include="*.ts" --include="*.js" | wc -l)
    
    echo "📊 使用统计:"
    echo "   - \$t() 使用: $dollar_t_count 次"
    echo "   - t() 使用: $t_func_count 次" 
    echo "   - i18n.t() 使用: $i18n_t_count 次"
    
    total_usage=$((dollar_t_count + t_func_count + i18n_t_count))
    echo "   - 总计: $total_usage 次 i18n 调用"
    echo
}

# 查找硬编码文本
check_hardcoded_text() {
    echo "🔤 检查潜在的硬编码中文..."
    
    # 查找模板中的中文字符
    hardcoded_count=$(grep -r "[\u4e00-\u9fa5]" "$SRC_DIR" --include="*.vue" | grep -v "// " | grep -v "/\*" | wc -l)
    
    if [[ $hardcoded_count -gt 0 ]]; then
        echo "⚠️  发现 $hardcoded_count 行可能包含硬编码中文"
        echo "   建议检查这些文件并考虑使用 i18n"
    else
        echo "✅ 未发现明显的硬编码中文"
    fi
    echo
}

# 检查动态键白名单
check_whitelist() {
    echo "📋 检查动态键白名单..."
    
    whitelist_file="$LOCALES_DIR/dynamic-keys.json"
    if [[ -f "$whitelist_file" ]]; then
        if python3 -m json.tool "$whitelist_file" > /dev/null 2>&1; then
            pattern_count=$(python3 -c "import json; data=json.load(open('$whitelist_file')); print(len(data.get('whitelist', [])))")
            echo "✅ 动态键白名单: $pattern_count 个模式"
        else
            echo "❌ 动态键白名单 JSON 格式错误"
        fi
    else
        echo "⚠️  未找到动态键白名单文件"
    fi
    echo
}

# 生成简单报告
generate_report() {
    echo "📄 生成检查报告..."
    
    report_file="$WEB_DIR/reports/i18n-simple-check-$(date +%Y%m%d-%H%M%S).txt"
    mkdir -p "$(dirname "$report_file")"
    
    {
        echo "i18n 简单检查报告"
        echo "=================="
        echo "检查时间: $(date)"
        echo "项目路径: $WEB_DIR"
        echo
        
        echo "文件统计:"
        find "$LOCALES_DIR" -name "*.json" | while read -r file; do
            lines=$(wc -l < "$file")
            echo "  $(basename "$(dirname "$file")")/$(basename "$file"): $lines 行"
        done
        echo
        
        echo "总文件数: $(find "$LOCALES_DIR" -name "*.json" | wc -l)"
        echo "总行数: $(find "$LOCALES_DIR" -name "*.json" -exec cat {} \; | wc -l)"
        
    } > "$report_file"
    
    echo "✅ 报告已生成: $report_file"
    echo
}

# 主函数
main() {
    check_directories
    check_file_sync
    check_json_syntax
    check_usage_patterns
    check_hardcoded_text
    check_whitelist
    generate_report
    
    echo "🎉 i18n 检查完成!"
    echo "如需详细分析，请运行: node scripts/i18n-check.js"
}

# 运行主函数
main