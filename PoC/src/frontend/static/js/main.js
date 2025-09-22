document.addEventListener('DOMContentLoaded', function() {
    const chatHistory = document.getElementById('chat-history');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    
    // Configure Marked.js options
    marked.setOptions({
        gfm: true,
        breaks: true,
        smartypants: true
    });
    
    // Function to add a message to the chat history
    function addMessageToChat(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message', `${role}-message`);
        
        // Check if content is a JSON string that might contain markdown
        let displayContent = content;
        try {
            // Try to parse as JSON to see if it's a structured response
            const parsed = JSON.parse(content);
            // If it's an object with a response property, use that
            if (parsed && typeof parsed === 'object' && parsed.response) {
                displayContent = parsed.response;
            }
        } catch (e) {
            // Not JSON, use content as is
        }
        
        // Render markdown content
        messageDiv.innerHTML = marked.parse(displayContent);
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
            
            // Get last call information for this agent
            const lastCall = data.agent_last_calls[agentName] || {};
            
            // Format timestamp if available
            let lastCallTime = 'Never';
            if (lastCall.timestamp) {
                const timestamp = new Date(lastCall.timestamp);
                lastCallTime = timestamp.toLocaleString();
            }
            
            // Extract target information based on agent type and method
            let targetInfo = '';
            if (lastCall.method && lastCall.kwargs) {
                if (agentName === 'SampleAgentA' && lastCall.method === 'perform_dns_lookup') {
                    const domain = lastCall.kwargs.domain || 'Not specified';
                    targetInfo = `<p><span class="target-label">Target:</span> ${domain}</p>`;
                } else if (agentName === 'SampleAgentB' && lastCall.method === 'perform_website_check') {
                    const url = lastCall.kwargs.url || 'Not specified';
                    targetInfo = `<p><span class="target-label">Target:</span> ${url}</p>`;
                }
            }
            
            // Format result if available
            let lastCallResult = 'None';
            if (lastCall.result) {
                if (lastCall.result.error) {
                    lastCallResult = `Error: ${lastCall.result.error}`;
                } else {
                    // Truncate long results
                    const resultStr = JSON.stringify(lastCall.result);
                    lastCallResult = resultStr.length > 100 ? 
                        resultStr.substring(0, 100) + '...' : 
                        resultStr;
                }
            }
            
            agentCard.innerHTML = `
                <h3>${agentName}</h3>
                <p><span class="status-label">Status:</span> Active</p>
                ${targetInfo}
                <p><span class="last-call-label">Last Call:</span> ${lastCallTime}</p>
                <p><span class="result-label">Results:</span> ${lastCallResult}</p>
            `;
            agentStatus.appendChild(agentCard);
        });
    } catch (error) {
        console.error('Error loading status:', error);
    }
}