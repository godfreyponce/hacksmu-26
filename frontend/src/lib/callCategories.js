export function categoryTokenRegex(category) {
  return new RegExp(`(^|[^a-z])${category}([^a-z]|$)`, 'i')
}

export function matchesCategory(label, category) {
  if (!label || !category) return false
  return categoryTokenRegex(category).test(String(label).toLowerCase())
}

export function countCategoryMentions(byType, category) {
  return Object.entries(byType || {}).reduce((sum, [label, count]) => {
    return matchesCategory(label, category) ? sum + Number(count || 0) : sum
  }, 0)
}