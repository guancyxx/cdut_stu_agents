// Agent types and information
export const AGENT_TYPES = {
  CODE_REVIEWER: 'code_reviewer',
  PROBLEM_ANALYZER: 'problem_analyzer',
  CONTEST_COACH: 'contest_coach',
  LEARNING_PARTNER: 'learning_partner',
  LEARNING_MANAGER: 'learning_manager'
}

export const AGENT_DISPLAY_NAMES = {
  [AGENT_TYPES.CODE_REVIEWER]: '代码审查专家',
  [AGENT_TYPES.PROBLEM_ANALYZER]: '问题解析专家',
  [AGENT_TYPES.CONTEST_COACH]: '竞赛教练',
  [AGENT_TYPES.LEARNING_PARTNER]: '学习伙伴',
  [AGENT_TYPES.LEARNING_MANAGER]: '学习管理专家'
}

export const AGENT_DESCRIPTIONS = {
  [AGENT_TYPES.CODE_REVIEWER]: '专注于代码质量、效率和风格评估，提供优化建议',
  [AGENT_TYPES.PROBLEM_ANALYZER]: '擅长算法解释和问题拆解，帮助理解题目本质',
  [AGENT_TYPES.CONTEST_COACH]: '提供竞赛策略和表现优化建议，提高比赛成绩',
  [AGENT_TYPES.LEARNING_PARTNER]: '提供情感支持和学习动力，陪伴学习旅程',
  [AGENT_TYPES.LEARNING_MANAGER]: '制定个性化学习路径，管理学习进度和效率'
}

export const AGENT_ICONS = {
  [AGENT_TYPES.CODE_REVIEWER]: '💻',
  [AGENT_TYPES.PROBLEM_ANALYZER]: '🧠',
  [AGENT_TYPES.CONTEST_COACH]: '🏆',
  [AGENT_TYPES.LEARNING_PARTNER]: '🤝',
  [AGENT_TYPES.LEARNING_MANAGER]: '📊'
}

export const AGENT_COLORS = {
  [AGENT_TYPES.CODE_REVIEWER]: '#5a9fd4',
  [AGENT_TYPES.PROBLEM_ANALYZER]: '#9f5ad4',
  [AGENT_TYPES.CONTEST_COACH]: '#d45a5a',
  [AGENT_TYPES.LEARNING_PARTNER]: '#5ad47a',
  [AGENT_TYPES.LEARNING_MANAGER]: '#d4a05a'
}

// Extract agent type from message content
export function extractAgentFromMessage(content) {
  if (!content) return null
  
  // Look for agent markers in the response
  const agentMarkers = [
    { agent: AGENT_TYPES.CODE_REVIEWER, patterns: [/代码.*优化/, /代码.*审查/, /效率.*建议/] },
    { agent: AGENT_TYPES.PROBLEM_ANALYZER, patterns: [/算法.*解释/, /问题.*解析/, /动态规划/, /贪心算法/] },
    { agent: AGENT_TYPES.CONTEST_COACH, patterns: [/竞赛.*策略/, /比赛.*建议/, /时间.*管理/] },
    { agent: AGENT_TYPES.LEARNING_PARTNER, patterns: [/加油/, /坚持/, /相信.*你/, /学习.*伙伴/] },
    { agent: AGENT_TYPES.LEARNING_MANAGER, patterns: [/学习.*计划/, /学习.*路径/, /进度.*管理/] }
  ]
  
  for (const marker of agentMarkers) {
    if (marker.patterns.some(pattern => pattern.test(content))) {
      return marker.agent
    }
  }
  
  return null
}

// Get agent info by type
export function getAgentInfo(agentType) {
  return {
    type: agentType,
    name: AGENT_DISPLAY_NAMES[agentType] || 'AI助手',
    description: AGENT_DESCRIPTIONS[agentType] || '',
    icon: AGENT_ICONS[agentType] || '🤖',
    color: AGENT_COLORS[agentType] || '#666666'
  }
}