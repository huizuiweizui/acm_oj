// 洛谷 8 级难度：配色与表头短名（与 DifficultyBadge.vue 保持一致）
export const DIFF_COLORS = {
  '入门': '#fe4c61',
  '普及-': '#f39c11',
  '普及/提高-': '#ffc116',
  '普及+/提高': '#52c41a',
  '提高+/省选-': '#3498db',
  '省选/NOI-': '#9d3dcf',
  'NOI/NOI+/CTSC': '#0e1d69',
  '暂无评定': '#bfbfbf',
}

export const DIFF_SHORT = {
  '入门': '入门',
  '普及-': '普及-',
  '普及/提高-': '普/提-',
  '普及+/提高': '普+/提',
  '提高+/省选-': '提+/省-',
  '省选/NOI-': '省/NOI-',
  'NOI/NOI+/CTSC': 'NOI+',
  '暂无评定': '未评定',
}

export const diffColor = (d) => DIFF_COLORS[d] ?? '#9ca3af'
