import axios from 'axios'

export default async function handler(req, res) {
    if (req.method !== 'GET') {
        return res.status(405).json({ error: 'Method not allowed' })
    }

    try {
        // Forward the request to kernel1 with authentication using Docker network
        const response = await axios.get('http://kernel1:8000/registry', {
            timeout: 5000
        })

        res.status(200).json(response.data)
    } catch (error) {
        console.error('Registry API error:', error.message)

        if (error.response) {
            // Kernel returned an error
            res.status(error.response.status).json({
                error: error.response.data.detail || 'Kernel registry error'
            })
        } else {
            // Network or other error
            res.status(500).json({
                error: 'Failed to connect to kernel registry'
            })
        }
    }
}
