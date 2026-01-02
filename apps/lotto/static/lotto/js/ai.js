const form = document.getElementById('ai-filter');
const heatmap = document.getElementById('ai-heatmap');
const topContainer = document.getElementById('ai-top');
const metaContainer = document.getElementById('ai-meta');
const i18n = window.AI_I18N || {};

function renderHeatmap(probabilities) {
    if (!heatmap) return;
    heatmap.innerHTML = '';
    const maxProb = Math.max(...probabilities.map(item => item.probability), 0.01);
    probabilities.forEach(item => {
        const cell = document.createElement('div');
        cell.className = 'ai-cell';
        const intensity = Math.min(item.probability / maxProb, 1);
        const alpha = 0.12 + intensity * 0.78;
        cell.style.backgroundColor = `rgba(11, 79, 140, ${alpha.toFixed(3)})`;
        cell.style.color = intensity > 0.55 ? '#ffffff' : '#1b2b38';
        const probText = `${(item.probability * 100).toFixed(1)}%`;
        cell.innerHTML = `<span class="ai-number">${item.number}</span><span class="ai-prob">${probText}</span>`;
        heatmap.appendChild(cell);
    });
}

function renderTop(numbers) {
    if (!topContainer) return;
    topContainer.innerHTML = '';
    numbers.forEach(num => {
        const badge = document.createElement('span');
        badge.className = 'badge rounded-pill bg-primary';
        badge.textContent = num;
        topContainer.appendChild(badge);
    });
}

function renderMeta(meta) {
    if (!metaContainer || !meta) return;
    const template = i18n.meta || 'Draws: {draws}, Samples: {samples}, Hidden: {hidden}, Epochs: {epochs}';
    metaContainer.textContent = template
        .replace('{draws}', meta.draws_used)
        .replace('{samples}', meta.samples)
        .replace('{hidden}', meta.hidden_size)
        .replace('{epochs}', meta.epochs);
}

function fetchAI(params = {}) {
    if (heatmap) {
        heatmap.innerHTML = `<div class="text-muted small">${i18n.loading || '加载中...'}</div>`;
    }
    const query = new URLSearchParams(params);
    fetch(`/api/ai/?${query.toString()}`)
        .then(res => res.json())
        .then(data => {
            renderHeatmap(data.probabilities || []);
            renderTop(data.top_numbers || []);
            renderMeta(data.meta || {});
        })
        .catch(err => console.error('ai error', err));
}

if (form) {
    form.addEventListener('submit', event => {
        event.preventDefault();
        const data = new FormData(form);
        const defaultWindow = form.dataset.default || 1000;
        const params = {
            window: data.get('window') || defaultWindow,
        };
        fetchAI(params);
    });
}

const initialWindow = form ? (form.dataset.default || 1000) : 1000;
fetchAI({ window: initialWindow });
