document.addEventListener('DOMContentLoaded', () => {
    let currentTab = 'cyber';
    let categoryFilter = '';
    let modeFilter = '';
    let currentPage = 1;
    const pageSize = 10;
    let totalPages = 1;
    let totalItems = 0;

    // Calendar state
    let calDate = new Date();
    let tagsList = [];
    let calendarEntries = [];

    const navTabs = document.querySelectorAll('.tab-btn');
    const filterSection = document.getElementById('filter-section');
    const categoryChips = document.querySelectorAll('#category-chips .chip');
    const modeChipsGroup = document.getElementById('mode-chips');
    const modeChips = document.querySelectorAll('#mode-chips .chip');
    const mainContent = document.getElementById('main-content');

    const todoView = document.getElementById('todo-view');
    const remindersBannerContainer = document.getElementById('reminders-banner-container');
    const dueSoonItemsContainer = document.getElementById('due-soon-items');
    const dueSoonNoteContainer = document.getElementById('due-soon-note');
    const todoCyberList = document.getElementById('todo-cyber-list');
    const todoAiList = document.getElementById('todo-ai-list');
    const todoCloudList = document.getElementById('todo-cloud-list');
    const todoCompletedList = document.getElementById('todo-completed-list');

    const calendarView = document.getElementById('calendar-view');
    const calMonthTitle = document.getElementById('cal-month-title');
    const calPrevMonthBtn = document.getElementById('cal-prev-month');
    const calNextMonthBtn = document.getElementById('cal-next-month');
    const calendarGrid = document.getElementById('calendar-grid');
    const tagsListContainer = document.getElementById('tags-list');
    const newTagForm = document.getElementById('new-tag-form');
    const detailPanel = document.getElementById('detail-panel');
    const detailContent = document.getElementById('detail-content');
    const closeDetailBtn = document.getElementById('close-detail-btn');

    const cardsContainer = document.getElementById('cards-container');
    const pagerText = document.getElementById('pager-text');
    const prevPageBtn = document.getElementById('prev-page');
    const nextPageBtn = document.getElementById('next-page');

    function createEl(tag, props = {}, children = []) {
        const el = document.createElement(tag);
        for (const [key, value] of Object.entries(props)) {
            if (key === 'className') {
                el.className = value;
            } else if (key === 'style' && typeof value === 'object') {
                Object.assign(el.style, value);
            } else if (key.startsWith('on') && typeof value === 'function') {
                el.addEventListener(key.substring(2).toLowerCase(), value);
            } else {
                el.setAttribute(key, value);
            }
        }
        children.forEach(child => {
            if (typeof child === 'string' || typeof child === 'number') {
                el.appendChild(document.createTextNode(String(child)));
            } else if (child instanceof Node) {
                el.appendChild(child);
            }
        });
        return el;
    }

    function getContrastColor(hexColor) {
        if (!hexColor || typeof hexColor !== 'string') return 'var(--ink)';
        let hex = hexColor.replace('#', '').trim();
        if (hex.length === 3) {
            hex = hex.split('').map(c => c + c).join('');
        }
        if (hex.length !== 6) return 'var(--ink)';

        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);

        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        return luminance > 0.6 ? 'var(--ink)' : '#ffffff';
    }

    navTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            navTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            currentTab = tab.dataset.domain;
            categoryFilter = '';
            modeFilter = '';

            categoryChips.forEach(c => c.classList.toggle('active', c.dataset.category === ''));
            modeChips.forEach(m => m.classList.toggle('active', m.dataset.mode === ''));
            modeChipsGroup.style.display = 'none';

            if (currentTab === 'todo') {
                filterSection.style.display = 'none';
                mainContent.style.display = 'none';
                calendarView.style.display = 'none';
                todoView.style.display = 'block';
                fetchReminders();
                fetchTodo();
            } else if (currentTab === 'calendar') {
                filterSection.style.display = 'none';
                mainContent.style.display = 'none';
                todoView.style.display = 'none';
                calendarView.style.display = 'block';
                fetchCalendarAndTags();
            } else {
                filterSection.style.display = 'flex';
                mainContent.style.display = 'block';
                todoView.style.display = 'none';
                calendarView.style.display = 'none';
                resetFiltersAndFetch();
            }
        });
    });

    categoryChips.forEach(chip => {
        chip.addEventListener('click', () => {
            categoryChips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');

            categoryFilter = chip.dataset.category;
            if (categoryFilter === 'hackathon') {
                modeChipsGroup.style.display = 'flex';
            } else {
                modeChipsGroup.style.display = 'none';
                modeFilter = '';
                modeChips.forEach(m => m.classList.toggle('active', m.dataset.mode === ''));
            }
            resetFiltersAndFetch();
        });
    });

    modeChips.forEach(chip => {
        chip.addEventListener('click', () => {
            modeChips.forEach(m => m.classList.remove('active'));
            chip.classList.add('active');

            modeFilter = chip.dataset.mode;
            resetFiltersAndFetch();
        });
    });

    prevPageBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            fetchOpportunities();
        }
    });

    nextPageBtn.addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            fetchOpportunities();
        }
    });

    function resetFiltersAndFetch() {
        currentPage = 1;
        fetchOpportunities();
    }

    // --- Opportunities ---

    async function fetchOpportunities() {
        cardsContainer.replaceChildren();
        const loadingEl = createEl('div', { className: 'empty-state' }, ['Loading opportunities...']);
        cardsContainer.appendChild(loadingEl);

        const params = new URLSearchParams({
            domain: currentTab,
            page: currentPage,
            page_size: pageSize
        });
        if (categoryFilter) params.append('category', categoryFilter);
        if (modeFilter) params.append('mode', modeFilter);

        try {
            const resp = await fetch(`/api/opportunities?${params.toString()}`);
            if (!resp.ok) throw new Error('Failed to fetch opportunities');
            const data = await resp.json();

            totalItems = data.total || 0;
            totalPages = data.total_pages || 1;
            currentPage = data.page || 1;

            updatePager();
            renderCards(data.items || []);
        } catch (err) {
            cardsContainer.replaceChildren();
            const errEl = createEl('div', { className: 'empty-state' }, ['Error loading opportunities. Please try again.']);
            cardsContainer.appendChild(errEl);
        }
    }

    function updatePager() {
        const start = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
        const end = Math.min(currentPage * pageSize, totalItems);
        pagerText.textContent = `${start}-${end} of ${totalItems}`;

        prevPageBtn.disabled = currentPage <= 1;
        nextPageBtn.disabled = currentPage >= totalPages || totalItems === 0;
    }

    function renderCards(items) {
        cardsContainer.replaceChildren();

        if (items.length === 0) {
            const emptyEl = createEl('div', { className: 'empty-state' }, ['No opportunities found.']);
            cardsContainer.appendChild(emptyEl);
            return;
        }

        items.forEach(item => {
            const cardHeader = createEl('div', { className: 'card-header' }, [
                item.category ? item.category.toUpperCase() : 'OPPORTUNITY'
            ]);

            const bodyChildren = [];

            const titleEl = createEl('h3', { className: 'card-title' }, [item.title || 'Untitled Opportunity']);
            bodyChildren.push(titleEl);

            const metaParts = [];
            if (item.domain) metaParts.push(item.domain.toUpperCase());
            if (item.category) metaParts.push(item.category.toUpperCase());
            if (item.mode) metaParts.push(item.mode.toUpperCase());
            if (metaParts.length > 0) {
                bodyChildren.push(createEl('div', { className: 'card-meta' }, [metaParts.join(' · ')]));
            }

            if (item.deadline_utc) {
                bodyChildren.push(createEl('div', { className: 'card-line' }, [`📅 Deadline: ${item.deadline_utc}`]));
            }

            if (item.event_date_utc) {
                bodyChildren.push(createEl('div', { className: 'card-line' }, [`📅 Event Date: ${item.event_date_utc}`]));
            }

            if (item.location) {
                bodyChildren.push(createEl('div', { className: 'card-line' }, [`📍 Location: ${item.location}`]));
            }

            if (item.about) {
                bodyChildren.push(createEl('p', { className: 'card-about' }, [item.about]));
            }

            if (item.rewards) {
                bodyChildren.push(createEl('div', { className: 'card-line' }, [`🎁 Rewards: ${item.rewards}`]));
            }

            if (item.entry_fee) {
                bodyChildren.push(createEl('div', { className: 'card-line' }, [`💰 Entry Fee: ${item.entry_fee}`]));
            }

            if (item.source_domain) {
                bodyChildren.push(createEl('div', { className: 'card-line' }, [`Source: ${item.source_domain}`]));
            }

            if (item.verified) {
                bodyChildren.push(createEl('div', { className: 'verified-badge' }, ['✓ Verified']));
            } else {
                bodyChildren.push(createEl('div', { className: 'unverified-badge' }, ['Unverified, check the link']));
            }

            if (!item.deadline_utc && !item.event_date_utc) {
                bodyChildren.push(createEl('div', { className: 'dates-missing-note' }, ['dates missing, check the link']));
            }

            const actionsEl = createEl('div', { className: 'card-actions' });

            if (item.url) {
                const linkBtn = createEl('a', {
                    className: 'pill-btn',
                    href: item.url,
                    target: '_blank',
                    rel: 'noopener'
                }, ['Source Link 🔗']);
                actionsEl.appendChild(linkBtn);
            }

            const todoBtn = createEl('button', {
                className: `pill-btn ${item.in_todo ? 'active' : ''}`
            }, [item.in_todo ? '✓ In To-Do' : '+ Add to To-Do']);

            todoBtn.addEventListener('click', async () => {
                todoBtn.disabled = true;
                try {
                    if (item.in_todo) {
                        const resp = await fetch(`/api/todo/${item.id}`, { method: 'DELETE' });
                        if (resp.ok) {
                            item.in_todo = false;
                            todoBtn.textContent = '+ Add to To-Do';
                            todoBtn.classList.remove('active');
                        }
                    } else {
                        const resp = await fetch(`/api/todo/${item.id}`, { method: 'POST' });
                        if (resp.ok) {
                            item.in_todo = true;
                            todoBtn.textContent = '✓ In To-Do';
                            todoBtn.classList.add('active');
                        }
                    }
                } catch (e) {
                    console.error('To-Do action failed', e);
                } finally {
                    todoBtn.disabled = false;
                }
            });
            actionsEl.appendChild(todoBtn);

            const calBtn = createEl('button', {
                className: `pill-btn ${item.in_calendar ? 'active' : ''}`
            }, [item.in_calendar ? '✓ In Calendar' : '+ Add to Calendar']);

            calBtn.addEventListener('click', async () => {
                calBtn.disabled = true;
                try {
                    if (item.in_calendar) {
                        const resp = await fetch(`/api/calendar/${item.id}`, { method: 'DELETE' });
                        if (resp.ok) {
                            item.in_calendar = false;
                            calBtn.textContent = '+ Add to Calendar';
                            calBtn.classList.remove('active');
                        }
                    } else {
                        const resp = await fetch(`/api/calendar/${item.id}`, { method: 'POST' });
                        if (resp.ok) {
                            item.in_calendar = true;
                            calBtn.textContent = '✓ In Calendar';
                            calBtn.classList.add('active');
                        }
                    }
                } catch (e) {
                    console.error('Calendar action failed', e);
                } finally {
                    calBtn.disabled = false;
                }
            });
            actionsEl.appendChild(calBtn);

            bodyChildren.push(actionsEl);

            const cardBody = createEl('div', { className: 'card-body' }, bodyChildren);
            const cardWindow = createEl('div', { className: 'card-window' }, [cardHeader, cardBody]);

            cardsContainer.appendChild(cardWindow);
        });
    }

    // --- To-Do Tab Functions ---

    async function fetchReminders() {
        remindersBannerContainer.replaceChildren();
        try {
            const resp = await fetch('/api/reminders');
            if (!resp.ok) return;
            const reminders = await resp.json();
            const unseen = reminders.filter(r => !r.seen);
            if (unseen.length === 0) return;

            const banner = createEl('div', { className: 'reminders-banner' });
            unseen.forEach(rem => {
                const textStr = rem.opportunity_title
                    ? `${rem.opportunity_title}: ${rem.message}`
                    : rem.message;
                const remItem = createEl('div', { className: 'reminder-item' }, [
                    createEl('span', {}, [textStr]),
                    createEl('button', {
                        className: 'dismiss-btn',
                        onClick: async () => {
                            await fetch(`/api/reminders/${rem.id}/seen`, { method: 'POST' });
                            remItem.remove();
                            if (banner.children.length === 0) banner.remove();
                        }
                    }, ['Dismiss'])
                ]);
                banner.appendChild(remItem);
            });
            remindersBannerContainer.appendChild(banner);
        } catch (e) {
            // Silently hide banner on failure
        }
    }

    async function fetchTodo() {
        try {
            const resp = await fetch('/api/todo');
            if (!resp.ok) return;
            const data = await resp.json();
            renderTodoData(data);
        } catch (e) {
            console.error('Fetch todo failed', e);
        }
    }

    function renderTodoData(data) {
        dueSoonItemsContainer.replaceChildren();
        dueSoonNoteContainer.style.display = 'none';

        todoCyberList.replaceChildren();
        todoAiList.replaceChildren();
        todoCloudList.replaceChildren();
        todoCompletedList.replaceChildren();

        const cyberActive = (data.cyber && data.cyber.active) || [];
        const cyberCompleted = (data.cyber && data.cyber.completed) || [];
        const aiActive = (data.ai && data.ai.active) || [];
        const aiCompleted = (data.ai && data.ai.completed) || [];
        const cloudActive = (data.cloud && data.cloud.active) || [];
        const cloudCompleted = (data.cloud && data.cloud.completed) || [];

        const allActive = [...cyberActive, ...aiActive, ...cloudActive];
        const allCompleted = [...cyberCompleted, ...aiCompleted, ...cloudCompleted];

        // 1. Render Due Soon
        const now = new Date();
        const next7Days = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);

        const dueSoon = allActive.filter(item => {
            if (!item.deadline_utc) return false;
            const dDate = new Date(item.deadline_utc.replace('Z', '+00:00'));
            return !isNaN(dDate) && dDate >= now && dDate <= next7Days;
        }).sort((a, b) => {
            return new Date(a.deadline_utc.replace('Z', '+00:00')) - new Date(b.deadline_utc.replace('Z', '+00:00'));
        }).slice(0, 5);

        if (dueSoon.length === 0) {
            dueSoonItemsContainer.appendChild(createEl('div', { className: 'card-line' }, ['Nothing due this week.']));
        } else {
            dueSoon.forEach(item => {
                const card = createEl('div', { className: 'due-soon-card' }, [
                    createEl('span', {}, [item.title]),
                    createEl('span', { className: 'card-meta' }, [`📅 ${item.deadline_utc}`])
                ]);
                dueSoonItemsContainer.appendChild(card);
            });
        }

        if (allActive.length > 5) {
            dueSoonNoteContainer.textContent = `You have ${allActive.length} active. Want to drop one?`;
            dueSoonNoteContainer.style.display = 'block';
        }

        // 2. Render Active Lists
        renderTodoList(cyberActive, todoCyberList, false);
        renderTodoList(aiActive, todoAiList, false);
        renderTodoList(cloudActive, todoCloudList, false);

        // 3. Render Completed List
        renderTodoList(allCompleted, todoCompletedList, true);
    }

    function renderTodoList(items, container, isCompleted) {
        if (items.length === 0) {
            container.appendChild(createEl('div', { className: 'dates-missing-note' }, [isCompleted ? 'No completed items.' : 'No active items.']));
            return;
        }

        items.forEach(item => {
            const checkboxProps = {
                type: 'checkbox',
                className: 'todo-checkbox',
                onChange: async () => {
                    await fetch(`/api/todo/${item.opportunity_id}/toggle`, { method: 'PATCH' });
                    fetchTodo();
                }
            };

            // Active items render with checked=false, completed items render with checked=true
            if (isCompleted) {
                checkboxProps.checked = true;
            }

            const checkbox = createEl('input', checkboxProps);
            if (!isCompleted) {
                checkbox.checked = false;
            }

            const titleEl = createEl('h4', { className: 'todo-card-title' }, [item.title || 'Untitled Opportunity']);

            const removeBtn = createEl('button', {
                className: 'icon-btn',
                onClick: async () => {
                    await fetch(`/api/todo/${item.opportunity_id}`, { method: 'DELETE' });
                    fetchTodo();
                }
            }, ['✕']);

            const topRow = createEl('div', { className: 'todo-card-top' }, [checkbox, titleEl, removeBtn]);

            const cardBody = [topRow];

            const metaParts = [];
            if (item.domain) metaParts.push(item.domain.toUpperCase());
            if (item.category) metaParts.push(item.category.toUpperCase());
            if (item.mode) metaParts.push(item.mode.toUpperCase());
            if (metaParts.length > 0) {
                cardBody.push(createEl('div', { className: 'card-meta' }, [metaParts.join(' · ')]));
            }

            if (item.deadline_utc) {
                cardBody.push(createEl('div', { className: 'card-line' }, [`📅 Deadline: ${item.deadline_utc}`]));
            }
            if (item.event_date_utc) {
                cardBody.push(createEl('div', { className: 'card-line' }, [`📅 Event Date: ${item.event_date_utc}`]));
            }
            if (item.about) {
                cardBody.push(createEl('p', { className: 'card-about' }, [item.about]));
            }

            const actionsEl = createEl('div', { className: 'card-actions' });

            if (item.url) {
                actionsEl.appendChild(createEl('a', {
                    className: 'pill-btn',
                    href: item.url,
                    target: '_blank',
                    rel: 'noopener'
                }, ['Source Link 🔗']));
            }

            if (!isCompleted) {
                const calBtn = createEl('button', {
                    className: `pill-btn ${item.in_calendar ? 'active' : ''}`
                }, [item.in_calendar ? '✓ In Calendar' : '+ Add to Calendar']);

                calBtn.addEventListener('click', async () => {
                    calBtn.disabled = true;
                    try {
                        if (item.in_calendar) {
                            const resp = await fetch(`/api/calendar/${item.opportunity_id}`, { method: 'DELETE' });
                            if (resp.ok) {
                                item.in_calendar = false;
                                calBtn.textContent = '+ Add to Calendar';
                                calBtn.classList.remove('active');
                            }
                        } else {
                            const resp = await fetch(`/api/calendar/${item.opportunity_id}`, { method: 'POST' });
                            if (resp.ok) {
                                item.in_calendar = true;
                                calBtn.textContent = '✓ In Calendar';
                                calBtn.classList.add('active');
                            }
                        }
                    } catch (e) {
                        console.error('Calendar action failed', e);
                    } finally {
                        calBtn.disabled = false;
                    }
                });
                actionsEl.appendChild(calBtn);
            }

            cardBody.push(actionsEl);

            const card = createEl('div', { className: `todo-card ${isCompleted ? 'completed' : ''}` }, cardBody);
            container.appendChild(card);
        });
    }

    // --- Calendar Tab Functions ---

    calPrevMonthBtn.addEventListener('click', () => {
        calDate.setMonth(calDate.getMonth() - 1);
        fetchCalendarAndTags();
    });

    calNextMonthBtn.addEventListener('click', () => {
        calDate.setMonth(calDate.getMonth() + 1);
        fetchCalendarAndTags();
    });

    closeDetailBtn.addEventListener('click', () => {
        detailPanel.style.display = 'none';
    });

    newTagForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const nameInput = document.getElementById('new-tag-name');
        const colorInput = document.getElementById('new-tag-color');
        const name = nameInput.value.trim();
        const color = colorInput.value;
        if (!name) return;

        try {
            const resp = await fetch('/api/tags', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, color })
            });
            if (resp.ok) {
                nameInput.value = '';
                fetchCalendarAndTags();
            }
        } catch (err) {
            console.error('Create tag failed', err);
        }
    });

    async function fetchCalendarAndTags() {
        const year = calDate.getFullYear();
        const month = String(calDate.getMonth() + 1).padStart(2, '0');
        const monthStr = `${year}-${month}`;

        const monthName = calDate.toLocaleString('default', { month: 'long' });
        calMonthTitle.textContent = `${monthName} ${year}`;

        try {
            const [tagsResp, calResp] = await Promise.all([
                fetch('/api/tags'),
                fetch(`/api/calendar?month=${monthStr}`)
            ]);

            if (tagsResp.ok) tagsList = await tagsResp.json();
            if (calResp.ok) {
                const calData = await calResp.json();
                calendarEntries = calData.entries || [];
            }

            renderTagsPanel();
            renderCalendarGrid(year, calDate.getMonth() + 1);
        } catch (e) {
            console.error('Fetch calendar or tags failed', e);
        }
    }

    function renderTagsPanel() {
        tagsListContainer.replaceChildren();
        tagsList.forEach(tag => {
            const colorInput = createEl('input', {
                type: 'color',
                className: 'tag-color-input',
                value: tag.color
            });

            colorInput.addEventListener('change', async () => {
                const newColor = colorInput.value;
                tag.color = newColor;
                renderCalendarGrid(calDate.getFullYear(), calDate.getMonth() + 1);
                try {
                    await fetch(`/api/tags/${tag.id}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ color: newColor })
                    });
                } catch (e) {
                    console.error('Update tag color failed', e);
                }
            });

            const item = createEl('div', { className: 'tag-item' }, [
                createEl('span', {}, [tag.name]),
                colorInput
            ]);
            tagsListContainer.appendChild(item);
        });
    }

    function renderCalendarGrid(year, month) {
        calendarGrid.replaceChildren();

        const headers = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        headers.forEach(h => {
            calendarGrid.appendChild(createEl('div', { className: 'cal-header-cell' }, [h]));
        });

        const firstDayIdx = new Date(year, month - 1, 1).getDay();
        const daysInMonth = new Date(year, month, 0).getDate();

        for (let i = 0; i < firstDayIdx; i++) {
            calendarGrid.appendChild(createEl('div', { className: 'cal-day-cell other-month' }));
        }

        for (let d = 1; d <= daysInMonth; d++) {
            const dayStr = String(d).padStart(2, '0');
            const dateISO = `${year}-${String(month).padStart(2, '0')}-${dayStr}`;

            const dayNum = createEl('div', { className: 'cal-day-num' }, [d]);
            const dayCell = createEl('div', { className: 'cal-day-cell' }, [dayNum]);

            const dayEntries = calendarEntries.filter(e => {
                return e.date && e.date.startsWith(dateISO);
            });

            const maxVisible = 3;
            const visibleEntries = dayEntries.slice(0, maxVisible);
            const hiddenCount = dayEntries.length - maxVisible;

            visibleEntries.forEach(entry => {
                const prefix = entry.kind === 'deadline' ? 'D:' : 'E:';
                const labelText = `${prefix} ${entry.title || 'Untitled'}`;
                const textColor = getContrastColor(entry.tag_color);

                const chip = createEl('div', {
                    className: `cal-entry-chip ${entry.kind}`,
                    title: labelText,
                    style: {
                        backgroundColor: entry.tag_color || '#c4a9f9',
                        color: textColor
                    }
                }, [labelText]);

                chip.addEventListener('click', () => {
                    renderDetailPanel(entry);
                });
                dayCell.appendChild(chip);
            });

            if (hiddenCount > 0) {
                const moreBtn = createEl('div', {
                    className: 'cal-more-link',
                    style: {
                        fontSize: '0.65rem',
                        fontWeight: 'bold',
                        color: 'var(--purple)',
                        cursor: 'pointer',
                        marginTop: '2px'
                    }
                }, [`+${hiddenCount} more`]);

                moreBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    renderDayEntriesDetailPanel(dateISO, dayEntries);
                });
                dayCell.appendChild(moreBtn);
            }

            calendarGrid.appendChild(dayCell);
        }
    }

    function renderDetailPanel(entry) {
        detailContent.replaceChildren();

        const titleEl = createEl('h4', { className: 'card-title' }, [entry.title || 'Untitled']);
        const metaParts = [entry.domain, entry.category].filter(Boolean).map(s => s.toUpperCase());
        const metaEl = createEl('div', { className: 'card-meta' }, [metaParts.join(' · ')]);

        detailContent.appendChild(titleEl);
        if (metaParts.length > 0) detailContent.appendChild(metaEl);

        if (entry.event_date_utc) {
            detailContent.appendChild(createEl('div', { className: 'card-line' }, [`📅 Event Date: ${entry.event_date_utc}`]));
        }
        if (entry.deadline_utc) {
            detailContent.appendChild(createEl('div', { className: 'card-line' }, [`📅 Deadline: ${entry.deadline_utc}`]));
        }
        if (entry.location) {
            detailContent.appendChild(createEl('div', { className: 'card-line' }, [`📍 Location: ${entry.location}`]));
        }

        if (entry.url) {
            detailContent.appendChild(createEl('a', {
                className: 'pill-btn',
                href: entry.url,
                target: '_blank',
                rel: 'noopener'
            }, ['Source Link 🔗']));
        }

        const tagLabel = createEl('div', { className: 'card-line' }, ['Tag: ']);
        const tagSelect = createEl('select', { className: 'tag-select' });

        tagsList.forEach(t => {
            const opt = createEl('option', { value: t.id }, [t.name]);
            if (t.name === entry.tag_name) opt.selected = true;
            tagSelect.appendChild(opt);
        });

        tagSelect.addEventListener('change', async () => {
            const newTagId = parseInt(tagSelect.value, 10);
            try {
                await fetch(`/api/calendar/${entry.opportunity_id}/tag`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tag_id: newTagId })
                });
                fetchCalendarAndTags();
            } catch (err) {
                console.error('Assign tag failed', err);
            }
        });
        tagLabel.appendChild(tagSelect);
        detailContent.appendChild(tagLabel);

        const removeBtn = createEl('button', {
            className: 'pill-btn',
            style: { backgroundColor: '#fca5a5' },
            onClick: async () => {
                await fetch(`/api/calendar/${entry.opportunity_id}`, { method: 'DELETE' });
                detailPanel.style.display = 'none';
                fetchCalendarAndTags();
            }
        }, ['Remove from Calendar']);
        detailContent.appendChild(removeBtn);

        detailPanel.style.display = 'block';
    }

    function renderDayEntriesDetailPanel(dateISO, entries) {
        detailContent.replaceChildren();

        const titleEl = createEl('h4', { className: 'card-title' }, [`Entries for ${dateISO}`]);
        detailContent.appendChild(titleEl);

        entries.forEach((entry, idx) => {
            const itemBox = createEl('div', {
                style: {
                    borderTop: idx > 0 ? '2px solid var(--ink)' : 'none',
                    paddingTop: idx > 0 ? '8px' : '0',
                    marginTop: idx > 0 ? '8px' : '0'
                }
            });

            const prefix = entry.kind === 'deadline' ? 'D:' : 'E:';
            const itemTitle = createEl('h5', { className: 'card-title', style: { fontSize: '14px' } }, [`${prefix} ${entry.title || 'Untitled'}`]);
            const metaParts = [entry.domain, entry.category].filter(Boolean).map(s => s.toUpperCase());
            const metaEl = createEl('div', { className: 'card-meta' }, [metaParts.join(' · ')]);

            itemBox.appendChild(itemTitle);
            if (metaParts.length > 0) itemBox.appendChild(metaEl);

            if (entry.event_date_utc) {
                itemBox.appendChild(createEl('div', { className: 'card-line' }, [`📅 Event Date: ${entry.event_date_utc}`]));
            }
            if (entry.deadline_utc) {
                itemBox.appendChild(createEl('div', { className: 'card-line' }, [`📅 Deadline: ${entry.deadline_utc}`]));
            }
            if (entry.location) {
                itemBox.appendChild(createEl('div', { className: 'card-line' }, [`📍 Location: ${entry.location}`]));
            }
            if (entry.url) {
                itemBox.appendChild(createEl('a', {
                    className: 'pill-btn',
                    href: entry.url,
                    target: '_blank',
                    rel: 'noopener'
                }, ['Source Link 🔗']));
            }

            const tagLabel = createEl('div', { className: 'card-line' }, ['Tag: ']);
            const tagSelect = createEl('select', { className: 'tag-select' });

            tagsList.forEach(t => {
                const opt = createEl('option', { value: t.id }, [t.name]);
                if (t.name === entry.tag_name) opt.selected = true;
                tagSelect.appendChild(opt);
            });

            tagSelect.addEventListener('change', async () => {
                const newTagId = parseInt(tagSelect.value, 10);
                try {
                    await fetch(`/api/calendar/${entry.opportunity_id}/tag`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ tag_id: newTagId })
                    });
                    fetchCalendarAndTags();
                } catch (err) {
                    console.error('Assign tag failed', err);
                }
            });
            tagLabel.appendChild(tagSelect);
            itemBox.appendChild(tagLabel);

            const removeBtn = createEl('button', {
                className: 'pill-btn',
                style: { backgroundColor: '#fca5a5', marginTop: '6px' },
                onClick: async () => {
                    await fetch(`/api/calendar/${entry.opportunity_id}`, { method: 'DELETE' });
                    detailPanel.style.display = 'none';
                    fetchCalendarAndTags();
                }
            }, ['Remove from Calendar']);
            itemBox.appendChild(removeBtn);

            detailContent.appendChild(itemBox);
        });

        detailPanel.style.display = 'block';
    }

    // Initial fetch
    fetchOpportunities();
});
