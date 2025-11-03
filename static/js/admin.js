// Função para mudar de aba
function openTab(evt, tabName) {
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }
    tablinks = document.getElementsByClassName("tab-link");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
}

// Função para preencher o formulário de ensino
function teachFromRequest(question, requestId) {
    document.querySelector('.tab-link[onclick*="Ensinar"]').click();
    document.getElementById('questions').value = question;
    document.getElementById('form_request_id').value = requestId;
    document.getElementById('answer').focus();
}

// Busca de usuários
document.addEventListener('DOMContentLoaded', function() {
    // Busca na lista de usuários
    const adminUserSearchInput = document.getElementById('adminUserSearchInput');
    if (adminUserSearchInput) {
        adminUserSearchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const userItems = document.querySelectorAll('.user-item');
            
            userItems.forEach(item => {
                const username = item.querySelector('span:nth-child(1)').textContent.toLowerCase();
                const email = item.querySelector('.user-email').textContent.toLowerCase();
                
                if (username.includes(searchTerm) || email.includes(searchTerm)) {
                    item.style.display = 'flex';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }

    // Procura todos os botões "Ensinar" nas solicitações
    const teachButtons = document.querySelectorAll('.btn-teach-action');

    // Adiciona um listener de clique a cada um
    teachButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            const buttonElement = event.currentTarget;
            // Encontra o item da lista pai mais próximo do botão
            const requestItem = buttonElement.closest('.list-item');
            
            // Dentro desse item, encontra o texto da pergunta
            const questionSpan = requestItem.querySelector('.request-text');
            // Pega o texto e remove as aspas do início e do fim
            const questionText = questionSpan.textContent.trim().replace(/^"|"$/g, '');

            // Pega o ID da solicitação que guardámos no botão
            const requestId = buttonElement.dataset.requestId;

            // Chama a função original com os dados seguros
            teachFromRequest(questionText, requestId);
        });
    });
});