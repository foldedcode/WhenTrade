/**
 * 修复 end-of-stream 模块的兼容性问题
 */

// 在全局作用域注入必要的 polyfills
if (typeof window !== 'undefined') {
  // 确保 fs 存在
  if (!window.fs) {
    window.fs = {}
  }
  
  // 为 fs 的每个方法添加 bind 支持
  const fsMethods = [
    'open', 'close', 'read', 'write', 'stat', 'lstat', 'fstat',
    'readFile', 'writeFile', 'readdir', 'mkdir', 'rmdir', 'unlink',
    'rename', 'chmod', 'chown', 'utimes', 'realpath', 'mkdtemp',
    'writeFileSync', 'readFileSync', 'existsSync', 'createReadStream',
    'createWriteStream'
  ]
  
  fsMethods.forEach(method => {
    if (!window.fs[method]) {
      window.fs[method] = function() {}
    }
    // 确保每个方法都有 bind
    if (!window.fs[method].bind) {
      const originalMethod = window.fs[method]
      window.fs[method] = function(...args: any[]) {
        return originalMethod.apply(this, args)
      }
    }
  })
  
  // 修复 process.binding
  if (window.process && window.process.binding) {
    const originalBinding = window.process.binding
    window.process.binding = function(name: string) {
      const result = originalBinding.call(this, name)
      
      // 如果返回的是 fs，确保所有方法都有 bind
      if (name === 'fs' && result) {
        Object.keys(result).forEach(key => {
          if (typeof result[key] === 'function' && !result[key].bind) {
            const fn = result[key]
            result[key] = function(...args: any[]) {
              return fn.apply(this, args)
            }
          }
        })
      }
      
      return result
    }
  }
}

export {}