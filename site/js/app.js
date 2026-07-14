/* ── Kicktipp WC 2026 Dashboard ─────────────────────────────────── */
const D = window.KICKTIPP;

/* ── Helpers ──────────────────────────────────────────────────────── */
function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function rankClass(rank) {
    if (rank === 1) return 'rank-1';
    if (rank === 2) return 'rank-2';
    if (rank === 3) return 'rank-3';
    return 'rank-other';
}

function statusClass(status) {
    return `status-${status}`;
}

function statusLabel(status) {
    return status === 'leading' ? 'Leading' : status === 'possible' ? 'Possible' : 'Eliminated';
}

/* ── Hero ─────────────────────────────────────────────────────────── */
function renderHero() {
    const meta = D.results_meta;
    $('#export-date').textContent = `Data exported: ${new Date(D.export_date).toLocaleString()} · Results updated: ${meta.completed} of ${meta.total_matches} matches played`;

    const stats = $('#hero-stats');
    stats.innerHTML = `
        <div class="hero-stat">
            <div class="hero-stat-value">${D.users.length}</div>
            <div class="hero-stat-label">Players</div>
        </div>
        <div class="hero-stat">
            <div class="hero-stat-value">${meta.completed}</div>
            <div class="hero-stat-label">Matches Played</div>
        </div>
        <div class="hero-stat">
            <div class="hero-stat-value">${D.stages.length}</div>
            <div class="hero-stat-label">Stages</div>
        </div>
        <div class="hero-stat">
            <div class="hero-stat-value">${D.top_scorers[0]?.name || '—'}</div>
            <div class="hero-stat-label">Top Scorer (${D.top_scorers[0]?.goals || 0} goals)</div>
        </div>
    `;
}

/* ── Standings Table ─────────────────────────────────────────────── */
let sortCol = 'points';
let sortAsc = false;

function renderStandings() {
    const tbody = $('#standings-body');
    const currentRankings = D.rankings[D.stages[D.stages.length - 1]] || [];

    // Sort
    const rows = [...currentRankings].sort((a, b) => {
        let va, vb;
        switch (sortCol) {
            case 'rank': va = a.rank; vb = b.rank; break;
            case 'user': va = a.user; vb = b.user; break;
            case 'points': va = a.points; vb = b.points; break;
            case 'exact': va = D.accuracy[a.user]?.exact || 0; vb = D.accuracy[b.user]?.exact || 0; break;
            case 'winner': va = (D.accuracy[a.user]?.correct_winner || 0) + (D.accuracy[a.user]?.winner_plus_diff || 0); vb = (D.accuracy[b.user]?.correct_winner || 0) + (D.accuracy[b.user]?.winner_plus_diff || 0); break;
            case 'missed': va = D.accuracy[a.user]?.missed || 0; vb = D.accuracy[b.user]?.missed || 0; break;
            default: va = a.points; vb = b.points;
        }
        if (typeof va === 'string') return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
        return sortAsc ? va - vb : vb - va;
    });

    tbody.innerHTML = rows.map(r => {
        const acc = D.accuracy[r.user] || {};
        const winnerCount = (acc.correct_winner || 0) + (acc.winner_plus_diff || 0);
        const sparkData = D.stages.map(s => {
            let cum = 0;
            for (const stage of D.stages) {
                cum += D.points_per_stage[r.user]?.[stage] || 0;
                if (stage === s) break;
            }
            return cum;
        });

        return `<tr>
            <td><span class="rank-badge ${rankClass(r.rank)}">${r.rank}</span></td>
            <td class="user-name">${r.user}</td>
            <td class="points-value">${r.points}</td>
            <td class="sparkline-cell"><canvas data-points="${sparkData.join(',')}"></canvas></td>
            <td>${acc.exact || 0}</td>
            <td>${winnerCount}</td>
            <td>${acc.missed || 0}</td>
        </tr>`;
    }).join('');

    // Draw sparklines
    tbody.querySelectorAll('canvas').forEach(canvas => {
        const pts = canvas.dataset.points.split(',').map(Number);
        drawSparkline(canvas, pts);
    });
}

function drawSparkline(canvas, data) {
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    ctx.clearRect(0, 0, w, h);

    // Gradient fill
    const gradient = ctx.createLinearGradient(0, 0, 0, h);
    gradient.addColorStop(0, 'rgba(124, 58, 237, 0.3)');
    gradient.addColorStop(1, 'rgba(124, 58, 237, 0)');

    ctx.beginPath();
    ctx.moveTo(0, h);
    data.forEach((v, i) => {
        const x = (i / (data.length - 1)) * w;
        const y = h - ((v - min) / range) * (h - 4) - 2;
        ctx.lineTo(x, y);
    });
    ctx.lineTo(w, h);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Line
    ctx.beginPath();
    data.forEach((v, i) => {
        const x = (i / (data.length - 1)) * w;
        const y = h - ((v - min) / range) * (h - 4) - 2;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = '#7c3aed';
    ctx.lineWidth = 2;
    ctx.stroke();
}

// Sortable headers
$$('th.sortable').forEach(th => {
    th.addEventListener('click', () => {
        const col = th.dataset.col;
        if (sortCol === col) sortAsc = !sortAsc;
        else { sortCol = col; sortAsc = false; }
        renderStandings();
    });
});

/* ── Time on 1st Place Chart ─────────────────────────────────────── */
let timeOnTopChart;

function renderTimeOnTop() {
    if (!timeOnTopChart) {
        timeOnTopChart = echarts.init($('#time-on-top-chart'), 'dark');
    }

    const includeTies = $('#tie-toggle').checked;
    const data = Object.entries(D.time_on_top)
        .sort((a, b) => b[1] - a[1]);

    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: p => `${p[0].name}: <b>${p[0].value.toFixed(1)}</b> stage${p[0].value !== 1 ? 's' : ''} on 1st place`
        },
        grid: { left: 120, right: 40, top: 20, bottom: 40 },
        xAxis: {
            type: 'value',
            name: 'Stages',
            nameTextStyle: { color: '#6b7280' },
            axisLabel: { color: '#9ca3af' },
            splitLine: { lineStyle: { color: '#1e293b' } }
        },
        yAxis: {
            type: 'category',
            data: data.map(d => d[0]).reverse(),
            axisLabel: { color: '#e5e7eb', fontWeight: 600 },
            axisLine: { lineStyle: { color: '#334155' } }
        },
        series: [{
            type: 'bar',
            data: data.map(d => ({
                value: d[1],
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        { offset: 0, color: '#7c3aed' },
                        { offset: 1, color: '#06b6d4' }
                    ])
                }
            })).reverse(),
            barWidth: 20,
            label: {
                show: true,
                position: 'right',
                formatter: p => p.value.toFixed(1),
                color: '#e5e7eb',
                fontSize: 12
            }
        }]
    };

    timeOnTopChart.setOption(option);
}

$('#tie-toggle').addEventListener('change', renderTimeOnTop);

/* ── Points Race Chart ───────────────────────────────────────────── */
let raceChart;
let raceStageIndex = 0;
let raceInterval = null;

function renderRace(stageIdx) {
    if (!raceChart) {
        raceChart = echarts.init($('#race-chart'), 'dark');
    }

    const stage = D.timeline[stageIdx];
    const sorted = [...stage.users].sort((a, b) => b.points - a.points);

    $('#race-stage-label').textContent = stage.label;

    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: p => `${p[0].name}: <b>${p[0].value}</b> pts`
        },
        grid: { left: 120, right: 60, top: 20, bottom: 40 },
        xAxis: {
            type: 'value',
            name: 'Points',
            nameTextStyle: { color: '#6b7280' },
            axisLabel: { color: '#9ca3af' },
            splitLine: { lineStyle: { color: '#1e293b' } }
        },
        yAxis: {
            type: 'category',
            data: sorted.map(u => u.user).reverse(),
            axisLabel: {
                color: '#e5e7eb',
                fontWeight: 600,
                fontSize: 13
            },
            axisLine: { lineStyle: { color: '#334155' } }
        },
        series: [{
            type: 'bar',
            data: sorted.map(u => ({
                value: u.points,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        { offset: 0, color: '#7c3aed' },
                        { offset: 1, color: '#06b6d4' }
                    ])
                }
            })).reverse(),
            barWidth: 24,
            label: {
                show: true,
                position: 'right',
                formatter: p => `${p.value} pts`,
                color: '#e5e7eb',
                fontSize: 12
            },
            animationDuration: 500,
            animationEasing: 'cubicOut'
        }]
    };

    raceChart.setOption(option, true);
}

function startRace() {
    if (raceInterval) return;
    $('#race-play').disabled = true;
    $('#race-pause').disabled = false;

    raceInterval = setInterval(() => {
        raceStageIndex++;
        if (raceStageIndex >= D.timeline.length) {
            raceStageIndex = D.timeline.length - 1;
            stopRace();
            return;
        }
        renderRace(raceStageIndex);
    }, 1500);
}

function stopRace() {
    if (raceInterval) {
        clearInterval(raceInterval);
        raceInterval = null;
    }
    $('#race-play').disabled = false;
    $('#race-pause').disabled = true;
}

$('#race-play').addEventListener('click', startRace);
$('#race-pause').addEventListener('click', stopRace);
$('#race-reset').addEventListener('click', () => {
    stopRace();
    raceStageIndex = 0;
    renderRace(0);
});

/* ── Prediction Quality ───────────────────────────────────────────── */
function renderQuality() {
    const grid = $('#quality-grid');
    const currentRankings = D.rankings[D.stages[D.stages.length - 1]] || [];
    const rankMap = {};
    currentRankings.forEach(r => rankMap[r.user] = r.rank);

    grid.innerHTML = D.users.map(user => {
        const acc = D.accuracy[user] || {};
        const rank = rankMap[user] || '—';
        const totalPred = acc.total_predicted || 0;
        const totalPlayed = acc.total_played || 0;
        const exact = acc.exact || 0;
        const exactDraw = acc.exact_draw || 0;
        const winnerPlusDiff = acc.winner_plus_diff || 0;
        const drawPredNoExact = acc.draw_pred_no_exact || 0;
        const correctWinner = acc.correct_winner || 0;
        const missed = acc.missed || 0;

        const fourPointers = acc.four_pointers || [];

        return `<div class="quality-card">
            <div class="quality-header">
                <span class="quality-name">${user}</span>
                <span class="quality-rank">Rank #${rank}</span>
            </div>
            <div class="quality-stats">
                <div class="quality-stat">
                    <div class="quality-stat-value stat-exact">${exact}</div>
                    <div class="quality-stat-label">Exact</div>
                </div>
                <div class="quality-stat">
                    <div class="quality-stat-value stat-winner">${correctWinner + winnerPlusDiff}</div>
                    <div class="quality-stat-label">Winner</div>
                </div>
                <div class="quality-stat">
                    <div class="quality-stat-value stat-missed">${missed}</div>
                    <div class="quality-stat-label">Missed</div>
                </div>
            </div>
            <div style="display:flex;gap:8px;font-size:12px;color:var(--text-dim);margin-bottom:8px;">
                <span>Exact draws: ${exactDraw}</span>
                <span>·</span>
                <span>Draw pred: ${drawPredNoExact}</span>
                <span>·</span>
                <span>Winner+diff: ${winnerPlusDiff}</span>
            </div>
            ${fourPointers.length > 0 ? `
            <div class="quality-four-pointers">
                <h4>4-Point Predictions (${fourPointers.length})</h4>
                ${fourPointers.map(fp => `
                    <div class="four-pointer">
                        <span class="match">${D.stage_labels[fp.stage] || fp.stage}: ${fp.match}</span>
                        <span class="score">${fp.predicted} ✓</span>
                    </div>
                `).join('')}
            </div>
            ` : ''}
        </div>`;
    }).join('');
}

/* ── What's Needed to Win ─────────────────────────────────────────── */
function renderWhatIf() {
    const grid = $('#what-if-grid');
    const includeSfFinal = $('#include-sf-final').checked;

    grid.innerHTML = D.users.map(user => {
        const wi = D.what_if[user];
        const above = includeSfFinal
            ? wi.above_users
            : wi.above_users.filter(u => {
                // Only include users who have remaining matches in the group stage + knockout already played
                // For simplicity, just show all above users
                return true;
            });

        return `<div class="what-if-card">
            <div class="what-if-header">
                <span class="what-if-name">${user}</span>
                <span class="status-badge ${statusClass(wi.status)}">${statusLabel(wi.status)}</span>
            </div>
            <div class="what-if-stats">
                <div class="what-if-stat">
                    <div class="what-if-stat-value">${wi.current}</div>
                    <div class="what-if-stat-label">Current</div>
                </div>
                <div class="what-if-stat">
                    <div class="what-if-stat-value">${wi.max_possible}</div>
                    <div class="what-if-stat-label">Max Possible</div>
                </div>
                <div class="what-if-stat">
                    <div class="what-if-stat-value">${wi.remaining_matches}</div>
                    <div class="what-if-stat-label">Remaining</div>
                </div>
            </div>
            <div class="what-if-verdict">${wi.verdict}</div>
            ${above.length > 0 ? `
            <div class="what-if-above">
                <h4>Users Above</h4>
                ${above.map(u => `
                    <div class="above-user">
                        <span>${u.user} (${u.current} pts, ${u.remaining} remaining)</span>
                        <span class="gap">${u.current - wi.current} pts ahead</span>
                    </div>
                `).join('')}
            </div>
            ` : ''}
        </div>`;
    }).join('');
}

$('#include-sf-final').addEventListener('change', renderWhatIf);

/* ── Bonus Predictions ────────────────────────────────────────────── */
function renderBonus() {
    const grid = $('#bonus-grid');
    const topScorer = D.top_scorers[0]?.name || '';

    grid.innerHTML = D.users.map(user => {
        const bp = D.bonus_preds[user] || {};
        const wcPick = bp.wc_winner || '—';
        const tsPick = bp.top_scorer || '—';

        // Check if WC winner is resolved (we don't have the actual winner yet)
        // For now, just show the picks
        return `<div class="bonus-card">
            <div class="bonus-name">${user}</div>
            <div class="bonus-pick">
                <span class="bonus-label">WC Winner</span>
                <span class="bonus-value">${wcPick}</span>
            </div>
            <div class="bonus-pick">
                <span class="bonus-label">Top Scorer</span>
                <span class="bonus-value">${tsPick}</span>
            </div>
        </div>`;
    }).join('');
}

/* ── Init ─────────────────────────────────────────────────────────── */
function init() {
    renderHero();
    renderStandings();
    renderTimeOnTop();
    renderRace(0);
    renderQuality();
    renderWhatIf();
    renderBonus();

    // Resize handler
    window.addEventListener('resize', () => {
        if (timeOnTopChart) timeOnTopChart.resize();
        if (raceChart) raceChart.resize();
    });
}

document.addEventListener('DOMContentLoaded', init);
