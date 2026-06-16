# 亮点二：竞赛评分模型（Codeforces 式 Rating）

> 对应里程碑 M6。实现：`judge/services/rating.py` 的 `apply_contest_rating()` + `judge/api_views.py`（结算/历史端点）+ 前端 `ProfileView.vue`（Rating 曲线）。

---

## 1. 问题背景与动机

一个竞赛平台需要一个能反映选手**真实实力**的单一数值——Rating。要求：

- **赛后按名次更新**：赢强者涨多、输弱者跌多。
- **零和性**：一场比赛不凭空造分/毁分（整体守恒）。
- **收敛性**：实力稳定的选手 Rating 趋于稳定。

> 注意区分：平台原有的 `UserProfile.rating` 是「首次 AC 按难度加分」的**练习积分**，只增不减、不反映对抗实力。本里程碑新增**独立**的 `contest_rating`（默认 1500），只由比赛结算更新，二者互不干扰。

## 2. 相关工作

| 模型 | 特点 |
|------|------|
| **Elo** | 两两对弈期望胜率，国际象棋经典 |
| **Glicko / Glicko-2** | 加入 rating 偏差（不确定性） |
| **TrueSkill** | 贝叶斯，支持多人/组队 |
| **Codeforces** | 在 Elo 基础上扩展到**多人单场排名**，本实现采用 |

本平台选 **Codeforces 算法**：它专为「多人参加同一场、按最终排名结算」设计，与 ACM/OI 赛制天然契合。

## 3. 方法（数学表述）

记参赛者集合 $\{1,\dots,n\}$，选手 $i$ 赛前 rating $R_i$，实际名次 $d_i$（并列取相同名次）。

### 3.1 两两胜率（Elo）

$$
P(a \text{ 胜 } b) = \frac{1}{1 + 10^{(R_b - R_a)/400}}
$$

### 3.2 期望名次（seed）

选手 $i$ 的**期望名次**定义为「期望排在他前面的人数 + 1」：

$$
\text{seed}_i = 1 + \sum_{j \ne i} P(j \text{ 胜 } i)
$$

> **关键**：求和**排除自身** $j \ne i$。这是 CF 算法实现中最易错的一处（见 §5.2）。

### 3.3 目标 rating（几何平均 + 反解）

取期望名次与实际名次的**几何平均**作为「这场该有的名次」：

$$
m_i = \sqrt{\text{seed}_i \cdot d_i}
$$

再**反解**出能达到该名次的 rating——即找 $r$ 使得「把 $i$ 换成 rating $r$ 后的期望名次」等于 $m_i$：

$$
R_i^\star = \big\{\, r : \text{getSeed}(r,\ \text{排除 } i) = m_i \,\big\},
\qquad \text{getSeed}(r, \text{排除 } i) = 1 + \sum_{j \ne i} P(j \text{ 胜 } r)
$$

由于 $\text{getSeed}(r)$ 关于 $r$ 单调递减，用**二分查找**求解。

### 3.4 增量与校正

原始增量取目标与现值之差的一半（稳定收敛）：

$$
\Delta_i = \frac{R_i^\star - R_i}{2}
$$

随后两步校正：

**① 零和校正**——整体平移使总变化 $\approx 0$：

$$
\text{inc} = -\Big\lfloor \frac{\sum_i \Delta_i}{n} \Big\rfloor - 1, \qquad \Delta_i \mathrel{+}= \text{inc}
$$

**② 头部稳定**——取 rating 最高的 $s = \mathrm{round}(4\sqrt{n})$ 人，对其增量做温和向下修正 $\text{inc}_2 \in [-10, 0]$，防止顶尖选手因偶然波动剧烈掉分。

最终 $R_i' = \max(1,\ R_i + \Delta_i)$。

## 4. 算法伪代码

```
apply_contest_rating(contest):
    if contest.rating_applied: return            # 幂等守卫
    standings = compute_ranks(contest)           # [(user, rank)]，ICPC 罚时排名
    R = {u: 赛前 contest_rating}
    for i in 选手:
        seed_i  = 1 + Σ_{j≠i} P(R[j] 胜 R[i])
        m_i     = sqrt(seed_i × rank_i)
        target  = 二分 r 使 getSeed(r, 排除 i) = m_i
        Δ[i]    = (target − R[i]) // 2
    零和校正(Δ);  头部稳定(Δ)
    事务内：更新所有 contest_rating；写 RatingChange(rank, old, new, Δ)
    contest.rating_applied = True
```

## 5. 实现要点与踩坑

### 5.1 名次计算（`_compute_ranks`）

按 ICPC 规则（解题数↓、罚时↑）排名，并列同名次。罚时 = 每道 AC 题 `(AC 时刻 − 开赛) 分钟 + 20 × 错误次数` 之和。IOI 赛制暂以解题数近似（可扩展为按总分）。

### 5.2 ⚠️ 核心踩坑：seed 必须排除自身

开发时第一版把自己也算进了 seed 的求和（用 `seed_all` 含自身项 $P=0.5$），结果**末名选手反而涨分**。原因：$m_i$ 用的是「排除自身」的 seed，而反解时用的 `seed_all` 含自身，**两者量纲不一致**。

修正：seed 与反解的 `getSeed` 都严格 $\sum_{j \ne i}$。修正后立刻正常——这是 CF 实现最隐蔽的 bug，值得在论文/讲解里点出。

### 5.3 幂等与历史

- `Contest.rating_applied` 布尔守卫：重复结算直接跳过，避免二次加减。
- `RatingChange(user, contest, rank, old_rating, new_rating, delta)`：每场每人一条，`unique_together`。这张表既是审计，也是**画 Rating 曲线**的数据源。

### 5.4 触发方式

无自动调度，由**比赛创建者/管理员**在比赛结束后调 `POST /contests/<id>/finalize-rating/` 结算（端点校验：已结束、未结算、创建者/管理员）。`GET /users/<id>/rating-history/` 提供曲线数据。

## 6. 实验与结果

4 人比赛，全部初始 1500，按名次 1/2/3/4 结算：

| 名次 | $\Delta$ | 赛后 rating |
|------|----------|-------------|
| 1 | **+112** | 1612 |
| 2 | +19 | 1519 |
| 3 | −39 | 1461 |
| 4 | **−94** | 1406 |

**性质验证**：

- **单调**：名次越高，涨分越多（+112 > +19 > −39 > −94）。
- **近似零和**：$\sum \Delta = -2$（整数取整 + 校正导致的微小偏差，符合预期）。
- **幂等**：第二次结算返回 `None`（`rating_applied` 已置位）。

## 7. 复杂度

设 $n$ 名选手。每位 seed 求和 $O(n)$，二分约 13 次每次 $O(n)$，故单人 $O(n \log V)$（$V$ 为 rating 上界 8000），总计 $O(n^2 \log V)$。$n$ 数百内完全够用（结算是离线一次性操作）。

## 8. 局限与未来工作

- **IOI 名次近似**：当前用解题数排名，未充分利用 IOI 总分（可换为按 §05 的 IOI 分数排名）。
- **未建模不确定性**：Elo 系不像 Glicko-2 有 rating 偏差；新人/活跃度差异未特别处理（可加「首秀保护」等）。
- **冷启动**：全员从 1500 起，需多场才区分；可引入初始定级赛。

## 9. 写进论文的建议

**可表述为的创新点**：

> 「实现了基于 Codeforces 算法的竞赛评分模型：以 Elo 两两胜率为基础，通过**期望名次（seed）与实际名次的几何平均**反解目标 rating，取半步增量并施加零和与头部稳定校正，将两人对弈的 Elo 推广到多人单场排名。系统保证结算幂等并记录变化历史以可视化 rating 轨迹。」

**建议补充的实验/分析**：

1. **收敛性模拟**：构造已知「真实实力」的选手群，模拟多场比赛，观察 rating 是否收敛到真实序、需多少场。
2. **零和性度量**：统计多场结算的 $\sum\Delta$ 分布，验证守恒程度。
3. **与朴素 Elo 对比**：在多人场景下，逐对 Elo 累加 vs CF 单场结算的差异。
4. **数学推导**：把 §3 的 seed/几何平均/反解整理为论文公式推导，配 §5.2 的「排除自身」证明（量纲一致性）。
