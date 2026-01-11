const form = document.getElementById('analysis-filter');
const i18n = window.ANALYSIS_I18N || {};
const mainLabel = i18n.mainLabel || '主号频次';
const bonusLabel = i18n.bonusLabel || 'Bonus 频次';
const distributionLabel = i18n.distributionLabel || '分布';
let charts = {};
const rootStyle = getComputedStyle(document.body || document.documentElement);
const chartPrimary = rootStyle.getPropertyValue('--chart-primary').trim() || 'rgba(13, 110, 253, 0.6)';
const chartAccent = rootStyle.getPropertyValue('--chart-accent').trim() || 'rgba(25, 135, 84, 0.6)';

function buildBarChart(ctx, labels, data, label) {
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: chartPrimary,
            }],
        },
        options: {
            responsive: true,
            scales: {
                x: { ticks: { maxRotation: 0, autoSkip: true } },
                y: { beginAtZero: true },
            },
        },
    });
}

function buildLineChart(ctx, labels, series) {
    const datasets = series.map((item, idx) => ({
        label: `#${item.number}`,
        data: item.values,
        borderColor: `hsl(${(idx * 60) % 360}, 70%, 45%)`,
        tension: 0.2,
        fill: false,
    }));

    return new Chart(ctx, {
        type: 'line',
        data: { labels: labels, datasets },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true },
            },
        },
    });
}

function buildHistogramChart(ctx, labels, data) {
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: distributionLabel,
                data: data,
                backgroundColor: chartAccent,
            }],
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true },
            },
        },
    });
}

function updateCharts(payload) {
    const mainLabels = payload.main_frequency.map(item => item.number);
    const mainData = payload.main_frequency.map(item => item.count);
    const bonusLabels = payload.bonus_frequency.map(item => item.number);
    const bonusData = payload.bonus_frequency.map(item => item.count);

    const rollingLabels = payload.rolling_series.labels;
    const rollingSeries = payload.rolling_series.series;

    const sumLabels = payload.sum_distribution.map(item => `${item.bin_start}+`);
    const sumData = payload.sum_distribution.map(item => item.count);

    if (charts.main) charts.main.destroy();
    if (charts.bonus) charts.bonus.destroy();
    if (charts.rolling) charts.rolling.destroy();
    if (charts.sum) charts.sum.destroy();

    charts.main = buildBarChart(document.getElementById('mainFrequencyChart'), mainLabels, mainData, mainLabel);
    charts.bonus = buildBarChart(document.getElementById('bonusFrequencyChart'), bonusLabels, bonusData, bonusLabel);
    charts.rolling = buildLineChart(document.getElementById('rollingChart'), rollingLabels, rollingSeries);
    charts.sum = buildHistogramChart(document.getElementById('sumDistributionChart'), sumLabels, sumData);
}

function fetchAnalysis(params = {}) {
    const query = new URLSearchParams(params);
    fetch(`/api/analysis/?${query.toString()}`)
        .then(res => res.json())
        .then(updateCharts)
        .catch(err => console.error('analysis error', err));
}

if (form) {
    form.addEventListener('submit', event => {
        event.preventDefault();
        const data = new FormData(form);
        const defaultWindow = form.dataset.default || 1000;
        const params = {
            window: data.get('window') || defaultWindow,
            start_date: data.get('start_date'),
            end_date: data.get('end_date'),
        };
        fetchAnalysis(params);
    });
}

const initialWindow = form ? (form.dataset.default || 1000) : 1000;
fetchAnalysis({ window: initialWindow });
