// Sàng lọc Prompt Injection trong nội dung tài liệu (Rules mục 5).
// Backend (src/security/injection_filter.py) là lớp chặn chính thức trước khi gọi Gemini;
// bản này chạy ở trình duyệt để HR thấy cảnh báo ngay khi tải lên, và dùng chung
// định dạng cờ với backend: { chunk_id, page, rule_id, severity, match, excerpt }.

const INJECTION_RULES = [
  { id: "ignore_instructions", severity: "high", pattern: /\b(ignore|disregard|forget|override)\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier|preceding|system)\s+(instructions?|prompts?|rules?|directions?)/i },
  { id: "system_override", severity: "high", pattern: /\bsystem\s+(override|prompt\s+override|bypass)\b/i },
  { id: "dan_mode", severity: "high", pattern: /\b(DAN\s+mode|do\s+anything\s+now|developer\s+mode\s+enabled|jailbreak)\b/i },
  { id: "role_hijack", severity: "medium", pattern: /\byou\s+are\s+now\s+(a|an|in|the)\b/i },
  { id: "reveal_prompt", severity: "medium", pattern: /\b(reveal|print|show|output|repeat)\s+(your|the)\s+(system\s+prompt|hidden\s+instructions?|initial\s+instructions?)/i },
  { id: "output_manipulation", severity: "medium", pattern: /\b(mark|classify|label|report)\s+(this|all|every)\s+(\w+\s+){0,3}as\s+(verified|approved|compliant)\b/i },
  { id: "ignore_instructions_vi", severity: "high", pattern: /(bỏ\s+qua|phớt\s+lờ|quên|không\s+tuân\s+theo)\s+(mọi|tất\s+cả|các|những)?\s*(chỉ\s+dẫn|hướng\s+dẫn|lệnh|quy\s+tắc|yêu\s+cầu)\s+(trước|trước\s+đó|ở\s+trên|hệ\s+thống)/iu },
  { id: "system_override_vi", severity: "high", pattern: /(ghi\s+đè|vượt\s+qua)\s+(hệ\s+thống|chỉ\s+dẫn\s+hệ\s+thống|system\s+prompt)/iu },
  { id: "role_hijack_vi", severity: "medium", pattern: /(từ\s+bây\s+giờ|kể\s+từ\s+giờ)\s+bạn\s+(là|sẽ\s+đóng\s+vai)/iu },
];

const EXCERPT_RADIUS = 80;

/**
 * Quét danh sách chunk, trả về mỗi lần khớp một cờ.
 * @param {Array<{chunk_id, page, content}>} chunks
 */
export function scanChunks(chunks) {
  const flags = [];
  for (const chunk of chunks || []) {
    const text = String(chunk.content || "");
    for (const rule of INJECTION_RULES) {
      const re = new RegExp(rule.pattern.source, rule.pattern.flags.includes("g") ? rule.pattern.flags : `${rule.pattern.flags}g`);
      for (const m of text.matchAll(re)) {
        const start = Math.max(0, m.index - EXCERPT_RADIUS);
        const end = Math.min(text.length, m.index + m[0].length + EXCERPT_RADIUS);
        flags.push({
          chunk_id: chunk.chunk_id,
          page: chunk.page ?? null,
          rule_id: rule.id,
          severity: rule.severity,
          match: m[0],
          excerpt: `${start > 0 ? "…" : ""}${text.slice(start, end)}${end < text.length ? "…" : ""}`,
        });
      }
    }
  }
  return flags;
}

export function flaggedChunkIds(flags) {
  return new Set((flags || []).map(f => f.chunk_id));
}
