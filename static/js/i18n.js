// ===== BDE Score i18n System =====
// Shared internationalization for all pages

const i18nTranslations = {
  en: {
    // Landing page
    nav_features: "Features", nav_pricing: "Pricing", nav_compliance: "Compliance", nav_cta: "Get Started",
    nav_signin: "Sign In", nav_signup: "Sign Up",
    hero_badge: "Live — 73 stocks across 3 markets", hero_title1: "One Score.", hero_title2: "Every Market.",
    hero_desc: "AI-powered multi-factor quantitative analysis for US, HK & A-share markets. Real-time data. Explainable methodology. Regulatory-ready.",
    hero_btn1: "View Live Dashboard →", hero_btn2: "See Pricing",
    stat_stocks: "Stocks", stat_markets: "Markets", stat_monitoring: "Monitoring",
    feat_title: "Why BDE Score™?", feat_subtitle: "Institutional-grade analysis, accessible to everyone.",
    feat1_title: "Multi-Factor Scoring", feat1_desc: "Composite score from momentum, mean reversion, volume, volatility & trend analysis. Each factor transparently weighted.",
    feat2_title: "Three Markets, One View", feat2_desc: "US (25), HK (26), and A-shares (23) — normalized scoring across all markets for cross-market comparison.",
    feat3_title: "Real-Time Dual Channel", feat3_desc: "RESTful API for bots and MCP protocol for AI agents. Same data, two integration paths.",
    feat4_title: "EU AI Act Ready", feat4_desc: "Built for Article 50 transparency. Full audit trails, explainable scores, machine-readable compliance metadata.",
    feat5_title: "Historical Tracking", feat5_desc: "Track score evolution over 365 days. Identify trends before they become obvious. Backtest strategies.",
    feat6_title: "API-First Design", feat6_desc: "RESTful JSON API. Integrate BDE Score into your trading bots, dashboards, or research workflows.",
    price_title: "Simple, Transparent Pricing", price_subtitle: "Credit-based pay-per-use. Start free, scale as you grow.",
    tier_free_name: "Free", tier_free_tag: "Explore", tier_free_unit: "/forever",
    tier_free_f1: "1,000 free credits", tier_free_f2: "Live dashboard view", tier_free_f3: "3 queries/day limit", tier_free_f4: "All 3 markets", tier_free_btn: "Try Free",
    tier_starter_name: "Starter", tier_starter_tag: "Individual",
    tier_starter_f1: "No daily limit", tier_starter_f2: "Full API access", tier_starter_f3: "365-day history", tier_starter_btn: "Get Started",
    tier_std_name: "Standard", tier_std_tag: "Active traders",
    tier_std_f1: "Factor breakdown", tier_std_f2: "Push alerts", tier_std_f3: "Priority support", tier_std_btn: "Subscribe →",
    tier_pro_tag: "Power users",
    tier_pro_f1: "White-label API", tier_pro_f2: "Compliance reports", tier_pro_f3: "Dedicated SLA", tier_pro_btn: "Go Pro",
    price_note1: "1 credit = 1 API analysis call", price_note2: "Unused credits never expire", price_note3: "New users get 1,000 free credits",
    pay_title: "Pay with USDC", pay_desc: "Send USDC on Base chain to activate your credits",
    pay_note: "Base Network (ERC-20 USDC) · Send amount matching your chosen tier · Email receipt to confirm activation",
    comp_badge: "Regulatory Countdown", comp_title: "EU AI Act — Art.50 Compliance",
    comp_desc: "BDE Score™ is built with transparency at its core. When Art.50 takes effect, our system is already compliant.",
    comp1_title: "Audit Trails", comp1_desc: "Every score decision is logged with full factor weights and input data",
    comp2_title: "Explainable", comp2_desc: "Each stock's score breaks down into momentum, reversion, volume, volatility & trend",
    comp3_title: "Machine-Readable", comp3_desc: "Compliance metadata in JSON format for regulatory reporting",
    contact_title: "Get Early Access", contact_desc: "Join the waitlist for Premium and Institutional tiers. Be first to know when new features launch.",
    contact_btn: "Join Waitlist", contact_ok: "✓ You're on the list! We'll be in touch.",
    foot_dashboard: "Dashboard", foot_status: "Status", foot_pricing: "Pricing",
    foot_terms: "Terms of Service", foot_privacy: "Privacy Policy", foot_legal: "Legal Disclaimer",
    disc_title: "Disclaimer:", disc_text: "BDE Score™ is a technical analysis tool, not financial advice. All investment decisions should be made independently. Past performance does not guarantee future results. BDE Score™ does not provide investment suitability assessments.",
    
    // Auth pages (register/login)
    register_title: "Create Account", register_subtitle: "Start your free evaluation",
    login_title: "Welcome Back", login_subtitle: "Sign in to continue",
    email_label: "Email Address", password_label: "Password", confirm_label: "Confirm Password",
    register_btn: "Create Account", login_btn: "Sign In",
    have_account: "Already have an account?", no_account: "Don't have an account?",
    
    // Dashboard
    dash_title: "Dashboard", dash_subtitle: "Real-time BDE Score analysis",
    dash_logout: "Logout", dash_credits: "credits",
    
    // Pricing
    pricing_title: "Choose Your Plan", pricing_subtitle: "Start free, upgrade as you grow",
    popular_badge: "MOST POPULAR",
    
    // Payment
    payment_title: "Complete Payment", payment_subtitle: "Activate your credits",
    payment_amount: "Amount", payment_address: "Send to this address",
    
    // Compliance
    check_title: "Compliance Check", check_subtitle: "Evaluate AI system compliance",
    check_btn: "Run Check", check_result: "Compliance Score",
    
    // Common
    loading: "Loading...", error: "Error", success: "Success", cancel: "Cancel", confirm: "Confirm",
    back: "Back", next: "Next", submit: "Submit", save: "Save", delete: "Delete", edit: "Edit"
  },
  zh: {
    nav_features: "功能特性", nav_pricing: "定价", nav_compliance: "合规", nav_cta: "立即开始",
    nav_signin: "登录", nav_signup: "注册",
    hero_badge: "实时在线 — 3个市场73只股票", hero_title1: "一个评分。", hero_title2: "全市场覆盖。",
    hero_desc: "AI驱动的多因子量化分析系统，覆盖美股、港股和A股。实时数据、可解释方法论、监管合规。",
    hero_btn1: "查看实时面板 →", hero_btn2: "查看定价",
    stat_stocks: "股票", stat_markets: "市场", stat_monitoring: "全天候监控",
    feat_title: "为什么选择 BDE Score™？", feat_subtitle: "机构级分析，人人可用。",
    feat1_title: "多因子评分", feat1_desc: "综合动量、均值回归、成交量、波动率和趋势分析的复合评分，每个因子透明加权。",
    feat2_title: "三市一网", feat2_desc: "美股(25)、港股(26)、A股(23)——跨市场标准化评分，横向可比。",
    feat3_title: "实时双通道", feat3_desc: "RESTful API对接交易机器人，MCP协议对接AI Agent。同一数据，两种集成路径。",
    feat4_title: "EU AI Act就绪", feat4_desc: "为第50条透明度要求而生。完整审计追踪、可解释评分、机器可读合规元数据。",
    feat5_title: "历史追踪", feat5_desc: "追踪365天评分演变。在趋势明朗前识别机会。支持策略回测。",
    feat6_title: "API优先设计", feat6_desc: "RESTful JSON API。将BDE Score集成到你的交易机器人、面板或研究工作流。",
    price_title: "简洁透明的定价", price_subtitle: "积分制按次付费。免费起步，按需扩展。",
    tier_free_name: "免费版", tier_free_tag: "体验", tier_free_unit: "/永久",
    tier_free_f1: "1,000免费积分", tier_free_f2: "实时面板查看", tier_free_f3: "每日3次查询", tier_free_f4: "全3市场", tier_free_btn: "免费试用",
    tier_starter_name: "入门版", tier_starter_tag: "个人用户",
    tier_starter_f1: "无每日限制", tier_starter_f2: "完整API访问", tier_starter_f3: "365天历史", tier_starter_btn: "开始使用",
    tier_std_name: "标准版", tier_std_tag: "活跃交易者",
    tier_std_f1: "因子拆解", tier_std_f2: "实时推送", tier_std_f3: "优先支持", tier_std_btn: "立即订阅 →",
    tier_pro_tag: "高级用户",
    tier_pro_f1: "白标API", tier_pro_f2: "合规报告", tier_pro_f3: "专属SLA", tier_pro_btn: "升级Pro",
    price_note1: "1积分 = 1次API分析", price_note2: "积分永不过期", price_note3: "新用户赠送1,000积分",
    pay_title: "USDC支付", pay_desc: "在Base链上发送USDC激活积分",
    pay_note: "Base网络 (ERC-20 USDC) · 发送对应套餐金额 · 邮件回执确认激活",
    comp_badge: "监管倒计时", comp_title: "EU AI Act — 第50条合规",
    comp_desc: "BDE Score™以透明为核心构建。当第50条生效时，我们的系统已经合规。",
    comp1_title: "审计追踪", comp1_desc: "每个评分决策都记录完整的因子权重和输入数据",
    comp2_title: "可解释性", comp2_desc: "每只股票的评分拆解为动量、回归、成交量、波动率和趋势",
    comp3_title: "机器可读", comp3_desc: "JSON格式的合规元数据，用于监管报告",
    contact_title: "获取早期访问", contact_desc: "加入高级版和机构版候补名单。第一时间获取新功能发布通知。",
    contact_btn: "加入候补", contact_ok: "✓ 已加入候补名单！我们会尽快联系您。",
    foot_dashboard: "数据面板", foot_status: "系统状态", foot_pricing: "定价",
    foot_terms: "服务条款", foot_privacy: "隐私政策", foot_legal: "法律声明",
    disc_title: "免责声明：", disc_text: "BDE Score™是技术分析工具，非投资建议。所有投资决策应独立做出。过往表现不代表未来收益。BDE Score™不提供投资适宜性评估。",
    
    register_title: "创建账户", register_subtitle: "开始免费评估",
    login_title: "欢迎回来", login_subtitle: "登录以继续",
    email_label: "邮箱地址", password_label: "密码", confirm_label: "确认密码",
    register_btn: "创建账户", login_btn: "登录",
    have_account: "已有账户？", no_account: "还没有账户？",
    
    dash_title: "数据面板", dash_subtitle: "实时BDE评分分析",
    dash_logout: "退出登录", dash_credits: "积分",
    
    pricing_title: "选择套餐", pricing_subtitle: "免费起步，按需升级",
    popular_badge: "最受欢迎",
    
    payment_title: "完成支付", payment_subtitle: "激活您的积分",
    payment_amount: "金额", payment_address: "发送至地址",
    
    check_title: "合规检查", check_subtitle: "评估AI系统合规性",
    check_btn: "运行检查", check_result: "合规评分",
    
    loading: "加载中...", error: "错误", success: "成功", cancel: "取消", confirm: "确认",
    back: "返回", next: "下一步", submit: "提交", save: "保存", delete: "删除", edit: "编辑"
  },
  ja: {
    nav_features: "機能", nav_pricing: "料金", nav_compliance: "コンプライアンス", nav_cta: "始める",
    nav_signin: "ログイン", nav_signup: "登録",
    hero_badge: "ライブ — 3市場73銘柄", hero_title1: "一つのスコア。", hero_title2: "全市場カバー。",
    hero_desc: "AI駆動の多因子量的分析。米国・香港・A株市場をカバー。リアルタイムデータ。説明可能な手法。規制対応済み。",
    hero_btn1: "ライブダッシュボード →", hero_btn2: "料金を見る",
    stat_stocks: "銘柄", stat_markets: "市場", stat_monitoring: "24時間監視",
    feat_title: "BDE Score™の特徴", feat_subtitle: "機関投資家レベルの分析を、すべての人に。",
    feat1_title: "多因子スコアリング", feat1_desc: "モメンタム、平均回帰、出来高、ボラティリティ、トレンド分析の複合スコア。各因子は透明に加重。",
    feat2_title: "3市場一つのビュー", feat2_desc: "米国(25)、香港(26)、A株(23)——全市場の正規化スコアでクロス市場比較。",
    feat3_title: "リアルタイム二重チャネル", feat3_desc: "ボット向けRESTful API、AIエージェント向けMCPプロトコル。同じデータ、2つの統合パス。",
    feat4_title: "EU AI Act対応", feat4_desc: "第50条の透明性要件に対応。完全な監査証跡、説明可能なスコア、機械読み取り可能なコンプライアンスメタデータ。",
    feat5_title: "履歴追跡", feat5_desc: "365日間のスコア推移を追跡。トレンドが明確になる前に識別。戦略バックテスト対応。",
    feat6_title: "APIファースト設計", feat6_desc: "RESTful JSON API。BDE Scoreを取引ボット、ダッシュボード、研究ワークフローに統合。",
    price_title: "シンプルで透明な料金", price_subtitle: "クレジット制の従量課金。無料で始めて、成長に応じて拡張。",
    tier_free_name: "無料", tier_free_tag: "お試し", tier_free_unit: "/永久",
    tier_free_f1: "1,000クレジット無料", tier_free_f2: "ライブダッシュボード", tier_free_f3: "1日3クエリ制限", tier_free_f4: "全3市場", tier_free_btn: "無料で始める",
    tier_starter_name: "スターター", tier_starter_tag: "個人向け",
    tier_starter_f1: "日次制限なし", tier_starter_f2: "フルAPIアクセス", tier_starter_f3: "365日履歴", tier_starter_btn: "始める",
    tier_std_name: "スタンダード", tier_std_tag: "アクティブトレーダー",
    tier_std_f1: "因子内訳", tier_std_f2: "プッシュ通知", tier_std_f3: "優先サポート", tier_std_btn: "契約する →",
    tier_pro_tag: "パワーユーザー",
    tier_pro_f1: "ホワイトラベルAPI", tier_pro_f2: "コンプライアンスレポート", tier_pro_f3: "専用SLA", tier_pro_btn: "Proにアップグレード",
    price_note1: "1クレジット = 1回API分析", price_note2: "未使用クレジットは無期限", price_note3: "新規ユーザーに1,000クレジット進呈",
    pay_title: "USDCで支払い", pay_desc: "BaseチェーンでUSDCを送信してクレジットを有効化",
    pay_note: "Baseネットワーク (ERC-20 USDC) · 選択したプランの金額を送信 · メールレシートでアクティベーション確認",
    comp_badge: "規制カウントダウン", comp_title: "EU AI Act — 第50条コンプライアンス",
    comp_desc: "BDE Score™は透明性を中核に構築。第50条施行時、すでにコンプライアンス済み。",
    comp1_title: "監査証跡", comp1_desc: "各スコア決定に完全な因子ウェイトと入力データを記録",
    comp2_title: "説明可能性", comp2_desc: "各銘柄のスコアはモメンタム、回帰、出来高、ボラティリティ、トレンドに分解",
    comp3_title: "機械読み取り可能", comp3_desc: "規制報告用JSON形式のコンプライアンスメタデータ",
    contact_title: "早期アクセスを取得", contact_desc: "プレミアム・機関投資家プランのウェイトリストに参加。新機能の最新情報をお届け。",
    contact_btn: "ウェイトリストに参加", contact_ok: "✓ リストに登録されました！ご連絡いたします。",
    foot_dashboard: "ダッシュボード", foot_status: "ステータス", foot_pricing: "料金",
    foot_terms: "利用規約", foot_privacy: "プライバシーポリシー", foot_legal: "法的通知",
    disc_title: "免責事項：", disc_text: "BDE Score™は技術分析ツールであり、投資助言ではありません。すべての投資判断は独立して行われるべきです。過去の成果は将来の成果を保証するものではありません。BDE Score™は投資適合性評価を提供しません。",
    
    register_title: "アカウント作成", register_subtitle: "無料評価を開始",
    login_title: "お帰りなさい", login_subtitle: "続行するにはログイン",
    email_label: "メールアドレス", password_label: "パスワード", confirm_label: "パスワード確認",
    register_btn: "アカウント作成", login_btn: "ログイン",
    have_account: "アカウントをお持ちですか？", no_account: "アカウントをお持ちでないですか？",
    
    dash_title: "ダッシュボード", dash_subtitle: "リアルタイムBDEスコア分析",
    dash_logout: "ログアウト", dash_credits: "クレジット",
    
    pricing_title: "プランを選択", pricing_subtitle: "無料で開始、按需アップグレード",
    popular_badge: "人気No.1",
    
    payment_title: "支払い完了", payment_subtitle: "クレジットを有効化",
    payment_amount: "金額", payment_address: "送信先アドレス",
    
    check_title: "コンプライアンスチェック", check_subtitle: "AIシステムのコンプライアンスを評価",
    check_btn: "チェック実行", check_result: "コンプライアンススコア",
    
    loading: "読み込み中...", error: "エラー", success: "成功", cancel: "キャンセル", confirm: "確認",
    back: "戻る", next: "次へ", submit: "送信", save: "保存", delete: "削除", edit: "編集"
  }
};

function setLang(lang) {
  const t = i18nTranslations[lang];
  if (!t) return;
  
  // Apply translations to all data-i18n elements
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (t[key]) el.textContent = t[key];
  });
  
  // Handle data-i18n-placeholder
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (t[key]) el.placeholder = t[key];
  });
  
  // Update language selector buttons
  document.querySelectorAll('.lang-btn').forEach(btn => {
    const isActive = btn.dataset.lang === lang;
    btn.classList.toggle('active', isActive);
    btn.classList.toggle('text-blue-400', isActive);
    btn.classList.toggle('bg-blue-500/20', isActive);
  });
  
  // Save preference
  localStorage.setItem('bde_lang', lang);
  
  // Page-specific callback (e.g., dashboard chart re-render)
  if (typeof window._i18nCallback === 'function') window._i18nCallback();
  
  // Update all internal links with lang param
  document.querySelectorAll('a[href^="/"]').forEach(a => {
    if (!a.href.includes('lang=')) {
      const sep = a.href.includes('?') ? '&' : '?';
      a.href = a.href.split('?')[0] + '?lang=' + lang;
    }
  });
  // Update .i18n-link elements (cross-page links)
  document.querySelectorAll('a.i18n-link').forEach(a => {
    const base = a.getAttribute('href').split('?')[0];
    a.setAttribute('href', base + (base.includes('/') ? '?lang=' : '') + lang);
  });
  
  // Set document language
  document.documentElement.lang = lang;
}

// Get current language
function getLang() {
  const urlLang = new URLSearchParams(window.location.search).get('lang');
  if (urlLang && i18nTranslations[urlLang]) return urlLang;
  
  const savedLang = localStorage.getItem('bde_lang');
  if (savedLang && i18nTranslations[savedLang]) return savedLang;
  
  const browserLang = navigator.language.startsWith('zh') ? 'zh' : 
                      navigator.language.startsWith('ja') ? 'ja' : 'en';
  return browserLang;
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  const lang = getLang();
  setLang(lang);
  
  // Bind language selector buttons
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => setLang(btn.dataset.lang));
  });
});
