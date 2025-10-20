// API endpoint
const API_URL = 'http://localhost:8000';

// DOM elements
const questionInput = document.getElementById('question');
const askBtn = document.getElementById('askBtn');
const captureBtn = document.getElementById('captureBtn');
const clearBtn = document.getElementById('clearBtn');
const memoryBtn = document.getElementById('memoryBtn');
const responseDiv = document.getElementById('response');
const responseContent = document.getElementById('responseContent');
const loadingDiv = document.getElementById('loading');
const methodBadge = document.getElementById('methodBadge');
const questionsCount = document.getElementById('questionsCount');
const docsCount = document.getElementById('docsCount');
const accuracyScore = document.getElementById('accuracyScore');

// Preference elements
const preferencesSection = document.getElementById('preferencesSection');
const expertiseLevel = document.getElementById('expertiseLevel');
const responseStyle = document.getElementById('responseStyle');
const depthPreference = document.getElementById('depthPreference');
const timeSensitivity = document.getElementById('timeSensitivity');
const confirmPrefsBtn = document.getElementById('confirmPrefsBtn');
const skipPrefsBtn = document.getElementById('skipPrefsBtn');

// State
let currentQuestion = '';
let userPreferences = null;

// Load stats on startup
loadStats();

// Event listeners
askBtn.addEventListener('click', showPreferences);
captureBtn.addEventListener('click', handleCapture);
clearBtn.addEventListener('click', handleClear);
memoryBtn.addEventListener('click', handleMemory);
confirmPrefsBtn.addEventListener('click', handleAskWithPreferences);
skipPrefsBtn.addEventListener('click', handleAskWithoutPreferences);

questionInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter' && e.ctrlKey) {
    showPreferences();
  }
});

// Step 1: Show preference collection after user enters question
function showPreferences() {
  const question = questionInput.value.trim();
  
  if (!question) {
    showError('Please enter a question first!');
    return;
  }
  
  currentQuestion = question;
  
  // Show preference section
  preferencesSection.style.display = 'block';
  
  // Scroll to preferences
  preferencesSection.scrollIntoView({ behavior: 'smooth' });
  
  // Hide response if visible
  hideResponse();
}

// Step 2: Ask with user preferences
async function handleAskWithPreferences() {
  // Collect preferences
  userPreferences = {
    expertise_level: expertiseLevel.value,
    response_style: responseStyle.value,
    depth_preference: depthPreference.value,
    time_sensitivity: timeSensitivity.value,
    focus_areas: ["AI", "technology"], // Default focus areas
    preferred_sources: [],
    location: null
  };
  
  await sendQuestion(currentQuestion, userPreferences);
}

// Step 3: Ask without preferences (use defaults)
async function handleAskWithoutPreferences() {
  await sendQuestion(currentQuestion, null);
}

// Send question to backend
async function sendQuestion(question, preferences) {
  // Hide preference section
  preferencesSection.style.display = 'none';
  
  showLoading(true);
  hideResponse();
  
  try {
    const requestBody = { question };
    
    // Include preferences if provided
    if (preferences) {
      requestBody.user_preferences = preferences;
    }
    
    const response = await fetch(`${API_URL}/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });
    
    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }
    
    const data = await response.json();
    showResponse(data, preferences);
    updateStats();
  } catch (error) {
    console.error('Error:', error);
    showError(`Failed to get response: ${error.message}\n\nMake sure the Python backend is running on port 8000.`);
  } finally {
    showLoading(false);
  }
}

async function handleCapture() {
  showLoading(true);
  
  try {
    // Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    // Execute script to get page content
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      function: extractPageContent,
    });
    
    const pageData = results[0].result;
    
    // Send to backend
    const response = await fetch(`${API_URL}/store`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(pageData),
    });
    
    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }
    
    const data = await response.json();
    showSuccess(`✓ Page captured successfully!\n\n${data.message}`);
    updateStats();
  } catch (error) {
    console.error('Error:', error);
    showError(`Failed to capture page: ${error.message}`);
  } finally {
    showLoading(false);
  }
}

function extractPageContent() {
  return {
    title: document.title,
    url: window.location.href,
    content: document.body.innerText.substring(0, 5000), // Limit to 5000 chars
    timestamp: new Date().toISOString(),
  };
}

async function handleMemory() {
  showLoading(true);
  
  try {
    const response = await fetch(`${API_URL}/memory`);
    
    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }
    
    const data = await response.json();
    showResponse({
      answer: data.summary,
      method: 'MEMORY',
      confidence: 100,
      documents_used: data.count,
    });
  } catch (error) {
    console.error('Error:', error);
    showError(`Failed to retrieve memory: ${error.message}`);
  } finally {
    showLoading(false);
  }
}

function handleClear() {
  questionInput.value = '';
  hideResponse();
  questionInput.focus();
}

function showResponse(data, preferences) {
  responseDiv.classList.remove('error');
  responseDiv.classList.add('show');
  
  let content = '';
  
  // Show preferences used (if any)
  if (preferences) {
    content += `🎯 Personalized for: ${preferences.expertise_level} level, ${preferences.response_style} style, ${preferences.depth_preference} depth\n\n`;
  } else if (data.user_preferences_applied) {
    content += `🎯 Personalized based on your preferences\n\n`;
  }
  
  content += data.answer || data.message || 'No response available';
  
  if (data.confidence !== undefined) {
    content += `\n\n📊 Confidence: ${data.confidence}%`;
  }
  
  if (data.method) {
    content += `\n🔧 Method: ${data.method}`;
  }
  
  if (data.reasoning_steps && data.reasoning_steps.length > 0) {
    content += '\n\n📋 Reasoning Steps:\n' + data.reasoning_steps.slice(0, 3).join('\n');
    if (data.reasoning_steps.length > 3) {
      content += `\n... and ${data.reasoning_steps.length - 3} more steps`;
    }
  }
  
  if (data.sources && data.sources.length > 0) {
    content += '\n\n📚 Sources:\n';
    data.sources.forEach((source, i) => {
      content += `${i + 1}. ${source}\n`;
    });
  }
  
  responseContent.textContent = content;
  methodBadge.textContent = data.method || 'RAG';
  
  // Update method badge color
  if (data.method === 'RAG') {
    methodBadge.style.background = '#4CAF50';
    methodBadge.textContent = 'RAG';
  } else if (data.method === 'LIVE_SEARCH') {
    methodBadge.style.background = '#2196F3';
    methodBadge.textContent = 'LIVE';
  } else if (data.method === 'GEMINI_KNOWLEDGE') {
    methodBadge.style.background = '#FF9800';
    methodBadge.textContent = 'GEMINI';
  } else {
    methodBadge.style.background = '#667eea';
  }
}

function showSuccess(message) {
  responseDiv.classList.remove('error');
  responseDiv.classList.add('show');
  responseContent.textContent = message;
  methodBadge.textContent = 'SUCCESS';
  methodBadge.style.background = '#48bb78';
}

function showError(message) {
  responseDiv.classList.add('error', 'show');
  responseContent.textContent = '❌ ' + message;
  methodBadge.textContent = 'ERROR';
  methodBadge.style.background = '#f44';
}

function hideResponse() {
  responseDiv.classList.remove('show');
}

function showLoading(show) {
  if (show) {
    loadingDiv.classList.add('show');
    askBtn.disabled = true;
    captureBtn.disabled = true;
  } else {
    loadingDiv.classList.remove('show');
    askBtn.disabled = false;
    captureBtn.disabled = false;
  }
}

async function updateStats() {
  try {
    const response = await fetch(`${API_URL}/stats`);
    const data = await response.json();
    
    questionsCount.textContent = data.questions || 0;
    docsCount.textContent = data.documents || 0;
    accuracyScore.textContent = (data.accuracy || 100) + '%';
  } catch (error) {
    console.error('Failed to update stats:', error);
  }
}

function loadStats() {
  updateStats();
}

