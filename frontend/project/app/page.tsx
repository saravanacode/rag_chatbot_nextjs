'use client';

import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Plus, Send, Globe, Key, MessageCircle, Trash2, Loader2, Database } from 'lucide-react';

type Screen = 'welcome' | 'apiKeys' | 'urls' | 'vectorizing' | 'chat';

interface ApiKeys {
  pinecone: string;
  firecrawl: string;
  chatgpt: string;
}

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

interface VectorizationStatus {
  in_progress: boolean;
  completed: boolean;
  total_urls: number;
  processed_urls: number;
  successful_docs: number;
  errors: string[];
}

interface BackendStatus {
  api_keys_configured: number;
  urls_stored: number;
  crawled_data_available: number;
  successful_crawls: number;
  demo_mode: boolean;
  ai_components_loaded: boolean;
  vectorization_status: VectorizationStatus;
  env_keys: {
    openai: boolean;
    pinecone: boolean;
    firecrawl: boolean;
  };
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';

export default function ChatbotApp() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('welcome');
  const [apiKeys, setApiKeys] = useState<ApiKeys>({
    pinecone: '',
    firecrawl: '',
    chatgpt: ''
  });
  const [urls, setUrls] = useState<string[]>([]);
  const [newUrl, setNewUrl] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isCrawling, setIsCrawling] = useState(false);
  const [backendStatus, setBackendStatus] = useState<BackendStatus | null>(null);
  const [backendConnected, setBackendConnected] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [vectorizationStatus, setVectorizationStatus] = useState<VectorizationStatus | null>(null);
  
  const vectorizationIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Check backend connection on mount
  useEffect(() => {
    checkBackendConnection();
  }, []);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (vectorizationIntervalRef.current) {
        clearInterval(vectorizationIntervalRef.current);
      }
    };
  }, []);

  const checkBackendConnection = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/health`);
      if (response.ok) {
        setBackendConnected(true);
        await fetchBackendStatus();
      }
    } catch (error) {
      console.error('Backend connection failed:', error);
      setBackendConnected(false);
    }
  };

  const fetchBackendStatus = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/status`);
      if (response.ok) {
        const status = await response.json();
        setBackendStatus(status);
        setVectorizationStatus(status.vectorization_status);
      }
    } catch (error) {
      console.error('Failed to fetch backend status:', error);
    }
  };

  const fetchVectorizationStatus = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/vectorization-status`);
      if (response.ok) {
        const result = await response.json();
        console.log('🔍 Vectorization Status:', result.data);
        setVectorizationStatus(result.data);
        
        // If vectorization is complete, stop polling and move to chat
        if (result.data.completed && currentScreen === 'vectorizing') {
          console.log('✅ Vectorization completed, moving to chat');
          
          if (vectorizationIntervalRef.current) {
            clearInterval(vectorizationIntervalRef.current);
            vectorizationIntervalRef.current = null;
          }
          
          await fetchBackendStatus();
          setCurrentScreen('chat');
          setIsCrawling(false);
          
          // Add success message
          setMessages([{
            id: '1',
            text: `🎉 Vectorization Complete! I've successfully processed ${result.data.processed_urls} URLs and indexed ${result.data.successful_docs} documents into the vector database.

I can now answer questions using semantic search through your content. The AI assistant is powered by:
• Sentence Transformer model for embeddings
• Pinecone vector database for search
• OpenAI GPT for intelligent responses

Try asking questions about your content!`,
            sender: 'bot',
            timestamp: new Date()
          }]);
        }
      }
    } catch (error) {
      console.error('Failed to fetch vectorization status:', error);
    }
  };

  const startVectorizationPolling = () => {
    if (vectorizationIntervalRef.current) {
      clearInterval(vectorizationIntervalRef.current);
    }
    
    vectorizationIntervalRef.current = setInterval(fetchVectorizationStatus, 2000);
  };

  const handleContinueToChat = () => {
    if (vectorizationIntervalRef.current) {
      clearInterval(vectorizationIntervalRef.current);
      vectorizationIntervalRef.current = null;
    }
    setCurrentScreen('chat');
    setIsCrawling(false);
    
    const docsCount = vectorizationStatus?.successful_docs || 0;
    setMessages([{
      id: '1',
      text: `🎉 Welcome to your AI Assistant! I've indexed ${docsCount} documents from your content. Ask me anything about what I've learned!

You can ask questions like:
• "What is this content about?"
• "Tell me the main topics"
• "What information do you have?"
• Or any specific questions about your content

I'm ready to help using vector search and AI reasoning!`,
      sender: 'bot',
      timestamp: new Date()
    }]);
  };

  const handleGetStarted = () => {
    setIsDemoMode(false);
    setCurrentScreen('apiKeys');
  };

  const handleDemo = async () => {
    if (!backendConnected) {
      alert('Backend server not connected! Please start the Flask server on localhost:5000');
      return;
    }

    if (!backendStatus?.env_keys.openai || !backendStatus?.env_keys.pinecone) {
      alert('Demo mode requires OpenAI and Pinecone environment variables to be set. Please use "Get Started" to enter API keys manually.');
      return;
    }

    setIsDemoMode(true);
    setIsCrawling(true);

    try {
      const demoResponse = await fetch(`${BACKEND_URL}/api/demo-mode`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (demoResponse.ok) {
        const result = await demoResponse.json();
        console.log('Demo mode started:', result);
        
        await fetchBackendStatus();
        setCurrentScreen('chat');
        
        setMessages([{
          id: '1',
          text: `🎉 Welcome to AI Assistant Demo Mode! I've loaded the sentence transformer model (${result.data.model_name}) and connected to the Pinecone vector database (${result.data.index_name}).

I can now search through pre-indexed content to answer your questions using semantic search and AI reasoning.

Try asking questions like:
• "Where can I find restaurants?"
• "How do I get free WiFi?"
• "What shopping options are available?"
• "Where are the prayer rooms?"
• "How do I get to the city center?"

I'm ready to help you with information from the vector database!`,
          sender: 'bot',
          timestamp: new Date()
        }]);
      } else {
        const error = await demoResponse.json();
        alert(`Demo mode failed: ${error.error}`);
      }
    } catch (error) {
      console.error('Error during demo setup:', error);
      alert('Failed to start demo mode. Please check the backend server and environment variables.');
    } finally {
      setIsCrawling(false);
    }
  };

  const handleApiKeysSubmit = async () => {
    if (!backendConnected) {
      alert('Backend server not connected! Please start the Flask server on localhost:5000');
      return;
    }

    try {
      const response = await fetch(`${BACKEND_URL}/api/store-config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          apiKeys: apiKeys,
          urls: []
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('API keys stored:', result);
        await fetchBackendStatus();
        setCurrentScreen('urls');
      } else {
        const error = await response.json();
        alert(`Failed to store API keys: ${error.error}`);
      }
    } catch (error) {
      console.error('Error storing API keys:', error);
      alert('Failed to connect to backend server');
    }
  };

  const addUrl = () => {
    if (newUrl.trim() && !urls.includes(newUrl.trim())) {
      setUrls([...urls, newUrl.trim()]);
      setNewUrl('');
    }
  };

  const removeUrl = (index: number) => {
    setUrls(urls.filter((_, i) => i !== index));
  };

  const handleCrawlAndVectorize = async () => {
    if (!backendConnected) {
      alert('Backend server not connected! Please start the Flask server on localhost:5000');
      return;
    }

    if (urls.length === 0) {
      alert('Please add at least one URL to crawl');
      return;
    }

    setIsCrawling(true);

    try {
      const storeResponse = await fetch(`${BACKEND_URL}/api/store-config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          apiKeys: apiKeys,
          urls: urls
        })
      });

      if (!storeResponse.ok) {
        throw new Error('Failed to store URLs');
      }

      const vectorizeResponse = await fetch(`${BACKEND_URL}/api/crawl-and-vectorize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (vectorizeResponse.ok) {
        const result = await vectorizeResponse.json();
        console.log('Vectorization started:', result);
        
        setCurrentScreen('vectorizing');
        startVectorizationPolling();
      } else {
        const error = await vectorizeResponse.json();
        alert(`Vectorization failed: ${error.error}`);
        setIsCrawling(false);
      }
    } catch (error) {
      console.error('Error during vectorization:', error);
      alert('Failed to start vectorization. Please check the backend server.');
      setIsCrawling(false);
    }
  };

  const sendMessage = async () => {
    if (!currentMessage.trim() || !backendConnected) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: currentMessage,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setCurrentMessage('');
    setIsLoading(true);

    try {
      const response = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.text
        })
      });

      if (response.ok) {
        const result = await response.json();
        const botMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: result.response,
          sender: 'bot',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, botMessage]);
      } else {
        const error = await response.json();
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: `Sorry, I encountered an error: ${error.error}`,
          sender: 'bot',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: "Sorry, I couldn't process your message. Please check if the backend server is running.",
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleBackToWelcome = () => {
    setCurrentScreen('welcome');
    setMessages([]);
    setUrls([]);
    setApiKeys({ pinecone: '', firecrawl: '', chatgpt: '' });
    setIsDemoMode(false);
    if (vectorizationIntervalRef.current) {
      clearInterval(vectorizationIntervalRef.current);
      vectorizationIntervalRef.current = null;
    }
  };

  return (
    <div className="min-h-screen bg-white text-black">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        
        {/* Backend Status Indicator */}
        {!backendConnected && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center gap-2 text-red-700">
              <div className="w-2 h-2 bg-red-500 rounded-full"></div>
              <span className="font-medium">Backend Disconnected</span>
            </div>
            <p className="text-sm text-red-600 mt-1">
              Please start the Flask server: <code className="bg-red-100 px-1 rounded">python app/backend_server.py</code>
            </p>
          </div>
        )}

        {backendConnected && backendStatus && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center gap-2 text-green-700">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="font-medium">
                Backend Connected {isDemoMode && '(AI Assistant Mode)'}
                {backendStatus.vectorization_status.completed && !isDemoMode && ' (Vectorized)'}
              </span>
            </div>
            <div className="text-sm text-green-600 mt-1 grid grid-cols-2 gap-4">
              <div>URLs: {backendStatus.urls_stored}</div>
              <div>AI Model: {backendStatus.ai_components_loaded ? '✓ Loaded' : '○ Not loaded'}</div>
              <div>Vectorized Docs: {backendStatus.vectorization_status.successful_docs}</div>
              <div>Env Keys: {Object.values(backendStatus.env_keys).filter(Boolean).length}/3</div>
            </div>
          </div>
        )}
        
        {/* Welcome Screen */}
        {currentScreen === 'welcome' && (
          <div className="flex items-center justify-center min-h-screen -mt-8">
            <div className="text-center space-y-8 animate-fade-in">
              <div className="space-y-4">
                <h1 className="text-6xl font-light tracking-tight">
                  Chat<span className="font-bold">Bot</span>
                </h1>
                <p className="text-xl text-gray-600 max-w-md mx-auto leading-relaxed">
                  Intelligent conversations powered by your content
                </p>
              </div>
              
              <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mt-12">
                <Button 
                  onClick={handleGetStarted}
                  className="bg-black text-white hover:bg-gray-800 px-8 py-6 text-lg rounded-full transition-all duration-300 hover:scale-105"
                  disabled={!backendConnected}
                >
                  Get Started
                </Button>
                <Button 
                  onClick={handleDemo}
                  variant="outline" 
                  className="border-2 border-black text-black hover:bg-black hover:text-white px-8 py-6 text-lg rounded-full transition-all duration-300 hover:scale-105"
                  disabled={!backendConnected || isCrawling}
                >
                  {isCrawling ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Loading AI Assistant...
                    </>
                  ) : (
                    'Try Demo'
                  )}
                </Button>
              </div>
              
              {backendStatus && (
                <div className="text-sm text-gray-500 mt-8">
                  <p>Demo mode: Pre-loaded AI assistant with vector search</p>
                  <p>Get Started: Add your URLs for crawling & vectorization</p>
                  <p>API Keys available: {Object.values(backendStatus.env_keys).filter(Boolean).length}/3 keys loaded</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* API Keys Screen */}
        {currentScreen === 'apiKeys' && (
          <div className="flex items-center justify-center min-h-screen -mt-8">
            <Card className="w-full max-w-md border-2 border-gray-200 shadow-lg animate-slide-up">
              <CardHeader className="text-center pb-2">
                <div className="mx-auto w-12 h-12 bg-black rounded-full flex items-center justify-center mb-4">
                  <Key className="w-6 h-6 text-white" />
                </div>
                <CardTitle className="text-2xl font-light">API Configuration</CardTitle>
                <p className="text-gray-600 text-sm">Enter your API keys or use environment variables</p>
                {backendStatus?.env_keys && (
                  <div className="text-xs text-gray-500 mt-2">
                    Env loaded: OpenAI({backendStatus.env_keys.openai ? '✓' : '✗'}), 
                    Pinecone({backendStatus.env_keys.pinecone ? '✓' : '✗'}), 
                    Firecrawl({backendStatus.env_keys.firecrawl ? '✓' : '✗'})
                  </div>
                )}
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Pinecone API Key {backendStatus?.env_keys.pinecone && <span className="text-green-600">(env loaded)</span>}
                    </label>
                    <Input
                      type="password"
                      placeholder={backendStatus?.env_keys.pinecone ? "Using environment variable" : "Enter Pinecone API key"}
                      value={apiKeys.pinecone}
                      onChange={(e) => setApiKeys(prev => ({ ...prev, pinecone: e.target.value }))}
                      className="border-2 border-gray-200 focus:border-black transition-colors"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Firecrawl API Key {backendStatus?.env_keys.firecrawl && <span className="text-green-600">(env loaded)</span>}
                    </label>
                    <Input
                      type="password"
                      placeholder={backendStatus?.env_keys.firecrawl ? "Using environment variable" : "Enter Firecrawl API key"}
                      value={apiKeys.firecrawl}
                      onChange={(e) => setApiKeys(prev => ({ ...prev, firecrawl: e.target.value }))}
                      className="border-2 border-gray-200 focus:border-black transition-colors"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      ChatGPT API Key {backendStatus?.env_keys.openai && <span className="text-green-600">(env loaded)</span>}
                    </label>
                    <Input
                      type="password"
                      placeholder={backendStatus?.env_keys.openai ? "Using environment variable" : "Enter ChatGPT API key"}
                      value={apiKeys.chatgpt}
                      onChange={(e) => setApiKeys(prev => ({ ...prev, chatgpt: e.target.value }))}
                      className="border-2 border-gray-200 focus:border-black transition-colors"
                    />
                  </div>
                </div>
                
                <div className="flex gap-2">
                  <Button 
                    onClick={handleBackToWelcome}
                    variant="outline"
                    className="flex-1 border-2 border-gray-200 hover:border-black transition-colors"
                  >
                    Back
                  </Button>
                  <Button 
                    onClick={handleApiKeysSubmit}
                    className="flex-1 bg-black text-white hover:bg-gray-800 py-6 text-lg rounded-full transition-all duration-300"
                    disabled={!backendConnected}
                  >
                    Continue
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* URLs Screen */}
        {currentScreen === 'urls' && (
          <div className="flex items-center justify-center min-h-screen -mt-8">
            <Card className="w-full max-w-2xl border-2 border-gray-200 shadow-lg animate-slide-up">
              <CardHeader className="text-center pb-2">
                <div className="mx-auto w-12 h-12 bg-black rounded-full flex items-center justify-center mb-4">
                  <Globe className="w-6 h-6 text-white" />
                </div>
                <CardTitle className="text-2xl font-light">Content Sources</CardTitle>
                <p className="text-gray-600 text-sm">Add URLs to crawl and vectorize with AI</p>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex gap-2">
                  <Input
                    placeholder="Enter URL (e.g., https://example.com)"
                    value={newUrl}
                    onChange={(e) => setNewUrl(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && addUrl()}
                    className="border-2 border-gray-200 focus:border-black transition-colors"
                  />
                  <Button 
                    onClick={addUrl}
                    className="bg-black text-white hover:bg-gray-800 px-4"
                  >
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
                
                {urls.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="font-medium text-gray-700">URLs to Crawl & Vectorize ({urls.length})</h3>
                    <div className="max-h-40 overflow-y-auto space-y-2">
                      {urls.map((url, index) => (
                        <div key={index} className="flex items-center justify-between bg-gray-50 p-3 rounded-lg">
                          <span className="text-sm truncate flex-1">{url}</span>
                          <Button
                            onClick={() => removeUrl(index)}
                            variant="ghost"
                            size="sm"
                            className="text-gray-500 hover:text-red-500"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                <div className="flex gap-2">
                  <Button 
                    onClick={handleBackToWelcome}
                    variant="outline"
                    className="flex-1 border-2 border-gray-200 hover:border-black transition-colors"
                  >
                    Back
                  </Button>
                  <Button 
                    onClick={handleCrawlAndVectorize}
                    className="flex-1 bg-black text-white hover:bg-gray-800 py-6 text-lg rounded-full transition-all duration-300"
                    disabled={urls.length === 0 || !backendConnected || isCrawling}
                  >
                    {isCrawling ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Starting...
                      </>
                    ) : (
                      <>
                        <Database className="w-4 h-4 mr-2" />
                        Crawl & Vectorize
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Vectorization Progress Screen */}
        {currentScreen === 'vectorizing' && vectorizationStatus && (
          <div className="flex items-center justify-center min-h-screen -mt-8">
            <Card className="w-full max-w-2xl border-2 border-gray-200 shadow-lg animate-slide-up">
              <CardHeader className="text-center pb-2">
                <div className="mx-auto w-12 h-12 bg-black rounded-full flex items-center justify-center mb-4">
                  <Database className="w-6 h-6 text-white animate-pulse" />
                </div>
                <CardTitle className="text-2xl font-light">Vectorizing Your Content</CardTitle>
                <p className="text-gray-600 text-sm">Crawling websites and creating AI embeddings...</p>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="flex justify-between text-sm text-gray-600">
                    <span>Progress</span>
                    <span>{vectorizationStatus.processed_urls} / {vectorizationStatus.total_urls} URLs</span>
                  </div>
                  
                  <Progress 
                    value={vectorizationStatus.total_urls > 0 ? (vectorizationStatus.processed_urls / vectorizationStatus.total_urls) * 100 : 0} 
                    className="w-full"
                  />
                  
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div className="bg-gray-50 p-3 rounded-lg">
                      <div className="font-medium text-gray-700">Documents Indexed</div>
                      <div className="text-xl font-bold text-green-600">{vectorizationStatus.successful_docs}</div>
                    </div>
                    <div className="bg-gray-50 p-3 rounded-lg">
                      <div className="font-medium text-gray-700">Errors</div>
                      <div className="text-xl font-bold text-red-600">{vectorizationStatus.errors.length}</div>
                    </div>
                  </div>
                  
                  {/* Show "Continue to Chat" button when vectorization is complete or has documents */}
                  {(vectorizationStatus.completed || 
                    (vectorizationStatus.processed_urls === vectorizationStatus.total_urls && 
                     vectorizationStatus.total_urls > 0 && 
                     !vectorizationStatus.in_progress) ||
                    vectorizationStatus.successful_docs > 0) && (
                    <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-green-700">
                            {vectorizationStatus.completed ? '✅ Vectorization Complete!' : '🔄 Processing Complete!'}
                          </div>
                          <div className="text-sm text-green-600">
                            {vectorizationStatus.successful_docs} documents successfully indexed
                          </div>
                        </div>
                        <Button 
                          onClick={handleContinueToChat}
                          className="bg-green-600 hover:bg-green-700 text-white"
                        >
                          Continue to Chat
                        </Button>
                      </div>
                    </div>
                  )}
                  
                  {/* Show manual continue option if some documents are ready */}
                  {vectorizationStatus.successful_docs > 0 && vectorizationStatus.in_progress && (
                    <div className="text-center">
                      <Button 
                        onClick={handleContinueToChat}
                        variant="outline"
                        className="border-2 border-gray-300 hover:border-black"
                      >
                        Start Chatting Now ({vectorizationStatus.successful_docs} docs ready)
                      </Button>
                    </div>
                  )}
                  
                  {vectorizationStatus.errors.length > 0 && (
                    <div className="bg-red-50 p-3 rounded-lg">
                      <div className="font-medium text-red-700 mb-2">Recent Errors:</div>
                      <div className="text-sm text-red-600 max-h-20 overflow-y-auto">
                        {vectorizationStatus.errors.slice(-3).map((error, index) => (
                          <div key={index} className="mb-1">{error}</div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                
                <div className="text-center text-sm text-gray-500">
                  <p>🤖 This process creates semantic embeddings for intelligent search</p>
                  <p>⏱️ {vectorizationStatus.in_progress ? 'Processing...' : 'Processing complete!'}</p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Chat Screen */}
        {currentScreen === 'chat' && (
          <div className="max-w-4xl mx-auto animate-fade-in">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-black rounded-full flex items-center justify-center">
                  <MessageCircle className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-medium">
                    ChatBot {isDemoMode && '(Demo)'} 
                    {backendStatus?.vectorization_status.completed && !isDemoMode && '(Vectorized)'}
                  </h1>
                  <p className="text-sm text-gray-600">
                    {isDemoMode ? 'Pre-loaded vector database' : 
                     backendStatus?.vectorization_status.completed ? 
                     `${backendStatus.vectorization_status.successful_docs} documents indexed` : 
                     'Ready to chat'}
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <Button 
                  onClick={handleBackToWelcome}
                  variant="outline"
                  className="border-2 border-gray-200 hover:border-black transition-colors"
                >
                  New Chat
                </Button>
              </div>
            </div>

            <Card className="border-2 border-gray-200 shadow-lg">
              <div className="h-96 overflow-y-auto p-6 space-y-4">
                {messages.map((message) => (
                  <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-2xl ${
                      message.sender === 'user' 
                        ? 'bg-black text-white' 
                        : 'bg-gray-100 text-black'
                    }`}>
                      <p className="text-sm whitespace-pre-wrap">{message.text}</p>
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 text-black max-w-xs lg:max-w-md px-4 py-2 rounded-2xl">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              
              <div className="border-t border-gray-200 p-4">
                <div className="flex gap-2">
                  <Input
                    placeholder="Ask a question about your content..."
                    value={currentMessage}
                    onChange={(e) => setCurrentMessage(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    className="border-2 border-gray-200 focus:border-black transition-colors"
                    disabled={isLoading || !backendConnected}
                  />
                  <Button 
                    onClick={sendMessage}
                    className="bg-black text-white hover:bg-gray-800 px-4"
                    disabled={isLoading || !currentMessage.trim() || !backendConnected}
                  >
                    {isLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}