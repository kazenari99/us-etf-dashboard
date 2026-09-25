/* Fund disclosure dates are independent of market-data dates. */
let fundProfiles = {}, profilesLoaded = false;
const fundEscape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fundDate = value => value ? String(value).slice(0,10) : '未提供';
function fundLink(url,label){
  try { const u=new URL(url); if(u.protocol!=='https:')return ''; return `<a href="${fundEscape(u.href)}" target="_blank" rel="noopener noreferrer">${fundEscape(label)} ↗</a>`; } catch {return '';}
}
function renderFundContext(x){
  const f=fundProfiles[x.ticker];
  if(!f)return `<section class="fund-section" id="fundContext"><h3>基金介绍与持仓</h3><p class="fund-note">${profilesLoaded?'暂无可核验资料。':'正在读取基金资料…'}</p></section>`;
  const rows=f.holdings||[], total=rows.reduce((s,r)=>s+r.weight,0);
  const stale=f.holdings_retrieved_at && Date.now()-Date.parse(f.holdings_retrieved_at)>7*86400000;
  const status=f.holdings_status==='retained'?'本次获取未成功，保留此前资料':f.holdings_asof?`来源标注日期 ${fundEscape(f.holdings_asof)}`:'来源未披露持仓日期，无法确认是否为最新持仓';
  const special=['GLD','SLV','USO','UNG','DBC','DBA'].includes(x.ticker)?'此类产品可能通过实物、期货或抵押资产提供敞口，不能把股票持仓表视为完整风险敞口。':x.group==='Bond'?'债券ETF的主要风险还包括久期和信用质量，前十大证券不足以代表完整组合。':'持仓权重反映披露时点，不能从权重变化直接推断基金主动买卖。';
  return `<section class="fund-section" id="fundContext">
    <div class="fund-heading"><h3>基金介绍</h3><span class="fund-tag">${fundEscape(f.family||'管理机构待补充')}</span></div>
    ${f.summary_zh?`<p>${fundEscape(f.summary_zh)}</p>`:`<p>${fundEscape(etfName(x.ticker))} · ${fundEscape(f.category||groupNames[x.group]||'分类待补充')}</p>`}
    ${f.description?`<details class="fund-description"><summary>查看基金策略说明（英文原文）</summary><p>${fundEscape(f.description)}</p></details>`:'<p class="fund-note">策略说明暂缺。</p>'}
    <p class="fund-note">资料获取 ${fundDate(f.profile_retrieved_at)} · ${fundLink(f.summary_source||f.profile_source,'基金介绍来源')}</p>
    <h3>主要持仓 <small>最多展示10项</small></h3>
    <p class="fund-note ${stale||f.holdings_status==='retained'?'fund-warning':''}">${status}${stale?' · 获取已超过7天':''}<br>获取日期 ${fundDate(f.holdings_retrieved_at)} · ${fundLink(f.holdings_source,f.holdings_provider||'持仓来源')}</p>
    ${rows.length?`<div class="fund-concentration"><span>已展示 ${rows.length} 项合计权重</span><strong>${(total*100).toFixed(1)}%</strong></div><p class="fund-note">权重以整个基金为分母，未将前十大重新归一化。</p><ol class="fund-holdings">${rows.map(r=>`<li><div><b>${fundEscape(r.symbol)}</b><span>${fundEscape(r.name)}</span></div><strong>${(r.weight*100).toFixed(2)}%</strong><div class="holding-track"><i style="width:${Math.min(100,r.weight*100)}%"></i></div></li>`).join('')}</ol>`:'<p class="fund-empty">当前来源未提供可用持仓明细，不代表基金没有持仓。</p>'}
    <p class="fund-note">${special}</p>
    <h3>交易前补充检查</h3><div class="fund-risk"><div><span>20日平均成交额</span><b>$${(x.adtv20/1e6).toFixed(1)}M</b></div><div><span>20日年化波动率</span><b>${(x.vol20_ann*100).toFixed(1)}%</b></div></div>
    <p class="fund-note">成交额不等于买卖价差。实时价差、折溢价和其他持仓重叠尚未接入；模型失效位不保证成交价格。动量评分是样本内排序，不是胜率。</p>
  </section>`;
}
fetch('./fund_profiles.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('unavailable');return r.json();}).then(p=>{fundProfiles=p.funds||{};}).catch(()=>{}).finally(()=>{
  profilesLoaded=true;
  const host=document.getElementById('fundContext');
  if(host&&typeof state!=='undefined'&&state.selected)host.outerHTML=renderFundContext(state.selected);
});
