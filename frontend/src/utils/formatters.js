/**
 * Formats a severity score (0.0 to 1.0) into a canonical dashboard format (0.0/10 to 10.0/10).
 * Examples: 0.61 -> "6.1/10", 0.495 -> "5.0/10"
 * 
 * @param {number} score - The severity score from 0.0 to 1.0
 * @returns {string} The formatted severity string
 */
export const formatSeverity = (score) => {
  if (score === undefined || score === null) return 'N/A';
  return `${(score * 10).toFixed(1)}/10`;
};
