// 智能体节点类型
export interface AgentNode {
  id: string
  name: string
  type: 'analyst' | 'researcher' | 'risk_manager' | 'trader'
  status: 'thinking' | 'analyzing' | 'debating' | 'concluded' | 'idle'
  position: { x: number, y: number }
  currentThought?: string
  confidence: number
  avatar?: string
  color?: string
}

// 智能体连接类型
export interface AgentConnection {
  source: string
  target: string
  type: 'data_flow' | 'debate' | 'consensus' | 'collaboration'
  strength: number
  message?: string
  animated?: boolean
}

// 可视化配置
export interface VisualizationConfig {
  width: number
  height: number
  nodeRadius: number
  linkDistance: number
  chargeStrength: number
  enableAnimation: boolean
  showThoughts: boolean
  showConnections: boolean
}

// 思维气泡
export interface ThoughtBubble {
  agentId: string
  content: string
  timestamp: string
  type: 'analysis' | 'question' | 'conclusion' | 'debate'
  confidence?: number
  relatedData?: any
}

// 协作事件
export interface CollaborationEvent {
  id: string
  type: 'agent_start' | 'agent_complete' | 'debate_start' | 'consensus_reached'
  participants: string[]
  timestamp: string
  data?: any
  description: string
}

// 网络图状态
export interface NetworkGraphState {
  nodes: AgentNode[]
  links: AgentConnection[]
  events: CollaborationEvent[]
  currentTime: number
  isPlaying: boolean
  playbackSpeed: number
}

// D3 仿真相关类型
export interface D3Node extends AgentNode {
  x?: number
  y?: number
  vx?: number
  vy?: number
  fx?: number | null
  fy?: number | null
}

export interface D3Link extends Omit<AgentConnection, 'source' | 'target'> {
  source: D3Node | string
  target: D3Node | string
  index?: number
} 