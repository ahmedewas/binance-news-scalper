'use strict';
const $ = id => document.getElementById(id);
const esc = v => String(v ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = (v, maxD = 2, minD = 0) => v !== null && v !== undefined && Number.isFinite(Number(v)) ? Number(v).toLocaleString('en-US',{maximumFractionDigits:maxD,minimumFractionDigits:minD}) : '—';
const money = (v, d = 2) => `$${num(v, d, d)}`;
const pnlMoney = (v, d = 4) => {
    if (v === null || v === undefined || !Number.isFinite(Number(v))) return '—';
    const n = Number(v);
    const sign = n > 0 ? '+' : n < 0 ? '-' : '';
    return `${sign}$${Math.abs(n).toFixed(d)}`;
};
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
    $('pos-box').innerHTML = pos.length ? pos.map((p,i)=>`<article class="position"><div class="section-head"><strong dir="ltr">${esc(p.symbol)}</strong><strong class="${Number(p.pnl_usd)>=0?'positive':'negative'}" dir="ltr">${esc(pnlMoney(p.pnl_usd,4))} (${esc(num(p.pnl_pct,2,2))}%)</strong><button class="danger close-position" data-index="${i}" data-mutation>إغلاق الصفقة</button></div><div class="position-details">${[['سعر الدخول',num(p.entry_price,6)],['السعر الحالي',num(p.current_price,6)],['رأس المال',money(p.cost_basis)],['أعلى قمة',`${p.peak_pct>0?'+':''}${num(p.peak_pct,2,2)}%`],['الهدف (TP)',`${num(p.target_tp,6)} (${num(p.dist_to_tp,2,2)}% متبقي)`],['الوقف (SL)',`${num(p.stop_loss,6)} (${num(p.dist_to_sl,2,2)}% أمان)`],['تأمين التعادل',p.is_breakeven_locked?'🛡️ مفعّل ومحمي (+0.35%)':'⏳ قيد المراقبة'],['المنقضي',`${num(p.elapsed_mins,1)}د`],['المتبقي',`${num(p.remaining_mins,1)}د`]].map(([k,v])=>`<div><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('')}</div></article>`).join('') : '<p class="empty">لا توجد صفقات مفتوحة حالياً</p>';
}
function renderRadar() {
    const q = $('radar-search').value.trim().toUpperCase(), f = $('radar-filter').value, s = $('radar-sort').value;
    const rows = array(state?.market_radar).filter(r=>String(r.symbol).toUpperCase().replace('/','').includes(q.replace('/','')) && (f==='all'||Boolean(r.approved)===(f==='approved'))).slice().sort((a,b)=>s==='symbol'?String(a.symbol).localeCompare(String(b.symbol)):Number(b[s]||0)-Number(a[s]||0));
    $('radar-count').textContent = `${rows.length} / ${array(state?.market_radar).length}`;
    $('radar-box').innerHTML = table(['العملة','المنظومة','السعر','المرحلة','التقييم','الحالة / السبب'],rows.map(r=>[r.symbol,r.pillar||'—',num(r.price,6),r.phase,`${num(r.score,0)}/100`,r.reason||r.status||(r.approved?'مؤهلة':'غير مؤهلة')]),'لا توجد عملات مطابقة');
}
function render(d) {
    const p = d.performance || {}, pos = array(d.open_positions), hist = array(d.trade_history), h = d.health || {}, ai = d.adaptive_ai || {};
    $('mode-badge').textContent = d.mode === 'PAPER' ? 'PAPER · محاكاة' : (d.mode || 'الوضع غير معروف');
    $('status-badge').textContent = d.is_active ? 'الدخول نشط':'الدخول متوقف';
    const allocatedCost = pos.reduce((acc, x) => acc + (Number(x.cost_basis) || 0), 0);
    $('bal').textContent = money(d.usdt_balance);
    $('bal-sub').textContent = pos.length ? `المحجوز: ${money(allocatedCost)} (${pos.length} صفقات)` : 'كامل السيولة متاحة للدخول';
    $('equity').textContent = money(d.equity);
    $('equity-sub').textContent = `رأس المال المبدئي: ${money(p.initial_balance || 500)} (عائد: ${p.total_pnl_pct >= 0 ? '+' : ''}${num(p.total_pnl_pct)}%)`;
    $('pnl').textContent = `${pnlMoney(p.total_pnl_usd, 4)} (${p.total_pnl_pct >= 0 ? '+' : ''}${num(p.total_pnl_pct)}%)`;
    $('pnl').className = Number(p.total_pnl_usd) >= 0 ? 'positive' : 'negative';
    $('pnl-sub').textContent = `محقق: ${pnlMoney(p.realized_pnl_usd, 4)} | عائم: ${pnlMoney(p.unrealized_pnl_usd, 4)}`;
    $('win-rate').textContent = `${num(p.win_rate, 1)}%`;
    $('win-rate').className = Number(p.win_rate) >= 50 ? 'positive' : 'negative';
    $('trades-sub').textContent = `${p.wins || 0} رابحة / ${p.losses || 0} خاسرة · إجمالي ${p.total_trades || 0}`;
    $('fees').textContent = `-${money(p.total_fees_usd || 0, 4)}`;
    $('fees').style.color = '#e09f3e';
    $('pf-sub').textContent = `معامل ربح: ${num(p.profit_factor)} · قبل الرسوم: ${pnlMoney(p.gross_pnl_usd || 0, 4)}`;
    $('session-time').textContent = p.elapsed_hours_str || '—';
    $('slots').textContent = `الخانات: ${pos.length}/${d.allocation?.total_slots ?? '—'} · ${money(d.allocation?.slot_size)} للخانة`;
    $('pending').textContent = `أوامر قيد المعالجة: ${pendingCount(d)}`;
    renderPositions(pos); renderRadar();
    details('health-box',[
        ['آخر دورة', h.last_step ? new Date(h.last_step).toLocaleTimeString('ar-EG') : '—'],
        ['آخر فحص سوق', h.last_scan ? new Date(h.last_scan).toLocaleTimeString('ar-EG') : '—'],
        ['إجمالي العمولات المخصومة', money(p.total_fees_usd||0, 4)],
        ['ربح إجمالي قبل الرسوم (Gross)', pnlMoney(p.gross_pnl_usd||0, 4)],
        ['صافي أرباح محققة في الجيب', pnlMoney(p.realized_pnl_usd||0, 4)],
        ['أرباح عائمة في الصفقات النشطة', pnlMoney(p.unrealized_pnl_usd||0, 4)],
        ['متوسط ربح الصفقة الرابحة', `+${money(p.avg_win_usd||0, 4)}`],
        ['متوسط خسارة الصفقة الخاسرة', `-${money(p.avg_loss_usd||0, 4)}`],
        ['أفضل صفقة في الجلسة', pnlMoney(p.best_trade_usd||0, 4)],
        ['أسوأ صفقة في الجلسة', pnlMoney(p.worst_trade_usd||0, 4)],
        ['الأخطاء المسجلة', array(h.errors).length],
        ['حالة تغذية الأسعار', stalePrices(d)?'قديمة — يلزم الانتباه':'محدثة وفورية'],
        ['حد خسارة الجلسة', d.mode==='PAPER'?'معطّل في المحاكاة':h.loss_limit_hit?'تم بلوغه — محظور':'لم يُبلغ']
    ]);
    const names = {take_profit_pct:'هدف الربح %',stop_loss_pct:'وقف الخسارة %',max_hold_minutes:'مدة الاحتفاظ القصوى',min_score:'أقل تقييم',max_positions:'أقصى صفقات',max_slots:'أقصى عدد مراكز',trailing_tp_pct:'تتبع الربح',timeout_minutes:'مهلة المركز بالدقائق',max_session_loss_pct:'حد خسارة الجلسة',enable_flow_entries:'دخول التدفق التجريبي',enable_volume_decay_exit:'خروج الحجم التجريبي',max_entries_per_hour:'أقصى دخولات/ساعة',symbol_cooldown_minutes:'فاصل إعادة الدخول/د'};
    const settingsList = Object.entries(d.settings||{}).filter(([k])=>!/token|secret|password|key/i.test(k)).map(([k,v])=>[names[k]||k,typeof v==='boolean'?(v?'مفعّل':'معطّل'):k.endsWith('_pct')?`${num(Number(v)*100)}%`:typeof v==='object'?JSON.stringify(v):v]);
    const aiList = [
        ['جيل التطور الجيني',`الجيل ${ai.generation||1} (TP: +${num(Number(ai.fittest_tp||0)*100)}% | SL: -${num(Number(ai.fittest_sl||0)*100)}%)`],
        ['ذاكرة الأنماط المتجهة',`${ai.memory_wins||0} بصمة رابحة / ${ai.memory_losses||0} مصيدة`],
        ['العملات المعاقبة',ai.penalized_symbols?.length ? ai.penalized_symbols.join(', ') : 'لا توجد عملات محظورة'],
        ['موجز تحليل الناقد',ai.critic_summary||'قيد المراقبة']
    ];
    details('settings-box', [...aiList, ...settingsList]);
    $('hist-box').innerHTML = table(
        ['العملة', 'الدخول', 'الخروج', 'إجمالي الربح (Gross)', 'العمولة (Fee)', 'صافي الربح (Net)', 'العائد %', 'المدة', 'الوقت', 'سبب الخروج'],
        hist.slice().reverse().map(t => {
            const fee = Number(t.fee_quote) || 0;
            const net = Number(t.pnl_usd) || 0;
            const gross = net + fee;
            const timeStr = t.timestamp ? (t.timestamp.length > 19 ? t.timestamp.slice(11, 19) : t.timestamp) : '—';
            return [
                t.symbol,
                num(t.entry_price, 6),
                num(t.exit_price, 6),
                pnlMoney(gross, 4),
                money(fee, 4),
                pnlMoney(net, 4),
                `${t.pnl_pct > 0 ? '+' : ''}${num(t.pnl_pct, 2)}%`,
                `${num(t.duration_mins, 1)}د`,
                timeStr,
                t.reason_arabic || t.reason
            ];
        }),
        'لا توجد صفقات مغلقة بعد'
    );
    $('hourly-box').innerHTML = table(['الساعة','الوقت','الصفقات','ربح الساعة','الرصيد'],array(p.hourly_snapshots).map(hs=>[hs.hour,hs.timestamp,hs.total_trades,pnlMoney(hs.hour_pnl_usd,4),money(hs.balance)]),'يظهر التقرير بعد اكتمال الساعة الأولى');
    $('news-box').innerHTML = array(d.latest_news).length ? d.latest_news.map(n=>`<article class="news"><div class="section-head"><strong>${esc(n.symbol)}</strong><span class="badge">${esc(n.score)}/100 · ${n.approved?'مؤهل':'غير مؤهل'}</span></div><h3>${esc(n.title)}</h3><p>${esc(n.phase)} · ${esc(n.published_at)}</p><p>${esc(n.reason||'لا يوجد تفسير متاح')}</p></article>`).join('') : '<p class="empty">لا توجد أخبار في هذه الجلسة بعد</p>';
    const keys = new Set([...pos.map(t=>`open:${t.symbol}:${t.entry_price}:${t.opened_at||t.entry_time||''}`),...hist.map(t=>`closed:${t.symbol}:${t.timestamp}:${t.exit_price}`)]);
    if (seen && [...keys].some(k=>!seen.has(k)) && typeof chime === 'function') chime();
    if (!seen) seen = new Set(); keys.forEach(k=>seen.add(k));
    if (typeof controls === 'function') controls();
}
function refresh() {
    if (statusFlight) return statusFlight;
    statusFlight = api('/api/status').then(d => {
        state = d; lastSuccess = Date.now();
        $('connection-state').textContent = 'متصل بنجاح';
        $('updated-at').textContent = `آخر تحديث: ${new Date().toLocaleTimeString('ar-EG')}`;
        render(d);
    }).catch(e => {
        $('connection-state').textContent = 'تعذر الاتصال';
        $('updated-at').textContent = e.message;
    }).finally(() => { statusFlight = null; });
    return statusFlight;
}
setInterval(refresh, 2500);
refresh();
