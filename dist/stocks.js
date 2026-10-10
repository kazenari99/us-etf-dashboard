/* ORBIT presentation of VCPScanner's public candidate snapshot. */
(() => {
  const $ = id => document.getElementById(id);
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const tradingView = ticker => `https://www.tradingview.com/chart/?symbol=${encodeURIComponent(ticker)}&interval=1D`;
  const number = x => typeof x === 'number' && Number.isFinite(x);
  const fmt = (x, digits=2) => number(x) ? x.toFixed(digits) : '—';
  const pct = x => number(x) ? `${x>=0?'+':''}${x.toFixed(1)}%` : '—';
  let rows=[], filtered=[], sort='rs_rating', direction=-1, lens='rs', payload;
  let starred;
  try { starred=new Set(JSON.parse(localStorage.getItem('orbit-stock-watchlist')||'[]')); } catch { starred=new Set(); }
  function view() {
    const stocks=location.hash==='#stocks';
    $('etfView').hidden=stocks; $('stocksView').hidden=!stocks;
    $('asOf').parentElement.hidden=stocks;
    document.querySelectorAll('[data-view]').forEach(b=>{const active=(b.dataset.view==='stocks')===stocks;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
    if(!stocks)window.dispatchEvent(new Event('resize'));
  }
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{location.hash=b.dataset.view==='stocks'?'stocks':'etf';view();}));
  addEventListener('hashchange',view);view();
  function render() {
    const query=$('stockSearch').value.trim().toLowerCase(), rs=Number($('stockRS').value), high=Number($('stockHigh').value), vol=Number($('stockVol').value);
    filtered=rows.filter(s=>(`${s.ticker} ${s.name}`.toLowerCase().includes(query)) && number(s.rs_rating) && s.rs_rating>=rs && number(s.below_52w_high_pct) && s.below_52w_high_pct<=high && (vol===0 || number(s.volume_ratio)&&s.volume_ratio>=vol) && (lens!=='rs'||s.rs_rating>=90) && (lens!=='high'||s.below_52w_high_pct<=5) && (lens!=='volume'||number(s.volume_ratio)&&s.volume_ratio>=1.5) && (lens!=='watch'||starred.has(s.ticker)));
    filtered.sort((a,b)=>{if(sort==='ticker'||sort==='sector'){if(!a[sort])return b[sort]?1:0;if(!b[sort])return -1;return direction*a[sort].localeCompare(b[sort]);}if(!number(a[sort]))return number(b[sort])?1:0;if(!number(b[sort]))return -1;return direction*(a[sort]-b[sort]);});
    $('stockCount').textContent=`候选数量 ${filtered.length} / ${rows.length}`;
    $('stockExport').disabled=!filtered.length;
    $('stockRows').innerHTML=filtered.map(s=>`<tr data-ticker="${esc(s.ticker)}" title="TradingView 日线图 ↗"><td><button class="stock-star ${starred.has(s.ticker)?'selected':''}" data-star="${esc(s.ticker)}" aria-label="${esc(s.ticker)} ★" aria-pressed="${starred.has(s.ticker)}">★</button></td><td><a class="stock-ticker" href="${tradingView(s.ticker)}" target="_blank" rel="noopener noreferrer" aria-label="${esc(s.ticker)} TradingView">${esc(s.ticker)}</a><small data-source-text>${esc(s.name)}</small></td><td>$${fmt(s.price)}</td><td class="stock-sector" data-source-text>${esc(s.sector||'—')}</td><td class="${s.change_pct>=0?'stock-up':'stock-down'}">${pct(s.change_pct)}</td><td class="stock-rs">${fmt(s.rs_rating,0)}</td><td class="stock-up">${pct(number(s.price_to_sma50)?(s.price_to_sma50-1)*100:null)}</td><td class="stock-up">${pct(number(s.price_to_sma200)?(s.price_to_sma200-1)*100:null)}</td><td><span class="stock-meter"><i style="width:${number(s.below_52w_high_pct)?Math.max(0,Math.min(100,100-s.below_52w_high_pct*4)):0}%"></i></span>${fmt(s.below_52w_high_pct,1)}%</td><td>${fmt(s.volume_ratio)}×</td><td><a class="stock-link" href="${tradingView(s.ticker)}" target="_blank" rel="noopener noreferrer">图表 ↗</a></td></tr>`).join('') || '<tr><td colspan="11">没有符合条件的股票</td></tr>';
    document.querySelectorAll('#stockLenses button').forEach(b=>{b.classList.toggle('active',b.dataset.lens===lens);b.setAttribute('aria-pressed',String(b.dataset.lens===lens));});
    document.querySelectorAll('#stockTable th button').forEach(b=>b.parentElement.setAttribute('aria-sort',b.dataset.key===sort?(direction===1?'ascending':'descending'):'none'));
  }
  ['stockRS','stockHigh','stockVol'].forEach(id=>$(id).addEventListener('change',render));
  $('stockSearch').addEventListener('input',render);
  $('stockLenses').addEventListener('click',e=>{const b=e.target.closest('[data-lens]');if(!b)return;lens=b.dataset.lens;if(lens==='all'){$('stockRS').value='70';$('stockHigh').value='25';$('stockVol').value='0';}if(lens==='rs')$('stockRS').value='90';render();});
  $('stockTable').addEventListener('click',e=>{
    if(e.target.closest('a'))return;
    const b=e.target.closest('button');
    if(!b){const row=e.target.closest('tr[data-ticker]');if(row && !window.getSelection()?.toString())window.open(tradingView(row.dataset.ticker),'_blank','noopener,noreferrer');return;}
    if(b.dataset.key){direction=sort===b.dataset.key?-direction:(['ticker','sector'].includes(b.dataset.key)?1:-1);sort=b.dataset.key;render();}
    if(b.dataset.star){const t=b.dataset.star;starred.has(t)?starred.delete(t):starred.add(t);try{localStorage.setItem('orbit-stock-watchlist',JSON.stringify([...starred]));}catch{}render();}
  });
  $('stockExport').addEventListener('click',()=>{
    const keys=['ticker','name','price','sector','change_pct','rs_rating','price_to_sma50','price_to_sma200','below_52w_high_pct','volume_ratio'];
    const quote=x=>`"${(typeof x==='number'?String(x):String(x??'').replace(/^[=+@\-]/,"'$&")).replace(/"/g,'""')}"`;
    const csv=['session_date,'+keys.join(','),...filtered.map(s=>[payload.session_date,...keys.map(k=>s[k])].map(quote).join(','))].join('\r\n');
    const url=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=`orbit-stocks-${payload.session_date}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  (async()=>{try{
    const response=await fetch('./stocks.json',{cache:'no-store'});if(!response.ok)throw new Error('HTTP '+response.status);payload=await response.json();
    if(!Array.isArray(payload.stocks)||payload.count!==payload.stocks.length)throw new Error('未通过数据完整性检查');
    const sectors=await fetch('./stock_sectors.json',{cache:'no-store'}).then(r=>r.ok?r.json():{}).catch(()=>({}));
    rows=payload.stocks.map(s=>({...s,sector:sectors[s.ticker]?.sector||null}));
    const pending=payload.session_date<payload.expected_session, failed=payload.fetch_status!=='ok';
    const retrieved=payload.fetched_at?new Date(payload.fetched_at).toLocaleString('zh-CN',{timeZone:'Asia/Tokyo',hour12:false}):'—';
    $('stockStatus').textContent=`数据交易日 ${payload.session_date||'—'} · 抓取时间 ${retrieved} 东京时间 · ${failed?'源站抓取失败，保留上次快照':pending?'源站尚未更新至ETF交易日':'源站快照已同步'}${pending?' '+payload.expected_session:''}`;
    $('stockStatus').classList.toggle('stale',pending||failed);render();
  }catch(e){$('stockStatus').textContent='暂无数据 · '+e.message;$('stockStatus').classList.add('stale');render();}})();
})();
