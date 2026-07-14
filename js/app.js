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

function getAccentColor() {
    return getComputedStyle(document.documentElement).getPropertyValue('--accent').trim();
}

/* ── Hero ─────────────────────────────────────────────────────────── */
function renderHero() {
    const meta = D.results_meta;
    const scheduled = meta.scheduled || 0;
    $('#export-date').textContent = `Data exported: ${new Date(D.export_date).toLocaleString()} · Results updated: ${meta.completed} of ${meta.total_matches} matches played`;

    const scorers = D.top_scorers.slice(0, 5);
    const scorersHtml = scorers.map(s =>
        `<div class="scorer">
            <span class="scorer-flag">${s.flag || ''}</span>
            <span class="scorer-name">${s.name}</span>
            <span class="scorer-goals">${s.goals}</span>
        </div>`
    ).join('');

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
            <div class="hero-stat-value">${scheduled}</div>
            <div class="hero-stat-label">Matches Left</div>
        </div>
        <div class="hero-stat hero-stat-wide">
            <div class="scorers-label">Top Scorers</div>
            <div class="scorers-list">${scorersHtml}</div>
        </div>
    `;
}

/* ── Standings Table ─────────────────────────────────────────────── */
let sortCol = 'points';
let sortAsc = false;

function renderStandings() {
    const tbody = $('#standings-body');
    const currentRankings = D.rankings[D.stages[D.stages.length - 1]] || [];

    const rows = [...currentRankings].sort((a, b) => {
        let va, vb;
        switch (sortCol) {
            case 'rank': va = a.rank; vb = b.rank; break;
            case 'user': va = a.user; vb = b.user; break;
            case 'points': va = a.points; vb = b.points; break;
            case 'exact': va = D.accuracy[a.user]?.exact || 0; vb = D.accuracy[b.user]?.exact || 0; break;
            case 'winner': va = (D.accuracy[a.user]?.correct_winner || 0) + (D.accuracy[a.user]?.winner_plus_diff || 0) + (D.accuracy[a.user]?.draw_pred_no_exact || 0); vb = (D.accuracy[b.user]?.correct_winner || 0) + (D.accuracy[b.user]?.winner_plus_diff || 0) + (D.accuracy[b.user]?.draw_pred_no_exact || 0); break;
            case 'missed': va = D.accuracy[a.user]?.missed || 0; vb = D.accuracy[b.user]?.missed || 0; break;
            default: va = a.points; vb = b.points;
        }
        if (typeof va === 'string') return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
        return sortAsc ? va - vb : vb - va;
    });

    tbody.innerHTML = rows.map(r => {
        const acc = D.accuracy[r.user] || {};
        const winnerCount = (acc.correct_winner || 0) + (acc.winner_plus_diff || 0) + (acc.draw_pred_no_exact || 0);
        const totalPlayed = acc.total_played || 0;

        return `<tr>
            <td><span class="rank-badge ${rankClass(r.rank)}">${r.rank}</span></td>
            <td class="user-name">${r.user}</td>
            <td class="points-value">${r.points}</td>
            <td>${acc.exact || 0}</td>
            <td>${winnerCount}</td>
            <td>${acc.missed || 0}</td>
            <td>${totalPlayed}</td>
        </tr>`;
    }).join('');
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

    const accent = getAccentColor();

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
            nameTextStyle: { color: '#565f89' },
            axisLabel: { color: '#9aa5ce' },
            splitLine: { lineStyle: { color: '#414868' } }
        },
        yAxis: {
            type: 'category',
            data: sorted.map(u => u.user).reverse(),
            axisLabel: {
                color: '#c0caf5',
                fontWeight: 600,
                fontSize: 13
            },
            axisLine: { lineStyle: { color: '#414868' } }
        },
        series: [{
            type: 'bar',
            data: sorted.map(u => ({
                value: u.points,
                itemStyle: { color: accent }
            })).reverse(),
            barWidth: 24,
            label: {
                show: true,
                position: 'right',
                formatter: p => `${p.value} pts`,
                color: '#c0caf5',
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
        const exact = acc.exact || 0;
        const correctWinner = (acc.correct_winner || 0) + (acc.winner_plus_diff || 0);
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
                    <div class="quality-stat-value stat-winner">${correctWinner}</div>
                    <div class="quality-stat-label">Winner</div>
                </div>
                <div class="quality-stat">
                    <div class="quality-stat-value stat-missed">${missed}</div>
                    <div class="quality-stat-label">Missed</div>
                </div>
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
    const scheduled = D.results_meta?.scheduled || 0;
    const explainer = $('#what-if-explainer');
    if (explainer) {
        explainer.textContent = `${scheduled} tournament match${scheduled !== 1 ? 'es' : ''} remaining. "Points possible" shows the maximum points each player can still earn from their pending predictions plus any bonus points still available.`;
    }

    grid.innerHTML = D.users.map(user => {
        const wi = D.what_if[user];
        const above = wi.above_users || [];

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
                    <div class="what-if-stat-value">${wi.points_possible}</div>
                    <div class="what-if-stat-label">Points Possible</div>
                </div>
                <div class="what-if-stat">
                    <div class="what-if-stat-value">${wi.max_possible}</div>
                    <div class="what-if-stat-label">Max Possible</div>
                </div>
            </div>
            <div class="what-if-verdict">${wi.verdict}</div>
            ${above.length > 0 ? `
            <div class="what-if-above">
                <h4>Users Above</h4>
                ${above.map(u => `
                    <div class="above-user">
                        <span>${u.user} (${u.current} pts)</span>
                        <span class="gap">${u.current - wi.current} pts ahead</span>
                    </div>
                `).join('')}
            </div>
            ` : ''}
        </div>`;
    }).join('');
}

/* ── Init ─────────────────────────────────────────────────────────── */
function init() {
    renderHero();
    renderStandings();
    renderRace(0);
    renderQuality();
    renderWhatIf();

    window.addEventListener('resize', () => {
        if (raceChart) raceChart.resize();
    });
}

document.addEventListener('DOMContentLoaded', init);
