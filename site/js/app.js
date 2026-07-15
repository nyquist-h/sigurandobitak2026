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

function getAccent2Color() {
    return getComputedStyle(document.documentElement).getPropertyValue('--accent-2').trim();
}

/* ── My Stats Mode ────────────────────────────────────────────────── */
let myPlayer = localStorage.getItem('kicktipp.myPlayer') || '';

function setMyPlayer(user) {
    myPlayer = user;
    localStorage.setItem('kicktipp.myPlayer', user);
    const raceSelect = $('#race-player-select');
    if (raceSelect) {
        raceSelect.value = user;
        raceSelectedPlayer = user;
        renderRace(raceStageIndex);
    }
    applyMyHighlight();
}

function applyMyHighlight() {
    $$('.is-me').forEach(el => el.classList.remove('is-me'));
    if (!myPlayer) return;
    const escaped = myPlayer.replace(/[^a-zA-Z0-9]/g, '_');
    $$(`[data-user="${myPlayer}"]`).forEach(el => el.classList.add('is-me'));
    $$(`#donut-${escaped}`).forEach(el => {
        el.closest('.quality-card')?.classList.add('is-me');
    });
    $$('.standing-card').forEach(el => {
        if (el.dataset.user === myPlayer) el.classList.add('is-me');
    });
    $$('.quality-card').forEach(el => {
        if (el.dataset.user === myPlayer) el.classList.add('is-me');
    });
    $$('.what-if-card').forEach(el => {
        if (el.dataset.user === myPlayer) el.classList.add('is-me');
    });
    $('#standings-table tbody tr').forEach(tr => {
        if (tr.dataset.user === myPlayer) tr.classList.add('is-me');
    });
}

/* ── Reduced Motion ───────────────────────────────────────────────── */
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ── Hero ─────────────────────────────────────────────────────────── */
function animateCounter(element, target, duration = 1500) {
    if (prefersReducedMotion) {
        element.textContent = target;
        return;
    }
    const start = 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(start + (target - start) * eased);
        element.textContent = current;
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

function renderHero() {
    const meta = D.results_meta;
    const scheduled = meta.scheduled || 0;
    $('#export-date').textContent = `Data exported: ${new Date(D.export_date).toLocaleString()} · Results updated: ${meta.completed} of ${meta.total_matches} matches played`;

    const currentRankings = D.rankings[D.stages[D.stages.length - 1]] || [];
    const leader = currentRankings[0];

    /* Chips */
    const chipsHtml = [];
    if (meta.wc_winner_determined) {
        chipsHtml.push(`<span class="hero-chip hero-chip-success">🏆 WC Winner: ${meta.wc_winner || 'TBD'}</span>`);
    }
    if (D.top_scorers.length > 0) {
        const ts = D.top_scorers[0];
        chipsHtml.push(`<span class="hero-chip hero-chip-accent">${ts.flag || '⚽'} Top Scorer: ${ts.name} (${ts.goals}g)</span>`);
    }
    if (scheduled > 0) {
        chipsHtml.push(`<span class="hero-chip">${scheduled} match${scheduled !== 1 ? 'es' : ''} left</span>`);
    }
    $('#hero-chips').innerHTML = chipsHtml.join('');

    /* Stats */
    const stats = $('#hero-stats');
    stats.innerHTML = `
        <div class="hero-stat">
            <div class="hero-stat-value" id="counter-players">${D.users.length}</div>
            <div class="hero-stat-label">Players</div>
        </div>
        <div class="hero-stat">
            <div class="hero-stat-value" id="counter-matches">${meta.completed}</div>
            <div class="hero-stat-label">Matches Played</div>
        </div>
        <div class="hero-stat">
            <div class="hero-stat-value" id="counter-leader">${leader?.points || 0}</div>
            <div class="hero-stat-label">Leader Points</div>
        </div>
    `;

    /* Leader card */
    if (leader) {
        const acc = D.accuracy[leader.user] || {};
        $('#hero-leader').innerHTML = `
            <div class="hero-leader-badge">1</div>
            <div class="hero-leader-info">
                <div class="hero-leader-name">${leader.user}</div>
                <div class="hero-leader-pts">${leader.points} pts · ${acc.exact || 0} exact · ${(acc.correct_winner || 0) + (acc.winner_plus_diff || 0) + (acc.draw_pred_no_exact || 0)} winner</div>
                <div class="hero-leader-max">Max possible: ${D.what_if[leader.user]?.max_possible || '—'}</div>
            </div>
        `;
    }

    /* Scorers scroll */
    const scorers = D.top_scorers.slice(0, 8);
    $('#scorers-scroll').innerHTML = scorers.map(s =>
        `<span class="scorer-chip">
            <span class="scorer-flag">${s.flag || ''}</span>
            <span>${s.name}</span>
            <span class="scorer-goals">${s.goals}g</span>
        </span>`
    ).join('');

    /* Counters */
    animateCounter($('#counter-players'), D.users.length, 1000);
    animateCounter($('#counter-matches'), meta.completed, 1200);
    animateCounter($('#counter-leader'), leader?.points || 0, 1500);
}

/* ── My Stats Selector ────────────────────────────────────────────── */
function initMyStatsSelector() {
    const select = $('#my-stats-select');
    D.users.forEach(user => {
        const opt = document.createElement('option');
        opt.value = user;
        opt.textContent = user;
        select.appendChild(opt);
    });
    if (myPlayer && D.users.includes(myPlayer)) {
        select.value = myPlayer;
    }
    select.addEventListener('change', (e) => setMyPlayer(e.target.value));
}

/* ── Standings Table ─────────────────────────────────────────────── */
let sortCol = 'points';
let sortAsc = false;

function renderStandings() {
    const tbody = $('#standings-body');
    const cardsList = $('#standings-cards');
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

    /* Update sort arrows */
    $$('th.sortable').forEach(th => {
        th.classList.remove('sorted');
        const arrow = th.querySelector('.sort-arrow');
        if (arrow) arrow.textContent = '';
    });
    const activeTh = $(`th.sortable[data-col="${sortCol}"]`);
    if (activeTh) {
        activeTh.classList.add('sorted');
        const arrow = activeTh.querySelector('.sort-arrow');
        if (arrow) arrow.textContent = sortAsc ? '▲' : '▼';
    }

    /* Table rows (desktop) */
    tbody.innerHTML = rows.map(r => {
        const acc = D.accuracy[r.user] || {};
        const winnerCount = (acc.correct_winner || 0) + (acc.winner_plus_diff || 0) + (acc.draw_pred_no_exact || 0);
        const totalPlayed = D.results_meta?.completed || 0;
        const totalPredicted = acc.total_predicted || 0;
        const noPrediction = totalPlayed - totalPredicted;

        return `<tr data-user="${r.user}">
            <td><span class="rank-badge ${rankClass(r.rank)}">${r.rank}</span></td>
            <td class="user-name">${r.user}</td>
            <td class="points-value">${r.points}</td>
            <td>${acc.exact || 0}</td>
            <td>${winnerCount}</td>
            <td>${acc.missed || 0}</td>
            <td>${totalPlayed}</td>
            <td>${noPrediction > 0 ? noPrediction : '—'}</td>
        </tr>`;
    }).join('');

    /* Cards (mobile) */
    cardsList.innerHTML = rows.map(r => {
        const acc = D.accuracy[r.user] || {};
        const winnerCount = (acc.correct_winner || 0) + (acc.winner_plus_diff || 0) + (acc.draw_pred_no_exact || 0);
        const totalPlayed = D.results_meta?.completed || 0;
        const totalPredicted = acc.total_predicted || 0;
        const noPrediction = totalPlayed - totalPredicted;
        const fourPointers = acc.four_pointers || [];

        return `<li class="standing-card" data-user="${r.user}">
            <div class="standing-card-top">
                <span class="rank-badge ${rankClass(r.rank)}">${r.rank}</span>
                <span class="standing-card-name">${r.user}</span>
                <span class="standing-card-points">${r.points}</span>
            </div>
            <div class="standing-card-pills">
                <span class="standing-pill standing-pill-exact">✓ ${acc.exact || 0}</span>
                <span class="standing-pill standing-pill-winner">W ${winnerCount}</span>
                <span class="standing-pill standing-pill-missed">✗ ${acc.missed || 0}</span>
                ${noPrediction > 0 ? `<span class="standing-pill standing-pill-nopred">— ${noPrediction}</span>` : ''}
            </div>
            <details class="standing-card-detail">
                <summary>Details</summary>
                <div class="standing-detail-row"><span>Total predicted</span><span>${totalPredicted}</span></div>
                <div class="standing-detail-row"><span>Exact draws</span><span>${acc.exact_draw || 0}</span></div>
                <div class="standing-detail-row"><span>Winner + diff</span><span>${acc.winner_plus_diff || 0}</span></div>
                <div class="standing-detail-row"><span>Correct winner</span><span>${acc.correct_winner || 0}</span></div>
                <div class="standing-detail-row"><span>Draw predicted</span><span>${acc.draw_pred_no_exact || 0}</span></div>
                ${fourPointers.length > 0 ? `<div class="standing-detail-row"><span>4-pointers</span><span>${fourPointers.length}</span></div>` : ''}
            </details>
        </li>`;
    }).join('');

    applyMyHighlight();
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
let raceSelectedPlayer = '';

function renderRace(stageIdx) {
    if (!raceChart) {
        raceChart = echarts.init($('#race-chart'));
    }

    const stage = D.timeline[stageIdx];
    const sorted = [...stage.users].sort((a, b) => b.points - a.points);

    $('#race-stage-label').textContent = stage.label;

    const scrubber = $('#race-scrubber');
    if (scrubber) {
        scrubber.max = D.timeline.length - 1;
        scrubber.value = stageIdx;
    }

    const accent = getAccentColor();
    const highlightColor = '#ff3b30';

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
            nameTextStyle: { color: '#86868b' },
            axisLabel: { color: '#6e6e73' },
            splitLine: { lineStyle: { color: '#e5e5ea' } }
        },
        yAxis: {
            type: 'category',
            data: sorted.map(u => u.user).reverse(),
            axisLabel: {
                color: '#1d1d1f',
                fontWeight: 600,
                fontSize: 13
            },
            axisLine: { lineStyle: { color: '#e5e5ea' } }
        },
        series: [{
            type: 'bar',
            data: sorted.map(u => ({
                value: u.points,
                itemStyle: {
                    color: u.user === raceSelectedPlayer ? highlightColor : accent
                }
            })).reverse(),
            barWidth: 24,
            label: {
                show: true,
                position: 'right',
                formatter: p => `${p.value} pts`,
                color: '#1d1d1f',
                fontSize: 12
            },
            animationDuration: 500,
            animationEasing: 'cubicOut'
        }]
    };

    raceChart.setOption(option, true);
}

function populateRaceSelect() {
    const select = $('#race-player-select');
    D.users.forEach(user => {
        const opt = document.createElement('option');
        opt.value = user;
        opt.textContent = user;
        select.appendChild(opt);
    });
    if (myPlayer && D.users.includes(myPlayer)) {
        select.value = myPlayer;
        raceSelectedPlayer = myPlayer;
    }
}

$('#race-player-select').addEventListener('change', (e) => {
    raceSelectedPlayer = e.target.value;
    renderRace(raceStageIndex);
});

$('#race-scrubber').addEventListener('input', (e) => {
    raceStageIndex = parseInt(e.target.value, 10);
    renderRace(raceStageIndex);
});

function startRace() {
    if (raceInterval) return;
    if (prefersReducedMotion) {
        raceStageIndex = D.timeline.length - 1;
        renderRace(raceStageIndex);
        return;
    }
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
let qualityDonutCharts = [];

function renderQuality() {
    const grid = $('#quality-grid');
    const currentRankings = D.rankings[D.stages[D.stages.length - 1]] || [];
    const rankMap = {};
    currentRankings.forEach(r => rankMap[r.user] = r.rank);

    grid.innerHTML = D.users.map(user => {
        const acc = D.accuracy[user] || {};
        const rank = rankMap[user] || '—';
        const exact = acc.exact || 0;
        const winnerCount = (acc.correct_winner || 0) + (acc.winner_plus_diff || 0) + (acc.draw_pred_no_exact || 0);
        const missed = acc.missed || 0;

        const fourPointers = acc.four_pointers || [];

        return `<div class="quality-card" data-user="${user}">
            <div class="quality-header">
                <span class="quality-name">${user}</span>
                <span class="quality-rank">Rank #${rank}</span>
            </div>
            <div class="quality-body">
                <div class="quality-donut" id="donut-${user.replace(/[^a-zA-Z0-9]/g, '_')}"></div>
                <div class="quality-stats">
                    <div class="quality-stat">
                        <div class="quality-stat-value stat-exact">${exact}</div>
                        <div class="quality-stat-label">Exact</div>
                    </div>
                    <div class="quality-stat">
                        <div class="quality-stat-value stat-winner">${winnerCount}</div>
                        <div class="quality-stat-label">Winner</div>
                    </div>
                    <div class="quality-stat">
                        <div class="quality-stat-value stat-missed">${missed}</div>
                        <div class="quality-stat-label">Missed</div>
                    </div>
                </div>
            </div>
            <div class="quality-donut-legend">
                <div class="quality-donut-legend-item">
                    <span class="quality-donut-dot dot-exact"></span>
                    <span>Exact</span>
                </div>
                <div class="quality-donut-legend-item">
                    <span class="quality-donut-dot dot-partial"></span>
                    <span>Partial</span>
                </div>
                <div class="quality-donut-legend-item">
                    <span class="quality-donut-dot dot-wrong"></span>
                    <span>Wrong</span>
                </div>
            </div>
            ${fourPointers.length > 0 ? `
            <details class="quality-four-pointers">
                <summary>4-Pointers (${fourPointers.length})</summary>
                ${fourPointers.map(fp => `
                    <div class="four-pointer">
                        <span class="match">${D.stage_labels[fp.stage] || fp.stage}: ${fp.match}</span>
                        <span class="score">${fp.predicted} ✓</span>
                    </div>
                `).join('')}
            </details>
            ` : ''}
        </div>`;
    }).join('');

    qualityDonutCharts = [];
    D.users.forEach(user => {
        const sd = D.scoring_distribution[user] || {};
        const exact = sd.exact || 0;
        const partial = (sd.winner_plus_diff || 0) + (sd.draw_pred_no_exact || 0) + (sd.correct_winner || 0);
        const wrong = sd.missed || 0;

        const chartId = `donut-${user.replace(/[^a-zA-Z0-9]/g, '_')}`;
        const chart = echarts.init(document.getElementById(chartId));
        qualityDonutCharts.push(chart);

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'item',
                formatter: '{b}: {c} ({d}%)'
            },
            series: [{
                type: 'pie',
                radius: ['50%', '75%'],
                avoidLabelOverlap: false,
                label: { show: false },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 11,
                        fontWeight: 'bold',
                        color: '#1d1d1f'
                    }
                },
                labelLine: { show: false },
                data: [
                    { value: exact, name: 'Exact', itemStyle: { color: '#34c759' } },
                    { value: partial, name: 'Partial', itemStyle: { color: '#0071e3' } },
                    { value: wrong, name: 'Wrong', itemStyle: { color: '#ff3b30' } }
                ]
            }]
        };

        chart.setOption(option, true);
    });

    applyMyHighlight();
}

/* ── What's Needed to Win ─────────────────────────────────────────── */
let whatIfFilter = 'all';

function renderWhatIf() {
    const grid = $('#what-if-grid');
    const scheduled = D.results_meta?.scheduled || 0;
    const explainer = $('#what-if-explainer');
    if (explainer) {
        explainer.textContent = `${scheduled} tournament match${scheduled !== 1 ? 'es' : ''} remaining (12 pts max). "Points possible" shows 12 pts from remaining games plus up to 20 bonus pts (WC winner + top scorer) if the user's picks are still in contention.`;
    }

    let users = D.users;
    if (whatIfFilter !== 'all') {
        users = users.filter(u => D.what_if[u]?.status === whatIfFilter);
    }

    grid.innerHTML = users.map(user => {
        const wi = D.what_if[user];
        const above = wi.above_users || [];

        return `<div class="what-if-card ${wi.status === 'leading' ? 'leading' : ''}" data-user="${user}">
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

    applyMyHighlight();
}

/* What-if filter tabs */
$$('.what-if-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        $$('.what-if-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        whatIfFilter = tab.dataset.filter;
        renderWhatIf();
    });
});

/* ── Scroll Spy for Bottom Tabs ─────────────────────────────────── */
function initScrollSpy() {
    const sections = ['standings', 'race', 'quality', 'what-if'];
    const tabItems = $$('.tab-item');
    const navLinks = $$('.nav-links a');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const id = entry.target.id;
                tabItems.forEach(t => t.classList.toggle('active', t.dataset.section === id));
                navLinks.forEach(a => {
                    const href = a.getAttribute('href').replace('#', '');
                    a.classList.toggle('active', href === id);
                });
            }
        });
    }, {
        rootMargin: '-20% 0px -60% 0px',
        threshold: 0
    });

    sections.forEach(id => {
        const el = document.getElementById(id);
        if (el) observer.observe(el);
    });
}

/* ── Init ─────────────────────────────────────────────────────────── */
function init() {
    renderHero();
    initMyStatsSelector();
    renderStandings();
    populateRaceSelect();
    renderRace(0);
    renderQuality();
    renderWhatIf();
    initScrollSpy();

    window.addEventListener('resize', () => {
        if (raceChart) raceChart.resize();
        qualityDonutCharts.forEach(c => c.resize());
    });
}

document.addEventListener('DOMContentLoaded', init);
