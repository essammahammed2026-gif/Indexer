/* SVG Icon Set */
const SVG_RAW = {
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
  folder: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>',
  pdf: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="9" y1="15" x2="15" y2="15"></line></svg>',
  excel: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="3" y1="15" x2="21" y2="15"></line><line x1="9" y1="3" x2="9" y2="21"></line><line x1="15" y1="3" x2="15" y2="21"></line></svg>',
  doc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>',
  image: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>',
  text: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><line x1="17" y1="10" x2="3" y2="10"></line><line x1="21" y1="6" x2="3" y2="6"></line><line x1="21" y1="14" x2="3" y2="14"></line><line x1="17" y1="18" x2="3" y2="18"></line></svg>',
  phone: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>',
  copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>',
  cross: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
  open: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>',
  context: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>',
  tag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path><line x1="7" y1="7" x2="7.01" y2="7"></line></svg>',
  target: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>',
  eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>',
  zoomIn: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="11" y1="8" x2="11" y2="14"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>',
  zoomOut: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>',
  refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>',
  cardView: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>',
  tableView: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="3" y1="15" x2="21" y2="15"></line><line x1="3" y1="21" x2="21" y2="21"></line><line x1="9" y1="3" x2="9" y2="21"></line></svg>',
  globe: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>',
  upload: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>',
  database: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>',
  download: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>',
  sparkles: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>',
  settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>',
  bell: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>',
  reindex: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-svg"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><polyline points="3 3 3 8 8 8"></polyline><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
  chevronRight: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="icon-svg" style="width:16px;height:16px;"><polyline points="9 18 15 12 9 6"></polyline></svg>'
};

function injectStaticIcons() {
  const setIcon = (id, svgHtml) => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = svgHtml;
  };
  setIcon('appLogoIcon', SVG_RAW.globe);
  setIcon('headerFolderIcon', SVG_RAW.folder);
  setIcon('headerRefreshIcon', SVG_RAW.refresh);
  setIcon('headerReindexIcon', SVG_RAW.reindex);
  setIcon('headerBellIcon', SVG_RAW.bell);
  setIcon('notifMenuBellIcon', SVG_RAW.bell);
  setIcon('hubBellIcon', SVG_RAW.bell);
  setIcon('menuNotifIcon', SVG_RAW.bell);
  setIcon('toolsIcon', SVG_RAW.settings);
  setIcon('menuBookmarkIcon', SVG_RAW.tag);
  setIcon('menuBackupIcon', SVG_RAW.database);
  setIcon('menuExportIcon', SVG_RAW.download);
  setIcon('menuImportIcon', SVG_RAW.upload);
  setIcon('menuCsvIcon', SVG_RAW.excel);

  setIcon('tabGlobalIcon', SVG_RAW.globe);
  setIcon('tabScopedIcon', SVG_RAW.target);

  setIcon('modeGeneralIcon', SVG_RAW.search);
  setIcon('modeTelecomIcon', SVG_RAW.phone);
  setIcon('scopedModeGeneralIcon', SVG_RAW.search);
  setIcon('scopedModeTelecomIcon', SVG_RAW.phone);

  setIcon('searchHeroIcon', SVG_RAW.search);
  setIcon('clearSearchIcon', SVG_RAW.cross);
  setIcon('btnSearchIcon', SVG_RAW.search);

  setIcon('filterAllIcon', SVG_RAW.sparkles);
  setIcon('filterDocIcon', SVG_RAW.pdf);
  setIcon('filterSheetIcon', SVG_RAW.excel);
  setIcon('filterImageIcon', SVG_RAW.image);
  setIcon('filterPhoneIcon', SVG_RAW.phone);
  setIcon('filterGroupIcon', SVG_RAW.folder);

  setIcon('viewCardIcon', SVG_RAW.cardView);
  setIcon('viewTableIcon', SVG_RAW.tableView);

  setIcon('scopedFolderBoxIcon', SVG_RAW.folder);
  setIcon('scopedPickBtnIcon', SVG_RAW.folder);
  setIcon('scopedPickFileIcon', SVG_RAW.doc);
  setIcon('scopedUploadBoxIcon', SVG_RAW.upload);
  setIcon('scopedDropIcon', SVG_RAW.image);
  setIcon('activeScopeIcon', SVG_RAW.folder);
  setIcon('searchScopedHeroIcon', SVG_RAW.search);
  setIcon('clearScopedIcon', SVG_RAW.cross);
  setIcon('scopedViewCardIcon', SVG_RAW.cardView);
  setIcon('scopedViewTableIcon', SVG_RAW.tableView);

  setIcon('modalSettingsIcon', SVG_RAW.settings);
  setIcon('headerDbIcon', SVG_RAW.database);
  setIcon('headerSettingsIcon', SVG_RAW.settings);

  setIcon('folderModalIcon', SVG_RAW.folder);
  setIcon('folderModalBtnIcon', SVG_RAW.folder);
  setIcon('filterModalIcon', SVG_RAW.tag);
  setIcon('bookmarkModalIcon', SVG_RAW.tag);
  setIcon('contextModalIcon', SVG_RAW.context);

  setIcon('imageModalIcon', SVG_RAW.image);
  setIcon('ocrToggleIcon', SVG_RAW.eye);
  setIcon('zoomInIcon', SVG_RAW.zoomIn);
  setIcon('zoomOutIcon', SVG_RAW.zoomOut);
  setIcon('resetZoomIcon', SVG_RAW.refresh);
  setIcon('closeModalIcon', SVG_RAW.cross);
  setIcon('copyAllIcon', SVG_RAW.copy);
}

function toggleToolsDropdown(e) {
  e.stopPropagation();
  const notifDd = document.getElementById('notifDropdown');
  const dbDd = document.getElementById('dbDropdown');
  if (notifDd) notifDd.classList.remove('open');
  if (dbDd) dbDd.classList.remove('open');
  document.getElementById('toolsDropdown').classList.toggle('open');
}

function toggleNotifDropdown(e) {
  e.stopPropagation();
  const toolsDd = document.getElementById('toolsDropdown');
  const dbDd = document.getElementById('dbDropdown');
  if (toolsDd) toolsDd.classList.remove('open');
  if (dbDd) dbDd.classList.remove('open');
  const notifDd = document.getElementById('notifDropdown');
  const isOpen = notifDd.classList.toggle('open');
  if (isOpen) {
    fetchNotifications();
  }
}

document.addEventListener('click', (e) => {
  const toolsDd = document.getElementById('toolsDropdown');
  if (toolsDd && !toolsDd.contains(e.target)) toolsDd.classList.remove('open');
  const notifDd = document.getElementById('notifDropdown');
  if (notifDd && !notifDd.contains(e.target)) notifDd.classList.remove('open');
  const dbDd = document.getElementById('dbDropdown');
  if (dbDd && !dbDd.contains(e.target)) dbDd.classList.remove('open');
});

// Force Refresh: Recheck files without wiping the index
async function triggerForceRefresh() {
  showToast("🔄 Rechecking index folder for changes...");
  try {
    const res = await fetch('/api/index/refresh', { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      showToast("⚡ Force refresh started! Checking file updates...");
      pollProgress();
      fetchNotifications();
    } else {
      alert(data.error || "Failed to start force refresh.");
    }
  } catch (e) {
    showToast("❌ Network error triggering refresh");
  }
}

// Force Re-Index: Full wipe and rebuild with confirmation
async function triggerForceReindex() {
  const confirmed = confirm("⚠️ ATTENTION: Force Re-Index will wipe the current index (universal search, OCR text, and CDR records) and re-index all documents from scratch.\n\nA safety backup will be created automatically.\n\nDo you want to proceed?");
  if (!confirmed) return;

  showToast("🧹 Wiping index & starting fresh re-index...");
  try {
    const res = await fetch('/api/index/reindex', { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      showToast("🚀 Re-index in progress! Tracking full scan...");
      pollProgress();
      fetchNotifications();
    } else {
      alert(data.error || "Failed to start re-indexing.");
    }
  } catch (e) {
    showToast("❌ Network error triggering re-index");
  }
}

// Notification Hub and Badge Management
let cachedNotifications = [];

async function fetchNotifications() {
  try {
    const res = await fetch('/api/notifications?limit=25');
    const data = await res.json();
    cachedNotifications = data.events || [];
    renderNotificationBadge(data.unread_count || 0);
    renderNotificationDropdown(cachedNotifications);
  } catch (e) {
    console.error("Error fetching notifications:", e);
  }
}

function renderNotificationBadge(unreadCount) {
  const badge = document.getElementById('notifBadge');
  const unreadLabel = document.getElementById('notifUnreadBadge');
  if (badge) {
    if (unreadCount > 0) {
      badge.style.display = 'inline-block';
      badge.innerText = unreadCount > 99 ? '99+' : unreadCount;
    } else {
      badge.style.display = 'none';
    }
  }
  if (unreadLabel) {
    unreadLabel.innerText = `${unreadCount} unread`;
  }
}

function renderNotificationDropdown(events) {
  const container = document.getElementById('notifDropdownList');
  if (!container) return;
  if (!events || events.length === 0) {
    container.innerHTML = '<div style="padding:20px; text-align:center; color:var(--text-dim); font-size:0.8rem;">No file changes recorded yet.</div>';
    return;
  }

  container.innerHTML = events.slice(0, 10).map(ev => {
    let tagClass = 'tag-modified';
    let typeName = ev.event_type;
    if (ev.event_type === 'added') { tagClass = 'tag-added'; typeName = 'Added'; }
    else if (ev.event_type === 'modified') { tagClass = 'tag-modified'; typeName = 'Updated'; }
    else if (ev.event_type === 'deleted') { tagClass = 'tag-deleted'; typeName = 'Removed'; }
    else if (ev.event_type === 'renamed') { tagClass = 'tag-renamed'; typeName = 'Renamed'; }
    else if (ev.event_type.startsWith('reindex')) { tagClass = 'tag-reindex'; typeName = 'Re-Index'; }

    return `
      <div class="notif-item ${ev.is_read ? '' : 'unread'}" onclick="markSingleNotificationRead(${ev.id})">
        <span class="notif-type-tag ${tagClass}">${typeName}</span>
        <div style="flex:1; overflow:hidden;">
          <div style="font-weight:600; color:#f8fafc; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" title="${escapeHtml(ev.file_path)}">
            ${escapeHtml(ev.filename || ev.file_path)}
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">
            ${escapeHtml(ev.details || '')}
          </div>
          <div style="font-size:0.7rem; color:var(--text-dim); margin-top:3px;">
            🕒 ${escapeHtml(ev.created_at || '')}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

async function markSingleNotificationRead(id) {
  try {
    await fetch('/api/notifications/read', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: [id] })
    });
    fetchNotifications();
  } catch (e) {
    console.error(e);
  }
}

async function markAllNotificationsRead() {
  try {
    await fetch('/api/notifications/read', { method: 'POST' });
    showToast("✓ All notifications marked as read");
    fetchNotifications();
    if (document.getElementById('notificationHubModal').classList.contains('active')) {
      loadNotificationHubContent();
    }
  } catch (e) {
    showToast("❌ Error marking notifications read");
  }
}

async function clearNotificationHistory() {
  if (!confirm("Are you sure you want to clear the notification log history?")) return;
  try {
    await fetch('/api/notifications/clear', { method: 'POST' });
    showToast("🗑 Notification history cleared");
    fetchNotifications();
    if (document.getElementById('notificationHubModal').classList.contains('active')) {
      loadNotificationHubContent();
    }
  } catch (e) {
    showToast("❌ Error clearing notifications");
  }
}

function openNotificationHub() {
  const dd = document.getElementById('notifDropdown');
  if (dd) dd.classList.remove('open');
  const toolsDd = document.getElementById('toolsDropdown');
  if (toolsDd) toolsDd.classList.remove('open');
  document.getElementById('notificationHubModal').classList.add('active');
  loadNotificationHubContent();
}

function closeNotificationHub() {
  document.getElementById('notificationHubModal').classList.remove('active');
}

async function loadNotificationHubContent() {
  const container = document.getElementById('hubNotificationList');
  const badge = document.getElementById('hubTotalBadge');
  container.innerHTML = '<div style="padding:24px; text-align:center; color:var(--text-dim);">Loading change log...</div>';

  try {
    const res = await fetch('/api/notifications?limit=200');
    const data = await res.json();
    const list = data.events || [];
    badge.innerText = `${data.total || list.length} total event(s) logged`;

    if (list.length === 0) {
      container.innerHTML = '<div style="padding:32px; text-align:center; color:var(--text-dim);">No file change events recorded in database yet.</div>';
      return;
    }

    container.innerHTML = list.map(ev => {
      let tagClass = 'tag-modified';
      let typeName = ev.event_type;
      if (ev.event_type === 'added') { tagClass = 'tag-added'; typeName = 'File Added'; }
      else if (ev.event_type === 'modified') { tagClass = 'tag-modified'; typeName = 'File Updated'; }
      else if (ev.event_type === 'deleted') { tagClass = 'tag-deleted'; typeName = 'File Deleted / Pruned'; }
      else if (ev.event_type === 'renamed') { tagClass = 'tag-renamed'; typeName = 'File Renamed / Moved'; }
      else if (ev.event_type.startsWith('reindex')) { tagClass = 'tag-reindex'; typeName = 'Re-Index Session'; }

      return `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; padding:12px; border-bottom:1px solid #1e293b50; gap:12px; ${ev.is_read ? '' : 'background:rgba(56,189,248,0.04); border-left:3px solid var(--accent);'}">
          <div style="display:flex; gap:10px; align-items:flex-start; flex:1; overflow:hidden;">
            <span class="notif-type-tag ${tagClass}" style="margin-top:2px;">${typeName}</span>
            <div style="flex:1; overflow:hidden;">
              <div style="font-weight:600; color:#f8fafc; font-size:0.86rem; word-break:break-all;">
                ${escapeHtml(ev.filename || ev.file_path)}
              </div>
              <div style="font-size:0.78rem; color:var(--text-muted); margin-top:3px;">
                ${escapeHtml(ev.details || '')}
              </div>
              ${ev.old_path ? `<div style="font-size:0.75rem; color:#94a3b8; font-family:'JetBrains Mono', monospace; margin-top:2px;">Previous: ${escapeHtml(ev.old_path)}</div>` : ''}
              <div style="font-size:0.74rem; color:var(--text-dim); margin-top:4px;">
                Path: <span style="font-family:'JetBrains Mono', monospace;">${escapeHtml(ev.file_path)}</span>
              </div>
            </div>
          </div>
          <div style="text-align:right; white-space:nowrap; font-size:0.76rem; color:var(--text-muted);">
            <div>${escapeHtml(ev.created_at || '')}</div>
            ${ev.records_count ? `<div style="color:var(--accent); font-weight:600; margin-top:4px;">${ev.records_count.toLocaleString()} records</div>` : ''}
          </div>
        </div>
      `;
    }).join('');
  } catch (e) {
    container.innerHTML = `<div style="padding:24px; text-align:center; color:#f43f5e;">Failed to load notification events: ${e}</div>`;
  }
}


let currentPage = 0;
const pageSize = 50;
let currentQuery = '';
let activeTypeFilter = 'all';
let currentSearchMode = 'general';
let totalResults = 0;
let lastResults = [];
let progressPollInterval = null;
let currentViewMode = 'card';
let debounceTimer = null;

function setSearchMode(mode) {
  currentSearchMode = mode;
  const isGeneral = (mode === 'general');
  document.getElementById('modeBtnGeneral').classList.toggle('active', isGeneral);
  document.getElementById('modeBtnTelecom').classList.toggle('active', !isGeneral);

  const desc = document.getElementById('modeDescText');
  const input = document.getElementById('queryInput');
  if (isGeneral) {
    desc.innerText = '📄 Universal search across documents, PDFs, OCR, sheets & text';
    input.placeholder = 'Search keywords, document text, topics, Egyptian/EN names, OCR images...';
  } else {
    desc.innerText = '📞 CDR caller, callee, tower cell, duration & phone intelligence';
    input.placeholder = 'Search phone numbers (e.g. 010..., 2012...), caller/callee, IMEI/IMSI, cell towers...';
  }

  if (currentQuery) {
    doSearch(0);
  }
}

function showToast(msg, duration = 3000) {
  const toast = document.getElementById('toast');
  toast.innerHTML = msg;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, duration);
}

function copyToClipboard(text, label = 'Copied') {
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    showToast(`📋 ${label}: ${escapeHtml(text.slice(0, 35))}${text.length > 35 ? '...' : ''}`);
  }).catch(() => {
    showToast(`📋 Copied to clipboard`);
  });
}

function switchView(mode) {
  currentViewMode = mode;
  document.getElementById('btnViewCard').classList.toggle('active', mode === 'card');
  document.getElementById('btnViewTable').classList.toggle('active', mode === 'table');
  document.getElementById('cardsContainer').style.display = (mode === 'card') ? 'flex' : 'none';
  document.getElementById('tableContainer').style.display = (mode === 'table') ? 'block' : 'none';
  if (lastResults && lastResults.length > 0) {
    renderFilteredResults();
  }
}

function handleInput(e) {
  const val = e.target.value.trim();
  document.getElementById('clearSearchBtn').style.display = val ? 'block' : 'none';
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    if (val.length >= 2 || val.length === 0) {
      doSearch(0);
    }
  }, 350);
}

function clearSearch() {
  document.getElementById('queryInput').value = '';
  document.getElementById('clearSearchBtn').style.display = 'none';
  document.getElementById('queryInput').focus();
  doSearch(0);
}

let isGroupedByFile = false;
let expandedGroupKeys = new Set();

function toggleGroupByFile() {
  isGroupedByFile = !isGroupedByFile;
  const btn = document.getElementById('btnGroupToggle');
  const pill = document.getElementById('btnFilterGroupPill');
  if (btn) btn.classList.toggle('active', isGroupedByFile);
  if (pill) pill.classList.toggle('active', isGroupedByFile);
  
  const icon = document.getElementById('groupToggleBtnIcon');
  const text = document.getElementById('groupToggleBtnText');
  if (icon && text) {
    icon.innerText = isGroupedByFile ? '📑' : '📁';
    text.innerText = isGroupedByFile ? 'Grouped (File)' : 'Group by File';
  }

  showToast(isGroupedByFile ? "📁 Results grouped by File & Sheet" : "📄 Showing individual results");
  renderFilteredResults();
}

function setTypeFilter(type, btnEl) {
  activeTypeFilter = type;
  document.querySelectorAll('.filter-tabs-row .filter-pill').forEach(el => {
    el.classList.remove('active');
  });
  if (btnEl) btnEl.classList.add('active');
  renderFilteredResults();
}

function renderFilteredResults() {
  if (!lastResults) return;
  let filtered = lastResults;
  if (activeTypeFilter === 'doc') {
    filtered = lastResults.filter(r => {
      const ext = (r.file || '').split('.').pop().toLowerCase();
      return ['pdf', 'docx', 'doc', 'odt', 'txt'].includes(ext);
    });
  } else if (activeTypeFilter === 'sheet') {
    filtered = lastResults.filter(r => {
      const ext = (r.file || '').split('.').pop().toLowerCase();
      return ['xlsx', 'xls', 'csv', 'tsv'].includes(ext);
    });
  } else if (activeTypeFilter === 'image') {
    filtered = lastResults.filter(r => isImageFile(r.file));
  } else if (activeTypeFilter === 'phone') {
    filtered = lastResults.filter(r => (r.target && r.target !== '—') || (r.other && r.other !== '—') || r.phone);
  }

  document.getElementById('resultsCount').innerText = `${filtered.length.toLocaleString()} result(s)`;
  
  if (isGroupedByFile) {
    renderGroupedByFile(filtered);
  } else {
    renderCards(filtered);
  }
  renderTableRows(filtered);

  // If user specifically filtered by image and results exist, preview first image
  if (activeTypeFilter === 'image' && filtered.length > 0) {
    const firstImg = filtered[0];
    showImagePreview(firstImg.path, firstImg.sheet, currentQuery);
  }
}

async function refreshStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    const statsBadge = document.getElementById('statsBadge');
    const fldEl = document.getElementById('currentFolderText');
    const fldTag = document.getElementById('currentFolderTag');

    if (!data.has_active_db || !data.active_db) {
      if (statsBadge) statsBadge.innerText = "No database loaded";
      if (fldEl) fldEl.innerText = "No folder loaded";
      if (fldTag) fldTag.title = "No active database index loaded (click to choose)";
      updateWatcherUI(false);
      renderInitialEmptyState();
      return;
    }

    if (statsBadge) statsBadge.innerText = `${(data.files || 0).toLocaleString()} files • ${(data.records || 0).toLocaleString()} entries`;
    if (typeof data.watcher !== 'undefined') {
      updateWatcherUI(data.watcher);
    }
    if (fldEl && data.folder) {
      const parts = data.folder.split('/');
      const shortName = parts.slice(-2).join('/') || data.folder;
      fldEl.innerText = shortName;
      if (fldTag) fldTag.title = `Active Index Directory: ${data.folder} (click to change)`;
    } else if (fldEl) {
      fldEl.innerText = "No folder set";
    }
    renderInitialEmptyState();
  } catch (e) {
    console.error(e);
  }
}

async function refreshWatcherStatus() {
  try {
    const res = await fetch('/api/watch/status');
    const data = await res.json();
    updateWatcherUI(data.active);
  } catch (e) {
    console.error(e);
  }
}

function updateWatcherUI(isActive) {
  const dot = document.getElementById('watcherDot');
  const label = document.getElementById('watcherLabel');
  if (isActive) {
    dot.className = 'watcher-dot active';
    label.innerText = 'Watcher Active';
    label.style.color = '#10b981';
  } else {
    dot.className = 'watcher-dot paused';
    label.innerText = 'Watcher Paused';
    label.style.color = '#94a3b8';
  }
}

async function toggleWatcher() {
  try {
    const res = await fetch('/api/watch/toggle', { method: 'POST' });
    const data = await res.json();
    updateWatcherUI(data.active);
    showToast(data.message || (data.active ? "Watcher turned ON" : "Watcher turned OFF"));
  } catch (e) {
    showToast("❌ Network error toggling watcher");
  }
}

// Database Switcher and Settings Management
let cachedDatabases = [];

function toggleDbDropdown(e) {
  e.stopPropagation();
  const dd = document.getElementById('dbDropdown');
  const toolsDd = document.getElementById('toolsDropdown');
  const notifDd = document.getElementById('notifDropdown');
  if (toolsDd) toolsDd.classList.remove('open');
  if (notifDd) notifDd.classList.remove('open');
  const isOpen = dd.classList.toggle('open');
  if (isOpen) {
    loadDatabases();
  }
}

async function loadDatabases() {
  try {
    const res = await fetch('/api/databases');
    const data = await res.json();
    if (data.ok) {
      cachedDatabases = data.databases || [];
      renderDbDropdownList(cachedDatabases, data.active_db);
      renderSettingsDbList(cachedDatabases, data.active_db);

      const activeObj = cachedDatabases.find(d => d.id === data.active_db);
      const activeNameEl = document.getElementById('activeDbName');
      const activePill = document.querySelector('.db-switch-pill');
      if (activeNameEl) {
        if (activeObj && data.active_db) {
          activeNameEl.innerText = activeObj.nickname || activeObj.id;
          if (activePill) activePill.classList.remove('no-db');
        } else {
          activeNameEl.innerText = "Select Index (Empty)";
          if (activePill) activePill.classList.add('no-db');
        }
      }
    }
  } catch (e) {
    console.error("Error loading databases:", e);
  }
}

function renderInitialEmptyState() {
  const container = document.getElementById('cardsContainer');
  if (!container) return;
  const q = (document.getElementById('queryInput')?.value || '').trim();
  if (q.length > 0) return;

  const activeObj = cachedDatabases.find(d => d.is_active);
  if (!activeObj) {
    container.innerHTML = `
      <div id="cardsInitialPlaceholder" style="text-align:center; padding: 48px 20px; color:var(--text-muted); background: var(--bg-card); border-radius:10px; border:1px solid var(--border-subtle); width:100%;">
        <div style="font-size:2rem; margin-bottom:8px;">🗄️</div>
        <div style="font-weight:600; color:var(--text-main); font-size:1.05rem; margin-bottom:6px;">No Database Index Loaded</div>
        <div style="font-size:0.84rem; color:var(--text-dim); margin-bottom:14px;">Select an index from the dropdown list above to begin searching, or create a new index.</div>
        <button class="btn-header primary" onclick="toggleDbDropdown(event)">📂 Choose Database Index ▾</button>
      </div>
    `;
  } else {
    container.innerHTML = `
      <div style="text-align:center; padding: 48px; color:#64748b; background: var(--bg-card); border-radius:10px; border:1px solid var(--border-subtle); width:100%;">
        Enter any keyword, name, or phone number above to search across the entire archive.
      </div>
    `;
  }
}

function renderDbDropdownList(databases, activeId) {
  const container = document.getElementById('dbListContainer');
  if (!container) return;
  if (!databases || databases.length === 0) {
    container.innerHTML = '<div style="padding:12px; text-align:center; color:var(--text-dim); font-size:0.8rem;">No databases registered yet. Click + New to index a folder.</div>';
    return;
  }

  let html = '';
  if (activeId) {
    html += `
      <div class="db-card-item unload-card" onclick="switchDatabase('')" style="margin-bottom:8px; border:1px dashed var(--border); background:rgba(255,255,255,0.02); text-align:center; padding:8px 10px; cursor:pointer; border-radius:6px;">
        <span style="font-size:0.78rem; color:var(--text-muted);">⚪ <b>Unload Current Index</b> (Empty State)</span>
      </div>
    `;
  }

  databases.forEach(db => {
    const isActive = (db.id === activeId);
    const badgeText = `${(db.files_count || 0).toLocaleString()} files • ${(db.records_count || 0).toLocaleString()} records`;
    const sizeText = formatFileSize(db.size);
    const watchIndicator = db.watch_folder ? (db.watch_active ? '🟢 Watching' : '⚪ Watch paused') : 'No watch folder';

    html += `
      <div class="db-card-item ${isActive ? 'active' : ''}" onclick="switchDatabase('${escapeHtml(db.id)}')">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div style="flex:1; min-width:0;">
            <div class="db-title-row">
              <span class="db-name">${escapeHtml(db.nickname || db.id)}</span>
              ${isActive ? '<span class="db-active-badge">ACTIVE</span>' : '<span style="font-size:0.72rem; color:var(--accent); font-weight:600; margin-left:6px; cursor:pointer;">[Click to Load]</span>'}
            </div>
            <div class="db-subtext" title="${escapeHtml(db.path)}">${escapeHtml(db.filename)} ${sizeText ? '• ' + sizeText : ''}</div>
            <div class="db-subtext" style="color:#64748b; margin-top:2px;">📁 ${badgeText} • <span style="font-size:0.7rem;">${watchIndicator}</span></div>
          </div>
          <div style="display:flex; gap:4px; margin-left:6px;" onclick="event.stopPropagation();">
            <button class="db-action-btn" title="Rename Nickname" onclick="renameDatabasePrompt('${escapeHtml(db.id)}', '${escapeHtml(db.nickname || db.id)}')">✏️</button>
            ${!isActive ? `<button class="db-action-btn delete" title="Delete Database Entry" onclick="deleteDatabasePrompt('${escapeHtml(db.id)}', '${escapeHtml(db.nickname || db.id)}')">🗑</button>` : ''}
          </div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function renderSettingsDbList(databases, activeId) {
  const container = document.getElementById('settingsDbList');
  const countBadge = document.getElementById('settingsDbCountBadge');
  if (!container) return;
  if (countBadge) {
    countBadge.innerText = `${databases.length} database(s)`;
  }
  if (!databases || databases.length === 0) {
    container.innerHTML = '<div style="padding:16px; text-align:center; color:var(--text-dim); font-size:0.8rem;">No databases registered.</div>';
    return;
  }

  let html = '';
  databases.forEach(db => {
    const isActive = (db.id === activeId);
    const sizeText = formatFileSize(db.size);
    html += `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 10px; margin-bottom:6px; background:#0f172a; border-radius:6px; border:1px solid ${isActive ? 'var(--accent)' : 'var(--border)'};">
        <div style="min-width:0; flex:1;">
          <div style="display:flex; align-items:center; gap:6px;">
            <b style="color:#f8fafc; font-size:0.84rem;">${escapeHtml(db.nickname || db.id)}</b>
            ${isActive ? '<span class="db-active-badge">ACTIVE</span>' : ''}
            <span style="font-size:0.72rem; color:var(--text-dim); font-family:\'JetBrains Mono\', monospace;">(${escapeHtml(db.filename)})</span>
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">
            ${(db.files_count || 0).toLocaleString()} files • ${(db.records_count || 0).toLocaleString()} records ${sizeText ? '• ' + sizeText : ''}
            ${db.watch_folder ? `• 📁 <span title="${escapeHtml(db.watch_folder)}">${escapeHtml(db.watch_folder.split('/').slice(-2).join('/'))}</span>` : ''}
          </div>
        </div>
        <div style="display:flex; gap:6px; margin-left:10px;">
          ${!isActive ? `<button class="btn-header" style="padding:3px 8px; font-size:0.75rem;" onclick="switchDatabase('${escapeHtml(db.id)}')">Switch To</button>` : ''}
          <button class="btn-header" style="padding:3px 8px; font-size:0.75rem;" onclick="renameDatabasePrompt('${escapeHtml(db.id)}', '${escapeHtml(db.nickname || db.id)}')">Rename</button>
          ${!isActive ? `<button class="btn-header" style="padding:3px 8px; font-size:0.75rem; color:#fca5a5;" onclick="deleteDatabasePrompt('${escapeHtml(db.id)}', '${escapeHtml(db.nickname || db.id)}')">Delete</button>` : ''}
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
}

async function switchDatabase(id) {
  const toolsDd = document.getElementById('dbDropdown');
  if (toolsDd) toolsDd.classList.remove('open');
  showToast(id ? `🔄 Loading database index...` : `⚪ Unloading database...`);
  try {
    const res = await fetch('/api/databases/switch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: id || "" })
    });
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ ${data.message || 'Updated database successfully!'}`);
      await loadDatabases();
      await refreshStats();
      await refreshWatcherStatus();
      loadQuickFilters();
      refreshBookmarkCount();
      fetchNotifications();
      if (currentQuery) {
        doSearch(0);
      } else {
        renderInitialEmptyState();
      }
    } else {
      alert(data.error || "Failed to switch database");
    }
  } catch (e) {
    showToast("❌ Network error switching database");
  }
}

async function renameDatabasePrompt(id, currentNick) {
  const newNick = prompt(`Enter new nickname for database "${currentNick}":`, currentNick);
  if (!newNick || newNick.trim() === '' || newNick.trim() === currentNick) return;
  try {
    const res = await fetch('/api/databases/rename', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: id, nickname: newNick.trim() })
    });
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ Database renamed to "${newNick.trim()}"`);
      loadDatabases();
    } else {
      alert(data.error || "Failed to rename database");
    }
  } catch (e) {
    showToast("❌ Network error renaming database");
  }
}

async function deleteDatabasePrompt(id, nick) {
  const confirmed = confirm(`Are you sure you want to remove the database profile "${nick}" from the registry?\n\nThe underlying .db file will remain untouched in your storage folder.`);
  if (!confirmed) return;

  try {
    const res = await fetch('/api/databases/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: id, delete_file: false })
    });
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ Removed database "${nick}"`);
      loadDatabases();
    } else {
      alert(data.error || "Failed to delete database");
    }
  } catch (e) {
    showToast("❌ Network error deleting database");
  }
}

// Settings Modal Management
async function openSettingsModal() {
  const modal = document.getElementById('settingsModal');
  if (!modal) return;
  modal.classList.add('active');

  try {
    const res = await fetch('/api/settings');
    const data = await res.json();
    if (data.ok) {
      document.getElementById('settingsDbStorageDir').value = data.db_storage_dir || '';
      const ws = data.watcher_settings || {};
      if (ws.poll_interval_seconds) {
        document.getElementById('settingsWatcherPoll').value = String(ws.poll_interval_seconds);
      }
      if (ws.debounce_delay_seconds) {
        document.getElementById('settingsWatcherDebounce').value = String(ws.debounce_delay_seconds);
      }
      if (ws.max_file_size_mb) {
        document.getElementById('settingsWatcherMaxSize').value = String(ws.max_file_size_mb);
      }
      if (typeof ws.ignore_hidden_temp !== 'undefined') {
        document.getElementById('settingsWatcherIgnoreTemp').checked = Boolean(ws.ignore_hidden_temp);
      }
    }
  } catch (e) {
    console.error("Error loading settings:", e);
  }

  loadDatabases();
}

function closeSettingsModal() {
  const modal = document.getElementById('settingsModal');
  if (modal) modal.classList.remove('active');
}

async function pickStorageDirNative() {
  try {
    const res = await fetch('/api/dialog/pick-folder');
    const data = await res.json();
    if (data.ok && data.path) {
      document.getElementById('settingsDbStorageDir').value = data.path;
      showToast(`Selected storage folder: ${data.path}`);
    }
  } catch (err) {
    showToast("❌ Could not open folder chooser");
  }
}

async function saveSettings() {
  const storageDir = document.getElementById('settingsDbStorageDir').value.trim();
  const pollInterval = parseInt(document.getElementById('settingsWatcherPoll').value, 10) || 3;
  const debounceDelay = parseInt(document.getElementById('settingsWatcherDebounce').value, 10) || 2;
  const maxSize = parseInt(document.getElementById('settingsWatcherMaxSize').value, 10) || 250;
  const ignoreTemp = document.getElementById('settingsWatcherIgnoreTemp').checked;

  try {
    const res = await fetch('/api/settings/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        db_storage_dir: storageDir,
        watcher_settings: {
          poll_interval_seconds: pollInterval,
          debounce_delay_seconds: debounceDelay,
          max_file_size_mb: maxSize,
          ignore_hidden_temp: ignoreTemp
        }
      })
    });
    const data = await res.json();
    if (data.ok) {
      showToast("✅ Settings saved successfully!");
      closeSettingsModal();
      loadDatabases();
      refreshWatcherStatus();
    } else {
      alert(data.error || "Failed to save settings");
    }
  } catch (e) {
    showToast("❌ Network error saving settings");
  }
}

function autoSuggestDbNickname() {
  const folderVal = document.getElementById('folderPathInput').value.trim();
  const nickInput = document.getElementById('folderNicknameInput');
  if (!folderVal) return;
  // If user hasn't explicitly written a nickname, suggest leaf folder name
  if (!nickInput.dataset.userEdited || nickInput.value.trim() === '') {
    const leaf = folderVal.replace(/\/+$/, '').split('/').pop();
    if (leaf) {
      nickInput.value = leaf;
    }
  }
}

function openFolderModal(createNew = false) {
  const modal = document.getElementById('folderModal');
  const title = document.getElementById('folderModalTitleText');
  const createCheck = document.getElementById('folderCreateNewDbCheck');
  const nickInput = document.getElementById('folderNicknameInput');
  const pathInput = document.getElementById('folderPathInput');

  if (nickInput) {
    nickInput.value = '';
    delete nickInput.dataset.userEdited;
  }
  if (pathInput) pathInput.value = '';

  if (createCheck) {
    createCheck.checked = createNew ? true : true;
  }
  if (title) {
    title.innerText = createNew ? "Index Folder into New Database" : "Index Directory";
  }

  modal.classList.add('active');
}

function closeFolderModal() {
  document.getElementById('folderModal').classList.remove('active');
}

async function pickFolderModalNative() {
  try {
    const res = await fetch('/api/dialog/pick-folder');
    const data = await res.json();
    if (data.ok && data.path) {
      document.getElementById('folderPathInput').value = data.path;
      autoSuggestDbNickname();
      showToast(`Selected: ${data.path}`);
    }
  } catch (err) {
    showToast("❌ Could not open folder chooser");
  }
}

function handleModalWebkitFolder(e) {
  const files = e.target.files;
  if (files && files.length > 0) {
    const firstFile = files[0];
    const path = firstFile.webkitRelativePath ? firstFile.webkitRelativePath.split('/')[0] : firstFile.name;
    document.getElementById('folderPathInput').value = path;
    autoSuggestDbNickname();
    showToast(`Selected: ${path}`);
  }
}

async function submitFolderIndex() {
  const folder = document.getElementById('folderPathInput').value.trim();
  const nickname = (document.getElementById('folderNicknameInput').value || '').trim();
  const createDb = document.getElementById('folderCreateNewDbCheck').checked ? '1' : '0';

  if (!folder) {
    alert("Please choose or enter a folder path!");
    return;
  }
  closeFolderModal();
  showToast(`⚡ Starting recursive indexing for ${folder}...`);
  try {
    const url = `/api/index/start?folder=${encodeURIComponent(folder)}&nickname=${encodeURIComponent(nickname)}&create_db=${createDb}`;
    const res = await fetch(url, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      showToast("Indexing launched! Watching progress...");
      pollProgress();
      loadDatabases();
    } else {
      alert(data.error || "Failed to start indexing.");
    }
  } catch (e) {
    showToast("❌ Network error starting indexing");
  }
}

function pollProgress() {
  if (progressPollInterval) clearInterval(progressPollInterval);
  const banner = document.getElementById('progressBanner');
  banner.style.display = 'block';

  progressPollInterval = setInterval(async () => {
    try {
      const res = await fetch('/api/progress');
      const data = await res.json();
      
      const pct = Math.round(data.percent || 0);
      document.getElementById('progressBarFill').style.width = pct + '%';
      document.getElementById('progressPercent').innerText = pct + '%';
      document.getElementById('progressStatus').innerText = data.status || 'Indexing...';
      document.getElementById('progressCurrentFile').innerText = data.current_file || '';
      document.getElementById('progressRecords').innerText = `${(data.records_indexed || 0).toLocaleString()} records indexed`;

      if (!data.in_progress && pct >= 100) {
        clearInterval(progressPollInterval);
        setTimeout(() => {
          banner.style.display = 'none';
          refreshStats();
          showToast("✅ Indexing completed!");
        }, 1800);
      }
    } catch (e) {
      console.error(e);
    }
  }, 1000);
}

function openFilterModal() {
  document.getElementById('filterNameInput').value = '';
  document.getElementById('filterQueryInput').value = '';
  document.getElementById('filterModal').classList.add('active');
}

function closeFilterModal() {
  document.getElementById('filterModal').classList.remove('active');
}

async function submitFilter() {
  const name = document.getElementById('filterNameInput').value.trim();
  const query = document.getElementById('filterQueryInput').value.trim();
  if (!name || !query) {
    alert("Please fill in both name and query!");
    return;
  }
  closeFilterModal();
  try {
    const res = await fetch('/api/filters/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, query })
    });
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ Added filter "${name}"`);
      loadQuickFilters();
    } else {
      alert("Failed to save filter.");
    }
  } catch (e) {
    showToast("❌ Network error saving filter");
  }
}

async function loadQuickFilters() {
  try {
    const res = await fetch('/api/filters');
    const data = await res.json();
    const list = document.getElementById('quickChipsList');
    list.innerHTML = '';
    data.filters.forEach(f => {
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.innerHTML = `${SVG_RAW.tag} ${escapeHtml(f.name)}`;
      chip.title = `Query: ${f.query} (Right click to delete)`;
      chip.onclick = () => {
        document.getElementById('queryInput').value = f.query;
        document.getElementById('clearSearchBtn').style.display = 'block';
        doSearch(0);
      };
      chip.oncontextmenu = async (e) => {
        e.preventDefault();
        if (confirm(`Delete filter "${f.name}"?`)) {
          await deleteQuickFilter(f.id);
        }
      };
      list.appendChild(chip);
    });
  } catch (e) {
    console.error(e);
  }
}

async function deleteQuickFilter(id) {
  try {
    const res = await fetch('/api/filters/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    });
    const data = await res.json();
    if (data.ok) {
      showToast("Filter removed");
      loadQuickFilters();
    }
  } catch (e) {
    showToast("❌ Network error removing filter");
  }
}

function openBookmarkModal(file, sheet, row, targetPhone) {
  document.getElementById('bmFilePath').value = file;
  document.getElementById('bmSheetName').value = sheet;
  document.getElementById('bmRowIdx').value = row;
  document.getElementById('bmNotesInput').value = '';
  document.getElementById('bookmarkTargetLabel').innerText = `${file.split('/').pop()} • ${sheet} • Row ${row} ${targetPhone ? '(' + targetPhone + ')' : ''}`;
  document.getElementById('bookmarkModal').classList.add('active');
}

function closeBookmarkModal() {
  document.getElementById('bookmarkModal').classList.remove('active');
}

async function submitBookmark() {
  const file = document.getElementById('bmFilePath').value;
  const sheet = document.getElementById('bmSheetName').value;
  const row = parseInt(document.getElementById('bmRowIdx').value, 10);
  const tag = document.getElementById('bmTagInput').value;
  const notes = document.getElementById('bmNotesInput').value.trim();

  closeBookmarkModal();
  try {
    const res = await fetch('/api/bookmarks/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file, sheet, row, tag, notes })
    });
    const data = await res.json();
    if (data.ok) {
      showToast(`🔖 Bookmarked as [${tag}]`);
      refreshBookmarkCount();
    } else {
      alert("Failed to bookmark record.");
    }
  } catch (e) {
    showToast("❌ Network error bookmarking record");
  }
}

async function refreshBookmarkCount() {
  try {
    const res = await fetch('/api/bookmarks');
    const data = await res.json();
    document.getElementById('bmCountBadge').innerText = data.bookmarks.length;
  } catch (e) {}
}

async function viewBookmarks() {
  try {
    const res = await fetch('/api/bookmarks');
    const data = await res.json();
    if (data.bookmarks.length === 0) {
      showToast("No bookmarks saved yet");
      return;
    }
    const fakeRows = data.bookmarks.map(b => ({
      file: b.file_path.split('/').pop(),
      path: b.file_path,
      sheet: b.sheet_name,
      row: b.row_idx,
      target: b.tag,
      other: b.notes || '—',
      name: '—',
      time: b.created_at || '—',
      dir: '—',
      snippet: `[${b.tag}] ${b.notes || 'No annotation'}`
    }));
    totalResults = fakeRows.length;
    lastResults = fakeRows;
    renderCards(fakeRows);
    document.getElementById('resultsCount').innerText = `${fakeRows.length} Bookmarks loaded`;
  } catch (e) {
    showToast("❌ Network error fetching bookmarks");
  }
}

async function doSearch(page = 0) {
  const q = document.getElementById('queryInput').value.trim();
  if (!q) {
    lastResults = [];
    totalResults = 0;
    renderViewData({ rows: [], total: 0 });
    document.getElementById('resultsCount').innerText = "Ready";
    document.getElementById('timing').innerText = "0ms";
    return;
  }

  currentPage = page;
  currentQuery = q;
  const offset = currentPage * pageSize;

  const t0 = performance.now();
  document.getElementById('resultsCount').innerText = "Searching...";

  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(currentQuery)}&limit=${pageSize}&offset=${offset}&mode=${encodeURIComponent(currentSearchMode)}`);
    const data = await res.json();
    const t1 = performance.now();
    document.getElementById('timing').innerText = `${Math.round(t1 - t0)}ms`;

    renderViewData(data);
  } catch (e) {
    console.error(e);
    document.getElementById('resultsCount').innerText = "Search error";
  }
}

function changePage(delta) {
  const newPage = currentPage + delta;
  if (newPage >= 0 && (newPage * pageSize) < totalResults) {
    doSearch(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function scrollToBottom() {
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function highlightMatch(text, query) {
  if (!text) return '';
  const escaped = escapeHtml(text);
  if (!query) return escaped;

  const cleanQuery = query.trim().replace(/"/g, '');
  if (!cleanQuery) return escaped;

  const terms = cleanQuery.split(/\s+/).filter(t => t.length > 0);
  if (terms.length === 0) return escaped;

  const pattern = terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
  const regex = new RegExp(`(${pattern})`, 'gi');
  return escaped.replace(regex, '<mark class="match-hl">$1</mark>');
}

function getFileExtBadge(filename) {
  const ext = (filename || '').split('.').pop().toLowerCase();
  if (ext === 'pdf') {
    return `<span class="file-type-pill pill-pdf">${SVG_RAW.pdf} PDF</span>`;
  } else if (['xlsx', 'xls', 'csv', 'tsv'].includes(ext)) {
    return `<span class="file-type-pill pill-xlsx">${SVG_RAW.excel} ${ext.toUpperCase()}</span>`;
  } else if (['docx', 'doc', 'odt'].includes(ext)) {
    return `<span class="file-type-pill pill-docx">${SVG_RAW.doc} ${ext.toUpperCase()}</span>`;
  } else if (['png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff'].includes(ext)) {
    return `<span class="file-type-pill pill-image">${SVG_RAW.image} ${ext.toUpperCase()}</span>`;
  } else {
    return `<span class="file-type-pill pill-txt">${SVG_RAW.text} ${ext.toUpperCase() || 'FILE'}</span>`;
  }
}

function renderViewData(data) {
  if (data.no_db) {
    lastResults = [];
    totalResults = 0;
    const paginationBar = document.getElementById('paginationBar');
    const topPaginationBar = document.getElementById('topPaginationBar');
    if (paginationBar) paginationBar.style.display = 'none';
    if (topPaginationBar) topPaginationBar.style.display = 'none';
    const container = document.getElementById('cardsContainer');
    if (container) {
      container.innerHTML = `
        <div style="text-align:center; padding: 48px 20px; color:var(--text-muted); background: var(--bg-card); border-radius:10px; border:1px solid var(--border-subtle); width:100%;">
          <div style="font-size:2rem; margin-bottom:8px;">⚠️</div>
          <div style="font-weight:600; color:#f8fafc; font-size:1.05rem; margin-bottom:6px;">No Database Index Loaded</div>
          <div style="font-size:0.84rem; color:var(--text-dim); margin-bottom:14px;">Please select an index from the database dropdown above before searching.</div>
          <button class="btn-header primary" onclick="toggleDbDropdown(event)">📂 Choose Database Index ▾</button>
        </div>
      `;
    }
    const rc = document.getElementById('resultsCount');
    if (rc) rc.innerText = "No database loaded";
    const tm = document.getElementById('timing');
    if (tm) tm.innerText = "0ms";
    return;
  }

  lastResults = data.rows || [];
  totalResults = data.total || 0;
  const paginationBar = document.getElementById('paginationBar');
  const topPaginationBar = document.getElementById('topPaginationBar');

  if (totalResults > pageSize) {
    const start = currentPage * pageSize + 1;
    const end = Math.min((currentPage + 1) * pageSize, totalResults);
    const infoText = `Showing ${start.toLocaleString()}-${end.toLocaleString()} of ${totalResults.toLocaleString()} records`;
    const pageBadgeText = `Page ${currentPage + 1} of ${Math.ceil(totalResults / pageSize)}`;
    const isPrevDisabled = (currentPage === 0);
    const isNextDisabled = ((currentPage + 1) * pageSize >= totalResults);

    paginationBar.style.display = 'flex';
    document.getElementById('pageInfo').innerText = infoText;
    document.getElementById('pageNumberBadge').innerText = pageBadgeText;
    document.getElementById('prevBtn').disabled = isPrevDisabled;
    document.getElementById('nextBtn').disabled = isNextDisabled;

    if (topPaginationBar) {
      topPaginationBar.style.display = 'flex';
      document.getElementById('topPageInfo').innerText = infoText;
      document.getElementById('topPageNumberBadge').innerText = pageBadgeText;
      document.getElementById('topPrevBtn').disabled = isPrevDisabled;
      document.getElementById('topNextBtn').disabled = isNextDisabled;
    }
  } else if (totalResults > 0) {
    paginationBar.style.display = 'flex';
    document.getElementById('pageInfo').innerText = `${totalResults.toLocaleString()} records`;
    document.getElementById('pageNumberBadge').innerText = `Page 1 of 1`;
    document.getElementById('prevBtn').disabled = true;
    document.getElementById('nextBtn').disabled = true;

    if (topPaginationBar) {
      topPaginationBar.style.display = 'flex';
      document.getElementById('topPageInfo').innerText = `${totalResults.toLocaleString()} records`;
      document.getElementById('topPageNumberBadge').innerText = `Page 1 of 1`;
      document.getElementById('topPrevBtn').disabled = true;
      document.getElementById('topNextBtn').disabled = true;
    }
  } else {
    paginationBar.style.display = 'none';
    if (topPaginationBar) topPaginationBar.style.display = 'none';
  }

  renderFilteredResults();
}

function formatFileSize(bytes) {
  if (!bytes || bytes <= 0) return '';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function toggleFileGroup(groupKey) {
  const card = document.getElementById('group_card_' + groupKey);
  if (!card) return;
  const isOpen = card.classList.contains('open');
  if (isOpen) {
    card.classList.remove('open');
    expandedGroupKeys.delete(groupKey);
  } else {
    card.classList.add('open');
    expandedGroupKeys.add(groupKey);
  }
}

function expandAllGroups(expand) {
  document.querySelectorAll('.file-group-card').forEach(card => {
    const key = card.getAttribute('data-group-key');
    if (expand) {
      card.classList.add('open');
      if (key) expandedGroupKeys.add(key);
    } else {
      card.classList.remove('open');
      if (key) expandedGroupKeys.delete(key);
    }
  });
}

function renderGroupedByFile(rows) {
  const container = document.getElementById('cardsContainer');
  container.innerHTML = '';

  if (!rows || rows.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding: 48px; color:#64748b; background: var(--bg-card); border-radius:10px; border:1px solid var(--border-subtle);">
        No matching records found for "${escapeHtml(currentQuery)}".
      </div>
    `;
    return;
  }

  // Group by path (or path + '#' + sheet)
  const groupMap = new Map();
  rows.forEach(r => {
    const groupKey = (r.path || r.file || 'unknown');
    if (!groupMap.has(groupKey)) {
      groupMap.set(groupKey, {
        file: r.file,
        path: r.path,
        folder: r.folder,
        size: r.size,
        indexed_at: r.indexed_at,
        items: []
      });
    }
    groupMap.get(groupKey).items.push(r);
  });

  const totalGroups = groupMap.size;
  const isGeneral = (currentSearchMode === 'general');

  // Controls bar: Total files count + Expand All / Collapse All
  const controlsBar = document.createElement('div');
  controlsBar.className = 'group-controls-bar';
  controlsBar.innerHTML = `
    <span>📁 <b>${totalGroups}</b> file(s) / sheet(s) matching • <b>${rows.length}</b> total hit(s)</span>
    <div style="display:flex; gap:8px;">
      <button class="btn-action" style="padding:2px 8px; font-size:0.75rem;" onclick="expandAllGroups(true)">Expand All</button>
      <button class="btn-action" style="padding:2px 8px; font-size:0.75rem;" onclick="expandAllGroups(false)">Collapse All</button>
    </div>
  `;
  container.appendChild(controlsBar);

  let groupIdx = 0;
  groupMap.forEach((grp, key) => {
    groupIdx++;
    const safeKey = 'grp_' + groupIdx;
    const isExpanded = expandedGroupKeys.has(safeKey);
    const escapedPath = (grp.path || '').replace(/'/g, "\\'");
    const isImage = isImageFile(grp.file);
    const sizeDisplay = grp.size ? formatFileSize(grp.size) : '';

    const groupCard = document.createElement('div');
    groupCard.className = 'file-group-card' + (isExpanded ? ' open' : '');
    groupCard.id = 'group_card_' + safeKey;
    groupCard.setAttribute('data-group-key', safeKey);

    // Group Header
    const folderDisplay = grp.folder ? escapeHtml(grp.folder) : '';
    const headerHtml = `
      <div class="file-group-header" onclick="toggleFileGroup('${safeKey}')">
        <div class="group-header-left">
          <span class="group-chevron">${SVG_RAW.chevronRight}</span>
          ${getFileExtBadge(grp.file)}
          <div style="min-width:0;">
            <div class="group-file-title">
              <span title="${escapeHtml(grp.path || '')}">${escapeHtml(grp.file || 'Unknown File')}</span>
              <span class="group-match-count">${grp.items.length} match${grp.items.length > 1 ? 'es' : ''}</span>
            </div>
            ${folderDisplay ? `<div class="group-folder-subtext" title="${folderDisplay}">📁 ${folderDisplay.length > 65 ? '...' + folderDisplay.slice(-60) : folderDisplay} ${sizeDisplay ? '• ' + sizeDisplay : ''}</div>` : ''}
          </div>
        </div>
        <div class="group-header-actions" onclick="event.stopPropagation()">
          ${isImage ? `<button class="btn-image-preview" onclick="showImagePreview('${escapedPath}', '', '${escapeHtml(currentQuery || '')}')" title="Inspect Image & OCR">${SVG_RAW.eye} Inspect</button>` : ''}
          <button class="btn-action" onclick="openFile('${escapedPath}', '', 1)" title="Open File">${SVG_RAW.open} Open</button>
          <button class="btn-action" onclick="revealFolder('${escapedPath}')" title="Open containing folder">${SVG_RAW.folder} Folder</button>
        </div>
      </div>
    `;

    // Group Body (Sub-items)
    const itemsHtml = grp.items.map(r => {
      const escapedSheet = (r.sheet || '').replace(/'/g, "\\'");
      const rowNum = r.row ? `Row ${r.row}` : '';

      let subMetaHtml = '';
      if (!isGeneral) {
        let pills = '';
        if (r.target && r.target !== '—') pills += `<span class="info-pill" onclick="copyToClipboard('${r.target}', 'Target Phone')">${SVG_RAW.phone} <b>${highlightMatch(r.target, currentQuery)}</b></span>`;
        if (r.other && r.other !== '—') pills += `<span class="info-pill" onclick="copyToClipboard('${r.other}', 'Party Phone')">${SVG_RAW.phone} <b>${highlightMatch(r.other, currentQuery)}</b></span>`;
        if (r.name && r.name !== '—') pills += `<span class="info-pill arabic" onclick="copyToClipboard('${r.name}', 'Name')">👤 <b>${highlightMatch(r.name, currentQuery)}</b></span>`;
        if (r.time && r.time !== '—') pills += `<span class="info-pill">📅 ${escapeHtml(r.time)}</span>`;
        if (pills) subMetaHtml = `<div class="card-pill-group" style="margin-top:4px;">${pills}</div>`;
      }

      return `
        <div class="group-sub-item">
          <div class="group-sub-header">
            <div>
              ${r.sheet ? `<span style="color:var(--accent); font-weight:600;">📑 ${escapeHtml(r.sheet)}</span>` : ''}
              ${rowNum ? `<span style="color:#94a3b8; margin-left:6px;">(${rowNum})</span>` : ''}
              ${r.indexed_at && r.indexed_at !== '—' ? `<span style="color:var(--text-dim); margin-left:8px;">📅 ${escapeHtml(r.indexed_at)}</span>` : ''}
            </div>
            <div style="display:flex; gap:4px;">
              <button class="btn-action" style="padding:2px 7px; font-size:0.75rem;" onclick="showContextWindow('${escapedPath}', '${escapedSheet}', ${r.row})" title="View ±3 lines context">
                ${SVG_RAW.context} Context
              </button>
              <button class="btn-action" style="padding:2px 7px; font-size:0.75rem;" onclick="openBookmarkModal('${escapedPath}', '${escapedSheet}', ${r.row}, '${escapeHtml(r.name || r.other || r.target || '')}')" title="Tag record">
                ${SVG_RAW.tag} Tag
              </button>
              <button class="btn-action" style="padding:2px 7px; font-size:0.75rem;" onclick="openFile('${escapedPath}', '${escapedSheet}', ${r.row})" title="Open at line">
                ${SVG_RAW.open} Jump
              </button>
            </div>
          </div>
          ${subMetaHtml}
          <div class="snippet-box" style="margin-top:6px;" ${isImage ? `style="cursor:pointer;" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(currentQuery || '')}')"` : ''}>
            ${highlightMatch(r.snippet, currentQuery)}
          </div>
        </div>
      `;
    }).join('');

    groupCard.innerHTML = `
      ${headerHtml}
      <div class="file-group-body">
        ${itemsHtml}
      </div>
    `;

    container.appendChild(groupCard);
  });
}

function renderCards(rows) {
  const container = document.getElementById('cardsContainer');
  container.innerHTML = '';

  if (!rows || rows.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding: 48px; color:#64748b; background: var(--bg-card); border-radius:10px; border:1px solid var(--border-subtle);">
        No matching records found for "${escapeHtml(currentQuery)}".
      </div>
    `;
    return;
  }

  const isGeneral = (currentSearchMode === 'general');

  rows.forEach(r => {
    const card = document.createElement('div');
    card.className = 'result-card';
    const escapedPath = (r.path || '').replace(/'/g, "\\'");
    const escapedSheet = (r.sheet || '').replace(/'/g, "\\'");
    const isImage = isImageFile(r.file);

    let metaRowHtml = '';
    if (isGeneral) {
      const folderDisplay = r.folder ? escapeHtml(r.folder) : '';
      const sizeDisplay = r.size ? formatFileSize(r.size) : '';
      metaRowHtml = `
        <div class="general-card-meta">
          ${folderDisplay ? `<span class="meta-tag" title="${folderDisplay}">${SVG_RAW.folder} ${folderDisplay.length > 55 ? '...' + folderDisplay.slice(-52) : folderDisplay}</span>` : ''}
          ${r.sheet ? `<span class="meta-tag">${SVG_RAW.context} ${escapeHtml(r.sheet)} (Row ${r.row})</span>` : ''}
          ${sizeDisplay ? `<span class="meta-tag">💾 ${sizeDisplay}</span>` : ''}
          ${r.indexed_at && r.indexed_at !== '—' ? `<span class="meta-tag">📅 ${escapeHtml(r.indexed_at)}</span>` : ''}
        </div>
      `;
    } else {
      let pillsHtml = '';
      if (r.target && r.target !== '—') {
        pillsHtml += `<span class="info-pill" onclick="copyToClipboard('${r.target}', 'Target Phone')">${SVG_RAW.phone} <b>${highlightMatch(r.target, currentQuery)}</b></span>`;
      }
      if (r.other && r.other !== '—') {
        pillsHtml += `<span class="info-pill" onclick="copyToClipboard('${r.other}', 'Party Phone')">${SVG_RAW.phone} <b>${highlightMatch(r.other, currentQuery)}</b></span>`;
      }
      if (r.name && r.name !== '—') {
        pillsHtml += `<span class="info-pill arabic" onclick="copyToClipboard('${r.name}', 'Name')">👤 <b>${highlightMatch(r.name, currentQuery)}</b></span>`;
      }
      if (r.time && r.time !== '—') {
        pillsHtml += `<span class="info-pill">📅 ${escapeHtml(r.time)}</span>`;
      }
      if (r.dir && r.dir !== '—') {
        pillsHtml += `<span class="info-pill">🔄 ${escapeHtml(r.dir)}</span>`;
      }
      if (r.address && r.address !== '—') {
        pillsHtml += `<span class="info-pill arabic">📍 ${highlightMatch(r.address, currentQuery)}</span>`;
      }
      if (pillsHtml) {
        metaRowHtml = `<div class="card-pill-group">${pillsHtml}</div>`;
      }
    }

    card.innerHTML = `
      <div class="card-header">
        <div class="file-meta">
          ${getFileExtBadge(r.file)}
          <span title="${escapeHtml(r.path || '')}">${escapeHtml(r.file)}</span>
        </div>
        <div class="card-actions">
          ${isImage ? `<button class="btn-image-preview" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(currentQuery || '')}')" title="Inspect Image & OCR Highlights">${SVG_RAW.eye} Preview & Text</button>` : ''}
          <button class="btn-action" onclick="showContextWindow('${escapedPath}', '${escapedSheet}', ${r.row})" title="View ±3 lines context">
            ${SVG_RAW.context} Context
          </button>
          <button class="btn-action" onclick="openBookmarkModal('${escapedPath}', '${escapedSheet}', ${r.row}, '${escapeHtml(r.name || r.other || r.target || '')}')" title="Tag record">
            ${SVG_RAW.tag} Tag
          </button>
          <button class="btn-action" onclick="openFile('${escapedPath}', '${escapedSheet}', ${r.row})">
            ${SVG_RAW.open} Open
          </button>
          <button class="btn-action" onclick="revealFolder('${escapedPath}')" title="Open containing folder">
            ${SVG_RAW.folder} Folder
          </button>
        </div>
      </div>
      ${metaRowHtml}
      <div class="snippet-box" ${isImage ? `style="cursor:pointer;" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(currentQuery || '')}')"` : ''}>
        ${highlightMatch(r.snippet, currentQuery)}
      </div>
    `;
    container.appendChild(card);
  });
}

function renderTableRows(rows) {
  const tbody = document.getElementById('tableBody');
  const thead = document.getElementById('tableHead');
  tbody.innerHTML = '';

  const isGeneral = (currentSearchMode === 'general');

  if (isGeneral) {
    thead.innerHTML = `
      <th>File</th>
      <th>Folder / Section</th>
      <th>Snippet / Matched Content</th>
      <th>Indexed</th>
      <th>Actions</th>
    `;
  } else {
    thead.innerHTML = `
      <th>File</th>
      <th>Time</th>
      <th>Dir</th>
      <th>Target</th>
      <th>Other Party</th>
      <th>Name</th>
      <th>Duration / Extra</th>
      <th>Location / Cell</th>
      <th>Action</th>
    `;
  }

  if (!rows || rows.length === 0) {
    const colspan = isGeneral ? 5 : 9;
    tbody.innerHTML = `<tr><td colspan="${colspan}" style="text-align:center; padding: 40px; color:#64748b;">No records match your query.</td></tr>`;
    return;
  }

  rows.forEach(r => {
    const tr = document.createElement('tr');
    const escapedPath = (r.path || '').replace(/'/g, "\\'");
    const escapedSheet = (r.sheet || '').replace(/'/g, "\\'");
    const isImage = isImageFile(r.file);

    if (isGeneral) {
      const folderName = r.folder ? r.folder.split('/').slice(-2).join('/') : '';
      tr.innerHTML = `
        <td title="${escapeHtml(r.path)}">
          ${getFileExtBadge(r.file)}
          <span style="margin-left:5px; font-weight:600;">${escapeHtml(r.file)}</span>
        </td>
        <td style="color:#94a3b8; font-size:0.8rem;" title="${escapeHtml(r.folder || '')}">
          <div>📁 ${escapeHtml(folderName || 'Root')}</div>
          ${r.sheet ? `<div style="color:var(--text-dim); font-size:0.75rem;">${escapeHtml(r.sheet)} (Row ${r.row})</div>` : ''}
        </td>
        <td style="max-width: 520px; font-family:'JetBrains Mono', monospace; font-size:0.8rem; line-height:1.45;">
          ${highlightMatch(r.snippet, currentQuery)}
        </td>
        <td style="white-space:nowrap; color:#94a3b8; font-size:0.78rem;">
          ${escapeHtml(r.indexed_at || r.time || '—')}
        </td>
        <td>
          <div style="display:flex; gap:4px;">
            ${isImage ? `<button class="btn-action" style="padding:2px 6px; color:#a855f7;" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(currentQuery || '')}')" title="Preview Image">${SVG_RAW.eye}</button>` : ''}
            <button class="btn-action" style="padding:2px 6px;" onclick="openFile('${escapedPath}', '${escapedSheet}', ${r.row})" title="Open File">${SVG_RAW.open}</button>
            <button class="btn-action" style="padding:2px 6px;" onclick="showContextWindow('${escapedPath}', '${escapedSheet}', ${r.row})" title="Context">${SVG_RAW.context}</button>
            <button class="btn-action" style="padding:2px 6px;" onclick="revealFolder('${escapedPath}')" title="Folder">${SVG_RAW.folder}</button>
          </div>
        </td>
      `;
    } else {
      tr.innerHTML = `
        <td title="${escapeHtml(r.path)}">${getFileExtBadge(r.file)} <span style="margin-left:4px;">${escapeHtml(r.file)}</span></td>
        <td>${escapeHtml(r.time)}</td>
        <td>${escapeHtml(r.dir)}</td>
        <td style="font-weight:600; cursor:pointer;" onclick="copyToClipboard('${r.target}', 'Target Phone')">${highlightMatch(r.target, currentQuery)}</td>
        <td style="font-weight:600; cursor:pointer;" onclick="copyToClipboard('${r.other}', 'Party Phone')">${highlightMatch(r.other, currentQuery)}</td>
        <td class="arabic" style="font-weight:600; cursor:pointer;" onclick="copyToClipboard('${r.name}', 'Name')">${highlightMatch(r.name, currentQuery)}</td>
        <td>${escapeHtml(r.duration)}</td>
        <td class="arabic">${highlightMatch(r.address || r.sheet, currentQuery)}</td>
        <td>
          <div style="display:flex; gap:4px;">
            ${isImage ? `<button class="btn-action" style="padding:2px 6px; color:#a855f7;" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(currentQuery || '')}')" title="Preview Image">${SVG_RAW.eye}</button>` : ''}
            <button class="btn-action" style="padding:2px 6px;" onclick="openFile('${escapedPath}', '${escapedSheet}', ${r.row})" title="Open">${SVG_RAW.open}</button>
            <button class="btn-action" style="padding:2px 6px;" onclick="showContextWindow('${escapedPath}', '${escapedSheet}', ${r.row})" title="Context">${SVG_RAW.context}</button>
          </div>
        </td>
      `;
    }
    tbody.appendChild(tr);
  });
}

async function openFile(filePath, sheetName, rowIdx) {
  showToast(`🚀 Opening ${filePath.split('/').pop()} at row ${rowIdx}...`);
  try {
    const res = await fetch(`/api/open?file=${encodeURIComponent(filePath)}&sheet=${encodeURIComponent(sheetName)}&row=${rowIdx}`);
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ ${data.message}`);
    } else {
      showToast(`❌ Error: ${data.error}`);
    }
  } catch (err) {
    showToast(`❌ Network error launching app`);
  }
}

async function revealFolder(filePath) {
  showToast(`📂 Opening folder...`);
  try {
    const res = await fetch(`/api/reveal?file=${encodeURIComponent(filePath)}`);
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ ${data.message}`);
    } else {
      showToast(`❌ Error: ${data.error}`);
    }
  } catch (err) {
    showToast(`❌ Network error opening folder`);
  }
}

async function showContextWindow(filePath, sheetName, rowIdx) {
  const modal = document.getElementById('contextModal');
  const label = document.getElementById('contextFileLabel');
  const box = document.getElementById('contextLinesBox');
  label.innerText = `${filePath} (${sheetName}, around Row ${rowIdx})`;
  box.innerHTML = 'Loading ±3 lines context...';
  modal.classList.add('active');

  try {
    const res = await fetch(`/api/context?file=${encodeURIComponent(filePath)}&sheet=${encodeURIComponent(sheetName)}&row=${rowIdx}`);
    const data = await res.json();
    if (data.ok && data.lines && data.lines.length > 0) {
      let html = '';
      data.lines.forEach(l => {
        const isTarget = (l.row === rowIdx);
        html += `<div style="padding: 4px 8px; border-radius: 4px; ${isTarget ? 'background: rgba(56, 189, 248, 0.2); font-weight: bold; border-left: 3px solid var(--accent);' : ''}">
          <span style="color:#64748b; margin-right: 8px;">[Row ${l.row}]</span>
          ${highlightMatch(l.content, currentQuery)}
        </div>`;
      });
      box.innerHTML = html;
    } else {
      box.innerHTML = '<span style="color:#64748b;">No surrounding context available.</span>';
    }
  } catch (err) {
    box.innerHTML = '<span style="color:#ef4444;">Error loading context.</span>';
  }
}

/* Image & Selectable OCR Text Inspector */
let currentImageBoxes = [];
let currentImageLines = [];
let originalImgWidth = 0;
let originalImgHeight = 0;
let currentImageScale = 1.0;
let showBoxesEnabled = true;

function isImageFile(filename) {
  if (!filename) return false;
  const ext = filename.split('.').pop().toLowerCase();
  return ['png', 'jpg', 'jpeg', 'tiff', 'bmp', 'webp'].includes(ext);
}

async function showImagePreview(filePath, sheetName, searchTerm) {
  const modal = document.getElementById('imagePreviewModal');
  const img = document.getElementById('imagePreviewElement');
  const overlay = document.getElementById('ocrBoxesOverlay');
  const label = document.getElementById('imagePreviewFileLabel');
  const notice = document.getElementById('imageOcrNotice');
  const details = document.getElementById('ocrStatusDetails');
  const textContainer = document.getElementById('ocrTextContainer');

  currentImageScale = 1.0;
  const container = document.getElementById('ocrPreviewContainer');
  if (container) container.style.transform = 'scale(1)';
  overlay.innerHTML = '';
  currentImageBoxes = [];
  currentImageLines = [];
  originalImgWidth = 0;
  originalImgHeight = 0;

  label.innerText = `${filePath} (${sheetName || 'Image'})`;
  notice.style.display = 'none';
  details.innerText = 'Analyzing image & loading OCR text layer...';
  textContainer.innerHTML = '<div style="color:#64748b; padding:24px; text-align:center;">Detecting text & coordinates...</div>';
  modal.classList.add('active');

  const encodedFile = encodeURIComponent(filePath);
  const encodedSheet = encodeURIComponent(sheetName || 'Image');

  const updateBoxesAndText = () => {
    if (!originalImgWidth || !originalImgHeight) {
      originalImgWidth = img.naturalWidth || 800;
      originalImgHeight = img.naturalHeight || 600;
    }
    renderOcrBoxes(searchTerm || currentQuery);
    renderOcrTextInspector(searchTerm || currentQuery);
    details.innerText = `${originalImgWidth} × ${originalImgHeight} px | ${currentImageBoxes.length} detected words`;
  };

  // Set img load handler FIRST before src
  img.onload = () => {
    updateBoxesAndText();
  };

  img.onerror = () => {
    details.innerText = '❌ Failed to load image file.';
    textContainer.innerHTML = '<div style="color:#ef4444; padding:20px;">Failed to load image file.</div>';
  };

  img.src = `/api/image/view?file=${encodedFile}`;

  // Fetch bounding boxes & lines
  try {
    const res = await fetch(`/api/image/boxes?file=${encodedFile}&sheet=${encodedSheet}`);
    const resData = await res.json();
    if (resData.ok && resData.data) {
      originalImgWidth = resData.data.width || img.naturalWidth || 0;
      originalImgHeight = resData.data.height || img.naturalHeight || 0;
      currentImageBoxes = resData.data.boxes || [];
      currentImageLines = resData.data.lines || [];
      updateBoxesAndText();
    }
  } catch (err) {
    console.error("Failed to fetch OCR boxes:", err);
  }

  if (img.complete && img.naturalWidth > 0) {
    updateBoxesAndText();
  }
}

function renderOcrTextInspector(searchTerm) {
  const container = document.getElementById('ocrTextContainer');
  const wordsBadge = document.getElementById('ocrWordsCountBadge');
  const cleanTerm = (searchTerm || '').trim().toLowerCase();

  let textLines = currentImageLines || [];
  if ((!textLines || textLines.length === 0) && currentImageBoxes && currentImageBoxes.length > 0) {
    textLines = [currentImageBoxes.map(b => b.text).join(' ')];
  }

  if (!textLines || textLines.length === 0) {
    container.innerHTML = '<div style="color:#64748b; padding:20px; text-align:center;">No OCR text detected in this image.</div>';
    if (wordsBadge) wordsBadge.innerText = '0 words';
    return;
  }

  const fullRawText = textLines.join('\n');
  const totalWords = fullRawText.split(/\s+/).filter(Boolean).length;
  if (wordsBadge) wordsBadge.innerText = `${totalWords} words`;

  let html = '';
  textLines.forEach((line, idx) => {
    const escaped = escapeHtml(line);
    let highlighted = escaped;
    if (cleanTerm) {
      const regex = new RegExp(`(${cleanTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
      highlighted = escaped.replace(regex, '<mark class="ocr-mark">$1</mark>');
    }
    html += `<div class="ocr-line" onclick="copyToClipboard('${line.replace(/'/g, "\\'")}', 'Line ${idx + 1}')"><span class="ocr-line-num">${idx + 1}</span><span class="ocr-line-content">${highlighted}</span></div>`;
  });

  container.innerHTML = html;
}

function copyAllOcrText() {
  let text = '';
  if (currentImageLines && currentImageLines.length > 0) {
    text = currentImageLines.join('\n');
  } else if (currentImageBoxes && currentImageBoxes.length > 0) {
    text = currentImageBoxes.map(b => b.text).join(' ');
  }
  if (!text) {
    showToast("No text to copy");
    return;
  }
  copyToClipboard(text, 'Full OCR Text');
}

function copySelectedOcrText() {
  const selection = window.getSelection().toString();
  if (selection && selection.trim()) {
    copyToClipboard(selection.trim(), 'Selected Text');
  } else {
    showToast("Highlight text with mouse first to copy selection");
  }
}

function renderOcrBoxes(searchTerm) {
  const overlay = document.getElementById('ocrBoxesOverlay');
  overlay.innerHTML = '';
  if (!showBoxesEnabled || !currentImageBoxes || currentImageBoxes.length === 0) {
    return;
  }

  const imgW = originalImgWidth || document.getElementById('imagePreviewElement').naturalWidth || 800;
  const imgH = originalImgHeight || document.getElementById('imagePreviewElement').naturalHeight || 600;

  const cleanTerm = (searchTerm || '').trim().toLowerCase();
  let matchCount = 0;
  let firstMatchEl = null;

  currentImageBoxes.forEach(b => {
    const word = (b.text || '').trim();
    if (!word) return;

    const leftPct = (b.left / imgW) * 100;
    const topPct = (b.top / imgH) * 100;
    const widthPct = (b.width / imgW) * 100;
    const heightPct = (b.height / imgH) * 100;

    const isMatch = cleanTerm && (
      word.toLowerCase().includes(cleanTerm) ||
      cleanTerm.includes(word.toLowerCase())
    );
    if (isMatch) matchCount++;

    const boxEl = document.createElement('div');
    boxEl.className = 'ocr-highlight-box' + (isMatch ? ' active-match' : '');
    boxEl.style.left = `${leftPct}%`;
    boxEl.style.top = `${topPct}%`;
    boxEl.style.width = `${widthPct}%`;
    boxEl.style.height = `${heightPct}%`;
    boxEl.title = `"${word}" (${Math.round(b.conf || 0)}% conf)\nClick to copy`;

    // Transparent live text layer for mouse dragging selection directly over the image!
    const textSpan = document.createElement('span');
    textSpan.className = 'ocr-live-text';
    textSpan.innerText = word;
    boxEl.appendChild(textSpan);

    boxEl.onclick = (e) => {
      e.stopPropagation();
      copyToClipboard(word, 'OCR Word');
    };

    overlay.appendChild(boxEl);

    if (isMatch && !firstMatchEl) {
      firstMatchEl = boxEl;
    }
  });

  const notice = document.getElementById('imageOcrNotice');
  if (cleanTerm) {
    notice.style.display = 'block';
    if (matchCount > 0) {
      notice.innerHTML = `🎯 Highlighted <b>${matchCount}</b> match(es) for "<b>${escapeHtml(cleanTerm)}</b>" on image & text inspector. Drag mouse across words to select & copy.`;
      if (firstMatchEl) {
        setTimeout(() => {
          firstMatchEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 150);
      }
    } else {
      notice.innerHTML = `ℹ️ Showing all ${currentImageBoxes.length} detected words on image.`;
    }
  } else {
    notice.style.display = 'none';
  }
}

function toggleOcrBoxes() {
  showBoxesEnabled = !showBoxesEnabled;
  const btn = document.getElementById('ocrToggleBtn');
  btn.innerHTML = `<span class="icon-cyan">${SVG_RAW.eye}</span> Boxes: ${showBoxesEnabled ? 'ON' : 'OFF'}`;
  const overlay = document.getElementById('ocrBoxesOverlay');
  overlay.style.display = showBoxesEnabled ? 'block' : 'none';
}

function zoomImage(delta) {
  currentImageScale = Math.max(0.4, Math.min(3.0, currentImageScale + delta));
  const container = document.getElementById('ocrPreviewContainer');
  container.style.transform = `scale(${currentImageScale})`;
  container.style.transformOrigin = 'top center';
}

function resetImageZoom() {
  currentImageScale = 1.0;
  const container = document.getElementById('ocrPreviewContainer');
  container.style.transform = 'scale(1)';
}

function closeImagePreview() {
  document.getElementById('imagePreviewModal').classList.remove('active');
  document.getElementById('imagePreviewElement').src = '';
  document.getElementById('ocrBoxesOverlay').innerHTML = '';
}

async function triggerBackup() {
  showToast("💾 Creating snapshot backup...");
  try {
    const res = await fetch('/api/backup');
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ ${data.message}`);
    } else {
      showToast(`❌ Backup failed`);
    }
  } catch (err) {
    showToast(`❌ Network error creating backup`);
  }
}

/* Tab Switcher */
let currentMainTab = 'global';

function switchMainTab(tab) {
  currentMainTab = tab;
  document.getElementById('tabBtnGlobal').classList.toggle('active', tab === 'global');
  document.getElementById('tabBtnScoped').classList.toggle('active', tab === 'scoped');
  document.getElementById('tabGlobalPane').style.display = (tab === 'global') ? 'block' : 'none';
  document.getElementById('tabScopedPane').style.display = (tab === 'scoped') ? 'block' : 'none';

  if (tab === 'global') {
    document.getElementById('queryInput').focus();
  } else {
    document.getElementById('scopedQueryInput').focus();
  }
}

/* Scoped Target / Restricted Search Logic with Native Folder Picker */
let scopedState = {
  active: false,
  type: null,
  path: null,
  filename: null,
  mode: 'general',
  currentPage: 0,
  pageSize: 50,
  currentQuery: '',
  totalResults: 0,
  lastResults: [],
  viewMode: 'card',
  debounceTimer: null
};

function setScopedSearchMode(mode) {
  scopedState.mode = mode;
  const isGeneral = (mode === 'general');
  document.getElementById('scopedModeBtnGeneral').classList.toggle('active', isGeneral);
  document.getElementById('scopedModeBtnTelecom').classList.toggle('active', !isGeneral);

  const desc = document.getElementById('scopedModeDescText');
  const input = document.getElementById('scopedQueryInput');
  if (isGeneral) {
    desc.innerText = 'Target document lookup';
    input.placeholder = 'Search keywords, document text, topics, Egyptian/EN names, OCR images...';
  } else {
    desc.innerText = 'Target CDR & phone records';
    input.placeholder = 'Search phone numbers, caller/callee, duration, cell towers...';
  }

  if (scopedState.active && scopedState.currentQuery) {
    doScopedSearch(0);
  }
}

function switchScopedView(mode) {
  scopedState.viewMode = mode;
  document.getElementById('btnScopedViewCard').classList.toggle('active', mode === 'card');
  document.getElementById('btnScopedViewTable').classList.toggle('active', mode === 'table');
  document.getElementById('scopedCardsContainer').style.display = (mode === 'card') ? 'flex' : 'none';
  document.getElementById('scopedTableContainer').style.display = (mode === 'table') ? 'block' : 'none';
  if (scopedState.lastResults && scopedState.lastResults.length > 0) {
    renderScopedViewData({ rows: scopedState.lastResults, total: scopedState.totalResults, type: scopedState.lastResults[0]?.phone ? 'prefix' : 'cdr' });
  }
}

function handleScopedInput(e) {
  const val = e.target.value.trim();
  document.getElementById('clearScopedSearchBtn').style.display = val ? 'block' : 'none';
  if (scopedState.debounceTimer) clearTimeout(scopedState.debounceTimer);
  scopedState.debounceTimer = setTimeout(() => {
    if (val.length >= 2 || val.length === 0) {
      doScopedSearch(0);
    }
  }, 350);
}

function clearScopedSearch() {
  document.getElementById('scopedQueryInput').value = '';
  document.getElementById('clearScopedSearchBtn').style.display = 'none';
  document.getElementById('scopedQueryInput').focus();
  doScopedSearch(0);
}

function setScopedTarget(type, path, label) {
  scopedState.active = true;
  scopedState.type = type;
  scopedState.path = path;
  scopedState.filename = label || path.split('/').pop();

  const banner = document.getElementById('activeScopeBanner');
  banner.style.display = 'flex';
  document.getElementById('activeScopeLabel').innerText = `${type.toUpperCase()}: ${path}`;
  document.getElementById('scopedTargetBadge').innerText = scopedState.filename;
  document.getElementById('scopedTargetBadge').style.background = '#10b98130';
  document.getElementById('scopedTargetBadge').style.color = '#10b981';

  document.getElementById('scopedQueryInput').focus();
  if (document.getElementById('scopedQueryInput').value.trim()) {
    doScopedSearch(0);
  } else {
    document.getElementById('scopedResultsCount').innerText = `Target locked: ${scopedState.filename}. Ready.`;
  }
}

function clearScopedTarget() {
  scopedState.active = false;
  scopedState.type = null;
  scopedState.path = null;
  scopedState.filename = null;
  scopedState.lastResults = [];
  scopedState.totalResults = 0;

  document.getElementById('activeScopeBanner').style.display = 'none';
  document.getElementById('scopedTargetBadge').innerText = 'Folder or File';
  document.getElementById('scopedTargetBadge').style.background = '#0ea5e920';
  document.getElementById('scopedTargetBadge').style.color = '#38bdf8';
  document.getElementById('scopedFileInput').value = '';
  document.getElementById('scopedResultsCount').innerText = 'Choose a folder or drop a file above to begin.';
  document.getElementById('scopedTiming').innerText = '0ms';
  renderScopedCards([]);
  renderScopedTableRows([]);
}

async function pickFolderNative() {
  showToast("📁 Opening folder selector...");
  try {
    const res = await fetch('/api/dialog/pick-folder');
    const data = await res.json();
    if (data.ok && data.path) {
      await executeTargetIndex(data.path);
    }
  } catch (err) {
    showToast("❌ Could not open native folder chooser");
  }
}

async function pickFileNative() {
  showToast("📄 Opening file selector...");
  try {
    const res = await fetch('/api/dialog/pick-file');
    const data = await res.json();
    if (data.ok && data.path) {
      await executeTargetIndex(data.path);
    }
  } catch (err) {
    showToast("❌ Could not open native file chooser");
  }
}

function handleWebkitFolderSelect(e) {
  const files = e.target.files;
  if (files && files.length > 0) {
    const firstFile = files[0];
    const path = firstFile.webkitRelativePath ? firstFile.webkitRelativePath.split('/')[0] : firstFile.name;
    showToast(`Selected folder: ${path}`);
    setScopedTarget('folder', path, path);
  }
}

async function executeTargetIndex(targetPath) {
  showToast(`⚡ Indexing target: ${targetPath.split('/').pop()}...`);
  try {
    const res = await fetch('/api/target/index', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: targetPath })
    });
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ ${data.message}`);
      setScopedTarget(data.is_dir ? 'folder' : 'file', data.target, targetPath.split('/').pop());
      refreshStats();
      if (isImageFile(data.target)) {
        showImagePreview(data.target, 'Image', '');
      }
    } else {
      alert(`❌ Error: ${data.error}`);
    }
  } catch (err) {
    showToast("❌ Network error indexing target");
  }
}

async function handleScopedFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  await uploadScopedFile(file);
}

async function uploadScopedFile(file) {
  showToast(`📤 Uploading and parsing ${file.name}...`);
  const formData = new FormData();
  formData.append('file', file, file.name);

  try {
    const res = await fetch('/api/target/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.ok) {
      showToast(`✅ Successfully uploaded and indexed ${data.filename}!`);
      setScopedTarget('file', data.path, data.filename);
      refreshStats();
      if (isImageFile(data.filename)) {
        showImagePreview(data.path, 'Image', '');
      }
    } else {
      alert(`❌ Upload failed: ${data.error}`);
    }
  } catch (err) {
    showToast("❌ Network error uploading file");
  }
}

function initDragAndDrop() {
  const dropZone = document.getElementById('scopedDropZone');
  if (!dropZone) return;

  ['dragenter', 'dragover'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add('dragover');
    }, false);
  });

  ['dragleave', 'drop'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove('dragover');
    }, false);
  });

  dropZone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files && files.length > 0) {
      uploadScopedFile(files[0]);
    }
  }, false);
}

async function doScopedSearch(page = 0) {
  if (!scopedState.active || !scopedState.path) {
    alert("Please choose a target folder or drop a file first!");
    return;
  }
  const q = document.getElementById('scopedQueryInput').value.trim();
  if (!q) {
    scopedState.lastResults = [];
    scopedState.totalResults = 0;
    renderScopedViewData({ rows: [], total: 0 });
    document.getElementById('scopedResultsCount').innerText = `Target locked: ${scopedState.filename}. Ready.`;
    document.getElementById('scopedTiming').innerText = "0ms";
    return;
  }

  scopedState.currentPage = page;
  scopedState.currentQuery = q;
  const offset = scopedState.currentPage * scopedState.pageSize;

  const t0 = performance.now();
  document.getElementById('scopedResultsCount').innerText = "Searching target...";

  try {
    const params = new URLSearchParams({
      q: scopedState.currentQuery,
      limit: scopedState.pageSize,
      offset: offset,
      mode: scopedState.mode || 'general'
    });
    if (scopedState.type === 'file') {
      params.append('file', scopedState.path);
    } else if (scopedState.type === 'folder') {
      params.append('folder', scopedState.path);
    }

    const res = await fetch(`/api/search?${params.toString()}`);
    const data = await res.json();
    const t1 = performance.now();
    document.getElementById('scopedTiming').innerText = `${Math.round(t1 - t0)}ms`;

    renderScopedViewData(data);
  } catch (e) {
    console.error(e);
    document.getElementById('scopedResultsCount').innerText = "Scoped search error";
  }
}

function changeScopedPage(delta) {
  const newPage = scopedState.currentPage + delta;
  if (newPage >= 0 && (newPage * scopedState.pageSize) < scopedState.totalResults) {
    doScopedSearch(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function renderScopedViewData(data) {
  scopedState.lastResults = data.rows || [];
  scopedState.totalResults = data.total || 0;
  const paginationBar = document.getElementById('scopedPaginationBar');
  const topPaginationBar = document.getElementById('scopedTopPaginationBar');

  if (scopedState.totalResults > scopedState.pageSize) {
    const start = scopedState.currentPage * scopedState.pageSize + 1;
    const end = Math.min((scopedState.currentPage + 1) * scopedState.pageSize, scopedState.totalResults);
    const infoText = `Showing ${start.toLocaleString()}-${end.toLocaleString()} of ${scopedState.totalResults.toLocaleString()} records`;
    const pageBadgeText = `Page ${scopedState.currentPage + 1} of ${Math.ceil(scopedState.totalResults / scopedState.pageSize)}`;
    const isPrevDisabled = (scopedState.currentPage === 0);
    const isNextDisabled = ((scopedState.currentPage + 1) * scopedState.pageSize >= scopedState.totalResults);

    paginationBar.style.display = 'flex';
    document.getElementById('scopedPageInfo').innerText = infoText;
    document.getElementById('scopedPageNumberBadge').innerText = pageBadgeText;
    document.getElementById('scopedPrevBtn').disabled = isPrevDisabled;
    document.getElementById('scopedNextBtn').disabled = isNextDisabled;

    if (topPaginationBar) {
      topPaginationBar.style.display = 'flex';
      document.getElementById('scopedTopPageInfo').innerText = infoText;
      document.getElementById('scopedTopPageNumberBadge').innerText = pageBadgeText;
      document.getElementById('scopedTopPrevBtn').disabled = isPrevDisabled;
      document.getElementById('scopedTopNextBtn').disabled = isNextDisabled;
    }
  } else if (scopedState.totalResults > 0) {
    paginationBar.style.display = 'flex';
    document.getElementById('scopedPageInfo').innerText = `${scopedState.totalResults.toLocaleString()} records`;
    document.getElementById('scopedPageNumberBadge').innerText = `Page 1 of 1`;
    document.getElementById('scopedPrevBtn').disabled = true;
    document.getElementById('scopedNextBtn').disabled = true;

    if (topPaginationBar) {
      topPaginationBar.style.display = 'flex';
      document.getElementById('scopedTopPageInfo').innerText = `${scopedState.totalResults.toLocaleString()} records`;
      document.getElementById('scopedTopPageNumberBadge').innerText = `Page 1 of 1`;
      document.getElementById('scopedTopPrevBtn').disabled = true;
      document.getElementById('scopedTopNextBtn').disabled = true;
    }
  } else {
    paginationBar.style.display = 'none';
    if (topPaginationBar) topPaginationBar.style.display = 'none';
  }

  document.getElementById('scopedResultsCount').innerText = `${scopedState.totalResults.toLocaleString()} matches in ${scopedState.filename}`;
  renderScopedCards(scopedState.lastResults);
  renderScopedTableRows(scopedState.lastResults);

  if (scopedState.lastResults.length > 0 && isImageFile(scopedState.lastResults[0].file)) {
    const firstImg = scopedState.lastResults[0];
    showImagePreview(firstImg.path, firstImg.sheet, scopedState.currentQuery);
  }
}

function renderScopedCards(rows) {
  const container = document.getElementById('scopedCardsContainer');
  container.innerHTML = '';

  if (!rows || rows.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding: 48px; color:#64748b; background: var(--bg-card); border-radius:10px; border:1px solid var(--border-subtle);">
        ${scopedState.active ? `No records found in "${scopedState.filename}" for "${escapeHtml(scopedState.currentQuery)}".` : 'No target selected yet. Choose a folder or file above.'}
      </div>
    `;
    return;
  }

  const isGeneral = ((scopedState.mode || 'general') === 'general');

  rows.forEach(r => {
    const card = document.createElement('div');
    card.className = 'result-card';
    const escapedPath = (r.path || '').replace(/'/g, "\\'");
    const escapedSheet = (r.sheet || '').replace(/'/g, "\\'");
    const isImage = isImageFile(r.file);

    let metaRowHtml = '';
    if (isGeneral) {
      const folderDisplay = r.folder ? escapeHtml(r.folder) : '';
      const sizeDisplay = r.size ? formatFileSize(r.size) : '';
      metaRowHtml = `
        <div class="general-card-meta">
          ${folderDisplay ? `<span class="meta-tag" title="${folderDisplay}">${SVG_RAW.folder} ${folderDisplay.length > 55 ? '...' + folderDisplay.slice(-52) : folderDisplay}</span>` : ''}
          ${r.sheet ? `<span class="meta-tag">${SVG_RAW.context} ${escapeHtml(r.sheet)} (Row ${r.row})</span>` : ''}
          ${sizeDisplay ? `<span class="meta-tag">💾 ${sizeDisplay}</span>` : ''}
          ${r.indexed_at && r.indexed_at !== '—' ? `<span class="meta-tag">📅 ${escapeHtml(r.indexed_at)}</span>` : ''}
        </div>
      `;
    } else {
      let pillsHtml = '';
      if (r.target && r.target !== '—') {
        pillsHtml += `<span class="info-pill" onclick="copyToClipboard('${r.target}', 'Target Phone')">${SVG_RAW.phone} <b>${highlightMatch(r.target, scopedState.currentQuery)}</b></span>`;
      }
      if (r.other && r.other !== '—') {
        pillsHtml += `<span class="info-pill" onclick="copyToClipboard('${r.other}', 'Party Phone')">${SVG_RAW.phone} <b>${highlightMatch(r.other, scopedState.currentQuery)}</b></span>`;
      }
      if (r.name && r.name !== '—') {
        pillsHtml += `<span class="info-pill arabic" onclick="copyToClipboard('${r.name}', 'Name')">👤 <b>${highlightMatch(r.name, scopedState.currentQuery)}</b></span>`;
      }
      if (r.time && r.time !== '—') {
        pillsHtml += `<span class="info-pill">📅 ${escapeHtml(r.time)}</span>`;
      }
      if (pillsHtml) {
        metaRowHtml = `<div class="card-pill-group">${pillsHtml}</div>`;
      }
    }

    card.innerHTML = `
      <div class="card-header">
        <div class="file-meta">
          ${getFileExtBadge(r.file)}
          <span title="${escapeHtml(r.path || '')}">${escapeHtml(r.file)}</span>
        </div>
        <div class="card-actions">
          ${isImage ? `<button class="btn-image-preview" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(scopedState.currentQuery || '')}')">${SVG_RAW.eye} Preview & Text</button>` : ''}
          <button class="btn-action" onclick="showContextWindow('${escapedPath}', '${escapedSheet}', ${r.row})">
            ${SVG_RAW.context} Context
          </button>
          <button class="btn-action" onclick="openFile('${escapedPath}', '${escapedSheet}', ${r.row})">
            ${SVG_RAW.open} Open
          </button>
          <button class="btn-action" onclick="revealFolder('${escapedPath}')">
            ${SVG_RAW.folder} Folder
          </button>
        </div>
      </div>
      ${metaRowHtml}
      <div class="snippet-box" ${isImage ? `style="cursor:pointer;" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(scopedState.currentQuery || '')}')"` : ''}>
        ${highlightMatch(r.snippet, scopedState.currentQuery)}
      </div>
    `;
    container.appendChild(card);
  });
}

function renderScopedTableRows(rows) {
  const tbody = document.getElementById('scopedTableBody');
  const thead = document.getElementById('scopedTableHead');
  tbody.innerHTML = '';

  const isGeneral = ((scopedState.mode || 'general') === 'general');

  if (isGeneral) {
    thead.innerHTML = `
      <th>File</th>
      <th>Folder / Section</th>
      <th>Snippet / Matched Content</th>
      <th>Indexed</th>
      <th>Actions</th>
    `;
  } else {
    thead.innerHTML = `
      <th>File</th>
      <th>Time</th>
      <th>Dir</th>
      <th>Target</th>
      <th>Other Party</th>
      <th>Name</th>
      <th>Duration / Extra</th>
      <th>Location / Cell</th>
      <th>Action</th>
    `;
  }

  if (!rows || rows.length === 0) {
    const colspan = isGeneral ? 5 : 9;
    tbody.innerHTML = `<tr><td colspan="${colspan}" style="text-align:center; padding: 40px; color:#64748b;">No records match your target search.</td></tr>`;
    return;
  }

  rows.forEach(r => {
    const tr = document.createElement('tr');
    const escapedPath = (r.path || '').replace(/'/g, "\\'");
    const escapedSheet = (r.sheet || '').replace(/'/g, "\\'");
    const isImage = isImageFile(r.file);

    if (isGeneral) {
      const folderName = r.folder ? r.folder.split('/').slice(-2).join('/') : '';
      tr.innerHTML = `
        <td title="${escapeHtml(r.path)}">
          ${getFileExtBadge(r.file)}
          <span style="margin-left:5px; font-weight:600;">${escapeHtml(r.file)}</span>
        </td>
        <td style="color:#94a3b8; font-size:0.8rem;" title="${escapeHtml(r.folder || '')}">
          <div>📁 ${escapeHtml(folderName || 'Root')}</div>
          ${r.sheet ? `<div style="color:var(--text-dim); font-size:0.75rem;">${escapeHtml(r.sheet)} (Row ${r.row})</div>` : ''}
        </td>
        <td style="max-width: 520px; font-family:'JetBrains Mono', monospace; font-size:0.8rem; line-height:1.45;">
          ${highlightMatch(r.snippet, scopedState.currentQuery)}
        </td>
        <td style="white-space:nowrap; color:#94a3b8; font-size:0.78rem;">
          ${escapeHtml(r.indexed_at || r.time || '—')}
        </td>
        <td>
          <div style="display:flex; gap:4px;">
            ${isImage ? `<button class="btn-action" style="padding:2px 6px; color:#a855f7;" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(scopedState.currentQuery || '')}')" title="Preview Image">${SVG_RAW.eye}</button>` : ''}
            <button class="btn-action" style="padding:2px 6px;" onclick="openFile('${escapedPath}', '${escapedSheet}', ${r.row})" title="Open File">${SVG_RAW.open}</button>
            <button class="btn-action" style="padding:2px 6px;" onclick="showContextWindow('${escapedPath}', '${escapedSheet}', ${r.row})" title="Context">${SVG_RAW.context}</button>
            <button class="btn-action" style="padding:2px 6px;" onclick="revealFolder('${escapedPath}')" title="Folder">${SVG_RAW.folder}</button>
          </div>
        </td>
      `;
    } else {
      tr.innerHTML = `
        <td title="${escapeHtml(r.path)}">${getFileExtBadge(r.file)} <span style="margin-left:4px;">${escapeHtml(r.file)}</span></td>
        <td>${escapeHtml(r.time)}</td>
        <td>${escapeHtml(r.dir)}</td>
        <td style="font-weight:600; cursor:pointer;" onclick="copyToClipboard('${r.target}', 'Target Phone')">${highlightMatch(r.target, scopedState.currentQuery)}</td>
        <td style="font-weight:600; cursor:pointer;" onclick="copyToClipboard('${r.other}', 'Party Phone')">${highlightMatch(r.other, scopedState.currentQuery)}</td>
        <td class="arabic" style="font-weight:600; cursor:pointer;" onclick="copyToClipboard('${r.name}', 'Name')">${highlightMatch(r.name, scopedState.currentQuery)}</td>
        <td>${escapeHtml(r.duration)}</td>
        <td class="arabic">${highlightMatch(r.address || r.sheet, scopedState.currentQuery)}</td>
        <td>
          <div style="display:flex; gap:4px;">
            ${isImage ? `<button class="btn-action" style="padding:2px 6px; color:#a855f7;" onclick="showImagePreview('${escapedPath}', '${escapedSheet}', '${escapeHtml(scopedState.currentQuery || '')}')">${SVG_RAW.eye}</button>` : ''}
            <button class="btn-action" style="padding:2px 6px;" onclick="openFile('${escapedPath}', '${escapedSheet}', ${r.row})">${SVG_RAW.open}</button>
            <button class="btn-action" style="padding:2px 6px;" onclick="showContextWindow('${escapedPath}', '${escapedSheet}', ${r.row})">${SVG_RAW.context}</button>
          </div>
        </td>
      `;
    }
    tbody.appendChild(tr);
  });
}

function exportIndex() {
  window.location.href = '/api/index/export';
}

function exportCSV() {
  if (!currentQuery) {
    alert("Please enter a search query before exporting CSV!");
    return;
  }
  window.location.href = `/api/search/csv?q=${encodeURIComponent(currentQuery)}`;
}

async function handleImportFile(e) {
  const file = e.target.files[0];
  if (!file) return;
  if (!confirm(`Are you sure you want to restore/import "${file.name}"? Existing index will be backed up.`)) {
    return;
  }
  showToast("📥 Uploading and verifying database...");
  const formData = new FormData();
  formData.append('dbfile', file, file.name);

  try {
    const res = await fetch('/api/index/import', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.ok) {
      showToast("✅ Database restored! Reloading stats...");
      refreshStats();
      doSearch(0);
    } else {
      alert(`❌ Import error: ${data.error}`);
    }
  } catch (err) {
    showToast("❌ Network error importing database");
  }
}

window.onload = () => {
  injectStaticIcons();
  loadDatabases();
  refreshStats();
  refreshWatcherStatus();
  loadQuickFilters();
  refreshBookmarkCount();
  fetchNotifications();
  initDragAndDrop();

  // Periodically refresh notifications & watcher badge
  setInterval(() => {
    fetchNotifications();
  }, 5000);
};
