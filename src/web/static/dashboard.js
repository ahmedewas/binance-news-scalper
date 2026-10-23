'use strict';
const $ = id => document.getElementById(id);
const esc = v => String(v ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = (v, d = 2) => v !== null && v !== undefined && Number.isFinite(Number(v)) ? Number(v).toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d}) : '—';
const money = v => `$${num(v)}`;
const array = v => Array.isArray(v) ? v : [];
const pendingCount = d => d?.pending_orders && typeof d.pending_orders === 'object' ? Object.keys(d.pending_orders).length : 0;
const stalePrices = d => Array.isArray(d?.health?.price_stale) ? d.health.price_stale.length > 0 : Boolean(d?.health?.price_stale);
let state = null, lastSuccess = 0, busy = false, statusFlight = null, journalFlight = null, timer, journal = '', journalAt = 0, seen = null, audioCtx, token = '', soundOn = false;
try { token = sessionStorage.getItem('dashboardToken') || ''; soundOn = localStorage.getItem('dashboardSound') === 'true'; } catch (_) {}
$('token').value = token;
function notify(m) { $('alert').textContent = m; $('alert').hidden = !m; }
async function api(path, body) {
    const c = new AbortController(), t = setTimeout(() => c.abort(), 12000), h = {Accept:'application/json'};
    if (token) h['X-Dashboard-Token'] = token;
    if (body !== undefined) { h['Content-Type'] = 'application/json'; h['X-Requested-With'] = 'ScalperDashboard'; }
    try {
        const res = await fetch(path, {method:body === undefined ? 'GET':'POST', headers:h, body:body === undefined ? undefined:JSON.stringify(body),signal:c.signal,cache:'no-store'});
        const data = await res.json();
        if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `فشل الطلب (${res.status})`);
        return data;
    } finally { clearTimeout(t); }
}
function table(headers, rows, empty) { return rows.length ? `<table class="table"><thead><tr>${headers.map(h=>`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table>` : `<p class="empty">${esc(empty)}</p>`; }
function details(id, pairs) { $(id).innerHTML = pairs.map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join(''); }
function renderPositions(pos) {
    $('position-count').textContent = `${pos.length} صفقات`;
    $('pos-box').innerHTML = pos.length ? pos.map((p,i)=>`<article class="position"><div class="section-head"><strong dir="ltr">${esc(p.symbol)}</strong><strong class="${Number(p.pnl_usd)>=0?'positive':'negative'}" dir="ltr">${esc(money(p.pnl_usd))} (${esc(num(p.pnl_pct))}%)</strong><button class="danger close-position" data-index="${i}" data-mutation>إغلاق الصفقة</button></div><div class="position-details">${[['سعر الدخول',num(p.entry_price,8)],['السعر الحالي',num(p.current_price,8)],['رأس المال',money(p.cost_basis)],['الهدف',num(p.target_tp,8)],['الوقف الحالي',num(p.stop_loss,8)],['تأمين التعادل',p.is_breakeven_locked?'مفعّل':'غير مفعّل'],['المدة بالدقائق',num(p.elapsed_mins,1)],['المتبقي بالدقائق',num(p.remaining_mins,1)]].map(([k,v])=>`<div><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('')}</div></article>`).join('') : '<p class="empty">لا توجد صفقات مفتوحة حالياً</p>';
}
function renderRadar() {
    const q = $('radar-search').value.trim().toUpperCase(), f = $('radar-filter').value, s = $('radar-sort').value;
    const rows = array(state?.market_radar).filter(r=>String(r.symbol).toUpperCase().replace('/','').includes(q.replace('/','')) && (f==='all'||Boolean(r.approved)===(f==='approved'))).slice().sort((a,b)=>s==='symbol'?String(a.symbol).localeCompare(String(b.symbol)):Number(b[s]||0)-Number(a[s]||0));
    $('radar-count').textContent = `${rows.length} / ${array(state?.market_radar).length}`;
    $('radar-box').innerHTML = table(['العملة','المنظومة','السعر','المرحلة','التقييم','الحالة / السبب'],rows.map(r=>[r.symbol,r.pillar||'—',num(r.price,8),r.phase,`${num(r.score,0)}/100`,r.reason||r.status||(r.approved?'مؤهلة':'غير مؤهلة')]),'لا توجد عملات مطابقة');
}
function render(d) {
    const p = d.performance || {}, pos = array(d.open_positions), hist = array(d.trade_history), h = d.health || {};
    $('mode-badge').textContent = d.mode === 'PAPER' ? 'PAPER · محاكاة' : (d.mode || 'الوضع غير معروف');
    $('status-badge').textContent = d.is_active ? 'الدخول نشط':'الدخول متوقف';
    $('bal').textContent = money(d.usdt_balance); $('equity').textContent = money(d.equity);
    $('pnl').textContent = `${money(p.total_pnl_usd)} (${num(p.total_pnl_pct)}%)`;
    $('pnl').className = Number(p.total_pnl_usd)>=0?'positive':'negative';
    $('win-rate').textContent = `نجاح ${num(p.win_rate)}% · ${p.wins||0} رابحة / ${p.losses||0} خاسرة`;
    $('session-time').textContent = p.elapsed_hours_str || '—';
    $('slots').textContent = `الخانات ${pos.length}/${d.allocation?.total_slots ?? '—'} · ${money(d.allocation?.slot_size)} للخانة`;
    $('pending').textContent = `أوامر قيد المعالجة: ${pendingCount(d)}`;
    renderPositions(pos); renderRadar();
    details('health-box',[['آخر دورة',h.last_step],['آخر فحص',h.last_scan],['الأخطاء',array(h.errors).length],['آخر خطأ',h.last_error||'لا يوجد'],['الأسعار',stalePrices(d)?'قديمة — يلزم الانتباه':'محدثة'],['حد خسارة الجلسة',d.mode==='PAPER'?'معطّل في المحاكاة':h.loss_limit_hit?'تم بلوغه — محظور':'لم يُبلغ']]);
    const names = {take_profit_pct:'هدف الربح %',stop_loss_pct:'وقف الخسارة %',max_hold_minutes:'مدة الاحتفاظ القصوى',min_score:'أقل تقييم',max_positions:'أقصى صفقات',max_slots:'أقصى عدد مراكز',trailing_tp_pct:'تتبع الربح',timeout_minutes:'مهلة المركز بالدقائق',max_session_loss_pct:'حد خسارة الجلسة',enable_flow_entries:'دخول التدفق التجريبي',enable_volume_decay_exit:'خروج الحجم التجريبي',max_entries_per_hour:'أقصى دخولات/ساعة',symbol_cooldown_minutes:'فاصل إعادة الدخول/د'};
    details('settings-box',Object.entries(d.settings||{}).filter(([k])=>!/token|secret|password|key/i.test(k)).map(([k,v])=>[names[k]||k,typeof v==='boolean'?(v?'مفعّل':'معطّل'):k.endsWith('_pct')?`${num(Number(v)*100)}%`:typeof v==='object'?JSON.stringify(v):v]));
    $('hist-box').innerHTML = table(['العملة','الدخول','الخروج','الربح USDT','الربح %','المدة / د','الوقت','سبب الخروج'],hist.slice().reverse().map(t=>[t.symbol,num(t.entry_price,8),num(t.exit_price,8),num(t.pnl_usd),num(t.pnl_pct),num(t.duration_mins,1),t.timestamp,t.reason_arabic||t.reason]),'لا توجد صفقات مغلقة بعد');
    $('hourly-box').innerHTML = table(['الساعة','الوقت','الصفقات','ربح الساعة','الرصيد'],array(p.hourly_snapshots).map(hs=>[hs.hour,hs.timestamp,hs.total_trades,money(hs.hour_pnl_usd),money(hs.balance)]),'يظهر التقرير بعد اكتمال الساعة الأولى');
    $('news-box').innerHTML = array(d.latest_news).length ? d.latest_news.map(n=>`<article class="news"><div class="section-head"><strong>${esc(n.symbol)}</strong><span class="badge">${esc(n.score)}/100 · ${n.approved?'مؤهل':'غير مؤهل'}</span></div><h3>${esc(n.title)}</h3><p>${esc(n.phase)} · ${esc(n.published_at)}</p><p>${esc(n.reason||'لا يوجد تفسير متاح')}</p></article>`).join('') : '<p class="empty">لا توجد أخبار في هذه الجلسة بعد</p>';
    const keys = new Set([...pos.map(t=>`open:${t.symbol}:${t.entry_price}:${t.opened_at||t.entry_time||''}`),...hist.map(t=>`closed:${t.symbol}:${t.timestamp}:${t.exit_price}`)]);
    if (seen && [...keys].some(k=>!seen.has(k)) && typeof chime === 'function') chime();
    if (!seen) seen = new Set(); keys.forEach(k=>seen.add(k));
    if (typeof controls === 'function') controls();
}
function refresh() {
    if (statusFlight) return statusFlight;
    clearTimeout(timer); $('refresh-btn').disabled = true;
    statusFlight = (async()=>{
        const start = performance.now();
        try { const d = await api('/api/status'); state = d; lastSuccess = Date.now(); render(d); $('connection-state').textContent = stalePrices(d)?'متصل · أسعار قديمة':'متصل'; $('connection-state').className=stalePrices(d)?'stale':'positive'; $('updated-at').textContent = `آخر تحديث: ${new Date().toLocaleTimeString('ar-EG')}`; $('lat-badge').textContent = `${Math.round(performance.now()-start)} ms`; }
        catch(e) { $('connection-state').textContent='فشل الاتصال · البيانات قديمة'; $('connection-state').className='negative'; $('updated-at').textContent=e.message; lastSuccess = 0; if (typeof controls === 'function') controls(); }
        finally { statusFlight=null; $('refresh-btn').disabled=false; timer=setTimeout(refresh,3000); }
    })();
    return statusFlight;
}
async function fetchJournal() {
    if (journalFlight) return journalFlight;
    $('journal-refresh').disabled = true;
    journalFlight = (async()=>{try { const d=await api('/api/journal'); journal=String(d.journal||'لا توجد سجلات بعد.'); journalAt=Date.now(); $('journal-box').textContent=journal; $('journal-state').textContent=`تم التحديث ${new Date().toLocaleTimeString('ar-EG')}`; return true; } catch(e){$('journal-state').textContent=`تعذر تحديث السجل: ${e.message}`; return false;} finally{journalFlight=null;$('journal-refresh').disabled=false;}})(); return journalFlight;
}
