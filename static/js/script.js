document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('messageInput');
    if (!messageInput) return;

    const sendButton = document.getElementById('sendButton');
    const messagesContainer = document.getElementById('messagesContainer');
    const newChatBtn = document.getElementById('newChatBtn');
    const welcomeMessage = document.getElementById('welcomeMessage');
    const historyList = document.getElementById('historyList');

    let currentConversationId = null;
    let isLoading = false;

    const loadChatHistory = async () => {
        try {
            const res = await fetch('/api/get_conversations');
            if (!res.ok) return;
            const data = await res.json();
            historyList.innerHTML = '';
            if (data.length > 0) {
                data.forEach(conv => {
                    const convElement = document.createElement('div');
                    convElement.className = 'history-item';
                    convElement.textContent = conv.title;
                    convElement.dataset.id = conv.id;
                    convElement.addEventListener('click', () => loadConversation(conv.id));
                    historyList.appendChild(convElement);
                });
            } else {
                historyList.innerHTML = '<p class="no-history">Nenhum chat salvo.</p>';
            }
        } catch (error) {
            console.error('Erro ao carregar histórico:', error);
        }
    };

    const loadConversation = async (convId) => {
        try {
            const res = await fetch(`/api/get_messages/${convId}`);
            if (!res.ok) throw new Error('Falha ao carregar mensagens.');
            
            const messages = await res.json();
            messagesContainer.innerHTML = '';
            messages.forEach(msg => addMessage(msg.role, msg.content));
            currentConversationId = convId;
            messageInput.disabled = false;
            updateUIState();
            scrollToBottom();
        } catch (error) {
            console.error('Erro ao carregar conversa:', error);
        }
    };

    const createNewConversation = async () => {
        try {
            const res = await fetch('/api/new_conversation', { method: 'POST' });
            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.error || 'Falha ao criar nova conversa.');
            }
            
            const data = await res.json();
            currentConversationId = data.conversation_id;
            
            messagesContainer.innerHTML = '';
            if (welcomeMessage) {
                messagesContainer.appendChild(welcomeMessage.cloneNode(true));
            }
            messageInput.value = '';
            messageInput.disabled = false;
            updateUIState();
        } catch (error) {
            alert(error.message);
            messageInput.disabled = true;
            updateUIState();
        }
    };

    const sendMessage = async () => {
        const messageText = messageInput.value.trim();
        if (!messageText || isLoading || !currentConversationId) return;

        isLoading = true;
        updateUIState();
        
        addMessage('user', messageText);
        messageInput.value = '';
        autoResizeTextarea();

        const loadingPlaceholder = addMessage('assistant', '', true);

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: messageText, conversation_id: currentConversationId }),
            });

            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.response || data.error || 'Erro de comunicação com o servidor.');
            }
            
            updateMessage(loadingPlaceholder, data.response);

            if (data.is_blocked) {
                messageInput.disabled = true;
                updateUIState();
                if (data.site_down) { return; }
                
                const suggestButton = document.createElement('button');
                suggestButton.className = 'btn-suggest-teaching';
                suggestButton.innerHTML = '<i class="fas fa-lightbulb"></i> Ensinar ZIPBUM sobre isso';
                suggestButton.onclick = async () => {
                    await fetch('/api/request_teaching', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ question: data.original_question })
                    });
                    suggestButton.textContent = 'Obrigado pela sugestão!';
                    suggestButton.disabled = true;
                };
                messagesContainer.appendChild(suggestButton);
                scrollToBottom();
            }
            loadChatHistory();
        } catch (error) {
            console.error('Erro:', error);
            updateMessage(loadingPlaceholder, error.message);
        } finally {
            isLoading = false;
            updateUIState();
        }
    };

    const addMessage = (role, text, isLoadingMsg = false) => {
        const welcome = document.getElementById('welcomeMessage');
        if (welcome) welcome.style.display = 'none';

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        let avatarHtml;
        if (role === 'user') {
            avatarHtml = `<div class="message-avatar"><i class="fas fa-user"></i></div>`;
        } else {
            avatarHtml = `<div class="message-avatar"><img src="/static/img/logo.png" alt="ZIPBUM Logo"></div>`;
        }
        
        const textHtml = `<div class="message-text"><p>${text}</p></div>`;

        messageDiv.innerHTML = avatarHtml + textHtml;
        
        if (isLoadingMsg) {
            messageDiv.classList.add('loading');
            messageDiv.querySelector('p').innerHTML = '<i class="fas fa-spinner fa-pulse"></i>';
        }

        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
        return messageDiv;
    };
    
    const updateMessage = (element, newText) => {
        element.classList.remove('loading');
        element.querySelector('.message-text p').innerText = newText;
        scrollToBottom();
    };
    
    const scrollToBottom = () => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    };
    
    const autoResizeTextarea = () => {
        messageInput.style.height = 'auto';
        const newHeight = Math.min(messageInput.scrollHeight, 200);
        messageInput.style.height = `${newHeight}px`;
    };
    
    const updateUIState = () => {
        sendButton.disabled = messageInput.value.trim().length === 0 || isLoading || messageInput.disabled;
    };
    
    sendButton.addEventListener('click', sendMessage);
    newChatBtn.addEventListener('click', createNewConversation);

    messageInput.addEventListener('input', () => {
        autoResizeTextarea();
        updateUIState();
    });

    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    createNewConversation();
    loadChatHistory();
});