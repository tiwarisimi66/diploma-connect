/**
 * script.js - Main client-side interactivity for DiplomaConnect
 * Clean, lightweight vanilla JavaScript.
 */

document.addEventListener("DOMContentLoaded", function () {
    // 1. Mobile Sidebar Drawer Toggle & Backdrop
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebarClose = document.getElementById("sidebarClose");
    const sidebarBackdrop = document.getElementById("sidebarBackdrop");
    const appSidebar = document.getElementById("appSidebar");

    function openDrawer() {
        if (appSidebar) appSidebar.classList.add("open");
        if (sidebarBackdrop) sidebarBackdrop.classList.add("active");
        document.body.style.overflow = "hidden";
    }

    function closeDrawer() {
        if (appSidebar) appSidebar.classList.remove("open");
        if (sidebarBackdrop) sidebarBackdrop.classList.remove("active");
        document.body.style.overflow = "";
    }

    if (sidebarToggle && appSidebar) {
        sidebarToggle.addEventListener("click", function (e) {
            e.stopPropagation();
            if (appSidebar.classList.contains("open")) {
                closeDrawer();
            } else {
                openDrawer();
            }
        });
    }

    if (sidebarClose) {
        sidebarClose.addEventListener("click", function (e) {
            e.stopPropagation();
            closeDrawer();
        });
    }

    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener("click", function () {
            closeDrawer();
        });
    }

    // Close on escape key
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && appSidebar && appSidebar.classList.contains("open")) {
            closeDrawer();
        }
    });

    // 2. Auto-dismiss Flash Alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert.alert-dismissible");
    alerts.forEach(function (alert) {
        setTimeout(function () {
            try {
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                if (bsAlert) {
                    bsAlert.close();
                }
            } catch (err) {
                alert.style.display = "none";
            }
        }, 5000);
    });

    // 3. Profile Photo Instant Preview on Select
    const profilePhotoInput = document.getElementById("profilePhotoInput");
    if (profilePhotoInput) {
        profilePhotoInput.addEventListener("change", function () {
            if (this.files && this.files[0]) {
                const form = document.getElementById("photoForm");
                if (form) {
                    form.submit();
                }
            }
        });
    }
});

// ============================================================
// BRANCH / STREAM FILTER — Opportunities & Events pages
// Pure client-side. No AJAX. No backend changes.
// Added additively — does not affect any existing JS logic.
// ============================================================

(function () {
    'use strict';

    function initBranchFilter(pillSelector, cardSelector, noResultsId, clearBtnId) {
        var pills = document.querySelectorAll(pillSelector);
        if (!pills.length) return;

        var noResults = noResultsId ? document.getElementById(noResultsId) : null;

        pills.forEach(function (pill) {
            pill.addEventListener('click', function () {
                var filter = this.getAttribute('data-filter');

                pills.forEach(function (p) { p.classList.remove('active'); });
                this.classList.add('active');

                var cards = document.querySelectorAll(cardSelector);
                var visibleCount = 0;

                cards.forEach(function (card) {
                    var branch = card.getAttribute('data-branch') || 'general';
                    if (filter === 'all' || branch === filter) {
                        card.classList.remove('branch-hidden');
                        visibleCount++;
                    } else {
                        card.classList.add('branch-hidden');
                    }
                });

                if (noResults) {
                    if (visibleCount === 0 && filter !== 'all') {
                        noResults.style.display = 'block';
                    } else {
                        noResults.style.display = 'none';
                    }
                }
            });
        });

        if (clearBtnId) {
            var clearBtn = document.getElementById(clearBtnId);
            if (clearBtn) {
                clearBtn.addEventListener('click', function () {
                    var allPill = document.querySelector(pillSelector + '[data-filter="all"]');
                    if (allPill) allPill.click();
                });
            }
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        // Opportunities page
        initBranchFilter(
            '.opportunities-page .branch-pill',
            '.opportunity-card[data-branch]',
            'noBranchResultsOpps',
            'clearBranchFilterOpps'
        );

        // Events page
        initBranchFilter(
            '.events-page .branch-pill',
            '#eventsList [data-branch]',
            'noBranchResults',
            'clearBranchFilterEvents'
        );
    });
}());
