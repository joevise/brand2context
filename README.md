# Brand2Context

**把品牌的公开信息，变成 AI 能调用的结构化知识库。**

输入一个官网链接 → 输出一个品牌知识 MCP Server / API。

## 问题

AI 时代，消费者获取信息的方式从"搜索引擎"转向"直接问 AI"。但 AI 对品牌的理解往往是过时的、不准确的、甚至错误的。品牌方毫无控制力。

## 解决方案

Brand2Context 帮品牌把散落在全网的公开信息（官网、公众号、知乎、行业报告等），自动抓取并结构化为标准品牌知识库。这个知识库可以被任何 AI Agent 通过 MCP / API 直接调用。

## 核心流程

```
品牌官网 URL → 全站抓取 → AI 结构化理解 → 品牌知识库 → MCP Server / API
```

## 品牌知识 Schema

Brand2Context 使用标准化的品牌知识 Schema，覆盖消费者决策全链路的信息需求。

详见 [schema/README.md](schema/README.md)

## 技术栈

- 抓取引擎：基于 link2context（全站抓取 + SPA 支持）
- 结构化引擎：LLM 驱动的信息抽取
- 知识库：结构化 JSON + 向量检索
- 对外接口：MCP Server（Streamable HTTP）+ REST API

## Roadmap

- [ ] Phase 1: Schema 定义 + 单站抓取 + 结构化抽取
- [ ] Phase 2: 多源抓取（公众号、知乎、抖音简介）
- [ ] Phase 3: 自动更新 + 变化监控
- [ ] Phase 4: 品牌管理后台 + SaaS 化

## License

MIT
