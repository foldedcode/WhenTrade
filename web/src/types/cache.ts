/**
 * 缓存系统类型定义
 * 支持多层缓存架构：内存缓存 + 本地存储缓存 + IndexedDB
 */

// 缓存层类型
export enum CacheLayer {
  MEMORY = 'memory',
  LOCAL_STORAGE = 'localStorage', 
  INDEXED_DB = 'indexedDB'
}

// 缓存项接口
export interface CacheItem<T = any> {
  key: string
  value: T
  ttl?: number
  createdAt: number
  updatedAt: number
  accessCount: number
  lastAccessed: number
  size?: number
  metadata?: Record<string, any>
}

// 缓存策略
export interface CacheStrategy {
  ttl?: number // 生存时间(秒)
  maxSize?: number // 最大缓存大小
  maxCount?: number // 最大缓存项数量
  evictionPolicy?: EvictionPolicy // 淘汰策略
  priority?: CachePriority // 缓存优先级
  layers?: CacheLayer[] // 启用的缓存层
  compression?: boolean // 是否压缩
  encryption?: boolean // 是否加密
}

// 淘汰策略
export enum EvictionPolicy {
  LRU = 'lru', // 最近最少使用
  LFU = 'lfu', // 最少使用频率
  FIFO = 'fifo', // 先进先出
  TTL = 'ttl' // 基于过期时间
}

// 缓存优先级
export enum CachePriority {
  LOW = 1,
  MEDIUM = 2,
  HIGH = 3,
  CRITICAL = 4
}

// 缓存统计信息
export interface CacheStats {
  totalItems: number
  totalSize: number
  hitCount: number
  missCount: number
  hitRate: number
  memoryUsage: number
  localStorageUsage: number
  indexedDBUsage: number
}

// 缓存操作选项
export interface CacheOptions {
  strategy?: Partial<CacheStrategy>
  skipMemory?: boolean
  skipLocalStorage?: boolean
  skipIndexedDB?: boolean
  forceRefresh?: boolean
  silent?: boolean // 静默模式，不触发事件
}

// 缓存事件类型
export enum CacheEventType {
  SET = 'set',
  GET = 'get',
  DELETE = 'delete',
  CLEAR = 'clear',
  EXPIRE = 'expire',
  EVICT = 'evict',
  ERROR = 'error'
}

// 缓存事件
export interface CacheEvent<T = any> {
  type: CacheEventType
  key: string
  value?: T
  layer?: CacheLayer
  timestamp: number
  metadata?: Record<string, any>
}

// 缓存监听器
export type CacheListener<T = any> = (event: CacheEvent<T>) => void

// 缓存存储接口
export interface CacheStorage {
  get<T>(key: string): Promise<CacheItem<T> | null>
  set<T>(key: string, item: CacheItem<T>): Promise<void>
  delete(key: string): Promise<boolean>
  clear(): Promise<void>
  keys(): Promise<string[]>
  size(): Promise<number>
}

// 内存缓存配置
export interface MemoryCacheConfig {
  maxSize: number // 最大内存使用量(MB)
  maxCount: number // 最大缓存项数量
  ttl: number // 默认TTL(秒)
  cleanupInterval: number // 清理间隔(秒)
}

// 本地存储缓存配置
export interface LocalStorageCacheConfig {
  prefix: string // 键前缀
  maxSize: number // 最大存储大小(MB)
  compression: boolean // 是否压缩
  ttl: number // 默认TTL(秒)
}

// IndexedDB缓存配置
export interface IndexedDBCacheConfig {
  dbName: string // 数据库名称
  version: number // 数据库版本
  storeName: string // 存储对象名称
  maxSize: number // 最大存储大小(MB)
  ttl: number // 默认TTL(秒)
}

// 分层缓存配置
export interface LayeredCacheConfig {
  memory: MemoryCacheConfig
  localStorage: LocalStorageCacheConfig
  indexedDB: IndexedDBCacheConfig
  defaultStrategy: CacheStrategy
  enableMetrics: boolean // 启用指标收集
  enableEvents: boolean // 启用事件
}

// 缓存键生成器
export interface CacheKeyGenerator {
  generate(namespace: string, params: Record<string, any>): string
  validate(key: string): boolean
}

// 缓存序列化器
export interface CacheSerializer {
  serialize<T>(value: T): string | ArrayBuffer
  deserialize<T>(data: string | ArrayBuffer): T
  getSize(data: string | ArrayBuffer): number
}

// 缓存加密器
export interface CacheEncryption {
  encrypt(data: string): Promise<string>
  decrypt(encryptedData: string): Promise<string>
}

// 缓存压缩器
export interface CacheCompression {
  compress(data: string): Promise<string>
  decompress(compressedData: string): Promise<string>
  getCompressionRatio(original: string, compressed: string): number
} 