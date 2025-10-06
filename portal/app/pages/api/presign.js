import axios from 'axios'

export default async function handler(req,res){
    // Use Docker network instead of external port mapping
    const KERNEL = process.env.KERNEL_API || 'http://kernel1:8000'
    try{
        const r = await axios.post(`${KERNEL}/presign_upload`, req.body, {
            timeout: 10000
        })
        res.status(200).json(r.data)
    }catch(e){
        console.error('Presign error:', e.message)
        if (e.response) {
            res.status(e.response.status).json({
                error: e.response.data.detail || 'Presign failed'
            })
        } else {
            res.status(500).json({error: 'Failed to connect to kernel'})
        }
    }
}
    
