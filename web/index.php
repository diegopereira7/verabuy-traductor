<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VeraBuy Traductor</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <header>
        <h1>VeraBuy Traductor</h1>
        <nav>
            <button class="nav-btn active" data-tab="upload">Procesar Factura</button>
            <button class="nav-btn" data-tab="batch">Importación Masiva</button>
            <button class="nav-btn" data-tab="history">Historial</button>
            <button class="nav-btn" data-tab="synonyms">Sinónimos</button>
            <button class="nav-btn" data-tab="learned">Auto-Aprendizaje</button>
        </nav>
    </header>

    <main>
        <!-- TAB: Procesar Factura -->
        <section id="tab-upload" class="tab active">
            <div class="upload-zone" id="dropZone">
                <div class="upload-icon">&#128196;</div>
                <p>Arrastra un PDF aquí o haz clic para seleccionar</p>
                <input type="file" id="pdfInput" accept=".pdf" hidden>
                <button class="btn btn-primary" id="btnSelectFile">Seleccionar PDF</button>
            </div>

            <div id="processing" class="hidden">
                <div class="spinner"></div>
                <p>Procesando factura...</p>
            </div>

            <div id="resultSection" class="hidden">
                <!-- Cabecera de factura -->
                <div class="result-header" id="invoiceHeader"></div>

                <!-- Estadísticas -->
                <div class="stats-bar" id="statsBar"></div>

                <!-- Tabla de líneas -->
                <div class="table-container">
                    <table id="linesTable">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Descripción</th>
                                <th>Especie</th>
                                <th>Variedad</th>
                                <th>Talla</th>
                                <th>SPB</th>
                                <th>Tallos</th>
                                <th>Precio/T</th>
                                <th>Total</th>
                                <th>Artículo VeraBuy</th>
                                <th>Match</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>

                <button class="btn btn-secondary" id="btnNewUpload">Procesar otra factura</button>
            </div>
        </section>

        <!-- TAB: Importación Masiva -->
        <section id="tab-batch" class="tab hidden">
            <!-- Estado 1: Subida -->
            <div id="batch-upload-zone">
                <h2>Importación Masiva de Facturas</h2>
                <div class="batch-drop-zone" id="batchDropZone">
                    <div class="upload-icon">&#128230;</div>
                    <p>Arrastra un archivo <strong>.zip</strong> con facturas PDF</p>
                    <p class="text-muted">o haz clic para seleccionar</p>
                    <input type="file" id="batchZipInput" accept=".zip" hidden>
                    <button class="btn btn-primary" id="btnSelectZip">Seleccionar ZIP</button>
                </div>
            </div>

            <!-- Estado 2: Progreso -->
            <div id="batch-progress" class="hidden">
                <h2>Procesando Lote</h2>
                <div class="batch-progress-card">
                    <div class="batch-progress-header">
                        <span id="batch-status-text">Iniciando...</span>
                        <span id="batch-progress-count"></span>
                    </div>
                    <div class="batch-progress-bar-wrap">
                        <div class="batch-progress-bar" id="batchProgressBar" style="width: 0%"></div>
                    </div>
                    <div class="batch-progress-detail">
                        <span id="batch-current-pdf"></span>
                        <span id="batch-ok-err"></span>
                    </div>
                </div>
            </div>

            <!-- Estado 3: Resultados -->
            <div id="batch-results" class="hidden">
                <h2>Resultados del Lote</h2>

                <!-- Tarjetas resumen -->
                <div class="batch-summary" id="batchSummary"></div>

                <!-- Filtros -->
                <div class="filters">
                    <select id="batchFilterInvoice">
                        <option value="">Todas las facturas</option>
                    </select>
                    <select id="batchFilterStatus">
                        <option value="">Todos los estados</option>
                        <option value="ok">OK</option>
                        <option value="parcial">Parcial</option>
                        <option value="error">Error</option>
                    </select>
                    <input type="text" id="batchFilterText" placeholder="Buscar proveedor, factura...">
                </div>

                <!-- Tabla de resultados -->
                <div class="table-container">
                    <table id="batchTable">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>PDF</th>
                                <th>Proveedor</th>
                                <th>Factura</th>
                                <th>Fecha</th>
                                <th>Líneas</th>
                                <th>OK</th>
                                <th>Sin Match</th>
                                <th>Total USD</th>
                                <th>Estado</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>

                <!-- Acciones -->
                <div class="batch-actions">
                    <button class="btn btn-primary" id="btnBatchExcel">Descargar Excel</button>
                    <button class="btn btn-secondary" id="btnBatchNew">Nueva Importación</button>
                </div>
            </div>
        </section>

        <!-- TAB: Historial -->
        <section id="tab-history" class="tab hidden">
            <h2>Historial de Procesamiento</h2>
            <div id="historyLoading" class="hidden">
                <div class="spinner"></div>
            </div>
            <div class="table-container">
                <table id="historyTable">
                    <thead>
                        <tr>
                            <th>Fecha</th>
                            <th>Factura</th>
                            <th>Proveedor</th>
                            <th>PDF</th>
                            <th>Líneas</th>
                            <th>OK</th>
                            <th>Sin Match</th>
                            <th>Total USD</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </section>

        <!-- TAB: Sinónimos -->
        <section id="tab-synonyms" class="tab hidden">
            <h2>Diccionario de Sinónimos</h2>
            <div class="filters">
                <input type="text" id="synFilter" placeholder="Buscar por variedad, proveedor, especie...">
                <select id="synOriginFilter">
                    <option value="">Todos los orígenes</option>
                    <option value="auto">Auto</option>
                    <option value="auto-fuzzy">Fuzzy</option>
                    <option value="manual">Manual</option>
                    <option value="manual-web">Manual (Web)</option>
                </select>
                <span id="synCount"></span>
            </div>
            <div id="synLoading" class="hidden">
                <div class="spinner"></div>
            </div>
            <div class="table-container">
                <table id="synTable">
                    <thead>
                        <tr>
                            <th>Proveedor</th>
                            <th>Especie</th>
                            <th>Variedad</th>
                            <th>Talla</th>
                            <th>SPB</th>
                            <th>Grado</th>
                            <th>ID Artículo</th>
                            <th>Nombre Artículo</th>
                            <th>Origen</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </section>
        <!-- TAB: Auto-Aprendizaje -->
        <section id="tab-learned" class="tab hidden">
            <h2>Parsers Auto-Aprendidos</h2>
            <div id="learnedLoading" class="hidden"><div class="spinner"></div></div>

            <div id="learnedContent">
                <h3>Parsers Generados</h3>
                <div class="table-container">
                    <table id="learnedTable">
                        <thead>
                            <tr>
                                <th>Nombre</th>
                                <th>Especie</th>
                                <th>Score</th>
                                <th>Estado</th>
                                <th>Fecha</th>
                                <th>PDFs</th>
                                <th>Keywords</th>
                                <th>Activo</th>
                                <th>Acción</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>

                <h3 style="margin-top: 24px;">Pendientes de Revisión</h3>
                <div class="table-container">
                    <table id="pendingTable">
                        <thead>
                            <tr>
                                <th>Proveedor</th>
                                <th>Score</th>
                                <th>Razón</th>
                                <th>PDFs</th>
                                <th>Fecha</th>
                                <th>Acción Sugerida</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </section>
    </main>

    <footer>
        <p>VeraBuy Traductor v4.0 &mdash; Interfaz Web</p>
    </footer>

    <script src="assets/app.js"></script>
</body>
</html>
