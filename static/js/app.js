class RolePlayApp {
    constructor() {
        // DOM elements
        this.characterSelect = document.getElementById('character');
        this.characterName = document.getElementById('characterName');
        this.characterDescription = document.getElementById('characterDescription');
        this.characterAvatar = document.getElementById('characterAvatar');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.statusText = document.getElementById('statusText');
        this.transcriptArea = document.getElementById('transcriptArea');
        this.currentSpeech = document.getElementById('currentSpeech');
        this.startBtn = document.getElementById('startBtn');
        this.stopBtn = document.getElementById('stopBtn');
        this.textInput = document.getElementById('textInput');
        this.sendTextBtn = document.getElementById('sendTextBtn');
        this.audioPlayer = document.getElementById('audioPlayer');

        // State
        this.websocket = null;
        this.recognition = null;
        this.isRunning = false;
        this.isListening = false;

        // Character emoji mapping
        this.characterEmojis = {
            buyer: '💼',
            wizard: '🧙',
            interviewer: '👔',
            tutor: '👩‍🏫',
            chef: '👨‍🍳',
            detective: '🕵️'
        };

        this.bindEvents();
        this.updateCharacterDisplay();
        this.initSpeechRecognition();
    }

    initSpeechRecognition() {
        // Check if Web Speech API is available
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            console.error('Web Speech API not supported');
            this.addMessage('error', 'Speech recognition not supported in this browser. Please use Chrome.');
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }

            // Show interim results
            if (interimTranscript) {
                this.currentSpeech.textContent = interimTranscript;
            }

            // Process final results
            if (finalTranscript) {
                this.currentSpeech.textContent = '';
                this.processUserSpeech(finalTranscript);
            }
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            if (event.error === 'no-speech') {
                // Restart recognition if no speech detected
                if (this.isRunning && this.isListening) {
                    this.startListening();
                }
            } else if (event.error !== 'aborted') {
                this.addMessage('error', `Speech error: ${event.error}`);
            }
        };

        this.recognition.onend = () => {
            // Restart recognition if we're still running
            if (this.isRunning && this.isListening) {
                try {
                    this.recognition.start();
                } catch (e) {
                    // Already started
                }
            }
        };
    }

    bindEvents() {
        this.characterSelect.addEventListener('change', () => {
            this.updateCharacterDisplay();
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({
                    type: 'change_character',
                    character_id: this.characterSelect.value
                }));
            }
        });

        this.startBtn.addEventListener('click', () => this.start());
        this.stopBtn.addEventListener('click', () => this.stop());

        this.textInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !this.textInput.disabled) {
                this.sendTextMessage();
            }
        });

        this.sendTextBtn.addEventListener('click', () => this.sendTextMessage());
    }

    updateCharacterDisplay() {
        const selectedOption = this.characterSelect.selectedOptions[0];
        const characterId = this.characterSelect.value;
        const [name, description] = selectedOption.text.split(' - ');

        this.characterName.textContent = name;
        this.characterDescription.textContent = description;
        this.characterAvatar.textContent = this.characterEmojis[characterId] || '🤖';
    }

    setStatus(state) {
        this.statusIndicator.className = 'status-indicator ' + state;

        const statusMessages = {
            ready: 'Ready',
            listening: 'Listening...',
            processing: 'Thinking...',
            speaking: 'Speaking...',
            error: 'Error'
        };

        this.statusText.textContent = statusMessages[state] || state;
    }

    addMessage(role, text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        messageDiv.textContent = text;
        this.transcriptArea.appendChild(messageDiv);
        this.transcriptArea.scrollTop = this.transcriptArea.scrollHeight;
    }

    clearMessages() {
        this.transcriptArea.innerHTML = '';
    }

    async start() {
        if (!this.recognition) {
            this.addMessage('error', 'Speech recognition not available');
            return;
        }

        try {
            // Connect WebSocket
            const characterId = this.characterSelect.value;
            const wsUrl = `ws://${window.location.host}/ws/conversation/${characterId}`;
            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                this.isRunning = true;
                this.startBtn.disabled = true;
                this.stopBtn.disabled = false;
                this.textInput.disabled = false;
                this.sendTextBtn.disabled = false;
                this.characterSelect.disabled = true;

                this.clearMessages();
                this.addMessage('system', 'Connected! Start speaking...');

                // Start listening
                this.startListening();
            };

            this.websocket.onmessage = (event) => this.handleMessage(event);

            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.addMessage('error', 'Connection error. Please try again.');
                this.stop();
            };

            this.websocket.onclose = () => {
                // Only auto-stop if still running (unexpected close)
                if (this.isRunning) {
                    this.isRunning = false;
                    this.finalizeStop();
                }
            };

        } catch (error) {
            console.error('Error starting:', error);
            this.addMessage('error', `Failed to start: ${error.message}`);
        }
    }

    startListening() {
        if (!this.recognition || !this.isRunning) return;

        this.isListening = true;
        this.setStatus('listening');

        try {
            this.recognition.start();
        } catch (e) {
            // Recognition might already be running
            console.log('Recognition already started');
        }
    }

    stopListening() {
        this.isListening = false;
        if (this.recognition) {
            try {
                this.recognition.stop();
            } catch (e) {
                // Ignore
            }
        }
    }

    processUserSpeech(transcript) {
        if (!transcript.trim() || !this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            return;
        }

        // Stop listening while processing
        this.stopListening();

        // Show user message
        this.addMessage('user', transcript);
        this.setStatus('processing');

        // Send to server
        this.websocket.send(JSON.stringify({
            type: 'text_message',
            text: transcript
        }));
    }

    handleMessage(event) {
        const data = JSON.parse(event.data);

        switch (data.type) {
            case 'state':
                if (data.state === 'listening' && this.isRunning) {
                    this.startListening();
                } else {
                    this.setStatus(data.state);
                }
                break;

            case 'transcript':
                if (data.is_final) {
                    this.addMessage('user', data.text);
                    this.currentSpeech.textContent = '';
                } else {
                    this.currentSpeech.textContent = data.text;
                }
                break;

            case 'response_chunk':
                // Could show streaming response here
                break;

            case 'response':
                this.addMessage('assistant', data.text);
                break;

            case 'audio':
                this.playAudio(data.audio);
                break;

            case 'character':
                this.characterName.textContent = data.name;
                this.characterDescription.textContent = data.description;
                break;

            case 'interrupted':
                // Stop current audio playback
                this.audioPlayer.pause();
                this.audioPlayer.currentTime = 0;
                this.startListening();
                break;

            case 'error':
                this.addMessage('error', data.message);
                this.setStatus('error');
                // Try to recover by starting listening again
                setTimeout(() => {
                    if (this.isRunning) {
                        this.startListening();
                    }
                }, 1000);
                break;

            case 'system':
                this.addMessage('system', data.text);
                break;

            case 'assessment':
                this.showAssessment(data.text);
                // Now close the connection
                this.finalizeStop();
                break;
        }
    }

    showAssessment(text) {
        // Create assessment container
        const assessmentDiv = document.createElement('div');
        assessmentDiv.className = 'assessment';

        // Convert markdown-style formatting to HTML
        let formattedText = text
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>')
            .replace(/- /g, '&bull; ');

        assessmentDiv.innerHTML = `
            <div class="assessment-header">
                <span class="assessment-icon">📊</span>
                <span>Coaching Assessment</span>
            </div>
            <div class="assessment-content">${formattedText}</div>
        `;

        this.transcriptArea.appendChild(assessmentDiv);
        this.transcriptArea.scrollTop = this.transcriptArea.scrollHeight;
    }

    playAudio(base64Audio) {
        console.log('Playing audio, length:', base64Audio.length);

        // Stop listening while playing audio
        this.stopListening();

        try {
            const audioData = atob(base64Audio);
            const arrayBuffer = new ArrayBuffer(audioData.length);
            const view = new Uint8Array(arrayBuffer);

            for (let i = 0; i < audioData.length; i++) {
                view[i] = audioData.charCodeAt(i);
            }

            const blob = new Blob([arrayBuffer], { type: 'audio/mp3' });
            const audioUrl = URL.createObjectURL(blob);

            console.log('Audio blob created, size:', blob.size);

            // Make sure audio player is ready
            this.audioPlayer.volume = 1.0;
            this.audioPlayer.src = audioUrl;
            this.setStatus('speaking');

            const playPromise = this.audioPlayer.play();

            if (playPromise !== undefined) {
                playPromise.then(() => {
                    console.log('Audio playback started');
                }).catch(error => {
                    console.error('Error playing audio:', error);
                    // Try to play again with user gesture workaround
                    this.addMessage('system', 'Click anywhere to enable audio');
                    document.addEventListener('click', () => {
                        this.audioPlayer.play();
                    }, { once: true });
                    this.startListening();
                });
            }

            this.audioPlayer.onended = () => {
                console.log('Audio playback ended');
                URL.revokeObjectURL(audioUrl);
                // Resume listening after audio finishes
                if (this.isRunning) {
                    this.startListening();
                }
            };

            this.audioPlayer.onerror = (e) => {
                console.error('Audio error:', e);
                this.startListening();
            };

        } catch (error) {
            console.error('Error in playAudio:', error);
            this.startListening();
        }
    }

    sendTextMessage() {
        const text = this.textInput.value.trim();
        if (text && this.websocket?.readyState === WebSocket.OPEN) {
            this.stopListening();
            this.websocket.send(JSON.stringify({
                type: 'text_message',
                text: text
            }));
            this.addMessage('user', text);
            this.textInput.value = '';
            this.setStatus('processing');
        }
    }

    stop() {
        this.isRunning = false;

        // Stop speech recognition
        this.stopListening();

        // Stop audio playback
        this.audioPlayer.pause();
        this.audioPlayer.currentTime = 0;

        // Request assessment (don't close WebSocket yet - wait for assessment)
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.setStatus('processing');
            this.addMessage('system', 'Generating your coaching assessment...');
            this.websocket.send(JSON.stringify({ type: 'stop' }));
            // WebSocket will be closed after receiving assessment
        } else {
            this.finalizeStop();
        }
    }

    finalizeStop() {
        // Close WebSocket
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }

        // Reset UI
        this.startBtn.disabled = false;
        this.stopBtn.disabled = true;
        this.textInput.disabled = true;
        this.sendTextBtn.disabled = true;
        this.characterSelect.disabled = false;
        this.setStatus('ready');
        this.currentSpeech.textContent = '';

        this.addMessage('system', 'Session ended. Review your assessment above!');
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new RolePlayApp();
});
