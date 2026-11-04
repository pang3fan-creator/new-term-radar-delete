# 用户需求雷达：架构文档

这是 fork 的改造依据，不是上游的说明。上游 `README.md` 描述的是 what this repo is;本文描述的是 **what we are turning it into, and why**。

一句话：**每天早上给我 3–5 个昨天开始在 TikTok 上被人做出来的效果名，Google 上还没人占位，评论区在问"怎么做"。**

---

## 1. 为什么不沿用上游

四条，都测过：

| 事实 | 证据 |
|---|---|
| 它的判定明确排斥用户语言 | `radar/judge.py:22` 的 SYSTEM 原文：`Not names: ... 'video generator'` |
| 它的线索是"专名"，而专名不等于需求 | 30 条真实用户求助，judge 给 **30/30 全 0.00**；同样模型给 `opus 5.5` 0.90、`hyperframes` 0.80 |
| 它的源几乎全是供给侧 | 21 个线索里 15 个来自 GitHub 新仓库、6 个来自 sitemap/feed；用户社区一个没有 |
| 它的节奏是给"长期 SEO"设计的 | 8 小时一轮、`review.after_days: 14`、`country_min_volume: 1000`/月 |

一句话概括错位：**它找的是"开发者刚造出来的东西的名字"，我们要的是"普通人刚想要的东西的名字"。**

## 2. 三个已测的结论

这节是门槛数值的来源，改门槛先改这里。

**2.1 需求重复发生在"观看"里，不在"文字"里**

30 条用户请求聚类三次（原序/逆序/随机），一致率 99%，结论是 **25–28 件不同的事**——没有人在重复问。
但一条视频可以被一百万人看，每个人都想要同一个结果，却谁都不发帖。
→ 重复度要用 `播放量 + 创作者数` 量，不要用文本聚类。

**2.2 "想做"和"在看"能在评论里分开**

6 条视频各取 40 条评论，模型逐条判 want / react：

| 组 | want 占比 |
|---|---|
| `ai photo shoot`（效果可复刻） | **19%**（120 条） |
| `ai skit`（表演，不可复刻） | **4%**（120 条） |

误判模式已知：`is this AI?` 会被算成 want。定义要收紧成"**想产出同一个东西**"，不是"想知道这是怎么来的"。

**2.3 窗口不在 TikTok 的 caption 上，在 Google 的标题里**

| 视频年龄 | caption 带推销/教程 |
|---|---|
| ≤14 天 | 36%（n=11） |
| 15–90 天 | 42%（n=36） |
| >90 天 | 40%（n=53） |

平的。**卖货的人和视频同时出现**：一条 7 天前的视频已经在教 "HOW TO MAKE THIS VIDEO, download Danzify AI"。

但同一批词在 Google 上：

| 词 | 标题含该词的页面（近一个月） |
|---|---|
| `ai photo shoot` | 10 |
| `toc toc ai dance` | 68 |
| `thriller ai dance` | 76 |
| `hotel lobby ai` | **1,980** |

→ 竞争者检查用 `allintitle` 和域名，不用 caption 正则。
→ 而且必须抓**具体效果名**：`ai photo shoot` 只有 10 页，因为没人会为品类名建站。

**2.4 端到端跑过一遍：4 个候选，0 个出货**

100 条视频 → 命名成功 74 条（26 条判为"不是效果"）→ 近 14 天 7 个效果 → 取播放最高的 4 个送进门 2、门 3：

| 效果 | 观察 | 创作者 | 播放 | 最早 | caption 带推销 | want | intitle | 域名 |
|---|---|---|---|---|---|---|---|---|
| `toc toc ai dance` | 4 | 3 | 2.27M | 7 天 | 4/4 | 0/10 | 68 | 10-18 已注册 |
| `red light filter` | 2 | 2 | 282k | 7 天 | 1/2 | 0/10 | 10 | 08-12 已注册 |
| `nostalgia capcut filter` | 1 | 1 | 127k | 5 天 | 0/1 | 0/2 | 9 | 空 |
| `bby wow ai dance` | 1 | 1 | 11.6k | 8 天 | 1/1 | ? | 6 | 空 |

三条结论，都进了后面的设计：

1. **`toc toc ai dance` 是真需求**：3 个创作者、227 万播放、7 天内。但 `.com` 在 10 月 18 日就被注册了，intitle 68 —— 窗口在 16 天前就关了。**域名是最快的占位信号**，比任何关键词工具都快。
2. **want 在 top-10 评论上不可用**：同一条视频，40 条评论时 19%，10 条时 0%。点赞最高的评论是段子，不是"怎么做"。采样量必须回到 40 条。
3. **命名模型会静默漏行**：首轮 100 条里有 26 条不是回答 "none"，而是干脆不给这一行。必须断言"每个下标都有回答"，缺的重问。

**2.5 已成链，跑过三轮**（`python -m radar effects "ai dance filter" "capcut filter" --per 15`）

| 效果 | 创作者 | 播放 | 最新 | want | intitle | 域名 | 判定 |
|---|---|---|---|---|---|---|---|
| `capcut pioneer template` | 2 | 7.3M | 11-02 | 92%（36/39） | 22500 | 空 | 关：占满了 |
| `angry dance filter` | 1 | 12k | 10-27 | 0/0 | 31 | 10-26 已注册 | 关：有人占了 |
| `jeremy clarkson filter` | 1 | 7.3M | 10-21 | 0%（96 条） | 6 | 空 | 关：没人问怎么做 |
| `lyric video filter` | 1 | 37k | 10-24 | 39%（47/120） | 10 | 空 | 第一版误判为"开着"，命名应拒绝品类 |

三个行为是跑出来的，不是设计的：

1. **14 天新鲜度必须先过滤**：按全时段播放量排序时，第一名是 8 月的 9M 播放视频——没有窗口可言。加上过滤后 30 条只剩 6 条，成本不变但结论全变。
2. **want 需要最小样本**：`0 of 0` 和 `0 of 3` 不能读成"没人要"，要读成"没数据"。现在 `total == 0 → silent`，`total < 20 → thin`，两者都不判 pass。
3. **词表必须自己长大**：六个词就是漏斗的嘴，跑十天就空了。每次跑完再花一次调用，从当天命名的效果里反推 10 个"去找的地方"（`ai wedding filter`、`ai cosplay filter`），而不是编辑手法（`color grading`、`cinematic mood`——那是专业剪辑师的动作，普通人不会搜）。新词进 `queries` 表，之后按"最久没跑过"轮换，种子每天照跑。
4. **`intitle` 可信**：重测 `toc toc ai dance` 65 / `thriller ai dance` 76 / `ai dance filter` 10，与 10-30 的标定一致；`capcut pioneer template` 的 22500 是真的，那个模板已经占满了。

## 3. 判定链

四道门，全部为"与"。第 4 道只在"前三道都过了、本来要出货"时才花钱。

```
发现                                    判定                              输出
TikTok 搜索（近 7 天）  ──►  ① 具体性  ──►  ② 有人想要  ──►  ③ 没人占位  ──►  日报 3–5 条
按 DATE_POSTED 排序          这是不是一个    10 条评论里      intitle ≤ 20
每词 25 条                   可命名的效果    want ≥ 20%       域名可注册
```

| 门 | 检查 | 数据 | 成本 | 通过线 | 置信度 |
|---|---|---|---|---|---|
| 0 | 它是不是正在发生 | `uploadedAt` | 0 | 近 7 天有 ≥1 条 | 实测：100 条里只有 8 条 ≤7 天 |
| 1 | 这是不是一个效果名 | 模型读 caption + hashtag | 可忽略 | 2–4 词的具名效果，不是品类 | 未测 |
| 2 | 有没有人想要 | 40 条评论的 want 占比 | $0.05 | ≥ 20% | 40 条测出 19% vs 4%；10 条测出 0，不可用 |
| 3 | 有没有人占位 | `intitle` + RDAP + DoH 查 `.com/.ai/.io` | $0.004 / 24 秒 | ≤ 20 页 且 三个后缀都空 | 只有 4 个样本，线是猜的 |
| 4 | 还有没有人搜 | Google Trends（US，近 12 个月，**周**粒度） | $0.006 | 近 4 周 ≥ 前 13 周 × 1.2，且 ≥ 5 | 实测：`ai dance filter` 峰值 04-12、现在 7.8；`toc toc` 峰值 10-18、现在 41 |

第 4 道是 2026-11-03 补的：`nostalgia filter` 当天被判"开着"，但它的 Google Trends 曲线在春天就到顶了，现在全美搜量读数是 0。前三道量的都是"供给侧的现在"（视频在传、没人占位），没有一道量"需求还在不在"。它只对本来要出货的候选跑，所以一天最多一次 $0.006。

窗口要用 12 个月、周粒度，不是 3 个月日粒度：日粒度对小词会把整段抹成 0，读成"没人搜"，而实际只是低于采样门槛。同一个 `ai dance filter`，3 个月日粒度读 0，12 个月周粒度读 27.6（近 28 天）。Trends 每条曲线都在自己的窗口内归一化到 0–100，所以**换窗口就换答案**，这也是为什么"最近 30 天"和"最近 12 个月"看起来矛盾。

限制：它只认**这个词本身**。效果真、但人们搜的是另一个说法（`nostalgia effect` 而不是 `filter`）时，读不到。宁可错杀，不假开——这是当前的取舍。

## 4. 数据模型

新建 SQLite（沿用 `store.py` 的 `state/radar.db` 路径，但换表）：

```sql
-- 一个"效果"，是我们真正要找的东西
CREATE TABLE artifacts (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,   -- 'toc toc ai dance'
  kind        TEXT,                   -- effect / filter / challenge / tool
  first_seen  TEXT NOT NULL,
  last_seen   TEXT NOT NULL,
  status      TEXT DEFAULT 'watch'    -- watch / shipped / dead
);

-- 每一次看见它（一条视频就是一次观察），重复度从这里算
CREATE TABLE observations (
  id           INTEGER PRIMARY KEY,
  artifact_id  INTEGER REFERENCES artifacts(id),
  platform     TEXT NOT NULL,         -- tiktok / youtube
  url          TEXT NOT NULL UNIQUE,
  author       TEXT,
  caption      TEXT,
  views        INTEGER,
  comments     INTEGER,
  uploaded_at  TEXT,
  seen_at      TEXT NOT NULL,
  promo        INTEGER DEFAULT 0      -- caption 带 app/code/link
);

-- 每一次花钱的检查
CREATE TABLE checks (
  id          INTEGER PRIMARY KEY,
  artifact_id INTEGER REFERENCES artifacts(id),
  check       TEXT NOT NULL,          -- want / intitle / domain
  value       TEXT,
  verdict     TEXT,                   -- pass / fail
  cost_micro  INTEGER DEFAULT 0,
  at          TEXT NOT NULL
);
```

```sql
-- 搜索词表：种子每天跑，生成词按最久没跑过轮换
CREATE TABLE queries (
  word    TEXT PRIMARY KEY,           -- 'ai dance filter'
  source  TEXT NOT NULL,              -- seed / generated
  added   TEXT NOT NULL,              -- 2026-11-03
  runs    INTEGER NOT NULL DEFAULT 0,
  last    TEXT NOT NULL DEFAULT ''    -- 最后跑过的日期
);
```

```sql
-- 每天跑一次就一行：报告会覆盖，这一行不会
CREATE TABLE runs (
  id          INTEGER PRIMARY KEY,
  day         TEXT NOT NULL,
  at          TEXT NOT NULL,          -- 2026-11-03T17:41:00
  words       TEXT,                   -- 今天搜的词
  discovered  INTEGER,                -- 抓回多少条
  posts       INTEGER,                -- 14 天内、值得命名的
  named       INTEGER,                -- 命名成功几个
  candidates  INTEGER,                -- 进了报告前四的
  grown       TEXT,                   -- 给明天加的词
  cost_micro  INTEGER,
  opens       INTEGER
);
```

重复度 = `count(distinct observations.author)` 和 `sum(views)`，窗口内。**不要再做文本聚类。**

## 5. 调度与预算

Apify FREE：$5/月，实测单价 `$0.0003/条视频`、`$0.00125/条评论`；`goanyapi.intitle` `$0.004/次`，约 20 秒。

| 项 | 量 | 单价 | 日成本（实测 2026-11-03） |
|---|---|---|---|
| 视频搜索 | 150 条 | $0.0003 | $0.045 |
| 评论 | YouTube 优先，不够 20 条才问 TikTok | 免费 / $0.00125 | $0.013 |
| intitle | 4 次 | $0.004 | $0.016 |
| 命名 + want（AIsa） | 6 次调用 | — | $0.000 |
| **合计** | | | **$0.073/天 → $2.2/月（Apify 实测 $0.058）** |

离开评论就只剩发现这一步要钱，一天不到一毛，免费额度按月够用。代价是慢：YouTube 拉评论比 Apify 慢，一轮 6 分 45 秒（付费路径 3 分半）。

评论这一半是白嫖的：`yt-dlp --write-comments --js-runtimes node` 就能拿到播放数、上传日期和 40 条评论。四个候选的实测对照（TikTok 付费 vs YouTube 免费）：

| 词 | TikTok want | YouTube want |
|---|---|---|
| `ai photo shoot` | 19%（120 条） | 50%（84 条） |
| `nostalgia capcut filter` | 0%（2 条，样本不足） | 26%（42 条） |
| `toc toc ai dance` | 0%（10 条） | 11%（9 条） |
| `red light filter` | 0%（10 条） | 4%（80 条） |

两件事被证实：**排序一致**（TikTok 上最高的在 YouTube 上也最高，没人要的掉到 4%）；**能救样本**（`nostalgia capcut filter` 在 TikTok 只有 2 条评论，YouTube 上 42 条，26% 在问怎么做）。

两点注意：YouTube 搜索返回的多是教程，评论者本就"已经想学"，所以 want 天然偏高——两列比排序，不比大小；`yt-dlp` 必须有 JS runtime（`node`），否则播放数会错成 1、评论返回 0。

**新分工（已在 `radar/effects.py` 落地）：TikTok 发现（$0.045/天），YouTube 判定（免费）。**
YouTube 上这个效果还不存在时（评论 < 20 条），这一条候选回退成付费拉 TikTok 评论，两条视频约 $0.05；一天最多 4 次，实测一天只触发了一次左右。

节奏：**每小时发现，每天判定一次**。上游的 8 小时一轮 + 14 天回验是给长期 SEO 的；效果名的钱在 72 小时内，回验窗口应该是 7 天不是 14 天。

## 6. 现有代码怎么处理

| 处理 | 文件 | 理由 |
|---|---|---|
| 留 | `i18n.py`、`config.py`、`store.py` 的连接部分、`report.py` 的渲染骨架 | 双语强制、默认值单一来源，都是对的 |
| 改用途 | `judge.py` | 从"是不是专名"改成门 1"是不是一个可命名的效果" |
| 留作门 3 | `dotcom.py`（RDAP）、`goanyapi.intitle()` / `.serp()` | 原本做护城河，现在做占位检查 |
| 降级为证据 | `breakout.py`、`x_accounts`、`sitemaps.py`、`hf.py`、`feeds.py` | 不是线索源，是"这东西已经在被做"的旁证，默认不进日报 |
| 停用 | `usecases.py` 的 markets / page one / KD 部分 | 效果名的窗口是小时级，等不到 KD 数据 |
| 新写 | `tiktok.py`（Apify）、`artifact.py`（命名 + want + 判定） | 新增能力 |

`pains.py` 保留：它回答的是"现有工具做不到什么"，是效果名的补充证据，但不在主链路上。

## 7. 报告形态

日报正文只有一段话，每条 4 行：

```
toc toc ai dance                    想看 · 68 页 · 域名空
  3 个创作者 · 585k 播放 · 最早 10-20
  want 24%（40 条评论里 10 条在问怎么做）
  窗口：开着，但已经有人在教它
```

所有文案进 `i18n.py`，成对 en/zh，不留字面量。JSON 结构同步输出，给 MCP 和 skill 用。

## 8. 测试

两个 prompt 各有 fixture，先跑分再改，不看感觉：

```
python gitignore/experiments/eval_prompts.py   # 13 条真实 caption + 31 条真实评论 + 一整页 107 条，$0.05
```

当前 **naming 13/13、want 24/24**。三段真跑出来的经验：

| 观察 | 数字 | 做法 |
|---|---|---|
| 合成的 fixture 会自欺 | 12/12、20/20 全过，因为例句和 prompt 同源 | fixture 一律从 `tests/fixtures/tiktok-*.json` 里挑真实样本 |
| 批量越大越飘 | 24 条一次调用 23/24；12 条一批 24/24 | `want.BATCH = 12`，naming 25 |
| prompt 里写"先判断立场"会被当成输出 | label 返回了整句"asking what something is" | 末尾写死"label 只能是 want/react/sell 三个词之一" |


沿用现有铁律：`tests/conftest.py` 全局禁网，`pytest` 只跑离线。

手上已经有真实数据，直接当 fixture，不造假数据：

- `tests/fixtures/tiktok-search-100.json`（4 个词 × 25 条）
- `tests/fixtures/tiktok-comments-240.json`（6 条视频 × 40 条；标签由 `gitignore/experiments/intent.py` 生成，需人工抽检）

**解析契约**（这次踩到的坑）：模型会漏行，而不是给 `none`。任何"逐条打标"的调用都必须返回"每个下标都有值"，缺的重问，最多 3 轮；测试里要有一条 fixture 断言漏行会被补齐。

TDD 顺序：先写"给定这 100 条，应该挑出哪几个候选"的断言，再写实现。判定逻辑的测试用固定分档，不测模型的具体措辞。

**9.5 一条真实误判（2026-11-03 抓到并修掉）**

`celebrity signature imitation` 被判 open：38.9 万播放、want 37%（40/107）、intitle 10、域名空。看着像文章里那种机会。
看证据发现 40 条里绝大多数是"请帮我签个名"（`Please do a signature for my name 'Harsh Gupta'`）——这是**向创作者下单**，不是"教我怎么做"。
根因在 prompt 自己：want 的定义里写着 `'make me one'` 算 want。
改成"下单（part 2 / make me one / do X for my name）一律 react"后，**同样 107 条评论**重算：37% → 5%，判定变 cold。
教训：挂牌前先读三条证据原话；评测用例要从这种真实误判里长出来，不要自己编。

**9.6 本机 DNS 会说谎（2026-11-03 差点因此全盘判死）**

加了 `.ai` / `.io` 检查后，四个候选瞬间全变成"域名已注册"。查下去发现本机解析器对**任何**域名都返回 `198.18.x.x`（代理客户端的 fake-ip 网段），连 `zzqqxxnoise9931.com` 都能解析。
改用 Cloudflare DoH（`https://cloudflare-dns.com/dns-query?name=…&type=A`，`Status 3` = 不存在，`0` = 存在）后与 RDAP 完全一致：`toc toc ai dance` 2026-10-18 被注册，`celebrity signature imitation` 确实空着。
教训：**任何"是否存在"的判定都不能信任本机 resolver**；查不到 ≠ 存在，查不到要记 `unknown`，不能记 `taken`。

**9.7 评测漏掉的第二件事：整页同一种评论（2026-11-03）**

加了"下单算 react"的规则后，isolated 评测 31/31 全对，但生产里同一批 107 条评论仍算出 26% want —— 那些全是 `Please do a signature for my name 'Harsh Gupta'`。
原因：fixture 把不同类型的句子混在一批里，模型有对照；真实的一页评论是同质的，模型跟着上下文走。加入 4 条 few-shot 后：**26% → 5%**。
代价是 few-shot 一度把"what is this"教成了 want（fixture 从 31/31 掉到 27/31），把例子换成 `how do you make this` 才好。
`gitignore/experiments/eval_prompts.py` 现在多跑一项 `want-batch-signatures.json`（107 条真实下单评论），要求 < 20%；isolated 评测再好看也不能替代它。

## 9. 非目标

- 上站、支付、模板、部署——不在本项目，以后也不集成。
- 中文平台（小红书/即刻/微信）。
- GitHub 库名、HF 模型名作为**线索源**（保留为证据）。
- 全量扫描所有平台。预算不允许。
- 14 天回验。改 7 天。

## 10. 未解决

**名字没有身份。** 同一个东西两轮会产出两个名字：`jeremy clarkson capcut filter`（第 5 轮）和
`jeremy clarkson ai filter`（第 6 轮）。`artifacts.name UNIQUE` 因此挡不住重复，明天会把同一件事
当成新发现再报一次。要么让命名更稳（禁掉 capcut/ai 这类可变修饰），要么加别名表。

**want 的误报是"想看更多"而不是"想做"。** `friday night dinner ai filter` 的 3/76 里有
"Please let's see George an Mildred"——观众在点单内容，不是在问做法。占比低时无害，占比高时会
把一条假机会推上来。

**证据已经能追溯了。** 第 6 轮起，YouTube 用来判定 want 的那几个视频也会写进 `observations`
（platform=youtube，带 URL、频道、播放数），库里已有 10 条。之前"判定 open 却找不到是哪个视频
说的"不会再发生。

1. **`intitle` 的线是猜的。** 只有 10 / 68 / 76 / 1980 四个点，20 这个阈值没有数据支撑。攒到几十个样本再定。
2. **门 1 没测过。** "什么算一个效果名"目前只有直觉，`toc toc ai dance` 算，`ai photo shoot` 不算，但边界（`ai b-roll`？`red light filter`？）没有样本。
3. **want 的绝对率低且噪声大。** 19% 只有 6 条视频、120 条评论撑着；新视频评论本来就少（100 条里 52 条 ≤40 条评论），10 条采样的方差很大。
4. **Apify 的稳定性未知。** 一个 actor、一次运行。TikTok 封控、actor 下线都会让整条链路归零，需要备用 actor 或备用平台。
5. **YouTube 没接。** 按 §5 的账，它是唯一能让预算成立的平台，但一条代码都还没写。
6. **采样偏差没解决。** top-N 评论偏向段子和高赞，want 会被系统性低估。换"最近评论"还是按时间抽样，没测。
7. **`intitle` 有时不返回数值**（`bby wow ai dance` 返回空），需要 fallback 到 `serp` 计数，或标 unknown 而不是当成通过。

## 11. 实施顺序

| 里程碑 | 内容 | 验证 |
|---|---|---|
| M1 ✅ | `radar/artifacts.py` schema + 导入（`tests/test_artifacts.py` 6 条） | 已通过，离线 |
| M2 ✅ | `radar/naming.py`、`radar/want.py`（门 1、门 2） | `tests/test_effects.py`，含漏行重问 |
| M3 ✅ | `radar/claim.py`（门 3） | 复现 10 / 65 / 76 / 1980 |
| M4 ✅ | `radar/effects.py` 日报 + 成本记账 | 每条四行证据，末尾报当天花费 |
| M5 ✅ | 端到端实跑 | 三轮实跑，$0.017–0.025/次，2–7 分钟 |
| M6 ✅ | `radar/queries.py` 自我扩词 | `tests/test_queries.py` 6 条 + 真机抽检 |

M5 之前不碰调度，不碰配置系统。

## 12. 无人值守

`radar effects` 不带查询词时读 `effects.queries`（config），`effects.per` 决定每词取多少条，`effects.cool_days` 决定"凉了"阈值。
一轮 6 个查询 × 25 条 = 150 条 → 新鲜度过滤后约 30 条 → 命名 → 取播放最高 4 个判定：**6–7 分钟、$0.073**。
报告每行带 `new today` 或 `seen since <日期>`，判定多一档 `cooling`（最新一条超过 7 天，窗口在关）。
cron 一行即可：`17 */6 * * * cd <repo> && set -a && . ./.env && set +a && python3 -m radar effects --state state --out report-effects.md`
