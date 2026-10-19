let soundOn = true, audioCtx = null;
function toggleAudio() { soundOn = !soundOn; document.getElementById('sound-btn').innerText = soundOn ? '🔔' : '🔕'; }
function chime() {
    if (!soundOn) return;
    try {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator(), g = audioCtx.createGain();
        osc.frequency.setValueAtTime(880, audioCtx.currentTime);
        g.gain.setValueAtTime(0.12, audioCtx.currentTime);
        g.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.3);
        osc.connect(g); g.connect(audioCtx.destination);
        osc.start(); osc.stop(audioCtx.currentTime + 0.3);
    } catch(e) {}
}
async function fetchStatus() {
    try {
        const t0 = performance.now(), res = await fetch('/api/status'), lat = Math.round(performance.now() - t0);
        const d = await res.json(), p = d.performance || {};
        document.getElementById('lat-badge').innerText = `${lat} ms`;
        document.getElementById('mode-badge').innerText = d.mode;
        document.getElementById('mode-badge').className = d.mode === 'LIVE' ? 'badge badge-live' : 'badge badge-paper';
        document.getElementById('status-badge').innerText = d.is_active ? 'نشط' : 'متوقف';
        document.getElementById('status-badge').className = d.is_active ? 'badge badge-active' : 'badge badge-paused';
        document.getElementById('bal').innerText = `$${d.usdt_balance.toFixed(2)}`;
        const pnlP = p.total_pnl_pct || 0.0, pnlU = p.total_pnl_usd || 0.0;
        document.getElementById('pnl').innerHTML = `<span class="${pnlP >= 0 ? 'pnl-pos' : 'pnl-neg'}">${pnlP >= 0 ? '+' : ''}${pnlP}% ($${pnlU >= 0 ? '+' : ''}${pnlU.toFixed(2)})</span>`;
        document.getElementById('win-rate').innerText = `${p.win_rate || 0}% (${p.wins || 0}W / ${p.losses || 0}L)`;
        document.getElementById('session-time').innerText = p.elapsed_hours_str || '0h 0m';
        document.getElementById('slots').innerText = `${d.open_positions.length}/${d.allocation.total_slots} ($${d.allocation.slot_size.toFixed(2)} للخانة)`;
        renderPositions(d.open_positions);
        renderHourly(p.hourly_snapshots || []);
        renderHistory(d.trade_history || []);
        renderRadar(d.market_radar || []);
    } catch(e) { console.error(e); }
}
function renderPositions(pos) {
    const c = document.getElementById('pos-box');
    if (!pos || !pos.length) { c.innerHTML = '<div class="empty-text">لا توجد صفقات مفتوحة حالياً (يراقب السوق كل 3ث)</div>'; return; }
    c.innerHTML = pos.map(p => `
        <div class="item-box">
            <div class="item-head"><strong>${p.symbol}</strong> (خانة ${p.slot_id}) <span class="${p.pnl_pct>=0?'pnl-pos':'pnl-neg'}">${p.pnl_pct>=0?'+':''}${p.pnl_pct}% ($${p.pnl_usd>=0?'+':''}${p.pnl_usd})</span></div>
            <div class="item-detail">دخول: $${p.entry_price} | حالي: $${p.current_price} | رأس المال: $${p.cost_basis}</div>
            <div class="item-detail">الهدف (+1.2%): $${p.target_tp} | الوقف: $${p.stop_loss} ${p.is_breakeven_locked ? '🔒 مؤمن' : ''}</div>
            <div class="item-detail" style="color:var(--accent);">⏱️ مضى: ${p.elapsed_mins} دقيقة | متبقي للخروج الزمني: ${p.remaining_mins} دقيقة</div>
        </div>`).join('');
}
function renderHourly(h) {
    const c = document.getElementById('hourly-box');
    if (!h.length) { c.innerHTML = '<div class="empty-text">سيظهر تقرير الساعة الأولى بعد اكتمال 60 دقيقة من الجلسة</div>'; return; }
    c.innerHTML = `<table class="table"><tr><th>الساعة</th><th>الوقت</th><th>الصفقات</th><th>أرباح الساعة</th><th>الرصيد</th></tr>` +
        h.map(s => `<tr><td>س ${s.hour}</td><td>${s.timestamp}</td><td>${s.total_trades}</td><td class="${s.hour_pnl_usd>=0?'pnl-pos':'pnl-neg'}">$${s.hour_pnl_usd}</td><td>$${s.balance}</td></tr>`).join('') + `</table>`;
}
function renderHistory(hist) {
    const c = document.getElementById('hist-box');
    if (!hist.length) { c.innerHTML = '<div class="empty-text">لا توجد صفقات منتهية بعد</div>'; return; }
    c.innerHTML = hist.slice().reverse().map(t => `
        <div class="item-box">
            <div class="item-head"><strong>${t.symbol}</strong> <span class="${t.pnl_pct>=0?'pnl-pos':'pnl-neg'}">${t.pnl_pct>=0?'+':''}${t.pnl_pct}% ($${t.pnl_usd>=0?'+':''}${t.pnl_usd})</span></div>
            <div class="item-detail">سعر الدخول: $${t.entry_price} ⬅️ الخروج: $${t.exit_price} | مدة الصفقة: ${t.duration_mins} د | الساعة: ${t.timestamp}</div>
            <div class="reason-box"><strong>سبب الخروج:</strong> ${t.reason_arabic || t.reason}</div>
        </div>`).join('');
}
function renderRadar(r) {
    const c = document.getElementById('radar-box');
    if (!r.length) { c.innerHTML = '<div class="empty-text">جاري فحص مؤشرات السوق...</div>'; return; }
    c.innerHTML = `<table class="table"><tr><th>العملة</th><th>السعر</th><th>مرحلة السوق</th><th>التقييم</th><th>الحالة</th></tr>` +
        r.map(m => `<tr><td>${m.symbol}</td><td>$${m.price}</td><td>${m.phase}</td><td>${m.score}/100</td><td>${m.approved?'🚀 جاهز':m.score<75?'⏳ تحت 75':m.status}</td></tr>`).join('') + `</table>`;
}
async function fetchJournal() {
    try {
        const res = await fetch('/api/journal'), data = await res.json();
        const box = document.getElementById('journal-box');
        if (box) box.innerText = data.journal || 'لا توجد سجلات بعد.';
    } catch(e) {}
}
async function toggleBot() { await fetch('/api/toggle', {method: 'POST'}); fetchStatus(); }
async function emergencyClose() { if (confirm("إغلاق كافة الصفقات فوراً؟")) { await fetch('/api/close_all', {method: 'POST'}); fetchStatus(); } }
setInterval(fetchStatus, 3000); setInterval(fetchJournal, 10000); fetchStatus(); fetchJournal();
