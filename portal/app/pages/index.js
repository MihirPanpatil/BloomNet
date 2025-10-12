import { useState, useEffect } from 'react';
import axios from 'axios';

export default function Home() {
    const [registry, setRegistry] = useState(null);
    const [file, setFile] = useState(null); // The file to upload is stored here
    const [mart, setMart] = useState('photos');
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [systemStatus, setSystemStatus] = useState({});
    const [uploadHistory, setUploadHistory] = useState([]);
    const [uploadStatusMessage, setUploadStatusMessage] = useState(''); // For user feedback

    useEffect(() => {
        loadRegistry();
        loadSystemStatus();
        const interval = setInterval(loadSystemStatus, 10000);
        return () => clearInterval(interval);
    }, []);

    async function loadRegistry() {
        try {
            const r = await axios.get('/api/registry');
            setRegistry(r.data);
        } catch (e) {
            console.error('Registry load failed:', e);
        }
    }

    async function loadSystemStatus() {
        try{
            const services = [
                {name: 'Kernel 1', url: 'http://kernel1:8000/health'},
                {name: 'Kernel 2', url: 'http://kernel2:8000/health'},
                {name: 'Kernel 3', url: 'http://kernel3:8000/health'},
                {name: 'Photos Parent', url: 'http://photos-parent:8000/health'},
                {name: 'Research Parent', url: 'http://research-parent:8000/health'},
                {name: 'Clients Parent', url: 'http://clients-parent:8000/health'},
                {name: 'MinIO', url: 'http://minio:9000/minio/health/ready', isMinIO: true}
            ];
            const status = {};
            for(const service of services) {
                try{
                    const response = await axios.get(service.url, {timeout: 5000});
                    status[service.name] = { status: 'healthy', response: response.status };
                }catch(e){
                    console.error(`Health check failed for ${service.name}:`, e.message);
                    status[service.name] = { status: 'unhealthy', error: e.message };
                }
            }
            setSystemStatus(status);
        }catch(e){ console.error('System status load failed:', e); }
    }

    async function upload(e) {
        e.preventDefault();
        
        // **THE FIX**: Use the 'file' from the component's state, not from the event 'e'.
        if (!file) {
            setUploadStatusMessage('Please select a file first.');
            return;
        }

        setUploading(true);
        setUploadProgress(0);
        setUploadStatusMessage('Getting upload URL...');

        try {
            // 1. Get pre-signed URL from the backend API
            const response = await axios.post('/api/presign', {
                mart: mart,
                key: file.name
            });
            const { url } = response.data;
            setUploadStatusMessage('Uploading...');

            // 2. Upload the file directly to MinIO using XMLHttpRequest for progress
            const xhr = new XMLHttpRequest();
            xhr.open('PUT', url, true);
            
            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable) {
                    const percentComplete = (event.loaded / event.total) * 100;
                    setUploadProgress(Math.round(percentComplete));
                }
            };

            xhr.onload = async () => {
                if (xhr.status === 200) {
                    setUploadStatusMessage('Upload successful! Notifying kernel...');
                    // 3. Notify the kernel that the upload is complete
                    await axios.post('/api/notify', {
                        mart: mart,
                        key: file.name,
                    });
                    setUploadStatusMessage('Done!');
                    setUploadHistory(prev => [{ fileName: file.name, mart: mart, timestamp: new Date().toISOString(), status: 'success' }, ...prev]);
                } else {
                    throw new Error(`Upload to storage failed: ${xhr.statusText}`);
                }
                setUploading(false);
                setFile(null); // Clear the file input after successful upload
            };

            xhr.onerror = () => {
                throw new Error('A network error occurred during the upload.');
            };
            
            xhr.send(file);

        } catch (error) {
            console.error('Upload process failed:', error);
            setUploadStatusMessage(`Error: ${error.message}`);
            setUploading(false);
            setUploadHistory(prev => [{ fileName: file.name, mart: mart, timestamp: new Date().toISOString(), status: 'failed' }, ...prev]);
        }
    }

    const healthyCount = Object.values(systemStatus).filter(s => s.status === 'healthy').length;
    const totalServices = Object.keys(systemStatus).length;

    return (
        <div style={{
            minHeight: '100vh',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            fontFamily: 'Inter, system-ui, -apple-system, sans-serif'
        }}>
            <header style={{
                background: 'rgba(255,255,255,0.1)',
                backdropFilter: 'blur(10px)',
                borderBottom: '1px solid rgba(255,255,255,0.2)',
                padding: '1rem 2rem'
            }}>
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                    <div>
                        <h1 style={{margin: 0, color: 'white', fontSize: '2rem', fontWeight: 'bold'}}>
                            🌸 BloomNet Portal
                        </h1>
                        <p style={{margin: 0, color: 'rgba(255,255,255,0.8)', fontSize: '0.9rem'}}>
                            Fractal Data Architecture Dashboard
                        </p>
                    </div>
                    <div style={{textAlign: 'right'}}>
                        <div style={{color: 'white', fontSize: '0.8rem'}}>
                            System Status: {healthyCount}/{totalServices} services healthy
                        </div>
                        <div style={{marginTop: '0.5rem'}}>
                            {Object.entries(systemStatus).map(([name, status]) => (
                                <span key={name} style={{
                                    display: 'inline-block',
                                    marginLeft: '0.5rem',
                                    padding: '0.2rem 0.5rem',
                                    borderRadius: '0.5rem',
                                    fontSize: '0.7rem',
                                    background: status.status === 'healthy' ? '#10b981' : '#ef4444',
                                    color: 'white'
                                }}>
                                    {name}
                                </span>
                            ))}
                        </div>
                    </div>
                </div>
            </header>

            <main style={{padding: '2rem', maxWidth: '1200px', margin: '0 auto'}}>
                <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem'}}>
                    {/* Left Column - Registry & System Info */}
                    <div>
                        <div style={{
                            background: 'white',
                            borderRadius: '1rem',
                            padding: '1.5rem',
                            boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
                            marginBottom: '2rem'
                        }}>
                            <h3 style={{margin: '0 0 1rem 0', color: '#374151', display: 'flex', alignItems: 'center'}}>
                                🗂️ System Registry
                                <button
                                    onClick={loadRegistry}
                                    style={{
                                        marginLeft: 'auto',
                                        padding: '0.3rem 0.8rem',
                                        background: '#6366f1',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '0.5rem',
                                        cursor: 'pointer',
                                        fontSize: '0.8rem'
                                    }}
                                >
                                    🔄 Refresh
                                </button>
                            </h3>
                            <div style={{
                                maxHeight: '400px',
                                overflow: 'auto',
                                background: '#1f2937',
                                color: '#f9fafb',
                                padding: '1rem',
                                borderRadius: '0.5rem',
                                fontFamily: 'Monaco, monospace',
                                fontSize: '0.8rem'
                            }}>
                                {registry ? JSON.stringify(registry, null, 2) : 'Loading registry...'}
                            </div>
                        </div>

                        {/* Upload History */}
                        <div style={{
                            background: 'white',
                            borderRadius: '1rem',
                            padding: '1.5rem',
                            boxShadow: '0 10px 25px rgba(0,0,0,0.1)'
                        }}>
                            <h3 style={{margin: '0 0 1rem 0', color: '#374151'}}>📤 Upload History</h3>
                            <div style={{maxHeight: '300px', overflow: 'auto'}}>
                                {uploadHistory.length === 0 ? (
                                    <p style={{color: '#6b7280', fontStyle: 'italic'}}>No uploads yet</p>
                                ) : (
                                    uploadHistory.map((upload, index) => (
                                        <div key={index} style={{
                                            padding: '0.8rem',
                                            border: '1px solid #e5e7eb',
                                            borderRadius: '0.5rem',
                                            marginBottom: '0.5rem',
                                            background: upload.status === 'success' ? '#f0fdf4' : '#fef2f2'
                                        }}>
                                            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                                                <div>
                                                    <div style={{fontWeight: 'bold', color: '#374151'}}>
                                                        {upload.fileName}
                                                    </div>
                                                    <div style={{fontSize: '0.8rem', color: '#6b7280'}}>
                                                        {upload.mart} • {new Date(upload.timestamp).toLocaleString()}
                                                    </div>
                                                </div>
                                                <span style={{
                                                    padding: '0.2rem 0.5rem',
                                                    borderRadius: '0.3rem',
                                                    fontSize: '0.7rem',
                                                    background: upload.status === 'success' ? '#10b981' : '#ef4444',
                                                    color: 'white'
                                                }}>
                                                    {upload.status}
                                                </span>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Right Column - Upload Interface */}
                    <div>
                        <div style={{
                            background: 'white',
                            borderRadius: '1rem',
                            padding: '1.5rem',
                            boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
                            marginBottom: '2rem'
                        }}>
                            <h3 style={{margin: '0 0 1rem 0', color: '#374151'}}>📤 Upload to Data Mart</h3>

                            <form onSubmit={upload} style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
                                <div>
                                    <label style={{display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151'}}>
                                        Target Data Mart:
                                    </label>
                                    <select
                                        value={mart}
                                        onChange={e=>setMart(e.target.value)}
                                        style={{
                                            width: '100%',
                                            padding: '0.8rem',
                                            border: '2px solid #e5e7eb',
                                            borderRadius: '0.5rem',
                                            fontSize: '1rem',
                                            background: 'white'
                                        }}
                                    >
                                        <option value="photos">📸 Photos</option>
                                        <option value="research">🔬 Research</option>
                                        <option value="clients">👥 Clients</option>
                                    </select>
                                </div>

                                <div>
                                    <label style={{display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151'}}>
                                        File to Upload:
                                    </label>
                                    <div style={{
                                        padding: '1rem',
                                        border: '2px dashed #d1d5db',
                                        borderRadius: '0.5rem',
                                        textAlign: 'center',
                                        background: file ? '#f0f9ff' : '#f9fafb',
                                        cursor: 'pointer'
                                    }}>
                                        <input
                                            type="file"
                                            onChange={e=>setFile(e.target.files[0])}
                                            style={{display: 'none'}}
                                            id="file-input"
                                        />
                                        <label htmlFor="file-input" style={{cursor: 'pointer'}}>
                                            {file ? (
                                                <div>
                                                    <div style={{fontWeight: 'bold', color: '#2563eb'}}>{file.name}</div>
                                                    <div style={{fontSize: '0.8rem', color: '#6b7280'}}>
                                                        {(file.size / 1024).toFixed(1)} KB
                                                    </div>
                                                </div>
                                            ) : (
                                                <div style={{color: '#6b7280'}}>
                                                    <div style={{fontSize: '2rem', marginBottom: '0.5rem'}}>📁</div>
                                                    Click to select file or drag & drop
                                                </div>
                                            )}
                                        </label>
                                    </div>
                                </div>

                                {uploading && (
                                    <div>
                                        <div style={{marginBottom: '0.5rem', fontSize: '0.9rem', color: '#374151'}}>
                                            {uploadStatusMessage}
                                        </div>
                                        <div style={{
                                            width: '100%',
                                            height: '8px',
                                            background: '#e5e7eb',
                                            borderRadius: '4px',
                                            overflow: 'hidden'
                                        }}>
                                            <div style={{
                                                width: `${uploadProgress}%`,
                                                height: '100%',
                                                background: 'linear-gradient(90deg, #10b981, #34d399)',
                                                transition: 'width 0.3s ease'
                                            }} />
                                        </div>
                                    </div>
                                )}

                                <button
                                    type="submit"
                                    disabled={!file || uploading}
                                    style={{
                                        padding: '0.8rem 1.5rem',
                                        background: (!file || uploading) ? '#d1d5db' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '0.5rem',
                                        fontSize: '1rem',
                                        fontWeight: 'bold',
                                        cursor: (!file || uploading) ? 'not-allowed' : 'pointer',
                                        transition: 'all 0.2s ease'
                                    }}
                                >
                                    {uploading ? `🚀 Uploading... ${uploadProgress}%` : '📤 Upload File'}
                                </button>
                            </form>
                        </div>
                        {/* System Statistics */}
                        <div style={{
                            background: 'white',
                            borderRadius: '1rem',
                            padding: '1.5rem',
                            boxShadow: '0 10px 25px rgba(0,0,0,0.1)'
                        }}>
                            <h3 style={{margin: '0 0 1rem 0', color: '#374151'}}>📊 System Statistics</h3>
                            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem'}}>
                                <div style={{textAlign: 'center', padding: '1rem', background: '#f8fafc', borderRadius: '0.5rem'}}>
                                    <div style={{fontSize: '2rem', fontWeight: 'bold', color: '#6366f1'}}>
                                        {registry?.marts ? Object.keys(registry.marts).length : 0}
                                    </div>
                                    <div style={{color: '#6b7280', fontSize: '0.9rem'}}>Active Marts</div>
                                </div>
                                <div style={{textAlign: 'center', padding: '1rem', background: '#f8fafc', borderRadius: '0.5rem'}}>
                                    <div style={{fontSize: '2rem', fontWeight: 'bold', color: '#10b981'}}>
                                        {uploadHistory.filter(u => u.status === 'success').length}
                                    </div>
                                    <div style={{color: '#6b7280', fontSize: '0.9rem'}}>Successful Uploads</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
