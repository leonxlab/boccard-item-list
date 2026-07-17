document.addEventListener('DOMContentLoaded', function () {
    initPageControls();
    initPartialNavigation();
    initLanguageToggle();
    applyLanguage(getCurrentLanguage());
});

function initPageControls() {
    initUploadFileControl();
    initDetailsToggle();
    initSidebarToggle();
    syncPersistentEditTabs();
    initDataActions();
    initBulkSelect();
    initDeleteFileDialog();
    initEditTabCloseButtons();
    initTabReorder();
    applyLanguage(getCurrentLanguage());
}

var translations = {
    en: {
        auditLog: 'Audit Log',
        backToDashboard: 'Back to Dashboard',
        all: 'All',
        active: 'Active',
        activeTabInfo: 'Active Tab Info',
        actions: 'Actions',
        apply: 'Apply',
        browse: 'Browse',
        bulkActions: 'Bulk Actions',
        cancel: 'Cancel',
        chooseExcelFile: 'Choose Excel file',
        closeUploadDialog: 'Close upload dialog',
        createdAt: 'Created At',
        dashboard: 'Dashboard',
        dataManagement: 'DATA MANAGEMENT',
        delete: 'Delete',
        deleteFile: 'Delete File',
        deleteFilePrompt: 'Delete this file and all imported records?',
        deleteRecord: 'Delete Record',
        deleteSelected: 'Delete Selected',
        designation: 'Designation',
        edit: 'Edit',
        fileName: 'File Name',
        filterByDesignation: 'Filter by Designation',
        filterByRemarks: 'Filter by Remarks',
        filterByTagNumber: 'Filter by Tag Number',
        exportData: 'Export Data',
        exportCurrentTab: 'Export Current Tab',
        hideDetails: 'Hide Details',
        imported: 'Imported',
        itemList: 'Item List',
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
        sourceFile: 'Source File',
        status: 'Status',
        showMoreDetails: 'Show More Details',
        showingEntries: 'Showing {count} of {count} entries',
        switchLanguage: 'Switch language',
        system: 'SYSTEM',
        tagNumber: 'Tag Number',
        tips: 'Tips',
        totalRecords: 'Total Records',
        trash: 'Trash',
        tryDifferentSearch: 'Try a different search term or upload another workbook.',
        updatedAt: 'Updated At',
        uploadExcel: 'Upload Excel'
    },
    id: {
        auditLog: 'Log Audit',
        backToDashboard: 'Kembali ke Dashboard',
        all: 'Semua',
        active: 'Aktif',
        activeTabInfo: 'Info Tab Aktif',
        actions: 'Aksi',
        apply: 'Terapkan',
        browse: 'Pilih',
        bulkActions: 'Aksi Massal',
        cancel: 'Batal',
        chooseExcelFile: 'Pilih file Excel',
        closeUploadDialog: 'Tutup dialog upload',
        createdAt: 'Dibuat Pada',
        dashboard: 'Dashboard',
        dataManagement: 'MANAJEMEN DATA',
        delete: 'Hapus',
        deleteFile: 'Hapus File',
        deleteFilePrompt: 'Hapus file ini dan semua record yang diimpor?',
        deleteRecord: 'Hapus Record',
        deleteSelected: 'Hapus yang Dipilih',
        designation: 'Designation',
        edit: 'Edit',
        fileName: 'Nama File',
        filterByDesignation: 'Filter berdasarkan Designation',
        filterByRemarks: 'Filter berdasarkan Remarks',
        filterByTagNumber: 'Filter berdasarkan Tag Number',
        exportData: 'Ekspor Data',
        exportCurrentTab: 'Ekspor Tab Saat Ini',
        hideDetails: 'Sembunyikan Detail',
        imported: 'Diimpor',
        itemList: 'Daftar Item',
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
        sourceFile: 'File Sumber',
        status: 'Status',
        showMoreDetails: 'Tampilkan Detail',
        showingEntries: 'Menampilkan {count} dari {count} entri',
        switchLanguage: 'Ganti bahasa',
        system: 'SISTEM',
        tagNumber: 'Tag Number',
        tips: 'Tips',
        totalRecords: 'Total Record',
        trash: 'Sampah',
        tryDifferentSearch: 'Coba kata kunci lain atau upload workbook lain.',
        updatedAt: 'Diperbarui Pada',
        uploadExcel: 'Upload Excel'
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
        document.body.classList.toggle('sidebar-collapsed');
        button.setAttribute('aria-expanded', String(!document.body.classList.contains('sidebar-collapsed')));
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
        if (!(form instanceof HTMLFormElement) || form.hasAttribute('data-normal-submit')) {
            return;
        }

        if (form.id === 'deleteFileForm') {
            clearTabsForDeletedFile(form.dataset.deleteFileId);
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
    fetch(url, { headers: { 'X-Requested-With': 'fetch' } })
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
            replaceWorkspace(payload.html);
            window.history.pushState({}, '', payload.url);
        })
        .catch(function () {
            form.submit();
        });
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
