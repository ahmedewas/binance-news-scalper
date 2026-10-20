'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = (v, digits = 2) => v !== null && v !== undefined && Number.isFinite(Number(v)) ? Number(v).toLocaleString('en-US',{maximumFractionDigits:digits,minimumFractionDigits:digits}) : '—';
const money = v => `$${num(v)}`;
const array = v => Array.isArray(v) ? v : [];
const pendingCount = d => d?.pending_orders && typeof d.pending_orders === 'object' ? Object.keys(d.pending_orders).length : 0;
const stalePrices = d => Array.isArray(d?.health?.price_stale) ? d.health.price_stale.length > 0 : Boolean(d?.health?.price_stale);
let state = null, lastSuccess = 0, busy = false, statusFlight = null, journalFlight = null, timer, journal = '', journalAt = 0, seen = null, audioCtx;
let token = '', soundOn = false;
try { token = sessionStorage.getItem('dashboardToken') || ''; soundOn = localStorage.getItem('dashboardSound') === 'true'; } catch (_) {}
$('token').value = token;
function notify(message) { $('alert').textContent = message; $('alert').hidden = !message; }
async function api(path, body) {
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 12000);
    const headers = {Accept:'application/json'};
    if (token) headers['X-Dashboard-Token'] = token;
    if (body !== undefined) { headers['Content-Type'] = 'application/json'; headers['X-Requested-With'] = 'ScalperDashboard'; }
    try {
        const res = await fetch(path, {method:body === undefined ? 'GET':'POST', headers, body:body === undefined ? undefined:JSON.stringify(body),signal:controller.signal,cache:'no-store'});
        const data = await res.json();
        if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `فشل الطلب (${res.status})`);
        return data;
    } catch (error) { if (error.name === 'AbortError') throw new Error('انتهت مهلة الاتصال. حالة العملية غير مؤكدة؛ حدّث البيانات قبل تكرارها.'); throw error; }
    finally { clearTimeout(timeout); }
}
function controls() {
    const unavailable = busy || !state || Date.now() - lastSuccess > 15000;
    document.querySelectorAll('[data-mutation]').forEach(b => b.disabled = unavailable);
    $('pause-btn').disabled = unavailable || !state?.is_active;
    $('resume-btn').disabled = unavailable || !!state?.is_active || !!state?.health?.loss_limit_hit || pendingCount(state)>0;
    $('reconcile-btn').disabled = unavailable || !pendingCount(state);
    $('reset-btn').disabled = unavailable || state?.mode !== 'PAPER' || array(state?.open_positions).length>0 || pendingCount(state)>0;
    $('emergency-btn').disabled = unavailable;
    $('csv-btn').disabled = !array(state?.trade_history).length;
}
function table(headers, rows, empty) { return rows.length ? `<table class="table"><thead><tr>${headers.map(h=>`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table>` : `<p class="empty">${esc(empty)}</p>`; }
function details(id, pairs) { $(id).innerHTML = pairs.map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join(''); }
function renderPositions(positions) {
    $('position-count').textContent = `${positions.length} صفقات`;
    $('pos-box').innerHTML = positions.length ? positions.map((p,i)=>`<article class="position"><div class="section-head"><strong dir="ltr">${esc(p.symbol)}</strong><strong class="${Number(p.pnl_usd)>=0?'positive':'negative'}" dir="ltr">${esc(money(p.pnl_usd))} (${esc(num(p.pnl_pct))}%)</strong><button class="danger close-position" data-index="${i}" data-mutation>إغلاق الصفقة</button></div><div class="position-details">${[['سعر الدخول',num(p.entry_price,8)],['السعر الحالي',num(p.current_price,8)],['رأس المال',money(p.cost_basis)],['الهدف',num(p.target_tp,8)],['الوقف الحالي',num(p.stop_loss,8)],['تأمين التعادل',p.is_breakeven_locked?'مفعّل':'غير مفعّل'],['المدة بالدقائق',num(p.elapsed_mins,1)],['المتبقي بالدقائق',num(p.remaining_mins,1)]].map(([k,v])=>`<div><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('')}</div></article>`).join('') : '<p class="empty">لا توجد صفقات مفتوحة حالياً</p>';
}
function renderRadar() {
    const query = $('radar-search').value.trim().toUpperCase(), filter = $('radar-filter').value, sort = $('radar-sort').value;
    const rows = array(state?.market_radar).filter(r=>String(r.symbol).toUpperCase().replace('/','').includes(query.replace('/','')) && (filter==='all'||Boolean(r.approved)===(filter==='approved'))).slice().sort((a,b)=>sort==='symbol'?String(a.symbol).localeCompare(String(b.symbol)):Number(b[sort]||0)-Number(a[sort]||0));
    $('radar-count').textContent = `${rows.length} / ${array(state?.market_radar).length}`;
    $('radar-box').innerHTML = table(['العملة','السعر','المرحلة','التقييم','الحالة / السبب'],rows.map(r=>[r.symbol,num(r.price,8),r.phase,`${num(r.score,0)}/100`,r.reason || r.status || (r.approved?'مؤهلة':'غير مؤهلة')]),'لا توجد عملات مطابقة');
}
function render(d) {
    const p = d.performance || {}, positions = array(d.open_positions), history = array(d.trade_history), health = d.health || {};
    $('mode-badge').textContent = d.mode === 'PAPER' ? 'PAPER · محاكاة' : (d.mode || 'الوضع غير معروف');
    $('status-badge').textContent = d.is_active ? 'الدخول نشط':'الدخول متوقف';
    $('bal').textContent = money(d.usdt_balance); $('equity').textContent = money(d.equity);
    $('pnl').textContent = `${money(p.total_pnl_usd)} (${num(p.total_pnl_pct)}%)`;
    $('pnl').className = Number(p.total_pnl_usd)>=0?'positive':'negative';
    $('win-rate').textContent = `نجاح ${num(p.win_rate)}% · ${p.wins||0} رابحة / ${p.losses||0} خاسرة`;
    $('session-time').textContent = p.elapsed_hours_str || '—';
    $('slots').textContent = `الخانات ${positions.length}/${d.allocation?.total_slots ?? '—'} · ${money(d.allocation?.slot_size)} للخانة`;
    $('pending').textContent = `أوامر قيد المعالجة: ${pendingCount(d)}`;
    renderPositions(positions); renderRadar();
    details('health-box',[['آخر دورة',health.last_step],['آخر فحص',health.last_scan],['الأخطاء',array(health.errors).length],['آخر خطأ',health.last_error || 'لا يوجد'],['الأسعار',stalePrices(d)?'قديمة — يلزم الانتباه':'لا توجد أسعار مراكز متقادمة'],['حد خسارة الجلسة',health.loss_limit_hit?'تم بلوغه — الدخول محظور':'لم يُبلغ']]);
    const names = {take_profit_pct:'هدف الربح %',stop_loss_pct:'وقف الخسارة %',max_hold_minutes:'مدة الاحتفاظ القصوى',min_score:'أقل تقييم',max_positions:'أقصى صفقات',max_slots:'أقصى عدد مراكز',trailing_tp_pct:'تفعيل تتبع الربح',timeout_minutes:'مهلة المركز بالدقائق',max_session_loss_pct:'حد خسارة الجلسة',enable_flow_entries:'دخول التدفق التجريبي',enable_volume_decay_exit:'خروج الحجم التجريبي',max_entries_per_hour:'أقصى دخولات في الساعة',symbol_cooldown_minutes:'فاصل إعادة دخول العملة بالدقائق',scan_interval:'فاصل الفحص'};
    details('settings-box',Object.entries(d.settings || {}).filter(([k])=>!/token|secret|password|key/i.test(k)).map(([k,v])=>[names[k]||k,typeof v==='boolean'?(v?'مفعّل':'معطّل'):k.endsWith('_pct')?`${num(Number(v)*100)}%`:typeof v==='object'?JSON.stringify(v):v]));
    $('hist-box').innerHTML = table(['العملة','الدخول','الخروج','الربح USDT','الربح %','المدة / د','الوقت','سبب الخروج'],history.slice().reverse().map(t=>[t.symbol,num(t.entry_price,8),num(t.exit_price,8),num(t.pnl_usd),num(t.pnl_pct),num(t.duration_mins,1),t.timestamp,t.reason_arabic||t.reason]),'لا توجد صفقات مغلقة بعد');
    $('hourly-box').innerHTML = table(['الساعة','الوقت','الصفقات','ربح الساعة','الرصيد'],array(p.hourly_snapshots).map(h=>[h.hour,h.timestamp,h.total_trades,money(h.hour_pnl_usd),money(h.balance)]),'يظهر التقرير بعد اكتمال الساعة الأولى');
    $('news-box').innerHTML = array(d.latest_news).length ? d.latest_news.map(n=>`<article class="news"><div class="section-head"><strong>${esc(n.symbol)}</strong><span class="badge">${esc(n.score)} / 100 · ${n.approved?'مؤهل':'غير مؤهل'}</span></div><h3>${esc(n.title)}</h3><p>${esc(n.phase)} · ${esc(n.published_at)}</p><p>${esc(n.reason || 'لا يوجد تفسير متاح')}</p></article>`).join('') : '<p class="empty">لا توجد أخبار في هذه الجلسة بعد</p>';
    const keys = new Set([...positions.map(t=>`open:${t.symbol}:${t.entry_price}:${t.opened_at||t.entry_time||''}`),...history.map(t=>`closed:${t.symbol}:${t.timestamp}:${t.exit_price}`)]);
    if (seen && [...keys].some(k=>!seen.has(k))) chime();
    if (!seen) seen = new Set(); keys.forEach(k=>seen.add(k));
    controls();
}
function refresh() {
    if (statusFlight) return statusFlight;
    clearTimeout(timer); $('refresh-btn').disabled = true;
    statusFlight = (async()=>{
        const start = performance.now();
        try { const d = await api('/api/status'); state = d; lastSuccess = Date.now(); render(d); $('connection-state').textContent = stalePrices(d)?'متصل · أسعار قديمة':'متصل'; $('connection-state').className=stalePrices(d)?'stale':'positive'; $('updated-at').textContent = `آخر تحديث: ${new Date().toLocaleTimeString('ar-EG')}`; $('lat-badge').textContent = `${Math.round(performance.now()-start)} ms`; }
        catch(e) { $('connection-state').textContent='فشل الاتصال · البيانات قديمة'; $('connection-state').className='negative'; $('updated-at').textContent=e.message; lastSuccess = 0; controls(); }
        finally { statusFlight=null; $('refresh-btn').disabled=false; timer=setTimeout(refresh,3000); }
    })();
    return statusFlight;
}
async function fetchJournal() {
    if (journalFlight) return journalFlight;
    $('journal-refresh').disabled = true;
    journalFlight = (async()=>{try { const d=await api('/api/journal'); journal=String(d.journal || 'لا توجد سجلات بعد.'); journalAt=Date.now(); $('journal-box').textContent=journal; $('journal-state').textContent=`تم التحديث ${new Date().toLocaleTimeString('ar-EG')}`; return true; } catch(e){$('journal-state').textContent=`تعذر تحديث السجل: ${e.message}`; return false;} finally{journalFlight=null;$('journal-refresh').disabled=false;}})(); return journalFlight;
}
async function mutate(path, body) {
    if(busy) return; busy=true; controls(); notify('');
    try { const result=await api(path,body); if(path==='/api/close_all' && (Array.isArray(result.remaining)?result.remaining.length:Number(result.remaining)>0)) notify('توقف الدخول، لكن بعض الصفقات ما زالت مفتوحة. راجع السجل ثم أعد المحاولة.'); else if(path==='/api/reconcile' && result.remaining) notify('بعض الأوامر ما زالت غير محسومة. لم تُرسل أوامر جديدة.'); else notify('تم تنفيذ الطلب.'); }
    catch(e){notify(`تعذر تنفيذ الطلب: ${e.message}`);}
    finally { if(statusFlight) await statusFlight; await refresh(); busy=false; controls(); }
}
function download(name, content, type) { const url=URL.createObjectURL(new Blob([content],{type})), a=document.createElement('a'); a.href=url; a.download=name; document.body.append(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url),1000); }
function chime() { if(!soundOn || !audioCtx || audioCtx.state!=='running') return; const osc=audioCtx.createOscillator(), gain=audioCtx.createGain(); osc.frequency.value=880; gain.gain.setValueAtTime(.08,audioCtx.currentTime); gain.gain.exponentialRampToValueAtTime(.001,audioCtx.currentTime+.25); osc.connect(gain); gain.connect(audioCtx.destination); osc.start(); osc.stop(audioCtx.currentTime+.25); osc.onended=()=>{osc.disconnect();gain.disconnect();}; }
function soundLabel(){ $('sound-btn').textContent=soundOn?'الصوت: مفعّل':'الصوت: مغلق'; $('sound-btn').setAttribute('aria-pressed',String(soundOn)); }
async function unlockAudio(){ if(!soundOn) return; try { audioCtx ||= new (window.AudioContext||window.webkitAudioContext)(); await audioCtx.resume(); }catch(e){ soundOn=false; soundLabel(); notify('الصوت غير متاح في هذا المتصفح.'); } }
document.addEventListener('pointerdown',unlockAudio);
$('sound-btn').addEventListener('click',()=>{soundOn=!soundOn; try{localStorage.setItem('dashboardSound',String(soundOn));}catch(_){} soundLabel(); unlockAudio();});
$('connect-form').addEventListener('submit',async e=>{e.preventDefault(); if(statusFlight) await statusFlight; if(journalFlight) await journalFlight; token=$('token').value.trim(); try{sessionStorage.setItem('dashboardToken',token);}catch(_){} notify(''); refresh(); fetchJournal();});
$('refresh-btn').addEventListener('click',refresh);
$('reconcile-btn').addEventListener('click',()=>mutate('/api/reconcile',{}));
$('reset-btn').addEventListener('click',()=>{if(confirm('بدء جلسة ورقية جديدة؟ سيُؤرشف سجل الجلسة الحالية ويُعاد الرصيد الورقي إلى القيمة الابتدائية. تظل الدخولات متوقفة حتى تستأنفها.'))mutate('/api/paper/reset',{confirmation:'RESET PAPER'});});
$('pause-btn').addEventListener('click',()=>mutate('/api/active',{active:false}));
$('resume-btn').addEventListener('click',()=>mutate('/api/active',{active:true}));
$('emergency-btn').addEventListener('click',()=>{if(confirm('إغلاق كل الصفقات وإيقاف الدخول؟ قد تظهر خسارة محققة.')) mutate('/api/close_all',{});});
$('pos-box').addEventListener('click',e=>{const b=e.target.closest('.close-position'); if(!b || b.disabled)return; const p=state.open_positions[Number(b.dataset.index)]; if(p && confirm(`إغلاق صفقة ${p.symbol} الآن؟`)) mutate('/api/close',{symbol:p.symbol});});
['radar-search','radar-filter','radar-sort'].forEach(id=>$(id).addEventListener('input',renderRadar));
$('journal-refresh').addEventListener('click',fetchJournal);
$('journal-download').addEventListener('click',async()=>{const b=$('journal-download'); b.disabled=true; try{if(await fetchJournal())download('scalper-journal.txt',journal,'text/plain;charset=utf-8');}finally{b.disabled=false;}});
$('csv-btn').addEventListener('click',()=>{const keys=['symbol','entry_price','exit_price','pnl_usd','pnl_pct','duration_mins','timestamp','reason']; const quote=v=>'"'+String(v??'').replace(/^[=+@\-\t\r]/,"'$&").replace(/"/g,'""')+'"'; const rows=[keys,...array(state?.trade_history).map(t=>keys.map(k=>t[k]))]; download('scalper-trades.csv','\ufeff'+rows.map(r=>r.map(quote).join(',')).join('\r\n'),'text/csv;charset=utf-8');});
soundLabel(); controls(); refresh(); fetchJournal();
setInterval(()=>{if(Date.now()-lastSuccess>15000 && state){$('connection-state').textContent='البيانات قديمة · تحقق من الاتصال';$('connection-state').className='stale';controls();} if(Date.now()-journalAt>10000 && !document.hidden)fetchJournal();},5000);
