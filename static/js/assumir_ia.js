document.addEventListener('DOMContentLoaded', function() {
    const conversationsList = document.getElementById('listContainer');
    const messagesContainer = document.getElementById('messagesContainerAdmin');
    const messageInput = document.getElementById('messageInputAdmin');
    const sendButton = document.getElementById('sendButtonAdmin');
    const chatHeader = document.getElementById('chatHeaderAdmin');
    const inputContainer = document.getElementById('inputContainerAdmin');
    const userSearchInput = document.getElementById('userSearchInput');
    const backToUsersBtn = document.getElementById('backToUsersBtn');
    const sidebarTitle = document.getElementById('sidebarTitle');
    
    let currentConversationId = null;
    let currentUserEmail = null;
    let allConversationsData = {};

    async function fetchAllConversations() {
        try {
            const res = await fetch('/api/get_all_conversations');
            if (!res.ok) {
                const errorData = await res.json();
                throw new Error(errorData.error || `Erro do servidor: ${res.status}`);
            }
            allConversationsData = await res.json();
            renderUsersList(allConversationsData);
        } catch (err) {
            conversationsList.innerHTML = `<p class="no-history" style="color: var(--danger);">${err.message}</p>`;
        }
    }

    function renderUsersList(conversations) {
        conversationsList.innerHTML = '';
        
        if (!conversations || Object.keys(conversations).length === 0) {
            conversationsList.innerHTML = '<p class="no-history">Nenhum usuário com conversas encontrado.</p>';
            return;
        }

        Object.keys(conversations).forEach(email => {
            const userData = conversations[email];
            const userItem = document.createElement('div');
            userItem.className = 'history-item';
            userItem.innerHTML = `
                <div>
                    <strong>${userData.username}</strong>
                    <div style="font-size: 0.875rem; color: var(--gray);">${email}</div>
                </div>
            `;
            userItem.addEventListener('click', () => selectUser(email, userData));
            conversationsList.appendChild(userItem);
        });
    }

    function selectUser(email, userData) {
        currentUserEmail = email;
        sidebarTitle.textContent = `Conversas de ${userData.username}`;
        backToUsersBtn.style.display = 'block';
        userSearchInput.style.display = 'none';
        
        renderUserConversations(userData.conversations);
    }

    function renderUserConversations(conversations) {
        conversationsList.innerHTML = '';
        
        if (!conversations || conversations.length === 0) {
            conversationsList.innerHTML = '<p class="no-history">Nenhuma conversa encontrada para este usuário.</p>';
            return;
        }

        conversations.forEach(conv => {
            const convItem = document.createElement('div');
            convItem.className = 'history-item';
            convItem.textContent = conv.title;
            convItem.dataset.id = conv.id;
            convItem.addEventListener('click', () => selectConversation(conv.id, conv.title));
            conversationsList.appendChild(convItem);
        });
    }

    async function selectConversation(convId, title) {
        currentConversationId = convId;
        chatHeader.innerHTML = `<h1>${title}</h1>`;
        inputContainer.style.display = 'flex';
        messagesContainer.innerHTML = '<p>Carregando mensagens...</p>';

        try {
            const res = await fetch(`/api/admin_get_messages/${convId}`);
            const messages = await res.json();
            
            messagesContainer.innerHTML = '';
            messages.forEach(msg => {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${msg.role}`;
                const iconClass = msg.role === 'user' ? 'fa-user' : 'fa-robot';
                let avatarHtml = `<div class="message-avatar"><i class="fas ${iconClass}"></i></div>`;
                if (msg.role !== 'user') {
                    avatarHtml = `<div class="message-avatar"><img src="/static/img/logo.png" alt="ZIPBUM Logo"></div>`;
                }
                const textHtml = `<div class="message-text"><p>${msg.content}</p></div>`;
                messageDiv.innerHTML = avatarHtml + textHtml;
                messagesContainer.appendChild(messageDiv);
            });
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } catch (err) {
            messagesContainer.innerHTML = `<p style="color: var(--danger);">Erro ao carregar mensagens.</p>`;
        }
    }

    async function sendMessage() {
        const content = messageInput.value.trim();
        if (!content || !currentConversationId) return;

        try {
            await fetch('/api/admin_send_message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ conversation_id: currentConversationId, content: content }),
            });

            messageInput.value = '';
            // Recarrega as mensagens para mostrar a nova mensagem
            const currentTitle = chatHeader.querySelector('h1').textContent;
            selectConversation(currentConversationId, currentTitle);
        } catch (err) {
            alert('Erro ao enviar mensagem: ' + err.message);
        }
    }

    // Busca de usuários
    userSearchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const userItems = conversationsList.querySelectorAll('.history-item');
        
        userItems.forEach(item => {
            const userText = item.textContent.toLowerCase();
            if (userText.includes(searchTerm)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    });

    // Voltar para lista de usuários
    backToUsersBtn.addEventListener('click', function() {
        currentUserEmail = null;
        currentConversationId = null;
        sidebarTitle.textContent = 'Usuários';
        backToUsersBtn.style.display = 'none';
        userSearchInput.style.display = 'block'; 
        inputContainer.style.display = 'none';
        chatHeader.innerHTML = '<h1>Selecione um usuário para ver as conversas</h1>';
        messagesContainer.innerHTML = '';
        renderUsersList(allConversationsData);
    });
    
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    fetchAllConversations();
});