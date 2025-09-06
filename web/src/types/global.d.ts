declare global {
  interface Window {
    Buffer: typeof Buffer
    process: any
    global: Window
  }
}

export {}