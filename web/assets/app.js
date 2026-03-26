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
            if (target === 'learned') loadLearnedParsers();
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
        let rowNum = 0;
        tbody.innerHTML = data.lines.map((l) => {
            if (l.row_type === 'mixed_parent') {
                // Fila padre de caja mixta
                rowNum++;
                const labelBadge = l.label ? `<span class="badge badge-label">${esc(l.label)}</span>` : '';
                const parentRow = `
                    <tr class="row-mixed-parent">
                        <td>${rowNum}</td>
                        <td title="${esc(l.raw)}">CAJA MIXTA ${labelBadge}
                            <span class="mixed-desc">${esc(l.raw.substring(0, 55))}${l.raw.length > 55 ? '...' : ''}</span></td>
                        <td>${esc(l.species)}</td>
                        <td><strong>${l.num_varieties} variedades</strong></td>
                        <td>-</td>
                        <td>-</td>
                        <td>${l.stems || '-'}</td>
                        <td>-</td>
                        <td>$${num(l.line_total)}</td>
                        <td>-</td>
                        <td>-</td>
                    </tr>`;
                // Filas hijas
                const childRows = l.children.map(h => `
                    <tr class="row-mixed-child ${h.match_status === 'sin_match' ? 'row-sin-match' : ''}">
                        <td></td>
                        <td title="${esc(h.raw)}">↳ ${esc(h.raw.substring(0, 55))}${h.raw.length > 55 ? '...' : ''}</td>
                        <td>${esc(h.species)}</td>
                        <td><strong class="color-variety">${esc(h.variety)}</strong></td>
                        <td>${h.size || '-'}</td>
                        <td>${h.stems_per_bunch || '-'}</td>
                        <td>${h.stems || '-'}</td>
                        <td>$${num(h.price_per_stem)}</td>
                        <td>$${num(h.line_total)}</td>
                        <td>${h.articulo_id ? `<strong>${h.articulo_id}</strong> ${esc(h.articulo_name)}` : '<em>-</em>'}</td>
                        <td>${matchBadge(h.match_status, h.match_method)}</td>
                    </tr>`).join('');
                return parentRow + childRows;
            }
            // Línea normal
            rowNum++;
            return `
            <tr class="${l.match_status === 'sin_parser' ? 'row-sin-parser' : l.match_status !== 'ok' ? 'row-sin-match' : ''}">
                <td>${rowNum}</td>
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
            </tr>`;
        }).join('');
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
        tbody.innerHTML = list.map(s => {
            const raw = s.raw || `${s.species || ''} ${s.variety || ''} ${s.size || ''}CM ${s.stems_per_bunch || ''}U`;
            return `
            <tr>
                <td title="${esc(raw)}">${esc(raw.substring(0, 65))}${raw.length > 65 ? '...' : ''}</td>
                <td>${esc(s.invoice || '-')}</td>
                <td>${s.provider_id}</td>
                <td><strong>${esc(s.variety || '')}</strong></td>
                <td>${s.size || '-'}</td>
                <td>${s.articulo_id}</td>
                <td>${esc(s.articulo_name || '')}</td>
                <td>${originBadge(s.origen || '')}</td>
            </tr>`;
        }).join('');
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
                (s.raw || '').toLowerCase().includes(text) ||
                (s.invoice || '').toLowerCase().includes(text) ||
                (s.variety || '').toLowerCase().includes(text) ||
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

    // ═══════════════════════════════════════════════════════════════════════════
    // IMPORTACIÓN MASIVA
    // ═══════════════════════════════════════════════════════════════════════════

    const batchDropZone   = document.getElementById('batchDropZone');
    const batchZipInput   = document.getElementById('batchZipInput');
    const batchFolderInput = document.getElementById('batchFolderInput');
    const batchPdfInput   = document.getElementById('batchPdfInput');
    const batchUploadZone = document.getElementById('batch-upload-zone');
    const batchProgress   = document.getElementById('batch-progress');
    const batchResults    = document.getElementById('batch-results');

    let batchId = null;
    let batchPollingTimer = null;
    let batchAllResults = [];

    // Drag & drop — acepta ZIP, PDFs sueltos o carpetas
    if (batchDropZone) {
        batchDropZone.addEventListener('dragover', e => {
            e.preventDefault();
            batchDropZone.classList.add('drag-over');
        });
        batchDropZone.addEventListener('dragleave', () => batchDropZone.classList.remove('drag-over'));
        batchDropZone.addEventListener('drop', e => {
            e.preventDefault();
            batchDropZone.classList.remove('drag-over');
            const files = [...e.dataTransfer.files];
            if (files.length === 1 && files[0].name.toLowerCase().endsWith('.zip')) {
                batchUploadZip(files[0]);
            } else {
                const pdfs = files.filter(f => f.name.toLowerCase().endsWith('.pdf'));
                if (pdfs.length > 0) {
                    batchUploadPdfs(pdfs);
                } else {
                    alert('Arrastra archivos PDF o un ZIP');
                }
            }
        });
    }

    // Botón ZIP
    document.getElementById('btnSelectZip').addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();
        batchZipInput.click();
    });
    batchZipInput.addEventListener('change', () => {
        if (batchZipInput.files[0]) batchUploadZip(batchZipInput.files[0]);
    });

    // Botón Carpeta
    document.getElementById('btnSelectFolder').addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();
        batchFolderInput.click();
    });
    batchFolderInput.addEventListener('change', () => {
        const pdfs = [...batchFolderInput.files].filter(f => f.name.toLowerCase().endsWith('.pdf'));
        if (pdfs.length > 0) {
            batchUploadPdfs(pdfs);
        } else {
            alert('La carpeta no contiene archivos PDF');
        }
    });

    // Botón PDFs sueltos
    document.getElementById('btnSelectPdfs').addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();
        batchPdfInput.click();
    });
    batchPdfInput.addEventListener('change', () => {
        const pdfs = [...batchPdfInput.files];
        if (pdfs.length > 0) batchUploadPdfs(pdfs);
    });

    async function batchUploadZip(file) {
        if (!file.name.toLowerCase().endsWith('.zip')) {
            alert('Selecciona un archivo .zip');
            return;
        }

        // Mostrar progreso
        batchUploadZone.classList.add('hidden');
        batchProgress.classList.remove('hidden');
        batchResults.classList.add('hidden');

        document.getElementById('batch-status-text').textContent = 'Subiendo ZIP...';
        document.getElementById('batch-progress-count').textContent = '';
        document.getElementById('batchProgressBar').style.width = '0%';
        document.getElementById('batch-current-pdf').textContent = file.name;
        document.getElementById('batch-ok-err').textContent = '';

        const form = new FormData();
        form.append('zip', file);

        try {
            const res = await fetch('api.php?action=batch_upload', { method: 'POST', body: form });
            const data = await res.json();

            if (!data.ok) {
                alert('Error: ' + data.error);
                batchReset();
                return;
            }

            batchId = data.batch_id;
            document.getElementById('batch-status-text').textContent = 'Procesando...';
            document.getElementById('batch-progress-count').textContent = `0 / ${data.total_pdfs}`;

            // Iniciar polling
            batchPollingTimer = setInterval(batchPollStatus, 2000);

        } catch (err) {
            alert('Error de conexión: ' + err.message);
            batchReset();
        }
    }

    async function batchUploadPdfs(files) {
        batchUploadZone.classList.add('hidden');
        batchProgress.classList.remove('hidden');
        batchResults.classList.add('hidden');

        document.getElementById('batch-status-text').textContent = `Subiendo ${files.length} PDFs...`;
        document.getElementById('batch-progress-count').textContent = '';
        document.getElementById('batchProgressBar').style.width = '0%';
        document.getElementById('batch-current-pdf').textContent = '';
        document.getElementById('batch-ok-err').textContent = '';

        const form = new FormData();
        for (const f of files) {
            form.append('pdfs[]', f);
        }

        try {
            const res = await fetch('api.php?action=batch_upload_pdfs', { method: 'POST', body: form });
            const data = await res.json();

            if (!data.ok) {
                alert('Error: ' + data.error);
                batchReset();
                return;
            }

            batchId = data.batch_id;
            document.getElementById('batch-status-text').textContent = 'Procesando...';
            document.getElementById('batch-progress-count').textContent = `0 / ${data.total_pdfs}`;

            batchPollingTimer = setInterval(batchPollStatus, 2000);

        } catch (err) {
            alert('Error de conexión: ' + err.message);
            batchReset();
        }
    }

    async function batchPollStatus() {
        if (!batchId) return;

        try {
            const res = await fetch(`api.php?action=batch_status&batch_id=${batchId}`);
            const data = await res.json();

            if (!data.ok && data.error) {
                clearInterval(batchPollingTimer);
                alert('Error: ' + data.error);
                batchReset();
                return;
            }

            // Actualizar barra
            const pct = data.porcentaje || 0;
            document.getElementById('batchProgressBar').style.width = pct + '%';
            document.getElementById('batch-progress-count').textContent =
                `${data.progreso || 0} / ${data.total || 0}`;
            document.getElementById('batch-current-pdf').textContent = data.actual || '';
            document.getElementById('batch-ok-err').textContent =
                `OK: ${data.procesados_ok || 0} | Errores: ${data.con_error || 0}`;

            const statusMap = {
                'iniciando': 'Iniciando...',
                'cargando_datos': 'Cargando artículos y sinónimos...',
                'procesando': 'Procesando facturas...',
                'generando_excel': 'Generando Excel...',
            };
            document.getElementById('batch-status-text').textContent =
                statusMap[data.estado] || data.estado;

            // ¿Completado?
            if (data.estado === 'completado') {
                clearInterval(batchPollingTimer);
                batchShowResults(data);
            } else if (data.estado === 'error') {
                clearInterval(batchPollingTimer);
                alert('Error en el procesamiento: ' + (data.error || 'desconocido'));
                batchReset();
            }

        } catch (err) {
            // Silenciar errores de red durante polling
        }
    }

    function batchShowResults(data) {
        batchProgress.classList.add('hidden');
        batchResults.classList.remove('hidden');

        const r = data.resumen;
        batchAllResults = data.resultados || [];

        // Tarjetas resumen
        document.getElementById('batchSummary').innerHTML = `
            <div class="stat-card success">
                <div class="stat-value">${r.total_facturas}</div>
                <div class="stat-label">Facturas</div>
            </div>
            <div class="stat-card success">
                <div class="stat-value">${r.procesadas_ok}</div>
                <div class="stat-label">Procesadas</div>
            </div>
            ${r.con_error > 0 ? `<div class="stat-card danger">
                <div class="stat-value">${r.con_error}</div>
                <div class="stat-label">Con Error</div>
            </div>` : ''}
            <div class="stat-card primary">
                <div class="stat-value">${r.total_lineas}</div>
                <div class="stat-label">Líneas</div>
            </div>
            <div class="stat-card success">
                <div class="stat-value">${r.total_ok}</div>
                <div class="stat-label">Matcheadas</div>
            </div>
            ${r.total_sin_match > 0 ? `<div class="stat-card danger">
                <div class="stat-value">${r.total_sin_match}</div>
                <div class="stat-label">Sin Match</div>
            </div>` : ''}
            <div class="stat-card primary">
                <div class="stat-value">$${Number(r.total_usd).toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
                <div class="stat-label">Total USD</div>
            </div>
        `;

        // Llenar filtro de facturas
        const sel = document.getElementById('batchFilterInvoice');
        sel.innerHTML = '<option value="">Todas las facturas</option>';
        batchAllResults.forEach(r => {
            if (r.ok) {
                sel.innerHTML += `<option value="${esc(r.pdf)}">${esc(r.pdf)} — ${esc(r.provider)}</option>`;
            }
        });

        batchRenderTable(batchAllResults);
    }

    function batchRenderTable(list) {
        const tbody = document.querySelector('#batchTable tbody');
        tbody.innerHTML = list.map((r, i) => {
            let status, statusClass;
            if (!r.ok) {
                status = 'ERROR'; statusClass = 'badge badge-sin-match';
            } else if (r.sin_match > 0) {
                status = 'PARCIAL'; statusClass = 'badge badge-fuzzy';
            } else {
                status = 'OK'; statusClass = 'badge badge-ok';
            }
            return `
                <tr class="${!r.ok ? 'row-sin-match' : r.sin_match > 0 ? 'row-partial' : ''}">
                    <td>${i + 1}</td>
                    <td>${esc(r.pdf)}</td>
                    <td>${esc(r.provider || '-')}</td>
                    <td>${esc(r.invoice || '-')}</td>
                    <td>${esc(r.date || '-')}</td>
                    <td>${r.lineas || 0}</td>
                    <td>${r.ok_count || 0}</td>
                    <td>${r.sin_match || 0}</td>
                    <td>$${num(r.total_usd || 0)}</td>
                    <td><span class="${statusClass}">${status}</span>${!r.ok ? `<br><small>${esc(r.error)}</small>` : ''}</td>
                </tr>
            `;
        }).join('');
    }

    // Filtros batch
    function batchFilter() {
        const invFilter  = document.getElementById('batchFilterInvoice').value;
        const statFilter = document.getElementById('batchFilterStatus').value;
        const textFilter = document.getElementById('batchFilterText').value.toLowerCase();

        let filtered = batchAllResults;

        if (invFilter) {
            filtered = filtered.filter(r => r.pdf === invFilter);
        }
        if (statFilter) {
            filtered = filtered.filter(r => {
                if (statFilter === 'ok') return r.ok && r.sin_match === 0;
                if (statFilter === 'parcial') return r.ok && r.sin_match > 0;
                if (statFilter === 'error') return !r.ok;
                return true;
            });
        }
        if (textFilter) {
            filtered = filtered.filter(r =>
                (r.pdf || '').toLowerCase().includes(textFilter) ||
                (r.provider || '').toLowerCase().includes(textFilter) ||
                (r.invoice || '').toLowerCase().includes(textFilter)
            );
        }

        batchRenderTable(filtered);
    }

    document.getElementById('batchFilterInvoice').addEventListener('change', batchFilter);
    document.getElementById('batchFilterStatus').addEventListener('change', batchFilter);
    document.getElementById('batchFilterText').addEventListener('input', batchFilter);

    // Botones
    document.getElementById('btnBatchExcel').addEventListener('click', () => {
        if (batchId) {
            window.location.href = `api.php?action=batch_download&batch_id=${batchId}`;
        }
    });

    document.getElementById('btnBatchNew').addEventListener('click', () => {
        batchReset();
    });

    function batchReset() {
        batchId = null;
        if (batchPollingTimer) clearInterval(batchPollingTimer);
        batchPollingTimer = null;
        batchAllResults = [];
        batchUploadZone.classList.remove('hidden');
        batchProgress.classList.add('hidden');
        batchResults.classList.add('hidden');
        batchZipInput.value = '';
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // AUTO-APRENDIZAJE
    // ═══════════════════════════════════════════════════════════════════════════

    async function loadLearnedParsers() {
        try {
            const [parsersRes, pendingRes] = await Promise.all([
                fetch('api.php?action=learned_parsers').then(r => r.json()),
                fetch('api.php?action=pending_review').then(r => r.json()),
            ]);

            if (parsersRes.ok) renderLearnedTable(parsersRes.parsers || []);
            if (pendingRes.ok) renderPendingTable(pendingRes.pendientes || []);
        } catch (err) {
            console.error('Error cargando parsers aprendidos:', err);
        }
    }

    function renderLearnedTable(parsers) {
        const tbody = document.querySelector('#learnedTable tbody');
        if (!parsers.length) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--text-muted)">No hay parsers auto-generados todavía</td></tr>';
            return;
        }
        tbody.innerHTML = parsers.map(p => {
            const scorePct = Math.round(p.score * 100);
            const decBadge = p.decision === 'VERDE'
                ? '<span class="badge badge-ok">VERDE</span>'
                : '<span class="badge badge-fuzzy">AMARILLO</span>';
            return `
                <tr>
                    <td><strong>${esc(p.nombre)}</strong></td>
                    <td>${esc(p.species)}</td>
                    <td>${scorePct}%</td>
                    <td>${decBadge}</td>
                    <td>${esc(p.fecha)}</td>
                    <td>${p.num_pdfs}</td>
                    <td><small>${esc((p.keywords || []).join(', '))}</small></td>
                    <td>${p.activo ? '<span class="badge badge-ok">Sí</span>' : '<span class="badge badge-sin-match">No</span>'}</td>
                    <td><button class="btn btn-secondary btn-sm" onclick="toggleParser('${esc(p.nombre)}')">${p.activo ? 'Desactivar' : 'Activar'}</button></td>
                </tr>`;
        }).join('');
    }

    function renderPendingTable(pending) {
        const tbody = document.querySelector('#pendingTable tbody');
        if (!pending.length) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">No hay revisiones pendientes</td></tr>';
            return;
        }
        tbody.innerHTML = pending.map(p => `
            <tr class="row-partial">
                <td><strong>${esc(p.proveedor)}</strong></td>
                <td>${Math.round(p.score * 100)}%</td>
                <td>${esc(p.razon)}</td>
                <td>${(p.pdfs || []).length}</td>
                <td>${esc(p.fecha)}</td>
                <td><em>${esc(p.accion_sugerida)}</em></td>
            </tr>`).join('');
    }

    // Expose globally for onclick
    window.toggleParser = async function(nombre) {
        try {
            const res = await fetch('api.php?action=toggle_parser', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({nombre}),
            });
            const data = await res.json();
            if (data.ok) {
                loadLearnedParsers();
            } else {
                alert('Error: ' + data.error);
            }
        } catch (err) {
            alert('Error de conexión');
        }
    };
});
