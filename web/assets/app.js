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
    let historyData = [];

    async function loadHistory() {
        const loading = document.getElementById('historyLoading');
        loading.classList.remove('hidden');

        try {
            const resp = await fetch('api.php?action=history', { method: 'POST' });
            const data = await resp.json();
            loading.classList.add('hidden');
            if (!data.ok) return;
            historyData = data.history;
            renderHistory();
        } catch (err) {
            loading.classList.add('hidden');
        }
    }

    function renderHistory() {
        const tbody = document.querySelector('#historyTable tbody');
        tbody.innerHTML = historyData.map((h, i) => {
            const hasPdf = !!(h.pdf);
            const needsReview = (h.sin_match || 0) > 0;
            const detailId = `hist-detail-${i}`;
            return `
                <tr class="${needsReview ? 'row-sin-match' : ''}" data-idx="${i}">
                    <td>${esc(h.fecha || '')}</td>
                    <td>${esc(h.invoice_key || '')}</td>
                    <td>${esc(h.provider || '')}</td>
                    <td>${esc(h.pdf || '')}</td>
                    <td>${h.lineas || 0}</td>
                    <td>${h.ok || 0}</td>
                    <td>${h.sin_match || 0}</td>
                    <td>$${num(h.total_usd || 0)}</td>
                    <td>${hasPdf ? `<button class="btn btn-sm btn-secondary hist-expand" data-pdf="${esc(h.pdf)}" data-detail="${detailId}">Ver líneas</button>` : '-'}</td>
                </tr>
                <tr id="${detailId}" class="batch-lines-row hidden">
                    <td colspan="9">
                        <div class="batch-lines-detail">
                            <div class="hist-detail-loading"><div class="spinner"></div> Reprocesando...</div>
                        </div>
                    </td>
                </tr>`;
        }).join('');
    }

    // Expandir historial: reprocesar PDF y mostrar líneas
    document.querySelector('#historyTable tbody').addEventListener('click', async e => {
        const expandBtn = e.target.closest('.hist-expand');
        if (expandBtn) {
            const detailId = expandBtn.dataset.detail;
            const detailRow = document.getElementById(detailId);
            if (!detailRow) return;

            // Toggle
            if (!detailRow.classList.contains('hidden') && detailRow.dataset.loaded) {
                detailRow.classList.add('hidden');
                expandBtn.textContent = 'Ver líneas';
                return;
            }

            detailRow.classList.remove('hidden');
            expandBtn.textContent = 'Ocultar';

            // Si ya está cargado, no reprocesar
            if (detailRow.dataset.loaded) return;

            // Reprocesar el PDF
            const pdf = expandBtn.dataset.pdf;
            try {
                const resp = await fetch('api.php?action=reprocess', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pdf }),
                });
                const data = await resp.json();
                detailRow.dataset.loaded = '1';

                if (!data.ok) {
                    detailRow.querySelector('.batch-lines-detail').innerHTML =
                        `<p style="color:var(--danger)">Error: ${esc(data.error)}</p>`;
                    return;
                }

                // Actualizar conteos de la fila padre con datos reales del reprocesado
                const parentRow = detailRow.previousElementSibling;
                if (parentRow && data.stats) {
                    const cells = parentRow.querySelectorAll('td');
                    cells[4].textContent = data.stats.total_lineas || 0;
                    cells[5].textContent = data.stats.ok || 0;
                    cells[6].textContent = data.stats.sin_match || 0;
                    if (data.stats.sin_match > 0) {
                        parentRow.classList.add('row-sin-match');
                    } else {
                        parentRow.classList.remove('row-sin-match');
                    }
                }

                const lines = data.lines || [];
                const needsReview = lines.some(l => l.match_status !== 'ok' && !l.row_type);
                const providerId = data.header?.provider_id || 0;

                detailRow.querySelector('.batch-lines-detail').innerHTML = `
                    <table class="batch-lines-table">
                        <thead><tr>
                            <th>Descripción</th><th>Variedad</th><th>Talla</th>
                            <th>Tallos</th><th>Total</th>
                            <th>ID Artículo</th><th>Nombre Artículo</th>
                            <th>Match</th>${needsReview ? '<th>Acción</th>' : ''}
                        </tr></thead>
                        <tbody>${lines.filter(l => !l.row_type).map(l => {
                            const isBad = l.match_status !== 'ok';
                            const key = `${providerId}|${l.species || ''}|${l.variety || ''}|${l.size || 0}|${l.stems_per_bunch || 0}|${l.grade || ''}`;
                            return `<tr class="${isBad ? 'row-sin-match' : ''}" data-syn-key="${esc(key)}" data-pdf="${esc(pdf)}">
                                <td title="${esc(l.raw || '')}">${esc((l.raw || '').substring(0, 50))}${(l.raw||'').length > 50 ? '...' : ''}</td>
                                <td><strong>${esc(l.variety || '')}</strong></td>
                                <td>${l.size || '-'}</td>
                                <td>${l.stems || '-'}</td>
                                <td>$${num(l.line_total || 0)}</td>
                                <td>${l.articulo_id || '-'}</td>
                                <td>${esc(l.articulo_name || '-')}</td>
                                <td>${matchBadge(l.match_status || '', l.match_method || '')}</td>
                                ${needsReview && isBad ? `<td>
                                    <input type="number" class="edit-input batch-art-id" placeholder="ID" style="width:65px">
                                    <button class="btn-icon batch-line-save" title="Guardar">&#10003;</button>
                                </td>` : (needsReview ? '<td></td>' : '')}
                            </tr>`;
                        }).join('')}</tbody>
                    </table>`;
            } catch (err) {
                detailRow.querySelector('.batch-lines-detail').innerHTML =
                    `<p style="color:var(--danger)">Error de conexión</p>`;
            }
        }

        // Guardar match (reutiliza la misma lógica que batch)
        const saveBtn = e.target.closest('.batch-line-save');
        if (saveBtn) {
            const tr = saveBtn.closest('tr');
            const input = tr.querySelector('.batch-art-id');
            const artId = parseInt(input.value) || 0;
            if (!artId) { alert('Introduce un ID de artículo'); return; }
            const synKey = tr.dataset.synKey;

            try {
                const lookupResp = await fetch(`api.php?action=lookup_article&id=${artId}`);
                const lookupData = await lookupResp.json();
                if (!lookupData.ok) { alert(lookupData.error); return; }

                const saveResp = await fetch('api.php?action=save_synonym', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ key: synKey, articulo_id: artId, articulo_name: lookupData.nombre }),
                });
                const saveData = await saveResp.json();
                if (saveData.ok) {
                    const cells = tr.querySelectorAll('td');
                    cells[5].textContent = artId;
                    cells[6].textContent = lookupData.nombre;
                    cells[7].innerHTML = '<span class="badge badge-manual">manual-web</span>';
                    tr.classList.remove('row-sin-match');
                    cells[cells.length - 1].innerHTML = '<span style="color:green">&#10003;</span>';
                } else {
                    alert('Error: ' + saveData.error);
                }
            } catch (err) { alert('Error de conexión'); }
        }
    });

    // --- Synonyms Tab ---
    let allSynonyms = [];
    let filteredSynonyms = [];
    let synPage = 1;
    const SYN_PER_PAGE = 50;
    let synEditingKey = null;

    async function loadSynonyms() {
        document.getElementById('synLoading').classList.remove('hidden');
        try {
            const resp = await fetch('api.php?action=synonyms', { method: 'POST' });
            const data = await resp.json();
            document.getElementById('synLoading').classList.add('hidden');
            if (!data.ok) return;
            allSynonyms = data.synonyms;
            synPage = 1;
            filterSynonyms();
        } catch (err) {
            document.getElementById('synLoading').classList.add('hidden');
        }
    }

    function renderSynBadges() {
        const counts = {};
        allSynonyms.forEach(s => {
            const o = s.origen || 'otro';
            counts[o] = (counts[o] || 0) + 1;
        });
        const active = document.getElementById('synOriginFilter').value;
        const badges = [{ key: '', label: 'Todos', count: allSynonyms.length }];
        for (const [k, c] of Object.entries(counts).sort((a, b) => b[1] - a[1])) {
            badges.push({ key: k, label: k, count: c });
        }
        document.getElementById('synBadges').innerHTML = badges.map(b => {
            const cls = b.key === active ? 'syn-badge active' : 'syn-badge';
            const color = b.key.includes('fuzzy') ? 'badge-fuzzy' :
                          b.key.includes('manual') ? 'badge-manual' :
                          b.key.includes('marca') ? 'badge-marca' :
                          b.key === '' ? '' : 'badge-auto';
            return `<span class="${cls} ${color}" data-origin="${esc(b.key)}">${esc(b.label)}: ${b.count}</span>`;
        }).join('');
    }

    // Badge clicks
    document.getElementById('synBadges').addEventListener('click', e => {
        const badge = e.target.closest('.syn-badge');
        if (!badge) return;
        const origin = badge.dataset.origin;
        document.getElementById('synOriginFilter').value = origin;
        synPage = 1;
        filterSynonyms();
    });

    function filterSynonyms() {
        const text = document.getElementById('synFilter').value.toLowerCase();
        const origin = document.getElementById('synOriginFilter').value;
        filteredSynonyms = allSynonyms.filter(s => {
            const matchText = !text ||
                (s.raw || '').toLowerCase().includes(text) ||
                (s.invoice || '').toLowerCase().includes(text) ||
                (s.variety || '').toLowerCase().includes(text) ||
                (s.articulo_name || '').toLowerCase().includes(text) ||
                (s.key || '').toLowerCase().includes(text) ||
                String(s.provider_id).includes(text);
            const matchOrigin = !origin || (s.origen || '').includes(origin);
            return matchText && matchOrigin;
        });
        renderSynBadges();
        renderSynPage();
    }

    function renderSynPage() {
        const total = filteredSynonyms.length;
        const totalPages = Math.max(1, Math.ceil(total / SYN_PER_PAGE));
        if (synPage > totalPages) synPage = totalPages;
        const start = (synPage - 1) * SYN_PER_PAGE;
        const page = filteredSynonyms.slice(start, start + SYN_PER_PAGE);

        document.getElementById('synCount').textContent =
            `${total} sinónimos` + (total !== allSynonyms.length ? ` (de ${allSynonyms.length})` : '');

        const tbody = document.querySelector('#synTable tbody');
        tbody.innerHTML = page.map(s => {
            const raw = s.raw || `${s.species || ''} ${s.variety || ''} ${s.size || ''}CM ${s.stems_per_bunch || ''}U`;
            return `
            <tr data-key="${esc(s.key || '')}">
                <td title="${esc(raw)}">${esc(raw.substring(0, 60))}${raw.length > 60 ? '...' : ''}</td>
                <td>${esc(s.invoice || '-')}</td>
                <td><strong>${esc(s.variety || '')}</strong></td>
                <td>${s.size || '-'}</td>
                <td>${s.stems_per_bunch || '-'}</td>
                <td>${s.articulo_id}</td>
                <td>${esc(s.articulo_name || '')}</td>
                <td>${originBadge(s.origen || '')}</td>
                <td class="syn-actions">
                    <button class="btn-icon syn-edit" title="Editar">&#9998;</button>
                    <button class="btn-icon syn-delete" title="Eliminar">&#10005;</button>
                </td>
            </tr>`;
        }).join('');

        // Paginación
        const pagHtml = totalPages <= 1 ? '' : _buildPagination(synPage, totalPages);
        document.getElementById('synPagination').innerHTML = pagHtml;
        document.getElementById('synPaginationBottom').innerHTML = pagHtml;
    }

    function _buildPagination(current, total) {
        let html = '<div class="pagination">';
        if (current > 1) html += `<button class="pag-btn" data-page="${current - 1}">&laquo;</button>`;
        const start = Math.max(1, current - 3);
        const end = Math.min(total, current + 3);
        for (let p = start; p <= end; p++) {
            html += `<button class="pag-btn ${p === current ? 'active' : ''}" data-page="${p}">${p}</button>`;
        }
        if (current < total) html += `<button class="pag-btn" data-page="${current + 1}">&raquo;</button>`;
        html += '</div>';
        return html;
    }

    // Pagination clicks
    document.addEventListener('click', e => {
        const btn = e.target.closest('.pag-btn');
        if (btn) {
            synPage = parseInt(btn.dataset.page);
            renderSynPage();
            document.getElementById('synTable').scrollIntoView({ behavior: 'smooth' });
        }
    });

    function originBadge(origin) {
        const cls = origin.includes('fuzzy') ? 'badge-fuzzy' :
                    origin.includes('manual') ? 'badge-manual' :
                    origin.includes('marca') ? 'badge-marca' : 'badge-auto';
        return `<span class="badge ${cls}">${esc(origin)}</span>`;
    }

    // --- Synonym Actions: Edit & Delete ---
    document.querySelector('#synTable tbody').addEventListener('click', e => {
        const row = e.target.closest('tr');
        if (!row) return;
        const key = row.dataset.key;

        if (e.target.closest('.syn-edit')) {
            synStartEdit(row, key);
        } else if (e.target.closest('.syn-delete')) {
            synDelete(key);
        } else if (e.target.closest('.syn-save')) {
            synSaveEdit(row, key);
        } else if (e.target.closest('.syn-cancel')) {
            renderSynPage();
        }
    });

    function synStartEdit(row, key) {
        const s = allSynonyms.find(x => x.key === key);
        if (!s) return;
        row.innerHTML = `
            <td colspan="2"><input class="edit-input" id="editKey" value="${esc(s.key || '')}" style="width:100%"></td>
            <td><input class="edit-input" id="editVariety" value="${esc(s.variety || '')}"></td>
            <td>${s.size || '-'}</td>
            <td>${s.stems_per_bunch || '-'}</td>
            <td><input class="edit-input" id="editArtId" value="${s.articulo_id}" type="number" style="width:70px"></td>
            <td><input class="edit-input" id="editArtName" value="${esc(s.articulo_name || '')}" style="width:100%"></td>
            <td>${originBadge(s.origen || '')}</td>
            <td class="syn-actions">
                <button class="btn-icon syn-save" title="Guardar" style="color:green">&#10003;</button>
                <button class="btn-icon syn-cancel" title="Cancelar" style="color:gray">&#10007;</button>
            </td>`;
        synEditingKey = key;
        // Auto-lookup: al cambiar ID artículo, buscar nombre
        document.getElementById('editArtId').addEventListener('change', async () => {
            const id = parseInt(document.getElementById('editArtId').value) || 0;
            if (!id) return;
            try {
                const res = await fetch(`api.php?action=lookup_article&id=${id}`);
                const data = await res.json();
                if (data.ok) {
                    document.getElementById('editArtName').value = data.nombre;
                }
            } catch (err) { /* silenciar */ }
        });
    }

    async function synSaveEdit(row, originalKey) {
        const newKey = document.getElementById('editKey').value.trim();
        const artId = parseInt(document.getElementById('editArtId').value) || 0;
        const artName = document.getElementById('editArtName').value.trim();

        if (!newKey || !artId) { alert('Clave e ID artículo son obligatorios'); return; }

        try {
            const res = await fetch('api.php?action=update_synonym', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    original_key: synEditingKey,
                    new_key: newKey,
                    articulo_id: artId,
                    articulo_name: artName,
                }),
            });
            const data = await res.json();
            if (data.ok) {
                synEditingKey = null;
                loadSynonyms();
            } else {
                alert('Error: ' + data.error);
            }
        } catch (err) { alert('Error de conexión'); }
    }

    async function synDelete(key) {
        if (!confirm(`¿Eliminar sinónimo?\n${key}`)) return;
        try {
            const res = await fetch('api.php?action=delete_synonym', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key }),
            });
            const data = await res.json();
            if (data.ok) loadSynonyms();
            else alert('Error: ' + data.error);
        } catch (err) { alert('Error de conexión'); }
    }

    // --- Add synonym ---
    document.getElementById('btnAddSynonym').addEventListener('click', () => {
        document.getElementById('synAddForm').classList.toggle('hidden');
    });
    document.getElementById('btnSynAddCancel').addEventListener('click', () => {
        document.getElementById('synAddForm').classList.add('hidden');
    });
    // Auto-lookup en formulario de añadir
    document.getElementById('synAddArticuloId').addEventListener('change', async () => {
        const id = parseInt(document.getElementById('synAddArticuloId').value) || 0;
        if (!id) return;
        try {
            const res = await fetch(`api.php?action=lookup_article&id=${id}`);
            const data = await res.json();
            if (data.ok) {
                document.getElementById('synAddArticuloName').value = data.nombre;
            }
        } catch (err) { /* silenciar */ }
    });
    document.getElementById('btnSynAddSave').addEventListener('click', async () => {
        const key = document.getElementById('synAddKey').value.trim();
        const artId = parseInt(document.getElementById('synAddArticuloId').value) || 0;
        const artName = document.getElementById('synAddArticuloName').value.trim();
        if (!key || !artId) { alert('Clave e ID artículo son obligatorios'); return; }
        try {
            const res = await fetch('api.php?action=save_synonym', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key, articulo_id: artId, articulo_name: artName }),
            });
            const data = await res.json();
            if (data.ok) {
                document.getElementById('synAddForm').classList.add('hidden');
                document.getElementById('synAddKey').value = '';
                document.getElementById('synAddArticuloId').value = '';
                document.getElementById('synAddArticuloName').value = '';
                loadSynonyms();
            } else {
                alert('Error: ' + data.error);
            }
        } catch (err) { alert('Error de conexión'); }
    });

    // Filters
    document.getElementById('synFilter').addEventListener('input', () => { synPage = 1; filterSynonyms(); });
    document.getElementById('synOriginFilter').addEventListener('change', () => { synPage = 1; filterSynonyms(); });

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
            const hasLines = r.ok && r.lines && r.lines.length > 0;
            const needsReview = r.ok && r.sin_match > 0;
            const rowId = `batch-lines-${i}`;

            let html = `
                <tr class="${!r.ok ? 'row-sin-match' : r.sin_match > 0 ? 'row-partial' : ''} ${hasLines ? 'batch-expandable' : ''}" data-target="${rowId}">
                    <td>${i + 1}</td>
                    <td>${hasLines ? '<span class="expand-arrow">&#9654;</span> ' : ''}${esc(r.pdf)}</td>
                    <td>${esc(r.provider || '-')}</td>
                    <td>${esc(r.invoice || '-')}</td>
                    <td>${esc(r.date || '-')}</td>
                    <td>${r.lineas || 0}</td>
                    <td>${r.ok_count || 0}</td>
                    <td>${r.sin_match || 0}</td>
                    <td>$${num(r.total_usd || 0)}</td>
                    <td><span class="${statusClass}">${status}</span>${!r.ok ? `<br><small>${esc(r.error)}</small>` : ''}</td>
                </tr>`;

            // Fila expandible con líneas de detalle
            if (hasLines) {
                html += `<tr id="${rowId}" class="batch-lines-row hidden">
                    <td colspan="10">
                        <div class="batch-lines-detail">
                            <table class="batch-lines-table">
                                <thead><tr>
                                    <th>Descripción</th><th>Variedad</th><th>Talla</th>
                                    <th>Tallos</th><th>Total</th>
                                    <th>ID Artículo</th><th>Nombre Artículo</th>
                                    <th>Match</th>${needsReview ? '<th>Acción</th>' : ''}
                                </tr></thead>
                                <tbody>${r.lines.map(l => _batchLineRow(l, r, needsReview)).join('')}</tbody>
                            </table>
                        </div>
                    </td>
                </tr>`;
            }
            return html;
        }).join('');
    }

    function _batchLineRow(l, invoiceResult, showActions) {
        const isBad = l.match_status !== 'ok';
        const cls = isBad ? 'row-sin-match' : '';
        const key = `${invoiceResult.provider_id || 0}|${l.species || ''}|${l.variety || ''}|${l.size || 0}|${l.stems_per_bunch || 0}|${l.grade || ''}`;
        return `
            <tr class="${cls}" data-syn-key="${esc(key)}" data-pdf="${esc(invoiceResult.pdf)}">
                <td title="${esc(l.raw || '')}">${esc((l.raw || '').substring(0, 50))}${(l.raw || '').length > 50 ? '...' : ''}</td>
                <td><strong>${esc(l.variety || '')}</strong></td>
                <td>${l.size || '-'}</td>
                <td>${l.stems || '-'}</td>
                <td>$${num(l.line_total || 0)}</td>
                <td>${l.articulo_id || '-'}</td>
                <td>${esc(l.articulo_name || '-')}</td>
                <td>${matchBadge(l.match_status || '', l.match_method || '')}</td>
                ${showActions && isBad ? `<td>
                    <input type="number" class="edit-input batch-art-id" placeholder="ID" style="width:65px">
                    <button class="btn-icon batch-line-save" title="Guardar">&#10003;</button>
                </td>` : (showActions ? '<td></td>' : '')}
            </tr>`;
    }

    // Expandir/colapsar líneas de factura
    document.querySelector('#batchTable tbody').addEventListener('click', e => {
        const expandRow = e.target.closest('.batch-expandable');
        if (expandRow && !e.target.closest('.batch-line-save') && !e.target.closest('input')) {
            const targetId = expandRow.dataset.target;
            const linesRow = document.getElementById(targetId);
            if (linesRow) {
                linesRow.classList.toggle('hidden');
                const arrow = expandRow.querySelector('.expand-arrow');
                if (arrow) arrow.innerHTML = linesRow.classList.contains('hidden') ? '&#9654;' : '&#9660;';
            }
        }

        // Guardar match desde línea de batch
        const saveBtn = e.target.closest('.batch-line-save');
        if (saveBtn) {
            const tr = saveBtn.closest('tr');
            const input = tr.querySelector('.batch-art-id');
            const artId = parseInt(input.value) || 0;
            if (!artId) { alert('Introduce un ID de artículo'); return; }
            const synKey = tr.dataset.synKey;
            const pdf = tr.dataset.pdf;

            // Lookup nombre del artículo y guardar sinónimo
            fetch(`api.php?action=lookup_article&id=${artId}`)
                .then(r => r.json())
                .then(data => {
                    if (!data.ok) { alert(data.error); return; }
                    return fetch('api.php?action=save_synonym', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ key: synKey, articulo_id: artId, articulo_name: data.nombre }),
                    });
                })
                .then(r => r ? r.json() : null)
                .then(data => {
                    if (data && data.ok) {
                        // Actualizar visualmente
                        const cells = tr.querySelectorAll('td');
                        cells[5].textContent = artId;
                        cells[6].textContent = '';
                        fetch(`api.php?action=lookup_article&id=${artId}`)
                            .then(r => r.json())
                            .then(d => { if (d.ok) cells[6].textContent = d.nombre; });
                        cells[7].innerHTML = '<span class="badge badge-manual">manual-web</span>';
                        tr.classList.remove('row-sin-match');
                        const actionCell = cells[cells.length - 1];
                        actionCell.innerHTML = '<span style="color:green">&#10003;</span>';
                    } else if (data) {
                        alert('Error: ' + data.error);
                    }
                })
                .catch(err => alert('Error de conexión'));
        }
    });

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
