/* UI translations only. Market values, identifiers and source disclosures stay intact. */
(() => {
  const entries = [
    ['载入数据中','Loading data','データを読み込み中'],
    ['正在核对快照日期与来源…','Checking snapshot date and source…','日付とデータソースを確認中…'],
    ['筛选工具','Filters','絞り込み'],
    ['搜索代码或名称，如 CIBR、网络安全…','Search ticker or name, e.g. CIBR, cybersecurity…','銘柄コード・名称を検索（例：CIBR、サイバーセキュリティ）'],
    ['全部资产组','All asset groups','すべての資産分類'],
    ['资产组','Asset group','資産分類'],
    ['交易状态筛选','Filter by setup','取引状態で絞り込み'],
    ['全部','All','すべて'],['可交易','Actionable','取引候補'],['等待确认','Watch','確認待ち'],['趋势破坏','Broken trend','トレンド崩れ'],
    ['市场宽度概览','Market breadth overview','市場の広がり'],
    ['长趋势仍在，短线动量收缩','Long-term gains, weaker short-term momentum','長期上昇を維持、短期モメンタムは縮小'],
    ['正在分析市场宽度…','Analyzing market breadth…','市場の広がりを分析中…'],
    ['上涨比例','Share of ETFs with positive returns','上昇しているETFの割合'],
    ['20日 × 60日动量象限','20-day × 60-day momentum','20日 × 60日モメンタム'],
    ['120日弱','Weak 120D','120日・弱'],['120日强','Strong 120D','120日・強'],
    ['ETF 20日和60日收益散点图','ETF 20-day and 60-day return scatterplot','ETFの20日・60日リターン散布図'],
    ['右上角代表短中期同步上涨；圆点越大，20日平均成交额越高。点击圆点查看交易参数。','Upper right: positive short- and medium-term returns. Larger dots indicate higher 20-day average dollar volume. Select a dot for trade levels.','右上は短期・中期ともに上昇。点が大きいほど20日平均売買代金が多くなります。点を選ぶと取引の参考水準を表示します。'],
    ['综合动量排名','Composite momentum ranking','総合モメンタム順位'],
    ['当前交易机会','Current trade setups','現在の取引候補'],
    ['回踩优先，突破确认；过热品种等待均值回归。','Watch pullbacks and confirm breakouts. Wait for extended ETFs to cool down.','押し目を観察し、ブレイクアウトを確認。過熱したETFは落ち着くまで待ちます。'],
    ['ETF 扫描明细','ETF scan results','ETFスキャン詳細'],
    ['代码','Ticker','銘柄コード'],['收盘','Close','終値'],['相对SPY','vs. SPY','対SPY'],['评分','Score','スコア'],['状态','Setup','状態'],
    ['关闭详情','Close details','詳細を閉じる'],
    ['宽基','Broad market','市場全体'],['行业板块','Sectors','セクター'],['细分行业','Industries','業種'],['实物资产','Real assets','実物資産'],['因子','Factors','ファクター'],['债券','Bonds','債券'],['国际市场','International','海外市場'],
    ['动量成立','Momentum','モメンタム成立'],['强势·等回踩','Strong · wait for pullback','強い・押し目待ち'],
    ['扫描范围','Universe','対象銘柄'],['只 ETF','ETFs','本のETF'],['非杠杆代表性资产','Representative unleveraged assets','非レバレッジ型の代表的資産'],
    ['20日上涨','Positive over 20 days','20日間で上昇'],['60日上涨','Positive over 60 days','60日間で上昇'],['短线宽度','short-term breadth','短期の上昇比率'],['中期宽度','medium-term breadth','中期の上昇比率'],['多头排列','Bullish alignment','上昇配列'],
    ['多数资产仍保留120日涨幅，但短线参与度不足，当前更像结构性轮动。','Most assets retain their 120-day gains, but short-term participation is limited, suggesting selective rotation.','多くの資産は120日間の上昇を維持していますが、短期の上昇銘柄は限られ、選別的な資金移動が見られます。'],
    ['不同周期宽度较为接近，趋势扩散相对均衡。','Breadth is relatively similar across periods, with a more balanced spread of trends.','期間ごとの上昇比率は比較的近く、トレンドの広がりは均衡しています。'],
    ['没有符合条件的 ETF','No matching ETFs','条件に合うETFはありません'],
    ['回踩区','Pullback zone','押し目ゾーン'],['突破触发','Breakout trigger','ブレイク水準'],['失效参考','Invalidation level','無効化の参考水準'],
    ['综合动量评分','Composite momentum score','総合モメンタムスコア'],
    ['60日相对SPY','60-day return vs. SPY','60日リターン（対SPY）'],['ATR / 价格','ATR / price','ATR / 価格'],['距120日高点','From 120-day high','120日高値からの乖離'],
    ['等待价格进入回踩观察区 ','Watch for price to enter the pullback zone ','価格が押し目ゾーン '],['，观察是否止跌。',', then look for stabilization.',' に入り、下げ止まるかを確認します。'],
    ['趋势延续的突破触发参考为 ','The breakout reference for trend continuation is ','トレンド継続のブレイク参考水準は '],
    ['结构失效参考 ','Structural invalidation reference: ','トレンド構造の無効化参考水準：'],['；当前至该位置约 ','; distance from current price: ','。現在値からの距離：'],
    ['快照信息 HTTP','Snapshot metadata HTTP','スナップショット情報 HTTP'],
    ['页面正在更新，请刷新后重试','The page is updating. Please refresh and try again.','ページを更新中です。再読み込みしてください。'],
    ['快照日期或数量不一致','Snapshot date or record count mismatch','スナップショットの日付または件数が一致しません'],
    ['数据截止','Data through','データ基準日'],['日线','daily bars','日足'],['只完整','complete','件・完全'],['更新时间','Updated','更新日時'],['更新 ','Updated ','更新 '],['北京时间','China time (UTC+8)','中国時間（UTC+8）'],
    ['分红/拆股复权 · 云端自动刷新','Dividend/split adjusted · automatic cloud refresh','配当・株式分割調整済み・クラウド自動更新'],['本地快照','Imported local snapshot','ローカル取込スナップショット'],
    ['已超过4天未更新，请查看运行记录','No update for over 4 days. Check the run history.','4日以上更新されていません。実行履歴を確認してください。'],['数据载入失败','Unable to load data','データを読み込めませんでした'],
    ['基金介绍与持仓','Fund profile and holdings','ファンド概要と保有銘柄'],['暂无可核验资料。','No verifiable information available.','確認可能な情報がありません。'],['正在读取基金资料…','Loading fund information…','ファンド情報を読み込み中…'],
    ['本次获取未成功，保留此前资料','Refresh failed; previously retrieved information retained','取得に失敗したため、以前の情報を表示しています'],['来源标注日期','Source-reported date','情報元の記載日'],
    ['来源未披露持仓日期，无法确认是否为最新持仓','The source does not disclose a holdings date; freshness cannot be confirmed.','情報元が保有銘柄の基準日を公開していないため、最新情報かは確認できません。'],
    ['此类产品可能通过实物、期货或抵押资产提供敞口，不能把股票持仓表视为完整风险敞口。','These products may hold physical assets, futures or collateral. An equity holdings table does not represent their full exposure.','現物資産、先物、担保資産などを通じて投資する商品です。株式の保有一覧だけではリスク全体を把握できません。'],
    ['债券ETF的主要风险还包括久期和信用质量，前十大证券不足以代表完整组合。','Bond ETF risks also depend on duration and credit quality. The top ten securities do not describe the entire portfolio.','債券ETFのリスクにはデュレーションや信用力も関係します。上位10銘柄だけでは全体像を把握できません。'],
    ['持仓权重反映披露时点，不能从权重变化直接推断基金主动买卖。','Weights reflect the disclosure date. Changes in weights alone do not establish that the fund bought or sold a holding.','比率は開示時点のものです。比率の変化だけでファンドの売買を判断することはできません。'],
    ['基金介绍来源','Fund profile source','ファンド概要の情報元'],['基金介绍','Fund profile','ファンド概要'],['管理机构待补充','Manager unavailable','運用会社の情報なし'],['分类待补充','Category unavailable','分類情報なし'],
    ['查看基金策略说明（英文原文）','Read the fund strategy (English source text)','運用方針を読む（英語原文）'],['策略说明暂缺。','Strategy description unavailable.','運用方針の説明は未取得です。'],['资料获取','Profile retrieved','概要の取得日'],
    ['最多展示10项','Up to 10 holdings','最大10件'],['主要持仓','Major holdings','主な保有銘柄'],['获取已超过7天','Retrieved over 7 days ago','取得から7日以上経過'],['获取日期','Retrieved','取得日'],['持仓来源','Holdings source','保有銘柄の情報元'],['ARK 官方','ARK official','ARK公式'],
    ['权重以整个基金为分母，未将前十大重新归一化。','Weights are percentages of the entire fund; the top holdings have not been rescaled to 100%.','比率の分母はファンド全体です。表示銘柄の合計を100%に換算していません。'],
    ['当前来源未提供可用持仓明细，不代表基金没有持仓。','This source provides no usable holdings data. This does not mean the fund has no holdings.','情報元から利用可能な保有明細を取得できません。保有資産がないという意味ではありません。'],
    ['交易前补充检查','Before trading','取引前の確認'],['20日平均成交额','20-day avg. dollar volume','20日平均売買代金'],['20日年化波动率','20-day annualized volatility','20日年率換算ボラティリティ'],
    ['成交额不等于买卖价差。实时价差、折溢价和其他持仓重叠尚未接入；模型失效位不保证成交价格。动量评分是样本内排序，不是胜率。','Dollar volume is not the bid–ask spread. Live spreads, premiums/discounts and portfolio overlap are not connected. The invalidation level is not a guaranteed execution price. The momentum score ranks this universe; it is not a win probability.','売買代金と売買スプレッドは異なります。リアルタイムのスプレッド、乖離率、保有銘柄の重複は未対応です。無効化水準での約定は保証されません。モメンタムスコアは対象銘柄内の順位であり、勝率ではありません。'],
    ['主动管理的创新主题股票ETF，关注颠覆性技术相关公司。持仓可跨行业及国家，组合集中，收益对成长股估值与经理选股较敏感。','An actively managed innovation equity ETF focused on disruptive technology companies. Holdings span industries and countries. Its concentrated portfolio is sensitive to growth-stock valuations and the manager’s stock selection.','破壊的技術に関連する企業に投資する、アクティブ運用のイノベーション株式ETFです。業種・国をまたぐ集中型ポートフォリオで、成長株の評価や運用者の銘柄選択の影響を受けやすい特徴があります。'],
    ['未提供','Not provided','未提供'],['名称待补充','Name unavailable','名称未取得'],
    ['20日收益','20-day return','20日リターン'],['60日收益','60-day return','60日リターン'],['120日收益','120-day return','120日リターン'],
    ['20日','20D','20日'],['60日','60D','60日'],['120日','120D','120日']
  ];
  const names = [
    ['标普500 ETF','S&P 500 ETF','S&P 500 ETF'],['纳斯达克100 ETF','Nasdaq-100 ETF','NASDAQ 100 ETF'],['道琼斯工业平均 ETF','Dow Jones Industrial Average ETF','ダウ工業株30種 ETF'],['罗素2000 ETF','Russell 2000 ETF','ラッセル2000 ETF'],['标普中型股400 ETF','S&P MidCap 400 ETF','S&P中型株400 ETF'],['标普500等权 ETF','S&P 500 Equal Weight ETF','S&P 500 均等加重 ETF'],['美国全市场 ETF','Total US Stock Market ETF','米国株式市場全体 ETF'],
    ['科技精选行业 ETF','Technology Select Sector ETF','テクノロジー・セクター ETF'],['通信服务精选行业 ETF','Communication Services Select Sector ETF','通信サービス・セクター ETF'],['可选消费精选行业 ETF','Consumer Discretionary Select Sector ETF','一般消費財・セクター ETF'],['工业精选行业 ETF','Industrial Select Sector ETF','資本財・セクター ETF'],['金融精选行业 ETF','Financial Select Sector ETF','金融セクター ETF'],['能源精选行业 ETF','Energy Select Sector ETF','エネルギー・セクター ETF'],['材料精选行业 ETF','Materials Select Sector ETF','素材セクター ETF'],['必需消费精选行业 ETF','Consumer Staples Select Sector ETF','生活必需品セクター ETF'],['医疗保健精选行业 ETF','Health Care Select Sector ETF','ヘルスケア・セクター ETF'],['房地产精选行业 ETF','Real Estate Select Sector ETF','不動産セクター ETF'],['公用事业精选行业 ETF','Utilities Select Sector ETF','公益事業セクター ETF'],
    ['VanEck 半导体 ETF','VanEck Semiconductor ETF','VanEck 半導体 ETF'],['iShares 半导体 ETF','iShares Semiconductor ETF','iShares 半導体 ETF'],['北美科技软件 ETF','North American Tech-Software ETF','北米テクノロジー・ソフトウェア ETF'],['First Trust 网络安全 ETF','First Trust Cybersecurity ETF','First Trust サイバーセキュリティ ETF'],['First Trust 云计算 ETF','First Trust Cloud Computing ETF','First Trust クラウドコンピューティング ETF'],['全球机器人与人工智能 ETF','Global Robotics & AI ETF','世界ロボティクス・AI ETF'],['全球机器人与自动化 ETF','Global Robotics & Automation ETF','世界ロボティクス・自動化 ETF'],['ARK 创新 ETF','ARK Innovation ETF','ARK イノベーション ETF'],['iShares 生物科技 ETF','iShares Biotechnology ETF','iShares バイオテクノロジー ETF'],['标普生物科技 ETF','S&P Biotech ETF','S&P バイオテクノロジー ETF'],['标普区域银行 ETF','S&P Regional Banking ETF','S&P 地方銀行 ETF'],['标普银行 ETF','S&P Bank ETF','S&P 銀行 ETF'],['美国航空航天与国防 ETF','US Aerospace & Defense ETF','米国航空宇宙・防衛 ETF'],['Invesco 航空航天与国防 ETF','Invesco Aerospace & Defense ETF','Invesco 航空宇宙・防衛 ETF'],['标普零售 ETF','S&P Retail ETF','S&P 小売 ETF'],['美国运输业 ETF','US Transportation ETF','米国運輸 ETF'],['全球航空业 ETF','Global Airlines ETF','世界航空会社 ETF'],
    ['SPDR 黄金信托','SPDR Gold Trust','SPDR ゴールド・トラスト'],['iShares 白银信托','iShares Silver Trust','iShares シルバー・トラスト'],['VanEck 黄金矿业 ETF','VanEck Gold Miners ETF','VanEck 金鉱株 ETF'],['VanEck 小型黄金矿业 ETF','VanEck Junior Gold Miners ETF','VanEck 中小型金鉱株 ETF'],['全球铜矿 ETF','Global Copper Miners ETF','世界銅鉱株 ETF'],['全球铀产业 ETF','Global Uranium ETF','世界ウラン関連 ETF'],['Invesco 太阳能 ETF','Invesco Solar ETF','Invesco 太陽光エネルギー ETF'],['全球清洁能源 ETF','Global Clean Energy ETF','世界クリーンエネルギー ETF'],['Invesco 综合商品基金','Invesco Broad Commodity Fund','Invesco 総合商品ファンド'],['Invesco 农产品基金','Invesco Agriculture Fund','Invesco 農産物ファンド'],['美国石油基金','United States Oil Fund','米国石油ファンド'],['美国天然气基金','United States Natural Gas Fund','米国天然ガスファンド'],
    ['美国股票动量因子 ETF','US Equity Momentum Factor ETF','米国株モメンタム・ファクター ETF'],['美国股票质量因子 ETF','US Equity Quality Factor ETF','米国株クオリティ・ファクター ETF'],['美国股票低波动 ETF','US Minimum Volatility ETF','米国株低ボラティリティ ETF'],['美国股票价值因子 ETF','US Equity Value Factor ETF','米国株バリュー・ファクター ETF'],['Vanguard 成长股 ETF','Vanguard Growth ETF','Vanguard グロース ETF'],['Vanguard 价值股 ETF','Vanguard Value ETF','Vanguard バリュー ETF'],['罗素1000成长股 ETF','Russell 1000 Growth ETF','ラッセル1000 グロース ETF'],['罗素1000价值股 ETF','Russell 1000 Value ETF','ラッセル1000 バリュー ETF'],
    ['20年以上美国国债 ETF','20+ Year US Treasury ETF','米国長期国債20年超 ETF'],['7–10年美国国债 ETF','7–10 Year US Treasury ETF','米国国債7–10年 ETF'],['1–3年美国国债 ETF','1–3 Year US Treasury ETF','米国国債1–3年 ETF'],['美元高收益公司债 ETF','USD High Yield Corporate Bond ETF','米ドル建てハイイールド社債 ETF'],['美元投资级公司债 ETF','USD Investment Grade Corporate Bond ETF','米ドル建て投資適格社債 ETF'],['美国通胀保值国债 ETF','US Inflation-Protected Treasury ETF','米国物価連動国債 ETF'],
    ['发达市场（美加除外）ETF','Developed Markets ex-US/Canada ETF','先進国（米国・カナダ除く）ETF'],['新兴市场 ETF','Emerging Markets ETF','新興国市場 ETF'],['日本股票 ETF','Japan Equity ETF','日本株 ETF'],['韩国股票 ETF','South Korea Equity ETF','韓国株 ETF'],['台湾股票 ETF','Taiwan Equity ETF','台湾株 ETF'],['印度股票 ETF','India Equity ETF','インド株 ETF'],['中国股票 ETF','China Equity ETF','中国株 ETF'],['中国大型股 ETF','China Large-Cap ETF','中国大型株 ETF'],['欧洲股票 ETF','Europe Equity ETF','欧州株 ETF'],['巴西股票 ETF','Brazil Equity ETF','ブラジル株 ETF']
  ];
  const dictionary = new Map([...entries, ...names].map(([zh,en,ja]) => [zh,{en,zh,ja}]));
  const pattern = new RegExp([...dictionary.keys()].sort((a,b)=>b.length-a.length).map(x=>x.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('|'),'g');
  let language='en';
  try { const saved=localStorage.getItem('orbit-language'); if(['en','zh','ja'].includes(saved))language=saved; } catch {}
  const records=new WeakMap();
  function translate(text, lang=language) {
    if(lang==='zh')return text;
    return text.replace(pattern,key=>dictionary.get(key)[lang]).replace(/显示 (\d+) \/ (\d+) 只/g,(_,a,b)=>lang==='en'?`Showing ${a} / ${b} ETFs`:`${b}本中${a}本を表示`)
      .replace(/已展示 (\d+) 项合计权重/g,(_,n)=>lang==='en'?`Combined weight of ${n} shown holdings`:`表示中の${n}銘柄の合計比率`)
      .replace(/(\d+)日/g,(_,n)=>lang==='en'?`${n}D`:`${n}日`)
      .replace(/。/g,lang==='en'?'.':'。');
  }
  // Translate complete phrases before substituting numeric day labels.
  function localized(text,lang=language) {
    if(lang==='zh')return text;
    return translate(text,lang);
  }
  function update(node,key,get,set) {
    let slots=records.get(node);if(!slots){slots={};records.set(node,slots);}
    const value=get(), prior=slots[key];
    const source=prior&&value===prior.output?prior.source:value;
    const output=localized(source);slots[key]={source,output};if(output!==value)set(output);
  }
  function walk(root) {
    if(root.nodeType===Node.TEXT_NODE){
      if(root.parentElement?.closest('script,style,[data-language-control],[data-source-text]'))return;
      update(root,'text',()=>root.nodeValue,v=>root.nodeValue=v);return;
    }
    if(root.nodeType!==Node.ELEMENT_NODE)return;
    if(root.matches('script,style,[data-language-control],[data-source-text]'))return;
    for(const attr of ['placeholder','aria-label','title'])if(root.hasAttribute(attr))update(root,attr,()=>root.getAttribute(attr),v=>root.setAttribute(attr,v));
    for(const child of root.childNodes)walk(child);
  }
  const observer=new MutationObserver(changes=>{
    observer.disconnect();
    for(const change of changes){if(change.type==='childList')change.addedNodes.forEach(walk);else walk(change.target);}
    observe();
  });
  function observe(){observer.observe(document.body,{childList:true,subtree:true,characterData:true});}
  function setLanguage(lang){
    if(!['en','zh','ja'].includes(lang))return;
    language=lang;try{localStorage.setItem('orbit-language',lang);}catch{}
    document.documentElement.lang=lang==='zh'?'zh-CN':lang;
    observer.disconnect();walk(document.body);observe();
    document.querySelectorAll('[data-lang]').forEach(b=>{b.setAttribute('aria-pressed',String(b.dataset.lang===lang));});
  }
  window.orbitI18n={setLanguage,localized,searchNames:source=>[source,...['en','ja'].map(l=>localized(source,l))].join(' ')};
  document.querySelectorAll('[data-lang]').forEach(b=>b.addEventListener('click',()=>setLanguage(b.dataset.lang)));
  setLanguage(language);
})();
