'use strict';
function controls() {
    const unavail = busy || !state || Date.now() - lastSuccess > 15000, pCnt = pendingCount(state), oLen = array(state?.open_positions).length;
    document.querySelectorAll('[data-mutation]').forEach(b => b.disabled = unavail);
    $('pause-btn').disabled = unavail || !state?.is_active;
    $('resume-btn').disabled = unavail || !!state?.is_active || (state?.mode === 'LIVE' && Boolean(state?.health?.loss_limit_hit)) || pCnt > 0;
    $('reconcile-btn').disabled = unavail || !pCnt;
    $('reset-btn').disabled = unavail || state?.mode !== 'PAPER' || oLen > 0 || pCnt > 0;
    if ($('mode-paper-btn')) $('mode-paper-btn').disabled = unavail || (state?.mode === 'PAPER' && state?.is_active) || oLen > 0 || pCnt > 0;
    if ($('mode-live-btn')) $('mode-live-btn').disabled = unavail || (state?.mode === 'LIVE' && state?.is_active) || oLen > 0 || pCnt > 0;
    $('emergency-btn').disabled = unavail;
    $('csv-btn').disabled = !array(state?.trade_history).length;
}
async function mutate(path, body) {
    if(busy) return; busy=true; controls(); notify('');
    try { const result=await api(path,body); if(path==='/api/close_all' && (Array.isArray(result.remaining)?result.remaining.length:Number(result.remaining)>0)) notify('توقف الدخول، لكن بعض الصفقات ما زالت مفتوحة.'); else if(path==='/api/reconcile' && result.remaining) notify('بعض الأوامر ما زالت غير محسومة.'); else notify('تم تنفيذ الطلب بنجاح.'); }
    catch(e){notify(`تعذر تنفيذ الطلب: ${e.message}`);}
    finally { if(statusFlight) await statusFlight; await refresh(); busy=false; controls(); }
}
function download(name, content, type) { const url=URL.createObjectURL(new Blob([content],{type})), a=document.createElement('a'); a.href=url; a.download=name; document.body.append(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url),1000); }
function chime() { if(!soundOn || !audioCtx || audioCtx.state!=='running') return; const osc=audioCtx.createOscillator(), g=audioCtx.createGain(); osc.frequency.value=880; g.gain.setValueAtTime(.08,audioCtx.currentTime); g.gain.exponentialRampToValueAtTime(.001,audioCtx.currentTime+.25); osc.connect(g); g.connect(audioCtx.destination); osc.start(); osc.stop(audioCtx.currentTime+.25); osc.onended=()=>{osc.disconnect();g.disconnect();}; }
function soundLabel(){ $('sound-btn').textContent=soundOn?'الصوت: مفعّل':'الصوت: مغلق'; $('sound-btn').setAttribute('aria-pressed',String(soundOn)); }
async function unlockAudio(){ if(!soundOn) return; try { audioCtx ||= new (window.AudioContext||window.webkitAudioContext)(); await audioCtx.resume(); }catch(e){ soundOn=false; soundLabel(); notify('الصوت غير متاح في هذا المتصفح.'); } }
document.addEventListener('pointerdown',unlockAudio);
$('sound-btn').addEventListener('click',()=>{soundOn=!soundOn; try{localStorage.setItem('dashboardSound',String(soundOn));}catch(_){} soundLabel(); unlockAudio();});
$('connect-form').addEventListener('submit',async e=>{e.preventDefault(); if(statusFlight) await statusFlight; if(journalFlight) await journalFlight; token=$('token').value.trim(); try{sessionStorage.setItem('dashboardToken',token);}catch(_){} notify(''); refresh(); fetchJournal();});
$('refresh-btn').addEventListener('click',refresh);
$('reconcile-btn').addEventListener('click',()=>mutate('/api/reconcile',{}));
$('reset-btn').addEventListener('click',()=>{if(confirm('بدء جلسة ورقية جديدة؟ سيُؤرشف سجل الجلسة الحالية ويُعاد الرصيد الورقي للقيمة الابتدائية.'))mutate('/api/paper/reset',{confirmation:'RESET PAPER'});});
$('mode-paper-btn')?.addEventListener('click',()=>{if(confirm('بدء المحاكاة الورقية (PAPER) وتفعيل البحث عن الصفقات؟'))mutate('/api/mode',{mode:'PAPER'});});
$('mode-live-btn')?.addEventListener('click',()=>{if(confirm('تنبيه هام: التحويل إلى وضع التداول الحقيقي (LIVE) بأموال حقيقية؟ تأكد من مفاتيح API.'))mutate('/api/mode',{mode:'LIVE'});});
$('pause-btn').addEventListener('click',()=>mutate('/api/active',{active:false}));
$('resume-btn').addEventListener('click',()=>mutate('/api/active',{active:true}));
$('emergency-btn').addEventListener('click',()=>{if(confirm('إغلاق كل الصفقات وإيقاف الدخول فوراً؟')) mutate('/api/close_all',{});});
$('pos-box').addEventListener('click',e=>{const b=e.target.closest('.close-position'); if(!b || b.disabled)return; const p=state.open_positions[Number(b.dataset.index)]; if(p && confirm(`إغلاق صفقة ${p.symbol} الآن؟`)) mutate('/api/close',{symbol:p.symbol});});
['radar-search','radar-filter','radar-sort'].forEach(id=>$(id).addEventListener('input',renderRadar));
$('journal-refresh').addEventListener('click',fetchJournal);
$('journal-download').addEventListener('click',async()=>{const b=$('journal-download'); b.disabled=true; try{if(await fetchJournal())download('scalper-journal.txt',journal,'text/plain;charset=utf-8');}finally{b.disabled=false;}});
$('csv-btn').addEventListener('click',()=>{const keys=['symbol','entry_price','exit_price','fee_quote','pnl_usd','pnl_pct','duration_mins','timestamp','reason','reason_arabic']; const quote=v=>'"'+String(v??'').replace(/^[=+@\-\t\r]/,"'$&").replace(/"/g,'""')+'"'; const rows=[keys,...array(state?.trade_history).map(t=>keys.map(k=>t[k]))]; download('scalper-trades.csv','\ufeff'+rows.map(r=>r.map(quote).join(',')).join('\r\n'),'text/csv;charset=utf-8');});
soundLabel(); controls(); refresh(); fetchJournal();
setInterval(()=>{if(Date.now()-lastSuccess>15000 && state){$('connection-state').textContent='البيانات قديمة · تحقق من الاتصال';$('connection-state').className='stale';controls();} if(Date.now()-journalAt>10000 && !document.hidden)fetchJournal();},5000);
