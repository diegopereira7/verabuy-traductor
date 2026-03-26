/**
 * VeraBuy Traductor Web - Frontend
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- Navigation ---
    const navBtns = document.querySelectorAll('.nav-btn');
    const tabs = document.querySelectorAll('.tab');

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.tab;
            navBtns.forEach(b => b.classList.remove('active'));
            tabs.forEach(t => {
                t.classList.remove('active');
                t.classList.add('hidden');
            });
            btn.classList.add('active');
            const tab = document.getElementById('tab-' + target);
            tab.classList.remove('hidden');
            tab.classList.add('active');

            // Load data on tab switch
            if (target === 'history') loadHistory();
            if (target === 'synonyms') loadSynonyms();
        });
    });

    // --- File Upload ---
    const dropZone = document.getElementById('dropZone');
    const pdfInput = document.getElementById('pdfInput');
    const btnSelect = document.getElementById('btnSelectFile');
    const processing = document.getElementById('processing');
    const resultSection = document.getElementById('resultSection');
    const btnNewUpload = document.getElementById('btnNewUpload');

    btnSelect.addEventListener('click', (e) => {
        e.stopPropagation();
        pdfInput.click();
    });

    dropZone.addEventListener('click', () => pdfInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0 && files[0].type === 'application/pdf') {
            processFile(files[0]);
        }
    });

    pdfInput.addEventListener('change', () => {
        if (pdfInput.files.length > 0) {
            processFile(pdfInput.files[0]);
        }
    });

    btnNewUpload.addEventListener('click', resetUpload);

    function resetUpload() {
        pdfInput.value = '';
        dropZone.classList.remove('hidden');
        processing.classList.add('hidden');
        resultSection.classList.add('hidden');
    }

    async function processFile(file) {
        dropZone.classList.add('hidden');
        processing.classList.remove('hidden');
        resultSection.classList.add('hidden');

        const formData = new FormData();
        formData.append('pdf', file);

        try {
            const resp = await fetch('api.php?action=process', {
                method: 'POST',
                body: formData
            });
            const data = await resp.json();

            processing.classList.add('hidden');

            if (!data.ok) {
                alert('Error: ' + (data.error || 'Error desconocido'));
                resetUpload();
                return;
            }

            renderResult(data);
            resultSection.classList.remove('hidden');
        } catch (err) {
            processing.classList.add('hidden');
            alert('Error de conexión: ' + err.message);
            resetUpload();
        }
    }

    // --- Render Invoice Result ---
    function renderResult(data) {
        const h = data.header;
        document.getElementById('invoiceHeader').innerHTML = `
            <div class="field">
                <span class="field-label">Proveedor</span>
                <span class="field-value">${esc(h.provider_name)}</span>
            </div>
            <div class="field">
                <span class="field-label">Factura</span>
                <span class="field-value">${esc(h.invoice_number)}</span>
            </div>
            <div class="field">
                <span class="field-label">Fecha</span>
                <span class="field-value">${esc(h.date)}</span>
            </div>
            <div class="field">
                <span class="field-label">AWB</span>
                <span class="field-value">${esc(h.awb)}</span>
            </div>
            <div class="field">
                <span class="field-label">Total USD</span>
                <span class="field-value">$${num(h.total)}</span>
            </div>
            <div class="field">
                <span class="field-label">ID Proveedor</span>
                <span class="field-value">${h.provider_id}</span>
            </div>
        `;

        const s = data.stats;
        const sinParser = s.sin_parser || 0;
        document.getElementById('statsBar').innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${s.total_lineas}</div>
                <div class="stat-label">Total Líneas</div>
            </div>
            <div class="stat-card success">
                <div class="stat-value">${s.ok}</div>
                <div class="stat-label">Matcheadas</div>
            </div>
            <div class="stat-card ${s.sin_match > 0 ? 'danger' : 'success'}">
                <div class="stat-value">${s.sin_match}</div>
                <div class="stat-label">Sin Match</div>
            </div>
            ${sinParser > 0 ? `
            <div class="stat-card warning">
                <div class="stat-value">${sinParser}</div>
                <div class="stat-label">No Parseadas</div>
            </div>` : ''}
        `;

        const tbody = document.querySelector('#linesTable tbody');
        tbody.innerHTML = data.lines.map((l, i) => `
            <tr class="${l.match_status === 'sin_parser' ? 'row-sin-parser' : l.match_status !== 'ok' ? 'row-sin-match' : ''}">
                <td>${i + 1}</td>
                <td title="${esc(l.raw)}">${esc(l.raw.substring(0, 60))}${l.raw.length > 60 ? '...' : ''}</td>
                <td>${esc(l.species)}</td>
                <td><strong>${esc(l.variety)}</strong></td>
                <td>${l.size || '-'}</td>
                <td>${l.stems_per_bunch || '-'}</td>
                <td>${l.stems || '-'}</td>
                <td>$${num(l.price_per_stem)}</td>
                <td>$${num(l.line_total)}</td>
                <td>${l.articulo_id ? `<strong>${l.articulo_id}</strong> ${esc(l.articulo_name)}` : '<em>-</em>'}</td>
                <td>${matchBadge(l.match_status, l.match_method)}</td>
            </tr>
        `).join('');
    }

    function matchBadge(status, method) {
        if (status === 'ok') {
            return `<span class="badge badge-ok" title="${esc(method)}">${esc(method)}</span>`;
        }
        if (status === 'sin_parser') {
            return '<span class="badge badge-sin-parser">NO PARSEADO</span>';
        }
        return '<span class="badge badge-sin-match">SIN MATCH</span>';
    }

    // --- History Tab ---
    async function loadHistory() {
        const loading = document.getElementById('historyLoading');
        loading.classList.remove('hidden');

        try {
            // Use GET with action parameter via query string workaround
            const resp = await fetch('api.php?action=history', { method: 'POST' });
            const data = await resp.json();

            loading.classList.add('hidden');

            if (!data.ok) return;

            const tbody = document.querySelector('#historyTable tbody');
            tbody.innerHTML = data.history.map(h => `
                <tr class="${(h.sin_match || 0) > 0 ? 'row-sin-match' : ''}">
                    <td>${esc(h.fecha || '')}</td>
                    <td>${esc(h.invoice_key || '')}</td>
                    <td>${esc(h.provider || '')}</td>
                    <td>${esc(h.pdf || '')}</td>
                    <td>${h.lineas || 0}</td>
                    <td>${h.ok || 0}</td>
                    <td>${h.sin_match || 0}</td>
                    <td>$${num(h.total_usd || 0)}</td>
                </tr>
            `).join('');
        } catch (err) {
            loading.classList.add('hidden');
        }
    }

    // --- Synonyms Tab ---
    let allSynonyms = [];

    async function loadSynonyms() {
        const loading = document.getElementById('synLoading');
        loading.classList.remove('hidden');

        try {
            const resp = await fetch('api.php?action=synonyms', { method: 'POST' });
            const data = await resp.json();

            loading.classList.add('hidden');

            if (!data.ok) return;

            allSynonyms = data.synonyms;
            renderSynonyms(allSynonyms);
        } catch (err) {
            loading.classList.add('hidden');
        }
    }

    function renderSynonyms(list) {
        document.getElementById('synCount').textContent = `${list.length} sinónimos`;

        const tbody = document.querySelector('#synTable tbody');
        tbody.innerHTML = list.map(s => `
            <tr>
                <td>${s.provider_id}</td>
                <td>${esc(s.species || '')}</td>
                <td><strong>${esc(s.variety || '')}</strong></td>
                <td>${s.size || '-'}</td>
                <td>${s.stems_per_bunch || '-'}</td>
                <td>${esc(s.grade || '-')}</td>
                <td>${s.articulo_id}</td>
                <td>${esc(s.articulo_name || '')}</td>
                <td>${originBadge(s.origen || '')}</td>
            </tr>
        `).join('');
    }

    function originBadge(origin) {
        const cls = origin.includes('fuzzy') ? 'badge-fuzzy' :
                    origin.includes('manual') ? 'badge-manual' : 'badge-auto';
        return `<span class="badge ${cls}">${esc(origin)}</span>`;
    }

    // Synonym filtering
    const synFilter = document.getElementById('synFilter');
    const synOriginFilter = document.getElementById('synOriginFilter');

    function filterSynonyms() {
        const text = synFilter.value.toLowerCase();
        const origin = synOriginFilter.value;

        const filtered = allSynonyms.filter(s => {
            const matchText = !text ||
                (s.variety || '').toLowerCase().includes(text) ||
                (s.species || '').toLowerCase().includes(text) ||
                (s.articulo_name || '').toLowerCase().includes(text) ||
                String(s.provider_id).includes(text);

            const matchOrigin = !origin || (s.origen || '').includes(origin);

            return matchText && matchOrigin;
        });

        renderSynonyms(filtered);
    }

    synFilter.addEventListener('input', filterSynonyms);
    synOriginFilter.addEventListener('change', filterSynonyms);

    // --- Utilities ---
    function esc(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }

    function num(val) {
        if (val === null || val === undefined) return '0.00';
        return Number(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 5 });
    }
});
