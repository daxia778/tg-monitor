# TG Monitor Upgrade Progress

## Current Objective
Working on Phase 1 from `TODO.md`: Link Aggregation Engine Deepening (深度解析与智能分类).

## Tasks
### Phase 1: 🔗 链接聚合引擎深化 (深度解析与智能分类)
- [ ] **Meta Parser (网页元数据抓取)**: Asynchronously fetch `<title>`, `<meta description>`, and images for links (in `src/db/messages.py`). Handle User-Agent and timeouts.
- [ ] **Link Scorer (AI 智能标注与清洗)**: Use local CPA (LLM) to tag link metadata (e.g., "干货评测", "促销/羊毛"). Deduplicate and handle share counts.
- [ ] **Rich Link Cards (前端 UI 升级)**: Update `LinksPage.tsx` to display rich text cards instead of a text list, and allow filtering by tags.

## Issues Encountered
- (None yet)

## Achievements
- Initialized upgrade tracking.
