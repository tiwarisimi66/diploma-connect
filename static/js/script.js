/**
 * script.js - Main client-side interactivity for DiplomaConnect
 * Clean, lightweight vanilla JavaScript.
 */

document.addEventListener("DOMContentLoaded", function () {
    // 1. Mobile Sidebar Drawer Toggle
    const sidebarToggle = document.getElementById("sidebarToggle");
    const appSidebar = document.getElementById("appSidebar");

    if (sidebarToggle && appSidebar) {
        sidebarToggle.addEventListener("click", function (e) {
            e.stopPropagation();
            appSidebar.classList.toggle("open");
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener("click", function (e) {
            if (window.innerWidth < 992 && appSidebar.classList.contains("open")) {
                if (!appSidebar.contains(e.target) && e.target !== sidebarToggle) {
                    appSidebar.classList.remove("open");
                }
            }
        });
    }

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
