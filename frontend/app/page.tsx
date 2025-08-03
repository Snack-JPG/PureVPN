'use client'

import React, { useState, useEffect } from 'react'
import axios from 'axios'
import QRCode from 'react-qr-code'

interface VPNStatus {
  status: string
  message?: string
  progress?: number
  server_ip?: string
  connection_type?: string
  estimated_cost?: string
  active_servers?: number
  total_peers?: number
  available_slots?: number
}

interface ConfigData {
  username: string
  config: string
  filename: string
}

export default function PureVPN() {
  const [vpnStatus, setVpnStatus] = useState<VPNStatus>({ status: 'idle' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [username, setUsername] = useState('user')
  const [config, setConfig] = useState<ConfigData | null>(null)
  const [showGuide, setShowGuide] = useState(false)

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await axios.get('/api/status')
        setVpnStatus(response.data)
        
        if (response.data.status === 'connected' && !config) {
          loadUserConfig()
        }
      } catch (err) {
        console.error('Status check failed:', err)
      }
    }

    checkStatus()
    const interval = setInterval(checkStatus, 2000)
    return () => clearInterval(interval)
  }, [config])

  const connectToVPN = async () => {
    if (!username.trim()) {
      setError('Please enter a username')
      return
    }

    setLoading(true)
    setError('')
    
    try {
      await axios.post(`/api/join/${username}`)
      
      // Poll for completion
      const pollForCompletion = async () => {
        try {
          const response = await axios.get('/api/deployment-status')
          
          if (response.data.status === 'completed') {
            await loadUserConfig()
            setLoading(false)
          } else if (response.data.status === 'error') {
            setError(response.data.message)
            setLoading(false)
          } else {
            setTimeout(pollForCompletion, 1000)
          }
        } catch (err) {
          setError('Connection failed')
          setLoading(false)
        }
      }
      
      pollForCompletion()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to connect')
      setLoading(false)
    }
  }

  const disconnectFromVPN = async () => {
    try {
      await axios.post(`/api/disconnect/${username}`)
      setConfig(null)
      setVpnStatus({ status: 'idle' })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to disconnect')
    }
  }

  const loadUserConfig = async () => {
    try {
      const response = await axios.get(`/api/config/${username}`)
      setConfig(response.data)
    } catch (err) {
      console.error('Failed to load config:', err)
    }
  }

  const downloadConfig = () => {
    if (!config) return
    
    const blob = new Blob([config.config], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = config.filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const getStatusDisplay = () => {
    switch (vpnStatus.status) {
      case 'processing':
        return (
          <div className="text-blue-400 flex items-center space-x-2">
            <div className="animate-spin h-4 w-4 border-2 border-blue-400 border-t-transparent rounded-full"></div>
            <span>Connecting to Pure VPN...</span>
          </div>
        )
      case 'connected':
        return (
          <div className="text-green-400 flex items-center space-x-2">
            <div className="h-3 w-3 bg-green-400 rounded-full animate-pulse"></div>
            <span>Connected • {vpnStatus.server_ip}</span>
          </div>
        )
      case 'server_ready':
        return (
          <div className="text-blue-400 flex items-center space-x-2">
            <div className="h-3 w-3 bg-blue-400 rounded-full"></div>
            <span>Server Ready • {vpnStatus.server_ip}</span>
          </div>
        )
      case 'error':
        return (
          <div className="text-red-400 flex items-center space-x-2">
            <div className="h-3 w-3 bg-red-400 rounded-full"></div>
            <span>Error: {vpnStatus.message}</span>
          </div>
        )
      default:
        return (
          <div className="text-gray-400 flex items-center space-x-2">
            <div className="h-3 w-3 bg-gray-400 rounded-full"></div>
            <span>Ready to Connect</span>
          </div>
        )
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(120,119,198,0.1),transparent)] pointer-events-none"></div>
      
      {/* Header */}
      <header className="relative z-10 px-6 py-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="h-10 w-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Pure</h1>
                <p className="text-sm text-gray-400">Clean. Fast. Secure.</p>
              </div>
            </div>
            <button
              onClick={() => setShowGuide(!showGuide)}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
            >
              {showGuide ? 'Hide Guide' : 'Setup Guide'}
            </button>
          </div>
        </div>
      </header>

      <div className="relative z-10 px-6">
        <div className="max-w-6xl mx-auto">
          {/* Hero Section */}
          <div className="text-center mb-12">
            <h2 className="text-4xl md:text-6xl font-bold text-white mb-4">
              Pure VPN
            </h2>
            <p className="text-xl text-gray-300 mb-8 max-w-2xl mx-auto">
              No tracking. No logs. No nonsense. Just pure, private internet access in seconds.
            </p>
            <div className="flex items-center justify-center space-x-6 text-sm text-gray-400">
              <div className="flex items-center space-x-2">
                <div className="h-2 w-2 bg-green-400 rounded-full"></div>
                <span>Zero Logs</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="h-2 w-2 bg-blue-400 rounded-full"></div>
                <span>Instant Setup</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="h-2 w-2 bg-purple-400 rounded-full"></div>
                <span>Open Source</span>
              </div>
            </div>
          </div>

          {/* Setup Guide */}
          {showGuide && (
            <div className="mb-12 bg-slate-800/50 backdrop-blur-sm rounded-2xl p-8 border border-slate-700">
              <h3 className="text-2xl font-bold text-white mb-6">Quick Setup Guide</h3>
              <div className="grid md:grid-cols-2 gap-8">
                <div>
                  <h4 className="text-lg font-semibold text-blue-400 mb-4">📱 Mobile Setup</h4>
                  <ol className="space-y-3 text-gray-300">
                    <li className="flex space-x-3">
                      <span className="text-blue-400 font-mono">1.</span>
                      <span>Download WireGuard from App Store/Google Play</span>
                    </li>
                    <li className="flex space-x-3">
                      <span className="text-blue-400 font-mono">2.</span>
                      <span>Enter your username and click "Connect"</span>
                    </li>
                    <li className="flex space-x-3">
                      <span className="text-blue-400 font-mono">3.</span>
                      <span>Scan the QR code with WireGuard app</span>
                    </li>
                    <li className="flex space-x-3">
                      <span className="text-blue-400 font-mono">4.</span>
                      <span>Activate the VPN tunnel</span>
                    </li>
                  </ol>
                </div>
                <div>
                  <h4 className="text-lg font-semibold text-purple-400 mb-4">💻 Desktop Setup</h4>
                  <ol className="space-y-3 text-gray-300">
                    <li className="flex space-x-3">
                      <span className="text-purple-400 font-mono">1.</span>
                      <span>Download WireGuard for Windows/Mac/Linux</span>
                    </li>
                    <li className="flex space-x-3">
                      <span className="text-purple-400 font-mono">2.</span>
                      <span>Enter your username and click "Connect"</span>
                    </li>
                    <li className="flex space-x-3">
                      <span className="text-purple-400 font-mono">3.</span>
                      <span>Download the .conf file</span>
                    </li>
                    <li className="flex space-x-3">
                      <span className="text-purple-400 font-mono">4.</span>
                      <span>Import to WireGuard and activate</span>
                    </li>
                  </ol>
                </div>
              </div>
            </div>
          )}

          {/* Main VPN Interface */}
          <div className="grid lg:grid-cols-2 gap-8">
            {/* Control Panel */}
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-8 border border-slate-700">
              <h3 className="text-2xl font-bold text-white mb-6">Connect to Pure</h3>
              
              {/* Status */}
              <div className="mb-6 p-4 bg-slate-700/50 rounded-lg">
                {getStatusDisplay()}
              </div>

              {/* Username Input */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter your username"
                  className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={loading || vpnStatus.status === 'connected'}
                />
              </div>

              {/* Error Display */}
              {error && (
                <div className="mb-6 p-4 bg-red-900/50 border border-red-500 rounded-lg text-red-300">
                  {error}
                </div>
              )}

              {/* Connection Button */}
              {vpnStatus.status !== 'connected' ? (
                <button
                  onClick={connectToVPN}
                  disabled={loading || !username.trim()}
                  className="w-full py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-gray-600 disabled:to-gray-700 text-white font-semibold rounded-lg transition-all duration-200 transform hover:scale-105 disabled:scale-100 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <span className="flex items-center justify-center space-x-2">
                      <div className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></div>
                      <span>Connecting...</span>
                    </span>
                  ) : (
                    'Connect to Pure VPN'
                  )}
                </button>
              ) : (
                <button
                  onClick={disconnectFromVPN}
                  className="w-full py-4 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg transition-colors"
                >
                  Disconnect VPN
                </button>
              )}

              {/* Progress Bar */}
              {loading && vpnStatus.progress && (
                <div className="mt-4">
                  <div className="bg-slate-700 rounded-full h-2">
                    <div 
                      className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${vpnStatus.progress}%` }}
                    ></div>
                  </div>
                  <p className="text-sm text-gray-400 mt-2">{vpnStatus.message}</p>
                </div>
              )}
            </div>

            {/* Configuration Panel */}
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-8 border border-slate-700">
              <h3 className="text-2xl font-bold text-white mb-6">Your Configuration</h3>
              
              {config ? (
                <div className="space-y-6">
                  {/* QR Code */}
                  <div className="flex flex-col items-center">
                    <div className="bg-white p-4 rounded-xl mb-4">
                      <QRCode value={config.config} size={200} />
                    </div>
                    <p className="text-sm text-gray-400 text-center">
                      Scan with WireGuard mobile app
                    </p>
                  </div>

                  {/* Download Button */}
                  <button
                    onClick={downloadConfig}
                    className="w-full py-3 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-lg transition-colors flex items-center justify-center space-x-2"
                  >
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span>Download {config.filename}</span>
                  </button>

                  {/* Server Info */}
                  <div className="p-4 bg-slate-700/50 rounded-lg">
                    <h4 className="font-medium text-white mb-2">Connection Details</h4>
                    <div className="space-y-1 text-sm text-gray-300">
                      <div>Server: <span className="text-blue-400">{vpnStatus.server_ip}</span></div>
                      <div>Protocol: <span className="text-green-400">WireGuard</span></div>
                      <div>Encryption: <span className="text-purple-400">ChaCha20-Poly1305</span></div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12">
                  <div className="h-16 w-16 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="h-8 w-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </div>
                  <p className="text-gray-400">Connect to generate your configuration</p>
                </div>
              )}
            </div>
          </div>

          {/* Features */}
          <div className="mt-16 grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="h-12 w-12 bg-blue-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                <svg className="h-6 w-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Lightning Fast</h3>
              <p className="text-gray-400">Connect in seconds with WireGuard protocol</p>
            </div>
            <div className="text-center">
              <div className="h-12 w-12 bg-green-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                <svg className="h-6 w-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Zero Logs</h3>
              <p className="text-gray-400">We don't track, store, or monitor your activity</p>
            </div>
            <div className="text-center">
              <div className="h-12 w-12 bg-purple-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                <svg className="h-6 w-6 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Open Source</h3>
              <p className="text-gray-400">Full transparency. Audit the code yourself</p>
            </div>
          </div>

          {/* Footer */}
          <footer className="mt-16 py-8 border-t border-slate-700">
            <div className="text-center text-gray-400">
              <p>Pure VPN • Built with ❤️ for privacy</p>
            </div>
          </footer>
        </div>
      </div>
    </div>
  )
} 