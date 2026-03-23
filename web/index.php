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
            <button class="nav-btn" data-tab="history">Historial</button>
            <button class="nav-btn" data-tab="synonyms">Sinónimos</button>
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
    </main>

    <footer>
        <p>VeraBuy Traductor v4.0 &mdash; Interfaz Web</p>
    </footer>

    <script src="assets/app.js"></script>
</body>
</html>
