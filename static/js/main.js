document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------
    // Theme Toggle Handler
    // ----------------------------------------------------
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const themeIcon = themeToggleBtn ? themeToggleBtn.querySelector('i') : null;
    
    // Check local storage or system preference
    const currentTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', currentTheme);
    updateThemeIcon(currentTheme);
    
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            let theme = document.documentElement.getAttribute('data-theme');
            let newTheme = theme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }
    
    function updateThemeIcon(theme) {
        if (!themeIcon) return;
        if (theme === 'light') {
            themeIcon.className = 'fas fa-moon';
        } else {
            themeIcon.className = 'fas fa-sun';
        }
    }
    
    // ----------------------------------------------------
    // Mobile Sidebar Toggler
    // ----------------------------------------------------
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('open');
        });
        
        document.addEventListener('click', (e) => {
            if (sidebar.classList.contains('open') && !sidebar.contains(e.target) && e.target !== menuToggle) {
                sidebar.classList.remove('open');
            }
        });
    }

    // ----------------------------------------------------
    // Drag and Drop File Upload
    // ----------------------------------------------------
    const dropzone = document.getElementById('upload-dropzone');
    const fileInput = document.getElementById('timetable_file');
    
    if (dropzone && fileInput) {
        dropzone.addEventListener('click', () => fileInput.click());
        
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        
        ['dragleave', 'dragend'].forEach(type => {
            dropzone.addEventListener(type, () => {
                dropzone.classList.remove('dragover');
            });
        });
        
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                updateDropzoneText(e.dataTransfer.files[0].name);
            }
        });
        
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                updateDropzoneText(fileInput.files[0].name);
            }
        });
        
        function updateDropzoneText(name) {
            const dzText = dropzone.querySelector('p');
            const dzSubText = dropzone.querySelector('span');
            if (dzText) dzText.textContent = `Selected: ${name}`;
            if (dzSubText) dzSubText.textContent = "Ready to upload";
        }
    }

    // ----------------------------------------------------
    // In-App Notification System
    // ----------------------------------------------------
    const notifItems = document.querySelectorAll('.notification-item.unread');
    notifItems.forEach(item => {
        const markBtn = item.querySelector('.notification-mark-read');
        if (markBtn) {
            markBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                const notifId = item.dataset.id;
                try {
                    const res = await fetch(`/faculty/notifications/read/${notifId}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                    const data = await res.json();
                    if (data.success) {
                        item.classList.remove('unread');
                        markBtn.remove();
                        // Update badge counts if any
                        const badge = document.getElementById('notif-badge');
                        if (badge) {
                            let count = parseInt(badge.textContent);
                            if (count > 1) {
                                badge.textContent = count - 1;
                            } else {
                                badge.remove();
                            }
                        }
                    }
                } catch (err) {
                    console.error("Error marking notification as read:", err);
                }
            });
        }
    });

    // ----------------------------------------------------
    // Reassignment Editor & Conflict Live Validator
    // ----------------------------------------------------
    const reassignModal = document.getElementById('reassign-modal');
    if (reassignModal) {
        const reassignButtons = document.querySelectorAll('.btn-reassign');
        const modalForm = document.getElementById('reassign-form');
        const modalExamTitle = document.getElementById('modal-exam-title');
        const facultySelect = document.getElementById('modal-faculty-select');
        const validationBox = document.getElementById('modal-validation-box');
        const submitBtn = document.getElementById('modal-submit-btn');
        
        let activeAssignmentId = null;

        reassignButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const asgId = btn.dataset.id;
                const subject = btn.dataset.subject;
                const date = btn.dataset.date;
                const time = btn.dataset.time;
                const hall = btn.dataset.hall;
                const currentFacId = btn.dataset.facultyId;
                
                activeAssignmentId = asgId;
                modalExamTitle.textContent = `${subject} (${date} @ ${time} in ${hall})`;
                facultySelect.value = currentFacId || "unassigned";
                
                // Reset validation box
                validationBox.innerHTML = '';
                validationBox.style.display = 'none';
                submitBtn.disabled = false;
                
                modalForm.action = `/admin/assignments/edit/${asgId}`;
                openModal(reassignModal);
            });
        });

        // Add change listener to validate conflicts
        facultySelect.addEventListener('change', async () => {
            const facultyId = facultySelect.value;
            
            validationBox.innerHTML = '<div style="color: var(--text-secondary)"><i class="fas fa-spinner fa-spin"></i> Checking rules...</div>';
            validationBox.style.display = 'block';
            submitBtn.disabled = true;

            try {
                const res = await fetch('/admin/assignments/validate-edit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        assignment_id: activeAssignmentId,
                        faculty_id: facultyId
                    })
                });
                
                const data = await res.json();
                validationBox.innerHTML = '';
                
                if (data.errors && data.errors.length > 0) {
                    // Show errors - Block submission
                    let html = '<ul style="color: var(--danger); list-style-type: disc; padding-left: 20px;">';
                    data.errors.forEach(err => {
                        html += `<li><strong>Blocked:</strong> ${err}</li>`;
                    });
                    html += '</ul>';
                    validationBox.innerHTML = html;
                    submitBtn.disabled = true;
                } else if (data.warnings && data.warnings.length > 0) {
                    // Show warnings - Allow submission but caution user
                    let html = '<ul style="color: var(--warning); list-style-type: disc; padding-left: 20px;">';
                    data.warnings.forEach(warn => {
                        html += `<li><strong>Warning:</strong> ${warn}</li>`;
                    });
                    html += '</ul>';
                    validationBox.innerHTML = html;
                    submitBtn.disabled = false;
                } else {
                    // Fully valid
                    validationBox.innerHTML = '<div style="color: var(--success);"><i class="fas fa-check-circle"></i> Faculty is available. No conflicts found.</div>';
                    submitBtn.disabled = false;
                }
            } catch (err) {
                validationBox.innerHTML = '<div style="color: var(--danger)">Error performing validation check.</div>';
                submitBtn.disabled = false;
            }
        });
    }

    // ----------------------------------------------------
    // Modal Overlay helper controls
    // ----------------------------------------------------
    window.openModal = function(modal) {
        modal.classList.add('open');
    };
    
    window.closeModal = function(modal) {
        modal.classList.remove('open');
    };
    
    const closeModalButtons = document.querySelectorAll('[data-close-modal]');
    closeModalButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.dataset.closeModal;
            const target = document.getElementById(targetId);
            if (target) closeModal(target);
        });
    });

    // Close on clicking outside modal
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(modal);
            }
        });
    });
});

// --------------------------------------------------------
// Custom Interactive Duty Calendar for Faculty Dashboard
// --------------------------------------------------------
window.initDutyCalendar = function(containerId, events) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let currentDate = new Date();
    
    function renderCalendar() {
        container.innerHTML = '';
        
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        
        // Month names
        const monthNames = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ];
        
        // Header
        const header = document.createElement('div');
        header.className = 'calendar-header';
        
        const prevBtn = document.createElement('button');
        prevBtn.className = 'btn btn-secondary btn-icon';
        prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
        prevBtn.addEventListener('click', () => {
            currentDate.setMonth(currentDate.getMonth() - 1);
            renderCalendar();
        });
        
        const title = document.createElement('h3');
        title.className = 'chart-title';
        title.textContent = `${monthNames[month]} ${year}`;
        
        const nextBtn = document.createElement('button');
        nextBtn.className = 'btn btn-secondary btn-icon';
        nextBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
        nextBtn.addEventListener('click', () => {
            currentDate.setMonth(currentDate.getMonth() + 1);
            renderCalendar();
        });
        
        header.appendChild(prevBtn);
        header.appendChild(title);
        header.appendChild(nextBtn);
        container.appendChild(header);
        
        // Grid
        const grid = document.createElement('div');
        grid.className = 'calendar-grid';
        
        // Days header
        const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
        days.forEach(d => {
            const dh = document.createElement('div');
            dh.className = 'calendar-day-header';
            dh.textContent = d;
            grid.appendChild(dh);
        });
        
        // Days values
        const firstDayIndex = new Date(year, month, 1).getDay();
        const lastDay = new Date(year, month + 1, 0).getDate();
        const prevLastDay = new Date(year, month, 0).getDate();
        
        // Previous month filler days
        for (let i = firstDayIndex; i > 0; i--) {
            const day = document.createElement('div');
            day.className = 'calendar-day other-month';
            day.innerHTML = `<span class="calendar-day-num">${prevLastDay - i + 1}</span>`;
            grid.appendChild(day);
        }
        
        // Current month days
        const today = new Date();
        for (let i = 1; i <= lastDay; i++) {
            const day = document.createElement('div');
            day.className = 'calendar-day';
            
            const isToday = today.getDate() === i && today.getMonth() === month && today.getFullYear() === year;
            if (isToday) {
                day.classList.add('today');
            }
            
            day.innerHTML = `<span class="calendar-day-num">${i}</span>`;
            
            // Format check YYYY-MM-DD
            const formattedDate = `${year}-${String(month + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
            
            const dayEventsContainer = document.createElement('div');
            dayEventsContainer.className = 'calendar-events-container';
            
            // Find events matching this date
            const dayEvents = events.filter(e => e.start.startsWith(formattedDate));
            dayEvents.forEach(ev => {
                const evDiv = document.createElement('div');
                evDiv.className = 'calendar-event';
                evDiv.textContent = ev.title;
                evDiv.title = ev.title;
                if (ev.status === 'Exchanged') {
                    evDiv.style.backgroundColor = 'var(--info-bg)';
                    evDiv.style.color = 'var(--info)';
                    evDiv.style.borderLeftColor = 'var(--info)';
                }
                dayEventsContainer.appendChild(evDiv);
            });
            
            day.appendChild(dayEventsContainer);
            grid.appendChild(day);
        }
        
        // Next month filler days to complete grid (42 blocks)
        const totalBlocks = 42;
        const currentBlocks = firstDayIndex + lastDay;
        const nextFiller = totalBlocks - currentBlocks;
        for (let i = 1; i <= nextFiller; i++) {
            const day = document.createElement('div');
            day.className = 'calendar-day other-month';
            day.innerHTML = `<span class="calendar-day-num">${i}</span>`;
            grid.appendChild(day);
        }
        
        container.appendChild(grid);
    }
    
    renderCalendar();
};
