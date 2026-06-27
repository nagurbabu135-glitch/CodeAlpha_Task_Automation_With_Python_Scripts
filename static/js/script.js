// AutoPy Frontend Javascript Logic

document.addEventListener('DOMContentLoaded', () => {
    // State management
    let demoPaths = null;
    let authState = {
        authenticated: false,
        username: null,
        db_connected: false
    };

    // DOM Elements - Navigation & Core
    const navItems = document.querySelectorAll('.nav-item');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const setupDemoBtn = document.getElementById('setup-demo-btn');
    const toast = document.getElementById('toast');
    const toastMsg = document.getElementById('toast-msg');

    // DOM Elements - Authentication
    const authOverlay = document.getElementById('auth-overlay');
    const btnShowLogin = document.getElementById('btn-show-login');
    const btnShowRegister = document.getElementById('btn-show-register');
    const formLogin = document.getElementById('form-login');
    const formRegister = document.getElementById('form-register');
    const userProfile = document.getElementById('user-profile');
    const displayUsername = document.getElementById('display-username');
    const logoutBtn = document.getElementById('logout-btn');

    // DOM Elements - History Tab
    const historyTable = document.getElementById('history-table');
    const historyRows = document.getElementById('history-rows');
    const historyLoading = document.getElementById('history-loading');
    const historyEmpty = document.getElementById('history-empty');

    // DOM Elements - Log Modal
    const logModal = document.getElementById('log-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalTaskName = document.getElementById('modal-task-name');
    const modalTimestamp = document.getElementById('modal-timestamp');
    const modalStatusBadge = document.getElementById('modal-status-badge');
    const modalParamsText = document.getElementById('modal-params-text');
    const modalLogsBody = document.getElementById('modal-logs-body');

    // DOM Elements - Forms
    const formMoveJpgs = document.getElementById('form-move-jpgs');
    const formExtractEmails = document.getElementById('form-extract-emails');
    const formScrapeTitle = document.getElementById('form-scrape-title');

    // Path Paste Helpers
    const pathButtons = document.querySelectorAll('.path-btn');

    // History data cache
    let historyCache = [];

    // ==========================================================================
    // 1. Navigation / Tab switching
    // ==========================================================================
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const tabId = item.getAttribute('data-tab');
            switchTab(tabId);
        });
    });

    function switchTab(tabId) {
        // Toggle active sidebar item
        navItems.forEach(n => {
            if (n.getAttribute('data-tab') === tabId) {
                n.classList.add('active');
            } else {
                n.classList.remove('active');
            }
        });

        // Toggle active tab pane
        tabPanes.forEach(p => {
            if (p.id === `tab-${tabId}`) {
                p.classList.add('active');
            } else {
                p.classList.remove('active');
            }
        });

        // If switching to History, reload history logs
        if (tabId === 'history') {
            loadHistory();
        }
    }

    // Overview spec card click navigation
    const specCards = document.querySelectorAll('.spec-card');
    specCards.forEach(card => {
        card.addEventListener('click', () => {
            const targetTab = card.getAttribute('data-target-tab');
            if (targetTab) {
                switchTab(targetTab);
            }
        });
    });

    // ==========================================================================
    // 2. Authentication State Management
    // ==========================================================================
    
    // Toggle Login vs Register view
    btnShowLogin.addEventListener('click', () => {
        btnShowLogin.classList.add('active');
        btnShowRegister.classList.remove('active');
        formLogin.classList.remove('hidden');
        formRegister.classList.add('hidden');
    });

    btnShowRegister.addEventListener('click', () => {
        btnShowRegister.classList.add('active');
        btnShowLogin.classList.remove('active');
        formRegister.classList.remove('hidden');
        formLogin.classList.add('hidden');
    });

    // Check Login Status on load
    async function checkAuthStatus() {
        try {
            const response = await fetch('/api/user-status');
            const data = await response.json();
            authState = data;
            
            if (authState.authenticated) {
                authOverlay.classList.add('hidden');
                userProfile.classList.remove('hidden');
                displayUsername.textContent = authState.username;
            } else {
                authOverlay.classList.remove('hidden');
                userProfile.classList.add('hidden');
            }
        } catch (err) {
            console.error('Error checking authentication status:', err);
        }
    }

    // Submit Registration
    formRegister.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('register-username').value;
        const password = document.getElementById('register-password').value;
        
        const btn = formRegister.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.textContent = 'Registering...';

        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await response.json();

            if (data.success) {
                showToast(data.message);
                // Switch to login
                btnShowLogin.click();
                document.getElementById('login-username').value = username;
                document.getElementById('login-password').focus();
            } else {
                showToast(data.error || 'Registration failed.', true);
            }
        } catch (err) {
            showToast('Network error during registration.', true);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Create Account';
        }
    });

    // Submit Login
    formLogin.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;

        const btn = formLogin.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.textContent = 'Signing In...';

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await response.json();

            if (data.success) {
                showToast(data.message);
                // Clear login inputs
                document.getElementById('login-password').value = '';
                // Check auth to refresh page view
                await checkAuthStatus();
            } else {
                showToast(data.error || 'Login failed.', true);
            }
        } catch (err) {
            showToast('Network error during login.', true);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Sign In';
        }
    });

    // Submit Logout
    logoutBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/api/logout', { method: 'POST' });
            const data = await response.json();
            if (data.success) {
                showToast(data.message);
                demoPaths = null;
                // Switch back to overview tab
                switchTab('overview');
                // Check auth to show login screen
                await checkAuthStatus();
            }
        } catch (err) {
            console.error('Logout failed:', err);
        }
    });

    // Helper to handle API response auth errors (e.g. 401 Unauthorized)
    function handleAuthError(response) {
        if (response.status === 401) {
            checkAuthStatus();
            showToast('Session expired. Please login again.', true);
            return true;
        }
        return false;
    }

    // ==========================================================================
    // 3. Execution History (MongoDB Logs Viewer)
    // ==========================================================================
    
    async function loadHistory() {
        historyLoading.classList.remove('hidden');
        historyTable.classList.add('hidden');
        historyEmpty.classList.add('hidden');
        
        try {
            const response = await fetch('/api/history');
            if (handleAuthError(response)) return;
            
            const data = await response.json();
            historyLoading.classList.add('hidden');

            if (data.success) {
                historyCache = data.history;
                
                if (historyCache.length === 0) {
                    historyEmpty.classList.remove('hidden');
                } else {
                    renderHistoryTable(historyCache);
                }
            } else {
                showToast(data.error || 'Failed to load history.', true);
            }
        } catch (err) {
            historyLoading.classList.add('hidden');
            showToast('Network error loading run history.', true);
        }
    }

    function renderHistoryTable(runs) {
        historyRows.innerHTML = '';
        runs.forEach(run => {
            const row = document.createElement('tr');
            
            // Format task name
            let taskLabel = run.task;
            if (run.task === 'move_jpgs') taskLabel = 'File Organizer';
            else if (run.task === 'extract_emails') taskLabel = 'Email Extractor';
            else if (run.task === 'scrape_title') taskLabel = 'Title Scraper';
            
            // Status badge
            const statusClass = run.success ? 'success' : 'failed';
            const statusIcon = run.success ? 'fa-circle-check' : 'fa-circle-xmark';
            const statusText = run.success ? 'Success' : 'Failed';
            
            row.innerHTML = `
                <td>${run.timestamp || 'N/A'}</td>
                <td><strong>${taskLabel}</strong></td>
                <td>
                    <span class="status-badge ${statusClass}">
                        <i class="fa-solid ${statusIcon}"></i> ${statusText}
                    </span>
                </td>
                <td>
                    <button class="btn-view" data-id="${run.id}">View logs</button>
                </td>
            `;
            historyRows.appendChild(row);
        });

        // Hook view buttons
        historyRows.querySelectorAll('.btn-view').forEach(btn => {
            btn.addEventListener('click', () => {
                const runId = btn.getAttribute('data-id');
                const run = historyCache.find(r => r.id === runId);
                if (run) showLogModal(run);
            });
        });

        historyTable.classList.remove('hidden');
    }

    function showLogModal(run) {
        // Format names
        let taskLabel = run.task;
        if (run.task === 'move_jpgs') taskLabel = 'File Organizer (move_jpgs)';
        else if (run.task === 'extract_emails') taskLabel = 'Email Extractor (extract_emails)';
        else if (run.task === 'scrape_title') taskLabel = 'Title Scraper (scrape_title)';

        modalTaskName.textContent = taskLabel;
        modalTimestamp.textContent = run.timestamp || 'N/A';
        
        // Status Badge
        modalStatusBadge.className = `status-badge ${run.success ? 'success' : 'failed'}`;
        modalStatusBadge.innerHTML = `<i class="fa-solid ${run.success ? 'fa-circle-check' : 'fa-circle-xmark'}"></i> ${run.success ? 'Success' : 'Failed'}`;
        
        // Parameters block
        modalParamsText.textContent = JSON.stringify(run.params, null, 2);
        
        // Logs block
        modalLogsBody.innerHTML = '';
        if (run.logs && run.logs.length > 0) {
            run.logs.forEach(line => {
                const logLine = document.createElement('div');
                // Detect line type and color
                logLine.style.lineHeight = '1.4';
                logLine.style.wordBreak = 'break-all';
                
                if (line.startsWith('Error') || line.startsWith('Unexpected error')) {
                    logLine.style.color = 'var(--danger)';
                } else if (line.startsWith('Success') || line.startsWith('Successfully') || line.startsWith('Moved') || line.startsWith('Saved')) {
                    logLine.style.color = 'var(--success)';
                } else {
                    logLine.style.color = '#94a3b8';
                }
                
                logLine.textContent = `  ${line}`;
                modalLogsBody.appendChild(logLine);
            });
        } else {
            modalLogsBody.textContent = '  No logs captured.';
        }

        logModal.classList.remove('hidden');
    }

    closeModalBtn.addEventListener('click', () => {
        logModal.classList.add('hidden');
    });

    logModal.addEventListener('click', (e) => {
        if (e.target === logModal) logModal.classList.add('hidden');
    });

    // ==========================================================================
    // 4. Console Logger (No-op after console UI removal)
    // ==========================================================================
    function logToConsole(message, type = 'log') {
        console.log(`[${type}] ${message}`);
    }

    // ==========================================================================
    // 5. Toast Notifications
    // ==========================================================================
    function showToast(message, isError = false) {
        toastMsg.textContent = message;
        toast.className = 'toast'; // reset classes
        
        if (isError) {
            toast.classList.add('error');
            document.getElementById('toast-icon').innerHTML = '<i class="fa-solid fa-circle-exclamation"></i>';
        } else {
            toast.classList.add('success');
            document.getElementById('toast-icon').innerHTML = '<i class="fa-solid fa-circle-check"></i>';
        }
        
        toast.classList.remove('hidden');
        
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 4000);
    }

    // ==========================================================================
    // 6. Setup Demo Workspace API Call
    // ==========================================================================
    setupDemoBtn.addEventListener('click', async () => {
        setupDemoBtn.disabled = true;
        const icon = setupDemoBtn.querySelector('i');
        icon.className = 'fa-solid fa-spinner fa-spin';
        
        try {
            const response = await fetch('/api/setup-demo', { method: 'POST' });
            if (handleAuthError(response)) return;
            
            const data = await response.json();
            
            if (data.success) {
                demoPaths = data.paths;
                showToast('Demo Workspace Created!');
            } else {
                showToast('Demo workspace setup failed.', true);
            }
        } catch (err) {
            showToast('Network error setting up demo.', true);
        } finally {
            setupDemoBtn.disabled = false;
            icon.className = 'fa-solid fa-flask';
        }
    });

    // ==========================================================================
    // 7. Path Helper autofill logic
    // ==========================================================================
    pathButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            const input = document.getElementById(targetId);
            
            if (!demoPaths) {
                showToast('Setup Demo Workspace first!', true);
                return;
            }

            let pathValue = '';
            switch (targetId) {
                case 'move-src':
                    pathValue = demoPaths.source_jpg_dir;
                    break;
                case 'move-dest':
                    pathValue = demoPaths.dest_jpg_dir;
                    break;
                case 'extract-src':
                    pathValue = demoPaths.emails_input_file;
                    break;
                case 'extract-dest':
                    pathValue = demoPaths.emails_output_file;
                    break;
                case 'scrape-url':
                    pathValue = 'https://news.ycombinator.com';
                    break;
                case 'scrape-dest':
                    pathValue = demoPaths.scraper_output_file;
                    break;
            }

            input.value = pathValue;
            showToast(`Autofilled demo path!`);
        });
    });

    // ==========================================================================
    // 8. Submit task automations
    // ==========================================================================
    
    // Task 1: JPG Organizer
    formMoveJpgs.addEventListener('submit', async (e) => {
        e.preventDefault();
        const source_dir = document.getElementById('move-src').value;
        const dest_dir = document.getElementById('move-dest').value;

        const btn = formMoveJpgs.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Organizing...';

        try {
            const response = await fetch('/api/run-task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    task: 'move_jpgs',
                    params: { source_dir, dest_dir }
                })
            });
            if (handleAuthError(response)) return;
            
            const data = await response.json();
            
            if (data.success) {
                showToast('Files organized successfully!');
            } else {
                showToast('Task failed. See history logs.', true);
            }
        } catch (err) {
            showToast('Network error executing task.', true);
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });

    // Task 2: Email Extractor
    formExtractEmails.addEventListener('submit', async (e) => {
        e.preventDefault();
        const source_file = document.getElementById('extract-src').value;
        const dest_file = document.getElementById('extract-dest').value;

        const btn = formExtractEmails.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Extracting...';

        try {
            const response = await fetch('/api/run-task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    task: 'extract_emails',
                    params: { source_file, dest_file }
                })
            });
            if (handleAuthError(response)) return;
            
            const data = await response.json();
            
            if (data.success) {
                showToast('Emails extracted successfully!');
            } else {
                showToast('Task failed. See history logs.', true);
            }
        } catch (err) {
            showToast('Network error executing task.', true);
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });

    // Task 3: Title Scraper
    formScrapeTitle.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = document.getElementById('scrape-url').value;
        const dest_file = document.getElementById('scrape-dest').value;

        const btn = formScrapeTitle.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Scraping...';

        try {
            const response = await fetch('/api/run-task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    task: 'scrape_title',
                    params: { url, dest_file }
                })
            });
            if (handleAuthError(response)) return;
            
            const data = await response.json();
            
            if (data.success) {
                showToast('Webpage title scraped successfully!');
            } else {
                showToast('Task failed. See history logs.', true);
            }
        } catch (err) {
            showToast('Network error executing task.', true);
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });

    // ==========================================================================
    // 9. Startup Checks
    // ==========================================================================
    checkAuthStatus();
});
