(() => {
    const toggle = document.getElementById('assistant-toggle');
    const panel = document.getElementById('assistant-panel');
    const form = document.getElementById('assistant-form');
    const feed = document.getElementById('assistant-feed');
    const status = document.getElementById('assistant-feedback');

    if (toggle && panel && form && feed && status) {
        const messageInput = document.getElementById('assistant-message');
        const emailInput = document.getElementById('assistant-email');
        const closeButton = panel.querySelector('.assistant-close');
        const conversationKey = 'gather-support-conversation';
        const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]').value;
        let conversationId = sessionStorage.getItem(conversationKey);

        if (!conversationId) {
            conversationId = window.crypto?.randomUUID
                ? window.crypto.randomUUID()
                : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
            sessionStorage.setItem(conversationKey, conversationId);
        }

        const setOpen = (open) => {
            panel.hidden = !open;
            toggle.setAttribute('aria-expanded', String(open));
            if (open) messageInput.focus();
        };
        const addMessage = (text, className) => {
            const item = document.createElement('p');
            item.className = className;
            item.textContent = text;
            feed.appendChild(item);
            feed.scrollTop = feed.scrollHeight;
            return item;
        };
        const feedbackButtons = (logId) => {
            const controls = document.createElement('div');
            controls.className = 'assistant-rating';
            controls.setAttribute('aria-label', 'Was this answer helpful?');
            for (const [rating, label] of [[5, 'Helpful'], [1, 'Not helpful']]) {
                const button = document.createElement('button');
                button.type = 'button';
                button.textContent = label;
                button.addEventListener('click', async () => {
                    status.textContent = 'Saving feedback…';
                    try {
                        const response = await fetch(form.dataset.feedbackUrl, {
                            method: 'POST',
                            credentials: 'same-origin',
                            headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
                            body: JSON.stringify({rating, conversation_id: conversationId, log_id: logId}),
                        });
                        const result = await response.json();
                        status.textContent = response.ok ? 'Thanks for your feedback.' : result.error;
                    } catch {
                        status.textContent = 'Feedback could not be sent. Please try again.';
                    }
                });
                controls.appendChild(button);
            }
            feed.appendChild(controls);
        };
        const addSuggestions = (suggestions) => {
            if (!suggestions.length) return;
            const controls = document.createElement('div');
            controls.className = 'assistant-suggestions';
            const label = document.createElement('span');
            label.textContent = 'Try asking:';
            controls.appendChild(label);
            suggestions.forEach((question) => {
                const button = document.createElement('button');
                button.type = 'button';
                button.textContent = question;
                button.addEventListener('click', () => {
                    messageInput.value = question;
                    form.requestSubmit();
                });
                controls.appendChild(button);
            });
            feed.appendChild(controls);
            feed.scrollTop = feed.scrollHeight;
        };

        toggle.addEventListener('click', () => setOpen(panel.hidden));
        closeButton.addEventListener('click', () => setOpen(false));
        document.querySelectorAll('.open-assistant').forEach((button) => {
            button.addEventListener('click', () => setOpen(true));
        });
        form.dataset.chatUrl = form.dataset.chatUrl || '/api/chat/';
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const message = messageInput.value.trim();
            if (!message) return;

            addMessage(message, 'assistant-question');
            messageInput.value = '';
            status.textContent = 'Thinking…';
            const submitButton = form.querySelector('button[type=submit]');
            submitButton.disabled = true;
            try {
                const response = await fetch(form.dataset.chatUrl, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
                    body: JSON.stringify({
                        message,
                        email: emailInput.value.trim(),
                        conversation_id: conversationId,
                    }),
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.error || 'The assistant could not answer right now.');
                conversationId = result.conversation_id;
                sessionStorage.setItem(conversationKey, conversationId);
                const logId = result.log_id || '';
                addMessage(result.answer, 'assistant-reply');
                if (result.ticket_id) {
                    addMessage(`Support ticket #${result.ticket_id} was created.`, 'assistant-note');
                }
                if (result.needs_clarification) {
                    addSuggestions(result.suggestions || []);
                } else {
                    feedbackButtons(logId);
                }
                status.textContent = result.warning || '';
            } catch (error) {
                addMessage(error.message || 'The assistant could not connect. Please try again.', 'assistant-note');
                status.textContent = '';
            } finally {
                submitButton.disabled = false;
                messageInput.focus();
            }
        });
    }

    const weatherCard = document.querySelector('[data-weather-url]');
    if (weatherCard) {
        const result = document.getElementById('weather-result');
        fetch(weatherCard.dataset.weatherUrl, {credentials: 'same-origin'})
            .then((response) => {
                if (!response.ok) throw new Error('Weather service unavailable');
                return response.json();
            })
            .then((weather) => {
                result.textContent = weather.fallback
                    ? weather.message
                    : `${weather.location}: ${weather.temperature_c}°C right now. Check a current forecast before your event.`;
            })
            .catch(() => {
                result.textContent = 'Live weather is temporarily unavailable. Please check a local forecast before your event.';
            });
    }
})();
