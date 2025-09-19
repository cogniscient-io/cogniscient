document.addEventListener('DOMContentLoaded', function() {
    const chatHistory = document.getElementById('chat-history');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    
    // Function to add a message to the chat history
    function addMessageToChat(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message', `${role}-message`);
        messageDiv.textContent = content;
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
    
    // Function to send a message to the backend
    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        addMessageToChat('user', message);
        userInput.value = '';
        
        try {
            // Send message to backend
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({message: message})
            });
            
            const data = await response.json();
            
            // Add assistant response to chat
            addMessageToChat('assistant', data.response);
        } catch (error) {
            console.error('Error sending message:', error);
            addMessageToChat('assistant', 'Error: Could not send message');
        }
    }
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // Load initial status
    loadStatus();
    
    // Set up periodic status updates
    setInterval(loadStatus, 30000);
});

async function loadStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        const agentStatus = document.getElementById('agent-status');
        agentStatus.innerHTML = '';
        
        data.agents.forEach(agentName => {
            const agentCard = document.createElement('div');
            agentCard.classList.add('agent-card');
            agentCard.innerHTML = `
                <h3>${agentName}</h3>
                <p>Status: Active</p>
            `;
            agentStatus.appendChild(agentCard);
        });
    } catch (error) {
        console.error('Error loading status:', error);
    }
}