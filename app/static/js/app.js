document.addEventListener('DOMContentLoaded', function () {
    initSplashScreen();
    initPageControls();
    initPartialNavigation();
    initLanguageToggle();
    applyLanguage(getCurrentLanguage());
});

function initPageControls() {
    syncDeviceNameInputs();
    initUploadFileControl();
    initDetailsToggle();
    initSidebarToggle();
    syncPersistentEditTabs();
    initDataActions();
    initBulkSelect();
    initDeleteFileDialog();
    initDevicePanel();
    initDashboardSearchSuggestions();
    initEditTabCloseButtons();
    initTabReorder();
    applyLanguage(getCurrentLanguage());
    startDeviceHeartbeat();
}

function getDeviceName() {
    var stored = localStorage.getItem('boccardDeviceName');
    if (stored) {
        return stored;
    }

    var suffix = Math.random().toString(16).slice(2, 8).toUpperCase();
    var deviceName = 'Device ' + suffix;
    localStorage.setItem('boccardDeviceName', deviceName);
    return deviceName;
}

function getDeviceId() {
    var stored = localStorage.getItem('boccardDeviceId');
    if (stored) {
        return stored;
    }

    var cryptoApi = window.crypto || window.msCrypto;
    var id = 'dev-' + Math.random().toString(16).slice(2, 10).toUpperCase();
    if (cryptoApi && cryptoApi.getRandomValues) {
        var values = new Uint32Array(2);
        cryptoApi.getRandomValues(values);
        id = 'dev-' + values[0].toString(16).toUpperCase().padStart(8, '0') + values[1].toString(16).toUpperCase().padStart(8, '0');
    }
    localStorage.setItem('boccardDeviceId', id);
    return id;
}

var SPLASH_TTL_MS = 24 * 60 * 60 * 1000; // 24 jam

function shouldShowSplash() {
    var lastShown = localStorage.getItem('boccardSplashLastShown');
    if (!lastShown) {
        return true;
    }
    var elapsed = Date.now() - parseInt(lastShown, 10);
    return isNaN(elapsed) || elapsed > SPLASH_TTL_MS;
}

function markSplashShown() {
    localStorage.setItem('boccardSplashLastShown', Date.now().toString());
}

function initSplashScreen() {
    var splash = document.getElementById('splashScreen');
    if (!splash) {
        return;
    }

    var deviceName = getDeviceName();
    var deviceId = getDeviceId();
    var nameTarget = splash.querySelector('[data-splash-device-name]');
    var idTarget = splash.querySelector('[data-splash-device-id]');
    if (nameTarget) {
        nameTarget.textContent = deviceName;
    }
    if (idTarget) {
        idTarget.textContent = deviceId;
    }

    if (!shouldShowSplash()) {
        splash.remove();
        return;
    }

    markSplashShown();

    window.requestAnimationFrame(function () {
        window.requestAnimationFrame(function () {
            window.setTimeout(function () {
                splash.classList.add('splash-done');
                window.setTimeout(function () {
                    splash.remove();
                }, 420);
            }, 1800);
        });
    });
}

function syncDeviceNameInputs() {
    var deviceName = getDeviceName();
    var deviceId = getDeviceId();
    document.querySelectorAll('form').forEach(function (form) {
        if ((form.method || 'get').toLowerCase() === 'get') {
            return;
        }
        var input = form.querySelector('input[name="device_name"]');
        if (!input) {
            input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'device_name';
            form.appendChild(input);
        }
        input.value = deviceName;

        var idInput = form.querySelector('input[name="device_id"]');
        if (!idInput) {
            idInput = document.createElement('input');
            idInput.type = 'hidden';
            idInput.name = 'device_id';
            form.appendChild(idInput);
        }
        idInput.value = deviceId;
    });
}

var deviceHeartbeatStarted = false;

function startDeviceHeartbeat() {
    if (deviceHeartbeatStarted) {
        return;
    }
    deviceHeartbeatStarted = true;

    sendDeviceHeartbeat();
    window.setInterval(sendDeviceHeartbeat, 30000);
}

function sendDeviceHeartbeat() {
    fetch('/devices/heartbeat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'fetch',
            'X-Device-Name': getDeviceName(),
            'X-Device-ID': getDeviceId()
        },
        body: JSON.stringify({ ok: true })
    }).then(function () {
        refreshDeviceList();
    }).catch(function () {});
}

function initDevicePanel() {
    var panel = document.getElementById('devicePanel');
    var toggle = document.getElementById('devicePanelToggle');
    if (!panel || !toggle || panel.dataset.ready === 'true') {
        return;
    }

    panel.dataset.ready = 'true';
    var stored = localStorage.getItem('boccardDevicePanelOpen');
    setDevicePanelOpen(panel, toggle, stored !== 'false');

    toggle.addEventListener('click', function () {
        var nextOpen = panel.classList.contains('collapsed');
        setDevicePanelOpen(panel, toggle, nextOpen);
        localStorage.setItem('boccardDevicePanelOpen', String(nextOpen));
    });

    refreshDeviceList();
}

function setDevicePanelOpen(panel, toggle, open) {
    panel.classList.toggle('collapsed', !open);
    toggle.setAttribute('aria-expanded', String(open));
}

function refreshDeviceList() {
    var list = document.getElementById('deviceList');
    var panel = document.getElementById('devicePanel');
    if (!list || !panel) {
        return;
    }

    fetch('/devices', {
        headers: {
            'X-Requested-With': 'fetch',
            'X-Device-Name': getDeviceName(),
            'X-Device-ID': getDeviceId()
        }
    })
        .then(function (response) {
            if (!response.ok) {
                throw new Error('Device list failed');
            }
            return response.json();
        })
        .then(function (payload) {
            renderDeviceList(list, payload.devices || []);
        })
        .catch(function () {});
}

function renderDeviceList(list, devices) {
    list.innerHTML = '';
    var onlineCount = devices.filter(function (device) {
        return device.online;
    }).length;
    var countTarget = document.querySelector('.device-panel-head span');
    if (countTarget) {
        countTarget.textContent = onlineCount + ' online';
    }

    if (!devices.length) {
        var empty = document.createElement('p');
        empty.className = 'muted';
        empty.textContent = 'No devices yet.';
        list.appendChild(empty);
        return;
    }

    devices.forEach(function (device) {
        var item = document.createElement('div');
        item.className = 'device-item ' + (device.online ? 'online' : 'offline');

        var dot = document.createElement('span');
        dot.className = 'device-status-dot';

        var copy = document.createElement('div');
        var name = document.createElement('strong');
        name.textContent = device.device_name || 'Unknown Device';
        var id = document.createElement('small');
        id.textContent = device.device_id || '-';
        copy.appendChild(name);
        copy.appendChild(id);

        var state = document.createElement('em');
        state.textContent = device.online ? 'Online' : 'Offline';

        item.appendChild(dot);
        item.appendChild(copy);
        item.appendChild(state);
        list.appendChild(item);
    });
}

function initDashboardSearchSuggestions() {
    var input = document.getElementById('dashboardSearchInput');
    var list = document.getElementById('dashboardSearchSuggestions');
    if (!input || !list || input.dataset.suggestionsReady === 'true') {
        return;
    }

    input.dataset.suggestionsReady = 'true';
    var debounceTimer = null;

    input.addEventListener('input', function () {
        window.clearTimeout(debounceTimer);
        debounceTimer = window.setTimeout(function () {
            loadDashboardSearchSuggestions(input, list);
        }, 140);
    });

    input.addEventListener('focus', function () {
        loadDashboardSearchSuggestions(input, list);
    });

    document.addEventListener('click', function (event) {
        if (!event.target.closest('.keyword-search')) {
            list.hidden = true;
        }
    });
}

function loadDashboardSearchSuggestions(input, list) {
    var value = input.value.trim();
    var fileId = input.dataset.fileId;
    if (!value || !fileId) {
        list.hidden = true;
        list.innerHTML = '';
        return;
    }

    var url = (input.dataset.suggestionsUrl || '/search-suggestions') +
        '?file_id=' + encodeURIComponent(fileId) +
        '&q=' + encodeURIComponent(value);

    fetch(url, {
        headers: {
            'X-Requested-With': 'fetch',
            'X-Device-Name': getDeviceName(),
            'X-Device-ID': getDeviceId()
        }
    })
        .then(function (response) {
            if (!response.ok) {
                throw new Error('Suggestion request failed');
            }
            return response.json();
        })
        .then(function (payload) {
            renderDashboardSearchSuggestions(input, list, payload.suggestions || []);
        })
        .catch(function () {
            list.hidden = true;
        });
}

function renderDashboardSearchSuggestions(input, list, suggestions) {
    list.innerHTML = '';
    if (!suggestions.length) {
        list.hidden = true;
        return;
    }

    suggestions.slice(0, 8).forEach(function (suggestion) {
        var button = document.createElement('button');
        button.type = 'button';
        button.textContent = suggestion;
        button.addEventListener('click', function () {
            input.value = suggestion;
            list.hidden = true;
            input.form?.requestSubmit();
        });
        list.appendChild(button);
    });
    list.hidden = false;
}

var translations = {
    en: {
        auditLog: 'Audit Log',
        backToDashboard: 'Back to Dashboard',
        all: 'All',
        active: 'Active',
        activeFileTabs: 'Active file tabs',
        activeTabInfo: 'Active Tab Info',
        actions: 'Actions',
        apply: 'Apply',
        auditLogPersistent: 'Persistent action history',
        autosaveSnapshots: 'Autosave backups',
        availableBackups: 'Available backups',
        backupRecovery: 'Backup & Recovery',
        browse: 'Browse',
        bulkActions: 'Bulk Actions',
        cancel: 'Cancel',
        chooseExcelFile: 'Choose Excel file',
        closeUploadDialog: 'Close upload dialog',
        createdAt: 'Created At',
        dashboard: 'Dashboard',
        dataSafety: 'Data Safety',
        dataSource: 'Data source',
        dataSourceLocal: 'Local SQLite database and uploaded Excel files',
        dataManagement: 'DATA MANAGEMENT',
        delete: 'Delete',
        deleteFile: 'Delete File',
        deleteFilePrompt: 'Delete this file and all imported records?',
        deleteRecord: 'Delete Record',
        deleteSelected: 'Delete Selected',
        designation: 'Designation',
        dragTabOrdering: 'Drag tab ordering',
        edit: 'Edit',
        enabled: 'Enabled',
        enabledAfterChanges: 'Enabled after import, edit, delete, and repair',
        fileName: 'File Name',
        fileCloseBehavior: 'File close behavior',
        fileCloseTrash: 'Move to trash, keep source workbook and snapshot',
        filterByDesignation: 'Filter by Designation',
        filterByRemarks: 'Filter by Remarks',
        filterByTagNumber: 'Filter by Tag Number',
        exportData: 'Export Data',
        exportCurrentTab: 'Export Current Tab',
        hideDetails: 'Hide Details',
        imported: 'Imported',
        interface: 'Interface',
        itemList: 'Item List',
        languageSwitch: 'Language switch',
        noFileChosen: 'No file chosen',
        noRecordsFound: 'No records found',
        noWorkbookLoaded: 'No workbook loaded yet',
        notFound: 'Not Found',
        notFoundMessage: 'The page you requested does not exist or has been moved.',
        quickActions: 'Quick Actions',
        refreshData: 'Refresh Data',
        remarksInPidDatabase: 'Remarks in P&ID Database',
        rowNumber: 'Row Number',
        search: 'Search',
        searchAcrossTabs: 'Search across all tabs...',
        searchByAnyKeyword: 'Search by any keyword...',
        selectRowsThenRunAction: 'Select rows in the table, then run the action.',
        settings: 'Settings',
        snapshotFolder: 'Temp backup folder',
        sourceFile: 'Source File',
        status: 'Status',
        storedInBrowserLocalStorage: 'Stored in browser local storage',
        showMoreDetails: 'Show More Details',
        showingEntries: 'Showing {count} of {count} entries',
        supportedUploadFormat: 'Supported upload format',
        supportedUploadValue: '.xlsx workbooks',
        switchLanguage: 'Switch language',
        system: 'SYSTEM',
        tagNumber: 'Tag Number',
        tempSnapshotFolder: 'temp/*.json',
        tips: 'Tips',
        totalRecords: 'Total Records',
        trash: 'Trash',
        trashMode: 'Trash mode',
        trashModeRestore: 'Deleted files and records can be restored',
        tryDifferentSearch: 'Try a different search term or upload another workbook.',
        updatedAt: 'Updated At',
        uploadExcel: 'Upload Excel',
        workbook: 'Workbook',
        languageSwitchValue: 'English / Indonesian',
        persistentEditTabs: 'Persistent edit tabs'
    },
    id: {
        auditLog: 'Log Audit',
        backToDashboard: 'Kembali ke Dashboard',
        all: 'Semua',
        active: 'Aktif',
        activeFileTabs: 'Tab file aktif',
        activeTabInfo: 'Info Tab Aktif',
        actions: 'Aksi',
        apply: 'Terapkan',
        auditLogPersistent: 'Riwayat aksi tersimpan permanen',
        autosaveSnapshots: 'Backup autosave',
        availableBackups: 'Backup tersedia',
        backupRecovery: 'Backup & Pemulihan',
        browse: 'Pilih',
        bulkActions: 'Aksi Massal',
        cancel: 'Batal',
        chooseExcelFile: 'Pilih file Excel',
        closeUploadDialog: 'Tutup dialog upload',
        createdAt: 'Dibuat Pada',
        dashboard: 'Dashboard',
        dataSafety: 'Keamanan Data',
        dataSource: 'Sumber data',
        dataSourceLocal: 'Database SQLite lokal dan file Excel yang diupload',
        dataManagement: 'MANAJEMEN DATA',
        delete: 'Hapus',
        deleteFile: 'Hapus File',
        deleteFilePrompt: 'Hapus file ini dan semua record yang diimpor?',
        deleteRecord: 'Hapus Record',
        deleteSelected: 'Hapus yang Dipilih',
        designation: 'Designation',
        dragTabOrdering: 'Urutan tab dengan drag',
        edit: 'Edit',
        enabled: 'Aktif',
        enabledAfterChanges: 'Aktif setelah import, edit, hapus, dan repair',
        fileName: 'Nama File',
        fileCloseBehavior: 'Perilaku tutup file',
        fileCloseTrash: 'Pindahkan ke sampah, simpan workbook sumber dan snapshot',
        filterByDesignation: 'Filter berdasarkan Designation',
        filterByRemarks: 'Filter berdasarkan Remarks',
        filterByTagNumber: 'Filter berdasarkan Tag Number',
        exportData: 'Ekspor Data',
        exportCurrentTab: 'Ekspor Tab Saat Ini',
        hideDetails: 'Sembunyikan Detail',
        imported: 'Diimpor',
        interface: 'Antarmuka',
        itemList: 'Daftar Item',
        languageSwitch: 'Pilihan bahasa',
        noFileChosen: 'Belum ada file dipilih',
        noRecordsFound: 'Record tidak ditemukan',
        noWorkbookLoaded: 'Belum ada workbook dimuat',
        notFound: 'Tidak Ditemukan',
        notFoundMessage: 'Halaman yang Anda minta tidak tersedia atau sudah dipindahkan.',
        quickActions: 'Aksi Cepat',
        refreshData: 'Segarkan Data',
        remarksInPidDatabase: 'Remarks di Database P&ID',
        rowNumber: 'Nomor Baris',
        search: 'Cari',
        searchAcrossTabs: 'Cari di semua tab...',
        searchByAnyKeyword: 'Cari dengan kata kunci...',
        selectRowsThenRunAction: 'Pilih baris di tabel, lalu jalankan aksi.',
        settings: 'Pengaturan',
        snapshotFolder: 'Folder temp backup',
        sourceFile: 'File Sumber',
        status: 'Status',
        storedInBrowserLocalStorage: 'Disimpan di local storage browser',
        showMoreDetails: 'Tampilkan Detail',
        showingEntries: 'Menampilkan {count} dari {count} entri',
        supportedUploadFormat: 'Format upload yang didukung',
        supportedUploadValue: 'Workbook .xlsx',
        switchLanguage: 'Ganti bahasa',
        system: 'SISTEM',
        tagNumber: 'Tag Number',
        tempSnapshotFolder: 'temp/*.json',
        tips: 'Tips',
        totalRecords: 'Total Record',
        trash: 'Sampah',
        trashMode: 'Mode sampah',
        trashModeRestore: 'File dan record yang dihapus bisa dipulihkan',
        tryDifferentSearch: 'Coba kata kunci lain atau upload workbook lain.',
        updatedAt: 'Diperbarui Pada',
        uploadExcel: 'Upload Excel',
        workbook: 'Workbook',
        languageSwitchValue: 'Bahasa Inggris / Bahasa Indonesia',
        persistentEditTabs: 'Tab edit persisten'
    }
};

function getCurrentLanguage() {
    var stored = localStorage.getItem('boccardLanguage');
    return stored === 'id' ? 'id' : 'en';
}

function t(key) {
    return (translations[getCurrentLanguage()] || translations.en)[key] || translations.en[key] || key;
}

function initLanguageToggle() {
    var toggle = document.getElementById('languageToggle');
    if (!toggle || toggle.dataset.ready === 'true') {
        return;
    }

    toggle.dataset.ready = 'true';
    toggle.addEventListener('click', function () {
        var nextLanguage = getCurrentLanguage() === 'en' ? 'id' : 'en';
        localStorage.setItem('boccardLanguage', nextLanguage);
        applyLanguage(nextLanguage);
    });
}

function applyLanguage(language) {
    var lang = language === 'id' ? 'id' : 'en';
    var dictionary = translations[lang] || translations.en;

    document.documentElement.lang = lang;
    document.querySelectorAll('[data-i18n]').forEach(function (element) {
        var key = element.dataset.i18n;
        if (dictionary[key]) {
            element.textContent = formatTranslation(dictionary[key], element.dataset);
        }
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function (element) {
        var key = element.dataset.i18nPlaceholder;
        if (dictionary[key]) {
            element.setAttribute('placeholder', dictionary[key]);
        }
    });
    document.querySelectorAll('[data-i18n-aria-label]').forEach(function (element) {
        var key = element.dataset.i18nAriaLabel;
        if (dictionary[key]) {
            element.setAttribute('aria-label', dictionary[key]);
        }
    });

    var languageLabel = document.querySelector('[data-language-label]');
    if (languageLabel) {
        languageLabel.textContent = lang === 'en' ? 'ID' : 'EN';
    }

    var detailToggle = document.getElementById('toggleDetailsColumns');
    if (detailToggle) {
        var expanded = detailToggle.getAttribute('aria-expanded') === 'true';
        detailToggle.textContent = expanded ? t('hideDetails') : t('showMoreDetails');
    }

    var uploadInput = document.getElementById('excelFileInput');
    var uploadFileName = document.getElementById('uploadFileName');
    if (uploadInput && uploadFileName && !uploadInput.files.length) {
        uploadFileName.textContent = t('noFileChosen');
    }
}

function formatTranslation(value, dataset) {
    return value.replace(/\{([a-zA-Z0-9_]+)\}/g, function (match, key) {
        return dataset[key] !== undefined ? dataset[key] : match;
    });
}

function initUploadFileControl() {
    var input = document.getElementById('excelFileInput');
    var fileName = document.getElementById('uploadFileName');
    if (!input || !fileName || input.dataset.ready === 'true') {
        return;
    }

    input.dataset.ready = 'true';
    input.addEventListener('change', function () {
        fileName.textContent = input.files.length ? input.files[0].name : t('noFileChosen');
    });
}

function initDetailsToggle() {
    var detailToggle = document.getElementById('toggleDetailsColumns');
    if (!detailToggle || detailToggle.dataset.ready === 'true') {
        return;
    }

    detailToggle.dataset.ready = 'true';
    detailToggle.addEventListener('click', function () {
        var table = document.querySelector('.records-table');
        var columns = document.querySelectorAll('.detail-column');
        var expanded = detailToggle.getAttribute('aria-expanded') === 'true';

        if (table) {
            table.classList.toggle('details-expanded', !expanded);
        }

        columns.forEach(function (column) {
            column.hidden = false;
            column.style.display = expanded ? 'none' : '';
        });

        detailToggle.setAttribute('aria-expanded', String(!expanded));
        detailToggle.textContent = expanded ? t('showMoreDetails') : t('hideDetails');

        var tableShell = document.getElementById('recordsTable');
        if (tableShell && !expanded) {
            window.requestAnimationFrame(function () {
                tableShell.scrollLeft = Math.max(0, tableShell.scrollWidth - tableShell.clientWidth);
            });
        }
    });
}

function initSidebarToggle() {
    var button = document.querySelector('.menu-button');
    if (!button || button.dataset.ready === 'true') {
        return;
    }

    button.dataset.ready = 'true';
    button.addEventListener('click', function (event) {
        event.preventDefault();
        if (document.body.classList.contains('sidebar-transitioning')) {
            return;
        }

        document.body.classList.add('sidebar-transitioning');
        window.requestAnimationFrame(function () {
            document.body.classList.toggle('sidebar-collapsed');
            button.setAttribute('aria-expanded', String(!document.body.classList.contains('sidebar-collapsed')));

            window.setTimeout(function () {
                document.body.classList.remove('sidebar-transitioning');
            }, 180);
        });
    });
}

function initDataActions() {
    document.querySelectorAll('[data-action]').forEach(function (control) {
        if (control.dataset.ready === 'true') {
            return;
        }

        control.dataset.ready = 'true';
        control.addEventListener('click', function (event) {
            var action = control.getAttribute('data-action');

            if (action === 'focus-tabs') {
                event.preventDefault();
                document.getElementById('pageTabs')?.focus();
            }

            if (action === 'focus-records') {
                event.preventDefault();
                var recordsTable = document.getElementById('recordsTable');
                recordsTable?.scrollIntoView({ block: 'nearest' });
                recordsTable?.focus();
            }

            if (action === 'focus-search') {
                event.preventDefault();
                document.querySelector('#filterBar input[type="search"]')?.focus();
            }

            if (action === 'bulk-mode') {
                event.preventDefault();
                var bulkActions = document.getElementById('bulkDeleteForm');
                var isHidden = !bulkActions || bulkActions.hidden;

                document.querySelectorAll('.bulk-column').forEach(function (column) {
                    column.hidden = !isHidden;
                });

                if (bulkActions) {
                    bulkActions.hidden = !isHidden;
                }

                showToast(isHidden ? 'Bulk actions enabled.' : 'Bulk actions hidden.');
            }

            if (action === 'needs-file') {
                event.preventDefault();
                showToast('Upload or select a file first.');
            }
        });
    });
}

function initBulkSelect() {
    var selectAll = document.getElementById('selectAllRecords');
    if (!selectAll || selectAll.dataset.ready === 'true') {
        return;
    }

    selectAll.dataset.ready = 'true';
    selectAll.addEventListener('change', function () {
        document.querySelectorAll('input[name="record_ids"]').forEach(function (checkbox) {
            checkbox.checked = selectAll.checked;
        });
    });
}

function initDeleteFileDialog() {
    var deleteFileDialog = document.getElementById('deleteFileDialog');
    var deleteFileForm = document.getElementById('deleteFileForm');

    document.querySelectorAll('[data-delete-file-id]').forEach(function (button) {
        if (button.dataset.ready === 'true') {
            return;
        }

        button.dataset.ready = 'true';
        button.addEventListener('click', function () {
            var fileId = button.getAttribute('data-delete-file-id');
            if (!deleteFileDialog || !deleteFileForm || !fileId) {
                return;
            }

            deleteFileForm.action = '/file/' + encodeURIComponent(fileId) + '/delete';
            deleteFileForm.dataset.deleteFileId = fileId;
            deleteFileDialog.showModal();
        });
    });

    if (deleteFileForm && deleteFileForm.dataset.ready !== 'true') {
        deleteFileForm.dataset.ready = 'true';
        deleteFileForm.addEventListener('submit', function () {
            clearTabsForDeletedFile(deleteFileForm.dataset.deleteFileId);
        });
    }

    document.querySelectorAll('[data-dialog-close]').forEach(function (button) {
        if (button.dataset.ready === 'true') {
            return;
        }

        button.dataset.ready = 'true';
        button.addEventListener('click', function () {
            deleteFileDialog?.close();
        });
    });
}

function initPartialNavigation() {
    if (document.body.dataset.partialNavReady === 'true') {
        return;
    }

    document.body.dataset.partialNavReady = 'true';

    document.addEventListener('click', function (event) {
        var link = event.target.closest('a[href]');
        if (!link || shouldUseNormalNavigation(link) || document.querySelector('.file-tabs.dragging-tabs')) {
            return;
        }

        var url = new URL(link.href, window.location.href);
        if (url.origin !== window.location.origin) {
            return;
        }

        event.preventDefault();
        loadPage(url.href, true);
    });

    document.addEventListener('submit', function (event) {
        var form = event.target;
        if (!(form instanceof HTMLFormElement)) {
            return;
        }

        if (form.id === 'deleteFileForm') {
            clearTabsForDeletedFile(form.dataset.deleteFileId);
            return;
        }

        if (form.hasAttribute('data-normal-submit')) {
            return;
        }

        event.preventDefault();
        submitForm(form, event.submitter);
    });

    window.addEventListener('popstate', function () {
        loadPage(window.location.href, false);
    });
}

function shouldUseNormalNavigation(link) {
    var href = link.getAttribute('href') || '';
    return link.target ||
        link.hasAttribute('download') ||
        href === '#' ||
        (href.includes('/file/') && href.includes('/export'));
}

function loadPage(url, pushState) {
    fetch(url, { headers: { 'X-Requested-With': 'fetch', 'X-Device-Name': getDeviceName(), 'X-Device-ID': getDeviceId() } })
        .then(function (response) {
            if (!response.ok) {
                throw new Error('Request failed');
            }
            return response.text();
        })
        .then(function (html) {
            replaceWorkspace(html);
            if (pushState) {
                window.history.pushState({}, '', url);
            }
        })
        .catch(function () {
            window.location.href = url;
        });
}

function submitForm(form, submitter) {
    var method = ((submitter && submitter.formMethod) || form.method || 'get').toUpperCase();
    var action = (submitter && submitter.formAction) || form.action || window.location.href;
    var options = { method: method, headers: { 'X-Requested-With': 'fetch' } };
    var targetUrl = action;
    var formData = new FormData(form);
    var savedEditTabId = getSavedEditTabId(form, submitter, method);
    if (method !== 'GET') {
        formData.set('device_name', getDeviceName());
        formData.set('device_id', getDeviceId());
    }

    if (form.id === 'deleteFileForm') {
        clearTabsForDeletedFile(form.dataset.deleteFileId);
    }

    if (submitter && submitter.name) {
        formData.append(submitter.name, submitter.value);
    }

    if (method === 'GET') {
        var params = new URLSearchParams(formData);
        targetUrl += (action.includes('?') ? '&' : '?') + params.toString();
    } else {
        options.body = formData;
    }

    fetch(targetUrl, options)
        .then(function (response) {
            if (!response.ok) {
                throw new Error('Request failed');
            }
            return response.text().then(function (html) {
                return { html: html, url: response.url || targetUrl };
            });
        })
        .then(function (payload) {
            document.querySelectorAll('dialog[open]').forEach(function (dialog) {
                dialog.close();
            });
            if (savedEditTabId) {
                closeStoredEditTab(savedEditTabId);
            }
            replaceWorkspace(payload.html);
            window.history.pushState({}, '', payload.url);
        })
        .catch(function () {
            form.submit();
        });
}

function getSavedEditTabId(form, submitter, method) {
    if (method !== 'POST' || !form.matches('.edit-page') || !form.dataset.editRecordId) {
        return null;
    }

    var submitAction = (submitter && submitter.formAction) || form.action || '';
    if (submitAction.includes('/delete/')) {
        return null;
    }

    return 'edit:' + form.dataset.editRecordId;
}

function closeStoredEditTab(tabId) {
    setStoredEditTabs(getStoredEditTabs().filter(function (item) {
        return item.id !== tabId;
    }));

    document.querySelectorAll('[data-tab-id]').forEach(function (tab) {
        if (tab.dataset.tabId === tabId) {
            tab.remove();
        }
    });
    saveCurrentTabOrder();
}

function replaceWorkspace(html) {
    var parsed = new DOMParser().parseFromString(html, 'text/html');
    var nextWorkspace = parsed.querySelector('.workspace');
    var currentWorkspace = document.querySelector('.workspace');
    var nextTitle = parsed.querySelector('title');

    if (!nextWorkspace || !currentWorkspace) {
        throw new Error('Workspace not found');
    }

    currentWorkspace.replaceWith(nextWorkspace);
    if (nextTitle) {
        document.title = nextTitle.textContent;
    }
    initPageControls();
}

function syncPersistentEditTabs() {
    var tabs = document.getElementById('pageTabs');
    if (!tabs) {
        return;
    }

    var currentEditTab = tabs.querySelector('[data-tab-kind="edit"][data-edit-id]');
    if (currentEditTab) {
        upsertStoredEditTab({
            id: currentEditTab.dataset.tabId,
            editId: currentEditTab.dataset.editId,
            fileId: currentEditTab.dataset.editFileId,
            title: currentEditTab.dataset.editTitle || currentEditTab.textContent.trim(),
            url: currentEditTab.dataset.editUrl || currentEditTab.querySelector('a')?.href || window.location.href
        });
    }

    var existingIds = new Set(Array.from(tabs.querySelectorAll('[data-tab-id]')).map(function (tab) {
        return tab.dataset.tabId;
    }));

    getStoredEditTabs().forEach(function (item) {
        if (!item.id || existingIds.has(item.id)) {
            return;
        }
        tabs.appendChild(createEditTab(item, false));
    });

    applyStoredTabOrder();
}

function getStoredEditTabs() {
    try {
        return JSON.parse(localStorage.getItem('boccardEditTabs') || '[]');
    } catch (error) {
        return [];
    }
}

function setStoredEditTabs(items) {
    localStorage.setItem('boccardEditTabs', JSON.stringify(items));
}

function upsertStoredEditTab(tab) {
    var tabs = getStoredEditTabs().filter(function (item) {
        return item.id !== tab.id;
    });
    tabs.push(tab);
    setStoredEditTabs(tabs);
}

function createEditTab(item, active) {
    var tab = document.createElement('div');
    tab.className = 'file-tab' + (active ? ' active' : '');
    tab.dataset.tabId = item.id;
    tab.dataset.tabKind = 'edit';
    tab.dataset.editId = item.editId;
    if (item.fileId) {
        tab.dataset.editFileId = item.fileId;
    }
    tab.dataset.editTitle = item.title;
    tab.dataset.editUrl = item.url;

    var link = document.createElement('a');
    link.className = 'tab-link';
    link.href = item.url;
    link.innerHTML = '<i class="fa-solid fa-pen" aria-hidden="true"></i><span></span>';
    link.querySelector('span').textContent = item.title;

    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'tab-close';
    close.dataset.closeEditTab = item.id;
    close.setAttribute('aria-label', 'Close edit tab');
    close.innerHTML = '<i class="fa-solid fa-xmark" aria-hidden="true"></i>';

    tab.appendChild(link);
    tab.appendChild(close);
    return tab;
}

function clearTabsForDeletedFile(fileId) {
    if (!fileId) {
        return;
    }

    var remainingTabs = getStoredEditTabs().filter(function (item) {
        return !item.fileId || String(item.fileId) !== String(fileId);
    });
    setStoredEditTabs(remainingTabs);

    document.querySelectorAll('[data-tab-kind="edit"], [data-tab-kind="file"]').forEach(function (tab) {
        var tabFileId = tab.dataset.editFileId || (tab.dataset.tabId || '').replace('file:', '');
        if (String(tabFileId) === String(fileId)) {
            tab.remove();
        }
    });

    saveCurrentTabOrder();
}

function initEditTabCloseButtons() {
    document.querySelectorAll('[data-close-edit-tab]').forEach(function (button) {
        if (button.dataset.ready === 'true') {
            return;
        }

        button.dataset.ready = 'true';
        button.addEventListener('click', function (event) {
            event.preventDefault();
            event.stopPropagation();

            var tabId = button.dataset.closeEditTab;
            var tab = button.closest('[data-tab-id]');
            var wasActive = tab?.classList.contains('active');

            setStoredEditTabs(getStoredEditTabs().filter(function (item) {
                return item.id !== tabId;
            }));
            tab?.remove();
            saveCurrentTabOrder();

            if (wasActive) {
                var fallback = document.querySelector('[data-tab-kind="file"] .tab-link') ||
                    document.querySelector('[data-tab-kind="dashboard"] .tab-link') ||
                    document.querySelector('#pageTabs .tab-link');
                if (fallback) {
                    loadPage(fallback.href, true);
                }
            }
        });
    });
}

function initTabReorder() {
    var tabs = document.getElementById('pageTabs');
    if (!tabs) {
        return;
    }

    tabs.querySelectorAll('.file-tab').forEach(function (tab) {
        if (tab.dataset.reorderReady === 'true') {
            return;
        }

        tab.dataset.reorderReady = 'true';
        tab.draggable = true;

        tab.addEventListener('dragstart', function (event) {
            if (event.target.closest('.tab-close')) {
                event.preventDefault();
                return;
            }
            tab.classList.add('dragging');
            tabs.classList.add('dragging-tabs');
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', tab.dataset.tabId || '');
        });

        tab.addEventListener('dragend', function () {
            tab.classList.remove('dragging');
            tabs.classList.remove('dragging-tabs');
            tabs.querySelectorAll('.drag-over-left, .drag-over-right').forEach(function (item) {
                item.classList.remove('drag-over-left', 'drag-over-right');
            });
            saveCurrentTabOrder();
        });
    });

    if (tabs.dataset.reorderReady === 'true') {
        return;
    }

    tabs.dataset.reorderReady = 'true';

    tabs.addEventListener('dragover', function (event) {
        var dragging = tabs.querySelector('.file-tab.dragging');
        var target = event.target.closest('.file-tab');
        if (!dragging || !target || dragging === target) {
            return;
        }

        event.preventDefault();
        var rect = target.getBoundingClientRect();
        var placeAfter = event.clientX > rect.left + rect.width / 2;

        target.classList.toggle('drag-over-left', !placeAfter);
        target.classList.toggle('drag-over-right', placeAfter);

        if (placeAfter) {
            target.after(dragging);
        } else {
            target.before(dragging);
        }
    });

    tabs.addEventListener('drop', function (event) {
        event.preventDefault();
        saveCurrentTabOrder();
    });
}

function applyStoredTabOrder() {
    var tabs = document.getElementById('pageTabs');
    if (!tabs) {
        return;
    }

    var order = getStoredTabOrder();
    if (!order.length) {
        return;
    }

    var byId = new Map(Array.from(tabs.querySelectorAll('[data-tab-id]')).map(function (tab) {
        return [tab.dataset.tabId, tab];
    }));

    order.forEach(function (id) {
        var tab = byId.get(id);
        if (tab) {
            tabs.appendChild(tab);
        }
    });
}

function getStoredTabOrder() {
    try {
        return JSON.parse(localStorage.getItem('boccardTabOrder') || '[]');
    } catch (error) {
        return [];
    }
}

function saveCurrentTabOrder() {
    var tabs = document.getElementById('pageTabs');
    if (!tabs) {
        return;
    }

    localStorage.setItem('boccardTabOrder', JSON.stringify(Array.from(tabs.querySelectorAll('[data-tab-id]')).map(function (tab) {
        return tab.dataset.tabId;
    })));
}

function showToast(message) {
    var existing = document.querySelector('.toast');
    if (existing) {
        existing.remove();
    }

    var toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    window.setTimeout(function () {
        toast.remove();
    }, 2200);
}
