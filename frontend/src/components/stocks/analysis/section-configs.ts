// 各专家 SECTION_CONFIGS — 与 backend prompt 模板的 JSON schema 一一对应
// 注：本文件只承载声明式数据，不包含 React 组件；JSON 顶层 key + 中文标签映射

export interface SectionConfig {
  key: string
  title: string
  labels?: Record<string, string>
}

export const SECTION_CONFIGS: Record<string, SectionConfig[]> = {
  // 游资观点 v3.1.0（顶级游资 + 日内动能专家）
  hot_money_view: [
    {
      key: 'seat_analysis',
      title: '龙虎榜 · 席位分析',
      labels: {
        on_billboard_60d: '近 60 日上榜',
        buyer_seat_type: '买方席位性质',
        seat_signal: '席位信号',
        key_seats: '关键席位',
      },
    },
    {
      key: 'theme_position',
      title: '题材身位与板位',
      labels: {
        limit_status_today: '本日涨停状态',
        sector_rank: '板块地位',
        relative_position: '相对位置',
        ecology_note: '市场情绪生态',
      },
    },
    {
      key: 'limit_gene',
      title: '打板基因（近 60 日）',
      labels: {
        limit_up_count_60d: '涨停次数',
        t1_win_rate: 'T+1 胜率',
        t1_avg_pct: 'T+1 平均涨跌',
        gene_verdict: '基因判定',
      },
    },
    {
      key: 'capital_structure',
      title: '资金与筹码结构',
      labels: {
        main_flow_signal: '主力资金信号',
        divergence_flag: '分歧/一致',
      },
    },
    {
      key: 'momentum_signal',
      title: '竞价 · 量价动能',
      labels: {
        auction_signal: '竞价信号',
        volume_structure: '量能结构',
        technical_verdict: '技术共振',
      },
    },
    {
      key: 'next_day_scenarios',
      title: '次日三档情景概率',
      labels: {
        bull_pct_ge_3: '强势溢价（≥+3%）',
        neutral_minus2_to_3: '震荡平开（-2%~+3%）',
        bear_pct_le_minus2: '破板低开（≤-2%）',
        key_observation_window: '重点观察窗口',
      },
    },
    {
      key: 'execution_plan',
      title: '执行计划',
      labels: {
        entry_zones: '分批介入价位',
        stop_loss: '止损价位',
        add_position_trigger: '加仓触发',
        t0_reduce_signal: 'T+0 减仓信号',
      },
    },
  ],
  midline_review: [
    { key: 'review_adequacy', title: '复盘时效性' },
    { key: 'prediction_summary', title: '原预测摘要' },
    {
      key: 'hit_rate',
      title: '命中度评估',
      labels: {
        industry_cycle: '产业景气度演变',
        earnings_fulfillment: '业绩兑现度',
        technical_evolution: '技术结构演变',
        price_target: '目标价区间命中',
        score_rating: '评分档位',
      },
    },
    { key: 'mispriced_factors', title: '误判归因' },
    {
      key: 'execution_retrospective',
      title: '中线持有复盘',
      labels: {
        entry_executed_result: '按计划买入结果',
        stop_loss_triggered: '是否触发止损',
        catalyst_fulfilled: '催化剂兑现状态',
        overall_verdict: '整体战果',
      },
    },
    { key: 'prompt_improvement_hints', title: 'Prompt 改进建议' },
    { key: 'lesson_for_future', title: '可迁移经验' },
  ],
  longterm_review: [
    { key: 'review_adequacy', title: '复盘时效性' },
    { key: 'prediction_summary', title: '原预测摘要' },
    {
      key: 'hit_rate',
      title: '命中度评估',
      labels: {
        moat_validation: '护城河验证',
        earnings_quality_fulfillment: '盈利质量兑现',
        valuation_mean_reversion: '估值回归进度',
        expected_return: '预期回报拆解',
        risk_exposure: '风险暴露',
        score_rating: '评分档位',
      },
    },
    { key: 'mispriced_factors', title: '误判归因' },
    {
      key: 'execution_retrospective',
      title: '长线持有复盘',
      labels: {
        entry_executed_result: '按计划买入结果',
        dividend_received: '持有期间派息',
        dca_opportunity: '加仓机会',
        overall_verdict: '整体战果',
      },
    },
    { key: 'prompt_improvement_hints', title: 'Prompt 改进建议' },
    { key: 'lesson_for_future', title: '可迁移经验' },
  ],
  hot_money_review: [
    { key: 'prediction_summary', title: '原预测摘要' },
    {
      key: 'hit_rate',
      title: '命中度评估',
      labels: {
        next_day_scenario: '次日情景预测',
        seat_signal: '席位信号预测',
        theme_position: '题材身位预测',
        score_rating: '评分档位',
      },
    },
    { key: 'mispriced_factors', title: '误判归因' },
    {
      key: 'execution_retrospective',
      title: '执行计划复盘',
      labels: {
        entry_executed_result: '按计划买入结果',
        stop_loss_triggered: '是否触发止损',
        add_position_triggered: '是否触发加仓',
        overall_verdict: '整体战果',
      },
    },
    { key: 'prompt_improvement_hints', title: 'Prompt 改进建议' },
    { key: 'lesson_for_future', title: '可迁移经验' },
  ],
  midline_industry_expert: [
    {
      key: 'industry_cycle',
      title: '产业景气度',
      labels: {
        sector_name: '板块归属',
        cycle_stage: '景气周期阶段',
        relative_strength: '板块 vs 个股相对强度',
        catalyst_note: '中线催化要点',
      },
    },
    {
      key: 'fundamental_quality',
      title: '公司基本面质地',
      labels: {
        latest_earnings_trend: '最新业绩趋势',
        profitability_level: '盈利能力',
        valuation_signal: '估值信号',
        quality_verdict: '质地判定',
      },
    },
    {
      key: 'technical_structure',
      title: '中线技术结构',
      labels: {
        weekly_macd: '周线 MACD',
        monthly_boll_position: '月线布林',
        ma_anchor: '均线锚点',
        structure_verdict: '结构判定',
      },
    },
    {
      key: 'price_target',
      title: '目标价区间（3~12 个月）',
      labels: {
        time_horizon: '时间窗口',
        target_range_low: '下沿目标价',
        target_range_high: '上沿目标价',
        target_method: '推演方法',
        stop_loss: '中线止损',
      },
    },
    {
      key: 'catalysts_and_risks',
      title: '催化剂与风险',
      labels: {
        catalysts: '催化剂',
        risks: '风险',
      },
    },
  ],
  // CIO followup_triggers 由 FollowupTriggersSection 自定义渲染
  cio_directive: [
    {
      key: 'multi_dimension_scan',
      title: '多维度快速扫描',
      labels: {
        short_term: '短线（1-5 日）',
        mid_term: '中线（1-3 月）',
        long_term: '长线（1-3 年）',
      },
    },
    {
      key: 'cross_dimension_analysis',
      title: '跨维度共振/矛盾',
      labels: {
        consensus_or_conflict: '方向一致性',
        conflict_essence: '矛盾本质',
        cio_resolution: 'CIO 取舍',
      },
    },
    { key: 'core_drivers', title: '核心驱动因子' },
    { key: 'core_risks', title: '核心风险因子' },
    {
      key: 'rating_and_action',
      title: '综合评级与行动指令',
      labels: {
        rating: '综合评级',
        action: '行动指令',
        price_reference: '价位区间参考',
        rating_logic: '评级逻辑',
      },
    },
  ],
  longterm_value_watcher: [
    {
      key: 'moat_assessment',
      title: '护城河评估',
      labels: {
        moat_type: '护城河类型',
        moat_width: '护城河宽度',
        inference_basis: '推断依据',
      },
    },
    {
      key: 'earnings_quality',
      title: '长期盈利质量',
      labels: {
        roe_level: 'ROE 水平',
        gross_margin: '毛利率',
        repurchase_signal: '回购信号',
        earnings_trend: '业绩趋势',
        quality_verdict: '质地判定',
      },
    },
    {
      key: 'valuation_margin',
      title: '估值安全边际',
      labels: {
        current_pe: '当前 PE',
        pe_band_position: 'PE Band 分位',
        forward_pe_deviation: 'Forward PE 偏离',
        margin_verdict: '安全边际判定',
      },
    },
    {
      key: 'long_term_risk',
      title: '长线持有风险',
      labels: {
        shareholder_concentration: '股东集中度',
        northbound_trend: '北向资金趋势',
        pledge_risk: '股权质押',
        unlock_risk: '解禁风险',
        risk_verdict: '风险判定',
      },
    },
    {
      key: 'expected_return',
      title: '预期回报拆解（3~5 年）',
      labels: {
        time_horizon: '时间窗口',
        earnings_growth_contribution: '盈利增长贡献',
        valuation_expansion_contribution: '估值修复贡献',
        dividend_contribution: '股息贡献',
        total_annualized_return: '预期年化总回报',
      },
    },
  ],
}

// 兼容旧 schema 的 probability_metrics 字段标签
export const PM_FIELD_LABELS: Record<string, { label: string; prefix?: string }> = {
  next_day_plus_2_percent_prob: { label: '次日 +2% 概率' },
  confidence_level: { label: '置信度' },
  key_observation_window: { label: '观察窗口' },
  three_month_positive_return_prob: { label: '3 个月正收益概率' },
  trend_stage: { label: '趋势阶段' },
  key_catalyst: { label: '核心催化' },
  one_year_intrinsic_return_prob: { label: '1 年内在回报概率' },
  valuation_level: { label: '估值水位' },
  safety_margin: { label: '安全边际' },
  short_term_signal: { label: '短线信号' },
  mid_term_signal: { label: '中线信号' },
  long_term_signal: { label: '长线信号' },
}

export const JSON_ANALYSIS_TYPES = new Set([
  'hot_money_view', 'hot_money_review',
  'midline_industry_expert', 'midline_review',
  'longterm_value_watcher', 'longterm_review',
  'cio_directive', 'macro_risk_expert',
])
